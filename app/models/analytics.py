from app.database import get_database
from typing import Dict, Any, Optional, List
from bson import ObjectId
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Analytics:
    """
    Analytics Model for storing chatbot response metadata
    
    Fields:
    - user_id: str (user who made the query)
    - query: str (user's query)
    - intent: str (detected intent)
    - faq_matched: bool
    - similarity_score: float (0.0-1.0)
    - persona_used: str
    - sentiment: str
    - sentiment_score: float
    - fallback_ai_used: bool (whether Gemini was used)
    - misunderstanding_risk: float
    - grounding_confidence: float
    - is_grounded: bool
    - response_quality: float
    - created_at: datetime
    """

    collection_name = "analytics"

    @classmethod
    def get_collection(cls):
        """Get MongoDB collection"""
        db = get_database()
        collection = db[cls.collection_name]
        # Create indexes
        collection.create_index("user_id")
        collection.create_index("created_at")
        collection.create_index([("user_id", 1), ("created_at", -1)])
        return collection

    @classmethod
    async def record_interaction(
        cls,
        user_id: str,
        query: str,
        intent: str,
        analytics_metadata: Dict[str, Any],
        grounding_confidence: Optional[float] = None,
        is_grounded: Optional[bool] = None,
        response_quality: Optional[float] = None
    ) -> str:
        """
        Record analytics for a query/response interaction
        
        Args:
            user_id: User identifier
            query: User's query text
            intent: Detected intent from semantic search
            analytics_metadata: Dict with faq_matched, similarity_score, persona, sentiment, etc.
            grounding_confidence: Answer grounding confidence (0.0-1.0)
            is_grounded: Whether answer is grounded in facts
            response_quality: Quality score of response
        
        Returns:
            String ID of inserted document
        """
        try:
            collection = cls.get_collection()
            
            document = {
                "user_id": user_id,
                "query": query[:500],  # Store first 500 chars to save space
                "intent": intent,
                
                # From analytics metadata
                "faq_matched": analytics_metadata.get("faq_matched", False),
                "similarity_score": analytics_metadata.get("similarity_score", 0.0),
                "persona_used": analytics_metadata.get("persona_used", "neutral"),
                "persona_confidence": analytics_metadata.get("persona_confidence", 0.0),
                "sentiment": analytics_metadata.get("sentiment", "neutral"),
                "sentiment_score": analytics_metadata.get("sentiment_score", 0.0),
                "fallback_ai_used": analytics_metadata.get("fallback_ai_used", False),
                
                # Misunderstanding detection
                "misunderstanding_risk": analytics_metadata.get("misunderstanding_risk", 0.0),
                "misunderstanding_indicators": analytics_metadata.get("misunderstanding_indicators", []),
                "should_request_clarification": analytics_metadata.get("should_request_clarification", False),
                
                # Query metadata
                "query_complexity": analytics_metadata.get("query_metadata", {}).get("complexity", 0.0),
                "query_word_count": analytics_metadata.get("query_metadata", {}).get("word_count", 0),
                "is_vague_query": analytics_metadata.get("query_metadata", {}).get("is_vague", False),
                "has_technical_terms": analytics_metadata.get("query_metadata", {}).get("has_technical_terms", False),
                
                # FAQ source
                "faq_source": analytics_metadata.get("faq_source"),
                
                # Grounding info
                "grounding_confidence": grounding_confidence,
                "is_grounded": is_grounded,
                
                # Response quality
                "response_quality": response_quality,
                
                # Timestamp
                "created_at": datetime.utcnow()
            }
            
            result = collection.insert_one(document)
            logger.info(f"Recorded analytics for user {user_id}: {str(result.inserted_id)}")
            return str(result.inserted_id)
        
        except Exception as e:
            logger.error(f"Error recording analytics: {str(e)}")
            return None

    @classmethod
    async def get_user_analytics(
        cls,
        user_id: str,
        limit: int = 50,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get analytics records for a user
        
        Args:
            user_id: User identifier
            limit: Max records to return
            skip: Records to skip (for pagination)
        
        Returns:
            List of analytics documents
        """
        try:
            collection = cls.get_collection()
            
            records = collection.find(
                {"user_id": user_id}
            ).sort("created_at", -1).skip(skip).limit(limit)
            
            analytics_list = []
            for record in records:
                record["id"] = str(record["_id"])
                analytics_list.append(record)
            
            return analytics_list
        
        except Exception as e:
            logger.error(f"Error fetching user analytics: {str(e)}")
            return []

    @classmethod
    async def get_aggregate_stats(
        cls,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get aggregated analytics stats for a user
        
        Returns:
        {
            "total_queries": int,
            "avg_similarity_score": float,
            "faq_match_rate": float,
            "ai_fallback_rate": float,
            "avg_misunderstanding_risk": float,
            "sentiment_distribution": {...},
            "top_intents": [...]
        }
        """
        try:
            collection = cls.get_collection()
            
            pipeline = [
                {"$match": {"user_id": user_id}},
                {
                    "$group": {
                        "_id": "$user_id",
                        "total_queries": {"$sum": 1},
                        "avg_similarity_score": {"$avg": "$similarity_score"},
                        "faq_matched_count": {"$sum": {"$cond": ["$faq_matched", 1, 0]}},
                        "ai_fallback_count": {"$sum": {"$cond": ["$fallback_ai_used", 1, 0]}},
                        "avg_misunderstanding_risk": {"$avg": "$misunderstanding_risk"},
                        "avg_grounding_confidence": {"$avg": "$grounding_confidence"},
                        "avg_response_quality": {"$avg": "$response_quality"}
                    }
                }
            ]
            
            result = list(collection.aggregate(pipeline))
            
            if not result:
                return {
                    "total_queries": 0,
                    "avg_similarity_score": 0.0,
                    "faq_match_rate": 0.0,
                    "ai_fallback_rate": 0.0,
                    "avg_misunderstanding_risk": 0.0,
                    "avg_grounding_confidence": 0.0,
                    "avg_response_quality": 0.0
                }
            
            stats = result[0]
            total = stats.get("total_queries", 1)
            
            return {
                "total_queries": stats.get("total_queries", 0),
                "avg_similarity_score": round(stats.get("avg_similarity_score", 0.0), 2),
                "faq_match_rate": round(stats.get("faq_matched_count", 0) / total, 2),
                "ai_fallback_rate": round(stats.get("ai_fallback_count", 0) / total, 2),
                "avg_misunderstanding_risk": round(stats.get("avg_misunderstanding_risk", 0.0), 2),
                "avg_grounding_confidence": round(stats.get("avg_grounding_confidence", 0.0), 2),
                "avg_response_quality": round(stats.get("avg_response_quality", 0.0), 2)
            }
        
        except Exception as e:
            logger.error(f"Error fetching aggregate stats: {str(e)}")
            return {}

    @classmethod
    async def get_sentiment_distribution(
        cls,
        user_id: str
    ) -> Dict[str, int]:
        """
        Get sentiment distribution for user's queries
        
        Returns:
        {
            "positive": int,
            "neutral": int,
            "negative": int,
            "frustrated": int
        }
        """
        try:
            collection = cls.get_collection()
            
            pipeline = [
                {"$match": {"user_id": user_id}},
                {
                    "$group": {
                        "_id": "$sentiment",
                        "count": {"$sum": 1}
                    }
                }
            ]
            
            result = list(collection.aggregate(pipeline))
            
            distribution = {
                "positive": 0,
                "neutral": 0,
                "negative": 0,
                "frustrated": 0
            }
            
            for item in result:
                sentiment = item.get("_id", "neutral")
                if sentiment in distribution:
                    distribution[sentiment] = item.get("count", 0)
            
            return distribution
        
        except Exception as e:
            logger.error(f"Error fetching sentiment distribution: {str(e)}")
            return {}

    @classmethod
    async def get_top_intents(
        cls,
        user_id: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get most common intents for user
        
        Returns:
        [
            {"intent": "maintenance", "count": 15, "percentage": 35.7},
            ...
        ]
        """
        try:
            collection = cls.get_collection()
            
            pipeline = [
                {"$match": {"user_id": user_id}},
                {
                    "$group": {
                        "_id": "$intent",
                        "count": {"$sum": 1}
                    }
                },
                {"$sort": {"count": -1}},
                {"$limit": limit}
            ]
            
            result = list(collection.aggregate(pipeline))
            
            # Calculate total for percentages
            total = sum(item.get("count", 0) for item in result)
            
            intents = []
            for item in result:
                intent_data = {
                    "intent": item.get("_id", "unknown"),
                    "count": item.get("count", 0),
                    "percentage": round((item.get("count", 0) / total * 100), 1) if total > 0 else 0
                }
                intents.append(intent_data)
            
            return intents
        
        except Exception as e:
            logger.error(f"Error fetching top intents: {str(e)}")
            return []

    @classmethod
    async def delete_old_analytics(cls, days: int = 90) -> int:
        """
        Delete analytics records older than specified days
        (for data cleanup and privacy)
        """
        try:
            collection = cls.get_collection()
            cutoff_date = datetime.utcnow() - __import__('datetime').timedelta(days=days)
            
            result = collection.delete_many({"created_at": {"$lt": cutoff_date}})
            logger.info(f"Deleted {result.deleted_count} old analytics records")
            return result.deleted_count
        
        except Exception as e:
            logger.error(f"Error deleting old analytics: {str(e)}")
            return 0
