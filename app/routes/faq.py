from fastapi import APIRouter, HTTPException, Depends, status, Header, Request
from pydantic import BaseModel
from typing import List, Optional
from app.services.rag_service import RAGService
from app.services.chatbot_safety import safety
from app.services.greeting_service import GreetingService
from app.services.memory_service import MemoryService
from app.models.analytics import Analytics
from app.utils.auth import decode_token
from app.models.faq import FAQ
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/faq", tags=["FAQ"])

# ========== SCHEMAS ==========

class SearchQuery(BaseModel):
    query: str

class FAQResponse(BaseModel):
    _id: Optional[str] = None
    question: str
    answer: str
    category: Optional[str] = None
    id: Optional[str] = None

class QueryMetadata(BaseModel):
    complexity: float
    word_count: int
    char_count: int
    is_vague: bool
    has_technical_terms: bool

class AnalyticsMetadata(BaseModel):
    faq_matched: bool
    similarity_score: float
    persona_used: str
    persona_confidence: float
    sentiment: str
    sentiment_score: float
    fallback_ai_used: bool
    misunderstanding_risk: float
    misunderstanding_indicators: List[str]
    should_request_clarification: bool
    query_metadata: QueryMetadata
    timestamp: str

class SearchResponse(BaseModel):
    question: str
    answer: str
    relevantFAQs: List[FAQResponse]
    grounding_confidence: Optional[float] = None
    is_grounded: Optional[bool] = None
    intent: Optional[str] = None
    analytics: Optional[AnalyticsMetadata] = None

class GreetingResponse(BaseModel):
    greeting: str
    personalized: bool
    username: Optional[str] = None
    persona: str
    interaction_count: int
    last_seen: Optional[str] = None
    discovery_question: Optional[str] = None

class AnalyticsStatsResponse(BaseModel):
    total_queries: int
    avg_similarity_score: float
    faq_match_rate: float
    ai_fallback_rate: float
    avg_misunderstanding_risk: float
    avg_grounding_confidence: float
    avg_response_quality: float

class SentimentDistributionResponse(BaseModel):
    positive: int
    neutral: int
    negative: int
    frustrated: int

class IntentData(BaseModel):
    intent: str
    count: int
    percentage: float

# ========== DEPENDENCIES ==========

rag_service = RAGService()
memory_service = MemoryService()
greeting_service = GreetingService(memory_service)

def get_current_user_id(authorization: str = Header(None)):
    """Extract user_id from Bearer token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing"
        )
    
    token = authorization.replace("Bearer ", "")
    payload = decode_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    return payload.get("sub")

# ========== ROUTES ==========

@router.get("/greeting")
async def get_greeting(request: Request, authorization: str = Header(None)):
    """
    Get personalized greeting using Memory System
    
    Protocol:
    1. Check if user is authenticated (has Bearer token)
    2. If authenticated: retrieve user memory and personalize greeting
    3. If anonymous: return generic greeting
    
    Returns personalized greeting with user interaction history
    """
    try:
        user_id = None
        user_memory = None
        persona = "friendly"  # Default persona
        
        # Try to extract user from token if available
        if authorization and authorization.startswith("Bearer "):
            try:
                token = authorization.replace("Bearer ", "")
                payload = decode_token(token)
                if payload:
                    user_id = payload.get("sub")
                    # Get user memory for personalization
                    user_memory = await memory_service.get_user_memory(user_id)
                    # Get user's preferred persona from memory
                    if user_memory and user_memory.get("preferences"):
                        persona = user_memory["preferences"].get("tone", "friendly")
            except:
                pass  # Continue with anonymous greeting
        
        # Generate greeting
        greeting_data = await greeting_service.generate_greeting(
            user_id=user_id,
            user_memory=user_memory,
            persona=persona
        )
        
        return GreetingResponse(
            greeting=greeting_data["greeting"],
            personalized=greeting_data["personalized"],
            username=greeting_data.get("username"),
            persona=greeting_data["persona"],
            interaction_count=greeting_data.get("interaction_count", 0),
            last_seen=greeting_data.get("last_seen"),
            discovery_question=greeting_data.get("discovery_question")
        )
    
    except Exception as e:
        logger.error(f"Greeting error: {str(e)}")
        # Fallback to generic greeting
        return GreetingResponse(
            greeting="Hello! How can I help you today?",
            personalized=False,
            username=None,
            persona="friendly",
            interaction_count=0,
            last_seen=None
        )

@router.get("/all")
async def get_all_faqs():
    """
    Get all FAQs without authentication
    Used for populating public FAQ list on landing page
    """
    try:
        faqs = await FAQ.find_all()
        return {"faqs": faqs}
    except Exception as e:
        logger.error(f"Error fetching FAQs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching FAQs: {str(e)}"
        )

@router.post("/search")
async def search_faqs(query: SearchQuery, request: Request):
    """
    Search FAQs using RAG with Gemini 3.0 + Safety Compliance:
    1. Validate query (spam, abuse, injection, malicious intent)
    2. Search MongoDB for matching FAQs
    3. Send to Gemini for answer synthesis
    4. Return synthesized answer + relevant FAQs
    """
    try:
        if not query.query.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query cannot be empty"
            )
        
        # Get user ID from IP or session (for safety tracking)
        user_id = request.client.host if request.client else "anonymous"
        
        # Validate query for safety & compliance
        is_valid, error_message = await safety.validate_query(user_id, query.query)
        
        if not is_valid:
            logger.warning(f"Query blocked for user {user_id}: {error_message}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_message
            )

        # Call RAG service to process query
        result = await rag_service.search_and_generate(query.query)
        
        # Detect user intent
        intent, _ = rag_service.semantic_search.detect_intent(query.query)
        
        # Calculate response quality score based on grounding confidence
        response_quality = result.get("grounding_confidence", 0.0)
        
        # Record interaction in memory and analytics (if user_id available from token)
        if user_id != "anonymous":
            try:
                await memory_service.update_interaction(
                    user_id=user_id,
                    topic=intent or "general",
                    query=query.query,
                    response_quality=response_quality
                )
                
                # Record analytics to database
                await rag_service.record_analytics(
                    user_id=user_id,
                    query=query.query,
                    intent=intent or "general",
                    result=result
                )
            except Exception as e:
                logger.warning(f"Could not record interaction/analytics: {str(e)}")

        return SearchResponse(
            question=query.query,
            answer=result["answer"],
            relevantFAQs=result["relevant_faqs"],
            grounding_confidence=result.get("grounding_confidence"),
            is_grounded=result.get("is_grounded"),
            intent=intent,
            analytics=result.get("analytics")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search error: {str(e)}"
        )

@router.post("/add")
async def add_faq(
    question: str,
    answer: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Admin endpoint: Add new FAQ
    Automatically generates embedding for vector search
    """
    try:
        # Generate embedding for the question
        embedding = await rag_service.get_embedding(question)

        # Create FAQ document
        result = await FAQ.insert(question, answer, embedding)
        
        return {"success": True, "faq_id": str(result.inserted_id)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding FAQ: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error adding FAQ: {str(e)}"
        )

@router.delete("/{faq_id}")
async def delete_faq(
    faq_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """
    Admin endpoint: Delete FAQ
    """
    try:
        result = await FAQ.delete_by_id(faq_id)
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="FAQ not found"
            )
        return {"success": True, "message": "FAQ deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting FAQ: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting FAQ: {str(e)}"
        )

# ========== ANALYTICS ENDPOINTS ==========

@router.get("/analytics/stats")
async def get_analytics_stats(authorization: str = Header(None)):
    """
    Get aggregated analytics stats for current user
    Requires authentication
    
    Returns:
    {
        "total_queries": int,
        "avg_similarity_score": float,
        "faq_match_rate": float,
        "ai_fallback_rate": float,
        "avg_misunderstanding_risk": float,
        "avg_grounding_confidence": float,
        "avg_response_quality": float
    }
    """
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization required"
            )
        
        token = authorization.replace("Bearer ", "")
        payload = decode_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        user_id = payload.get("sub")
        
        stats = await Analytics.get_aggregate_stats(user_id)
        return AnalyticsStatsResponse(**stats) if stats else AnalyticsStatsResponse(
            total_queries=0,
            avg_similarity_score=0.0,
            faq_match_rate=0.0,
            ai_fallback_rate=0.0,
            avg_misunderstanding_risk=0.0,
            avg_grounding_confidence=0.0,
            avg_response_quality=0.0
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching analytics stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching analytics: {str(e)}"
        )

@router.get("/analytics/sentiment")
async def get_sentiment_distribution(authorization: str = Header(None)):
    """
    Get sentiment distribution of user's queries
    Requires authentication
    
    Returns sentiment counts and percentages
    """
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization required"
            )
        
        token = authorization.replace("Bearer ", "")
        payload = decode_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        user_id = payload.get("sub")
        
        distribution = await Analytics.get_sentiment_distribution(user_id)
        return SentimentDistributionResponse(**distribution) if distribution else SentimentDistributionResponse(
            positive=0, neutral=0, negative=0, frustrated=0
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching sentiment distribution: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching sentiment data: {str(e)}"
        )

@router.get("/analytics/intents")
async def get_top_intents(
    limit: int = 5,
    authorization: str = Header(None)
):
    """
    Get top intents/topics user has asked about
    Requires authentication
    
    Query params:
    - limit: Max intents to return (default 5)
    
    Returns list of intents with counts
    """
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization required"
            )
        
        token = authorization.replace("Bearer ", "")
        payload = decode_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        user_id = payload.get("sub")
        
        intents = await Analytics.get_top_intents(user_id, limit=limit)
        return {"intents": intents, "count": len(intents)}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching top intents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching intents: {str(e)}"
        )

@router.get("/analytics/history")
async def get_analytics_history(
    limit: int = 50,
    skip: int = 0,
    authorization: str = Header(None)
):
    """
    Get user's analytics history (recent queries)
    Requires authentication
    
    Query params:
    - limit: Records per page (default 50)
    - skip: Records to skip for pagination (default 0)
    
    Returns paginated list of analytics records
    """
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization required"
            )
        
        token = authorization.replace("Bearer ", "")
        payload = decode_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        user_id = payload.get("sub")
        
        history = await Analytics.get_user_analytics(user_id, limit=limit, skip=skip)
        return {"analytics": history, "count": len(history), "limit": limit, "skip": skip}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching analytics history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching history: {str(e)}"
        )