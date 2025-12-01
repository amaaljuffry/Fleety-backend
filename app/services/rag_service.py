import os
import json
from typing import List, Dict, Any, Optional
import logging
import google.generativeai as genai
from app.services.semantic_search import SemanticSearch
from app.services.analytics import ChatbotAnalytics
from app.services.fleety_assistant_prompt import FleetyAssistantPrompt
from app.models.analytics import Analytics

logger = logging.getLogger(__name__)

class RAGService:
    """
    RAG (Retrieval-Augmented Generation) Service using Google Gemini 3.0
    Enhanced with semantic search and answer grounding
    
    Flow:
    1. Semantic search FAQs (handles synonyms, typos, intent)
    2. Top 5 FAQs → Gemini 3.0 → Final Answer with context
    3. Ground answer in facts (no hallucinations)
    4. Validate data freshness
    """

    def __init__(self):
        # Gemini API configuration
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = None
        
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not set. Gemini features will be disabled.")
        else:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel("gemini-3.0-pro")
                logger.info("✅ Gemini 3.0 Pro model initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini model: {str(e)}")
                self.model = None
        
        # Initialize semantic search
        self.semantic_search = SemanticSearch()
        
        # Initialize analytics
        self.analytics = ChatbotAnalytics()
        
        # MongoDB connection
        from app.models.faq import FAQ
        self.faq_model = FAQ

    async def _is_gemini_available(self) -> bool:
        """Check if Gemini API is available"""
        return self.api_key is not None

    async def get_embedding(self, text: str) -> List[float]:
        """
        Gemini doesn't require separate embeddings.
        Using keyword search instead.
        """
        return None

    def classify_query_intent(self, query: str) -> str:
        """
        Classify user query intent to prevent wrong answer matching.
        
        Args:
            query: User's query string
            
        Returns:
            Intent category string
        """
        query_lower = query.lower()
        
        # Registration/Account creation intent
        if any(term in query_lower for term in ['register', 'sign up', 'create account', 'new account', 'get started']):
            return 'registration'
        
        # Password/Login issues
        if any(term in query_lower for term in ['password', 'login', 'forgot', 'reset password', 'locked out', 'can\'t login']):
            return 'password_help'
        
        # Vehicle management
        if any(term in query_lower for term in ['vehicle', 'add vehicle', 'car', 'truck', 'fleet', 'register vehicle']):
            return 'vehicle_management'
        
        # Maintenance queries
        if any(term in query_lower for term in ['maintenance', 'service', 'repair', 'oil change', 'reminder']):
            return 'maintenance'
        
        # Fuel/cost analysis
        if any(term in query_lower for term in ['fuel', 'efficiency', 'cost', 'consumption', 'analytics']):
            return 'fuel_tracking'
        
        return 'general'

    def should_override_similar_matches(
        self,
        query: str,
        matches: List[Dict[str, Any]],
        query_intent: str
    ) -> bool:
        """
        Override semantic search when it returns irrelevant but high-scoring matches.
        
        Examples:
        - Registration query but password reset FAQ has high similarity
        - Vehicle question but maintenance FAQ scored higher
        
        Args:
            query: Original user query
            matches: List of FAQ matches from semantic search
            query_intent: Classified intent from classify_query_intent()
            
        Returns:
            True if override needed (ignore top matches), False otherwise
        """
        if not matches or len(matches) < 2:
            return False
        
        top_match = matches[0].get('question', '').lower()
        query_lower = query.lower()
        
        # CRITICAL: Registration query but password reset matched
        if query_intent == 'registration':
            if any(term in top_match for term in ['password', 'forgot', 'reset']):
                logger.warning(
                    f"Intent override: Registration query but password FAQ matched. "
                    f"Query: '{query}' | Matched FAQ: '{matches[0].get('question')}'"
                )
                return True
        
        # Password help query but registration matched
        if query_intent == 'password_help':
            if any(term in top_match for term in ['register', 'sign up', 'create account']):
                logger.warning(
                    f"Intent override: Password query but registration FAQ matched. "
                    f"Query: '{query}' | Matched FAQ: '{matches[0].get('question')}'"
                )
                return True
        
        # Vehicle query but maintenance matched
        if query_intent == 'vehicle_management':
            if any(term in top_match for term in ['maintenance', 'service', 'repair']):
                logger.warning(
                    f"Intent override: Vehicle query but maintenance FAQ matched. "
                    f"Query: '{query}' | Matched FAQ: '{matches[0].get('question')}'"
                )
                return True
        
        return False

    def get_direct_answer_template(self, query_intent: str, query: str) -> Optional[str]:
        """
        Get a direct answer template for common queries without needing to search FAQs.
        
        Args:
            query_intent: Classified intent
            query: Original query
            
        Returns:
            Direct answer template or None if should proceed with FAQ search
        """
        # For registration queries, provide direct answer
        if query_intent == 'registration':
            return """To register for Fleety Fleet Management:

1. Visit our website and click 'Start Free Trial' or 'Sign Up'
2. Enter your company information (company name, email)
3. Create a secure password
4. Verify your email address by clicking the link sent to your inbox
5. Set up your fleet profile and add your first vehicle

Once registered, you can immediately start:
- Adding and managing vehicles
- Setting up maintenance schedules
- Tracking fuel efficiency
- Generating fleet reports

For login issues, use the 'Forgot Password' option on the login page."""
        
        # For password reset queries, provide direct answer
        if query_intent == 'password_help':
            return """To reset your password:

1. Go to the Fleety login page
2. Click 'Forgot Password'
3. Enter the email associated with your account
4. Check your email for a reset link (check spam folder if needed)
5. Click the link and follow the instructions to create a new password
6. Use your new password to log in

If you don't receive the email within 5 minutes, please contact support@fleety.com"""
        
        return None


    async def _keyword_search_faqs(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search FAQs using semantic search + intent matching
        Handles synonyms, typos, and intent detection
        """
        try:
            all_faqs = await self.faq_model.find_all()
            
            if not all_faqs:
                logger.warning("No FAQs found in database")
                return []
            
            # Use semantic search for intelligent matching
            semantic_results = self.semantic_search.search_faqs(
                query=query,
                faqs=all_faqs,
                top_k=top_k,
                threshold=0.3  # Lower threshold for broader matches
            )
            
            # Validate freshness of results
            validated_results = []
            for faq, similarity_score in semantic_results:
                is_fresh = self.semantic_search.validate_answer_freshness(faq)
                if is_fresh:
                    faq['similarity_score'] = similarity_score
                    validated_results.append(faq)
                else:
                    logger.warning(f"Skipping outdated FAQ: {faq.get('question', '')}")
            
            logger.info(f"Semantic search returned {len(validated_results)} relevant FAQs")
            return validated_results

        except Exception as e:
            logger.error(f"Error in semantic search: {str(e)}")
            return []


    async def search_relevant_faqs(
        self,
        query: str,
        query_embedding: List[float] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search MongoDB for FAQs using keyword search
        """
        try:
            # Use keyword search
            logger.info(f"Searching FAQs for query: {query}")
            return await self._keyword_search_faqs(query, top_k)

        except Exception as e:
            logger.error(f"Error searching FAQs: {str(e)}")
            return []

    async def generate_llm_answer(
        self,
        query: str,
        relevant_faqs: List[Dict[str, Any]],
        intent: Optional[str] = None,
        user_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Use Gemini 3.0 to synthesize an answer with Fleety domain expertise
        Falls back to best matching FAQ answer if Gemini unavailable
        
        Args:
            query: User's query
            relevant_faqs: List of relevant FAQ results
            intent: Detected user intent (for context)
            user_context: User data for personalization
        """
        try:
            if not await self._is_gemini_available() or not self.model:
                # Fallback: return just the best matching FAQ answer
                if relevant_faqs and len(relevant_faqs) > 0:
                    best_match = relevant_faqs[0]
                    answer = best_match.get('answer', 'No answer available.')
                    return answer
                return "I couldn't find relevant FAQs. Please contact support."
            
            # Build context from relevant FAQs
            context = "\n\n".join([
                f"Q: {faq.get('question', '')}\nA: {faq.get('answer', '')}"
                for faq in relevant_faqs
            ])

            # Get system prompt with domain expertise and context
            system_prompt = FleetyAssistantPrompt.get_contextual_prompt(intent or "general")
            
            # Build enhanced user prompt
            user_prompt = f"""Based on the following FAQs and your domain expertise, answer the user's question following your guidelines.

Context FAQs:
{context}

User Question: {query}

Provide a helpful, specific response that:
1. Directly answers their question
2. Includes step-by-step guidance if applicable
3. Offers proactive next steps or follow-up options
4. Uses clear, professional language"""

            # Call Gemini API with system prompt and user prompt
            response = self.model.generate_content(
                f"{system_prompt}\n\n{user_prompt}"
            )
            
            answer = response.text
            return answer.strip()

        except Exception as e:
            logger.error(f"Error generating answer with Gemini: {str(e)}")
            # Fallback: return best matching FAQ answer only
            if relevant_faqs and len(relevant_faqs) > 0:
                best_match = relevant_faqs[0]
                answer = best_match.get('answer', 'No answer available.')
                return answer
            return "I couldn't generate an answer. Please contact support."

    def _validate_context_appropriateness(
        self,
        query: str,
        relevant_faqs: List[Dict[str, Any]],
        similarity_score: float
    ) -> bool:
        """
        Validate that the best matching FAQ is logically appropriate for the query.
        Prevents illogical matches like "How to register?" → "Password reset instructions"
        
        Args:
            query: User's original query
            relevant_faqs: List of matched FAQs
            similarity_score: Similarity score of top match
            
        Returns:
            True if the match is contextually appropriate, False otherwise
        """
        if not relevant_faqs:
            return False
        
        # Define domain-specific validation rules
        query_lower = query.lower()
        top_faq = relevant_faqs[0]
        faq_question = top_faq.get('question', '').lower()
        
        # Keywords that indicate different domains
        registration_keywords = ['register', 'sign up', 'create account', 'account creation']
        password_keywords = ['password', 'forgot', 'reset', 'forgot password']
        vehicle_keywords = ['vehicle', 'add vehicle', 'car', 'truck', 'fleet']
        maintenance_keywords = ['maintenance', 'service', 'repair', 'oil change']
        fuel_keywords = ['fuel', 'efficiency', 'cost', 'consumption']
        
        # Check for domain mismatch
        is_registration_query = any(kw in query_lower for kw in registration_keywords)
        is_password_query = any(kw in query_lower for kw in password_keywords)
        is_vehicle_query = any(kw in query_lower for kw in vehicle_keywords)
        is_maintenance_query = any(kw in query_lower for kw in maintenance_keywords)
        is_fuel_query = any(kw in query_lower for kw in fuel_keywords)
        
        is_password_answer = any(kw in faq_question for kw in password_keywords)
        is_registration_answer = any(kw in faq_question for kw in registration_keywords)
        is_vehicle_answer = any(kw in faq_question for kw in vehicle_keywords)
        
        # Prevent illogical combinations
        if is_registration_query and is_password_answer:
            logger.warning(f"Context mismatch: Registration query matched password FAQ. Query: {query}")
            return False
        
        if is_password_query and is_registration_answer:
            logger.warning(f"Context mismatch: Password query matched registration FAQ. Query: {query}")
            return False
        
        # Lower confidence threshold for domain mismatches
        if (is_vehicle_query and not is_vehicle_answer and similarity_score < 0.5):
            logger.warning(f"Context mismatch: Vehicle query has low confidence match. Query: {query}")
            return False
        
        return True

    async def search_and_generate(self, query: str) -> Dict[str, Any]:
        """
        Complete RAG pipeline with semantic search + answer grounding + analytics:
        1. Semantic search MongoDB for relevant FAQs (handles synonyms, intent)
        2. Validate FAQ freshness (no outdated data)
        3. Ground answer in FAQ knowledge base
        4. Generate answer with Gemini 3.0 (or best FAQ match)
        5. Track comprehensive analytics metadata
        
        Returns:
            {
                "answer": "grounded, synthesized answer",
                "relevant_faqs": [list of top FAQs],
                "grounding_confidence": float (0.0-1.0),
                "is_grounded": bool,
                "analytics": {...analytics metadata...}
            }
        """
        try:
            logger.info(f"Processing query: {query}")
            
            # Step 0: Classify query intent for intelligent routing
            query_intent = self.classify_query_intent(query)
            logger.info(f"Query intent classified as: {query_intent}")
            
            # Step 0.5: Check if we have a direct answer template (registration, password, etc.)
            direct_answer = self.get_direct_answer_template(query_intent, query)
            if direct_answer:
                logger.info(f"Using direct answer template for {query_intent} query")
                analytics = self.analytics.build_metadata(
                    query=query,
                    answer=direct_answer,
                    faq_matched=False,
                    similarity_score=1.0,
                    used_gemini=False,
                    matched_faq=None
                )
                
                return {
                    "answer": direct_answer,
                    "relevant_faqs": [],
                    "grounding_confidence": 1.0,
                    "is_grounded": True,
                    "analytics": analytics
                }
            
            # Step 1: Semantic search for relevant FAQs
            relevant_faqs = await self._keyword_search_faqs(query, top_k=5)
            
            # Determine if FAQ was matched and get similarity score
            faq_matched = len(relevant_faqs) > 0
            similarity_score = relevant_faqs[0].get('similarity_score', 0.0) if faq_matched else 0.0
            
            # Step 1.5: Check if we need to override semantic search
            if faq_matched and self.should_override_similar_matches(query, relevant_faqs, query_intent):
                logger.info(f"Overriding semantic search match due to intent mismatch. Intent: {query_intent}")
                # Fall back to direct answer or clarification
                relevant_faqs = []
                faq_matched = False
                similarity_score = 0.0
            
            # Validate context appropriateness (prevent illogical matches)
            if faq_matched:
                is_contextually_appropriate = self._validate_context_appropriateness(
                    query=query,
                    relevant_faqs=relevant_faqs,
                    similarity_score=similarity_score
                )
                
                if not is_contextually_appropriate:
                    logger.warning(f"Context mismatch detected. Using clarification instead of forced match. Query: {query}")
                    clarification_answer = (
                        f"I want to make sure I understand your question correctly. You asked about '{query}'. "
                        f"Could you provide more details so I can give you accurate information? "
                        f"For example, are you trying to [register/add a vehicle/track maintenance/etc.]?"
                    )
                    
                    analytics = self.analytics.build_metadata(
                        query=query,
                        answer=clarification_answer,
                        faq_matched=False,
                        similarity_score=similarity_score,
                        used_gemini=False,
                        matched_faq=None
                    )
                    
                    return {
                        "answer": clarification_answer,
                        "relevant_faqs": [],
                        "grounding_confidence": 0.3,
                        "is_grounded": False,
                        "analytics": analytics
                    }
            
            if not relevant_faqs:
                logger.warning(f"No matching FAQs found for: {query}")
                no_match_answer = (
                    f"I couldn't find information about '{query}' in our FAQ database. "
                    f"Please contact our support team at support@fleety.com for assistance."
                )
                
                # Build analytics for no-match scenario
                analytics = self.analytics.build_metadata(
                    query=query,
                    answer=no_match_answer,
                    faq_matched=False,
                    similarity_score=0.0,
                    used_gemini=False,
                    matched_faq=None
                )
                
                return {
                    "answer": no_match_answer,
                    "relevant_faqs": [],
                    "grounding_confidence": 0.0,
                    "is_grounded": False,
                    "analytics": analytics
                }
            
            # Step 2: Generate answer with intent and user context
            used_gemini = await self._is_gemini_available()
            intent, _ = self.semantic_search.detect_intent(query)
            
            generated_answer = await self.generate_llm_answer(
                query=query,
                relevant_faqs=relevant_faqs,
                intent=intent,
                user_context=None  # Can be passed from FAQ route if available
            )
            
            # Step 3: Ground answer in FAQ data
            grounding_result = self.semantic_search.ground_answer(
                query=query,
                faq_results=relevant_faqs,
                answer=generated_answer
            )
            
            # Clean FAQ results for response (remove internal fields)
            clean_faqs = [
                {
                    "question": faq.get("question"),
                    "answer": faq.get("answer"),
                    "category": faq.get("category", "General"),
                    "id": faq.get("id", faq.get("_id"))
                }
                for faq in relevant_faqs
            ]
            
            # Step 4: Build comprehensive analytics metadata
            analytics = self.analytics.build_metadata(
                query=query,
                answer=grounding_result['grounded_answer'],
                faq_matched=True,
                similarity_score=similarity_score,
                used_gemini=used_gemini,
                matched_faq=relevant_faqs[0] if relevant_faqs else None
            )
            
            return {
                "answer": grounding_result['grounded_answer'],
                "relevant_faqs": clean_faqs,
                "grounding_confidence": grounding_result['confidence'],
                "is_grounded": grounding_result['is_grounded'],
                "analytics": analytics
            }
            
        except Exception as e:
            logger.error(f"Error in search_and_generate: {str(e)}")
            error_answer = f"An error occurred while searching FAQs: {str(e)}"
            
            # Build error analytics
            analytics = self.analytics.build_metadata(
                query=query,
                answer=error_answer,
                faq_matched=False,
                similarity_score=0.0,
                used_gemini=False,
                matched_faq=None
            )
            
            return {
                "answer": error_answer,
                "relevant_faqs": [],
                "grounding_confidence": 0.0,
                "is_grounded": False,
                "analytics": analytics
            }



    async def record_analytics(
        self,
        user_id: str,
        query: str,
        intent: str,
        result: Dict[str, Any]
    ) -> bool:
        """
        Record query analytics to MongoDB
        
        Args:
            user_id: User identifier
            query: User's query
            intent: Detected intent
            result: Result dict from search_and_generate with analytics
        
        Returns:
            True if recorded successfully
        """
        try:
            analytics_metadata = result.get("analytics", {})
            
            await Analytics.record_interaction(
                user_id=user_id,
                query=query,
                intent=intent,
                analytics_metadata=analytics_metadata,
                grounding_confidence=result.get("grounding_confidence"),
                is_grounded=result.get("is_grounded"),
                response_quality=analytics_metadata.get("similarity_score", 0.0)
            )
            
            logger.info(f"Analytics recorded for user {user_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error recording analytics: {str(e)}")
            return False