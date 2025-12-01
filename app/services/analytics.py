import logging
from typing import Dict, Any, Optional
from datetime import datetime
from app.services.semantic_search import SemanticSearch

logger = logging.getLogger(__name__)


class ChatbotAnalytics:
    """
    Analytics & Metadata Tagging Service
    
    Tracks:
    - FAQ matched (boolean)
    - Similarity score (0.0-1.0)
    - Persona used (friendly, professional, technical)
    - Sentiment score (negative, neutral, positive)
    - Fallback AI usage (whether Gemini was used)
    - Misunderstanding indicators (query complexity, intent mismatch)
    """

    def __init__(self):
        self.semantic_search = SemanticSearch()
        # Persona patterns for response classification
        self.persona_patterns = {
            "friendly": ["here's", "hope this helps", "feel free", "happy to help", "thanks for asking"],
            "professional": ["regarding", "therefore", "ensure", "implementation", "noted"],
            "technical": ["api", "query", "parameter", "endpoint", "database", "config", "schema"]
        }

    def analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze query for complexity and intent confidence"""
        query_lower = query.lower()
        
        # Calculate query complexity
        word_count = len(query.split())
        char_count = len(query)
        has_special_chars = any(c in query for c in ["?", "!", "*", "$", "%"])
        has_technical_terms = any(term in query_lower for term in ["api", "database", "schema", "config", "error"])
        
        # Query complexity score (0.0-1.0)
        complexity = min(1.0, (word_count / 20) + (0.1 if has_special_chars else 0) + (0.2 if has_technical_terms else 0))
        
        # Detect if query is vague (misunderstanding indicator)
        vague_indicators = ["what", "how", "when", "where", "why", "help", "?"]
        is_vague = sum(1 for indicator in vague_indicators if indicator in query_lower) >= 2
        
        return {
            "complexity": min(1.0, complexity),
            "word_count": word_count,
            "char_count": char_count,
            "is_vague": is_vague,
            "has_technical_terms": has_technical_terms
        }

    def detect_sentiment(self, text: str) -> Dict[str, Any]:
        """Detect sentiment in text"""
        text_lower = text.lower()
        
        # Sentiment indicators
        positive_words = ["great", "excellent", "good", "perfect", "amazing", "love", "helpful", "thanks"]
        negative_words = ["bad", "terrible", "poor", "hate", "broken", "error", "problem", "issue"]
        frustrated_words = ["frustrat", "annoyed", "angry", "upset", "confused"]
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        frustrated_count = sum(1 for word in frustrated_words if word in text_lower)
        
        # Calculate sentiment score (-1.0 to 1.0)
        total = positive_count + negative_count + frustrated_count
        if total == 0:
            sentiment_score = 0.0  # Neutral
            sentiment = "neutral"
        elif frustrated_count > 0:
            sentiment = "frustrated"
            sentiment_score = -0.8
        elif negative_count > positive_count:
            sentiment = "negative"
            sentiment_score = min(-1.0, -(negative_count / max(1, positive_count + negative_count)))
        elif positive_count > 0:
            sentiment = "positive"
            sentiment_score = min(1.0, positive_count / (positive_count + negative_count + 1))
        else:
            sentiment = "neutral"
            sentiment_score = 0.0
        
        return {
            "sentiment": sentiment,
            "sentiment_score": round(sentiment_score, 2),
            "positive_indicators": positive_count,
            "negative_indicators": negative_count,
            "frustrated_indicators": frustrated_count
        }

    def detect_persona(self, response: str) -> Dict[str, Any]:
        """Detect persona used in response"""
        response_lower = response.lower()
        
        persona_scores = {}
        for persona, patterns in self.persona_patterns.items():
            score = sum(1 for pattern in patterns if pattern in response_lower)
            persona_scores[persona] = score
        
        # Determine dominant persona
        if max(persona_scores.values()) == 0:
            dominant_persona = "neutral"
            persona_confidence = 0.0
        else:
            dominant_persona = max(persona_scores, key=persona_scores.get)
            total_matches = sum(persona_scores.values())
            persona_confidence = round(persona_scores[dominant_persona] / total_matches, 2)
        
        return {
            "persona": dominant_persona,
            "persona_confidence": persona_confidence,
            "persona_scores": persona_scores
        }

    def detect_misunderstanding_indicators(self, query: str, answer: str, similarity_score: float) -> Dict[str, Any]:
        """Detect if there are signs of potential misunderstanding"""
        indicators = []
        risk_score = 0.0
        
        # Low similarity score
        if similarity_score < 0.4:
            indicators.append("low_similarity_score")
            risk_score += 0.3
        
        # Query analysis
        query_analysis = self.analyze_query(query)
        if query_analysis["is_vague"]:
            indicators.append("vague_query")
            risk_score += 0.2
        
        # Query and answer length mismatch
        query_len = len(query.split())
        answer_len = len(answer.split())
        if query_len > 0 and (answer_len / query_len) > 10:
            indicators.append("verbose_response")
            risk_score += 0.1
        
        # Check for "I don't know" or uncertainty patterns
        uncertainty_patterns = ["i'm not sure", "i don't know", "unclear", "unfortunately", "cannot determine"]
        if any(pattern in answer.lower() for pattern in uncertainty_patterns):
            indicators.append("uncertain_response")
            risk_score += 0.2
        
        # Check if intent was detected
        intent, intent_confidence = self.semantic_search.detect_intent(query)
        if intent_confidence < 0.3:
            indicators.append("low_intent_confidence")
            risk_score += 0.2
        
        return {
            "misunderstanding_risk": round(min(1.0, risk_score), 2),
            "risk_indicators": indicators,
            "should_request_clarification": risk_score > 0.6
        }

    def build_metadata(
        self,
        query: str,
        answer: str,
        faq_matched: bool,
        similarity_score: float,
        used_gemini: bool,
        matched_faq: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build comprehensive metadata for response
        
        Returns analytics object with:
        - faq_matched: boolean
        - similarity_score: 0.0-1.0
        - persona: friendly|professional|technical|neutral
        - sentiment: positive|neutral|negative|frustrated
        - sentiment_score: -1.0 to 1.0
        - fallback_ai_used: boolean
        - misunderstanding_indicators: list
        - query_complexity: 0.0-1.0
        - response_metadata: detailed breakdown
        """
        
        # Analyze query
        query_analysis = self.analyze_query(query)
        
        # Detect sentiment
        sentiment_data = self.detect_sentiment(query)
        
        # Detect persona in response
        persona_data = self.detect_persona(answer)
        
        # Detect misunderstanding risk
        misunderstanding_data = self.detect_misunderstanding_indicators(query, answer, similarity_score)
        
        # Build metadata object
        metadata = {
            # Core analytics
            "faq_matched": faq_matched,
            "similarity_score": round(similarity_score, 2),
            "persona_used": persona_data["persona"],
            "persona_confidence": persona_data["persona_confidence"],
            "sentiment": sentiment_data["sentiment"],
            "sentiment_score": sentiment_data["sentiment_score"],
            "fallback_ai_used": used_gemini,
            
            # Misunderstanding detection
            "misunderstanding_risk": misunderstanding_data["misunderstanding_risk"],
            "misunderstanding_indicators": misunderstanding_data["risk_indicators"],
            "should_request_clarification": misunderstanding_data["should_request_clarification"],
            
            # Query metadata
            "query_metadata": {
                "complexity": query_analysis["complexity"],
                "word_count": query_analysis["word_count"],
                "char_count": query_analysis["char_count"],
                "is_vague": query_analysis["is_vague"],
                "has_technical_terms": query_analysis["has_technical_terms"]
            },
            
            # Sentiment breakdown
            "sentiment_breakdown": {
                "positive_indicators": sentiment_data["positive_indicators"],
                "negative_indicators": sentiment_data["negative_indicators"],
                "frustrated_indicators": sentiment_data["frustrated_indicators"]
            },
            
            # Persona breakdown
            "persona_breakdown": persona_data["persona_scores"],
            
            # FAQ metadata (if matched)
            "faq_source": None if not matched_faq else {
                "faq_id": matched_faq.get("id"),
                "faq_category": matched_faq.get("category"),
                "faq_question": matched_faq.get("question")
            },
            
            # Response timestamp
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return metadata
