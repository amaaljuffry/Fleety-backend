"""
Semantic Search & RAG Enhancement Module
Handles semantic similarity, intent matching, and grounding answers
"""
import logging
from typing import List, Dict, Any, Tuple
from difflib import SequenceMatcher
import re

logger = logging.getLogger(__name__)


class SemanticSearch:
    """
    Semantic search engine for FAQ matching
    Handles synonyms, typos, and intent matching
    """
    
    def __init__(self):
        """Initialize semantic search with synonym mappings"""
        self.synonym_map = {
            # Vehicle operations
            'add': ['create', 'register', 'new', 'insert'],
            'vehicle': ['car', 'truck', 'fleet', 'auto', 'automobile'],
            'delete': ['remove', 'erase', 'drop'],
            'edit': ['modify', 'update', 'change'],
            
            # Maintenance
            'maintenance': ['service', 'repair', 'upkeep', 'servicing'],
            'record': ['history', 'log', 'entry', 'document'],
            'cost': ['price', 'expense', 'fee', 'charge', 'amount'],
            
            # Reminders
            'reminder': ['alert', 'notification', 'notification', 'reminder'],
            'due': ['upcoming', 'scheduled', 'coming'],
            
            # Reports
            'report': ['analysis', 'analytics', 'data', 'summary', 'statistics'],
            'export': ['download', 'save', 'extract', 'generate'],
            
            # Account/Auth
            'account': ['profile', 'user account', 'login account'],
            'login': ['sign in', 'authenticate', 'access'],
            'password': ['credentials', 'secret', 'pass'],
            'signup': ['register', 'create account', 'join'],
            
            # Team
            'team': ['members', 'users', 'people', 'staff'],
            'invite': ['add member', 'include', 'join'],
            'role': ['permission', 'access level', 'responsibility'],
            
            # General
            'how': ['what is the way', 'procedure', 'steps', 'guide'],
            'track': ['monitor', 'follow', 'watch', 'trace'],
            'payment': ['billing', 'subscription', 'pricing', 'charges'],
        }
        
        # Intent patterns
        self.intent_patterns = {
            'add_vehicle': [r'add.*vehicle', r'new.*vehicle', r'register.*vehicle', r'create.*car'],
            'maintenance': [r'maintenance', r'service', r'repair', r'upkeep'],
            'reminder': [r'reminder', r'alert', r'notification', r'due.*date'],
            'track_cost': [r'track.*cost', r'maintenance.*cost', r'spending', r'expense'],
            'account_setup': [r'create.*account', r'sign.*up', r'register', r'account'],
            'login': [r'login', r'sign.*in', r'access', r'password'],
            'export': [r'export', r'download', r'report', r'generate'],
            'gps': [r'gps', r'location', r'track.*vehicle', r'real.*time'],
            'team': [r'team', r'invite', r'member', r'role', r'permission'],
            'compliance': [r'compliance', r'license', r'driver'],
        }
    
    def normalize_text(self, text: str) -> str:
        """Normalize text for comparison"""
        text = text.lower().strip()
        # Remove punctuation
        text = re.sub(r'[^\w\s]', '', text)
        return text
    
    def expand_with_synonyms(self, text: str) -> str:
        """
        Expand text with synonyms for better matching
        Example: "add vehicle" → "add create register new insert vehicle car truck fleet auto"
        """
        normalized = self.normalize_text(text)
        words = normalized.split()
        expanded = list(words)
        
        for word in words:
            if word in self.synonym_map:
                expanded.extend(self.synonym_map[word])
        
        return ' '.join(expanded)
    
    def detect_intent(self, query: str) -> Tuple[str, float]:
        """
        Detect user intent from query
        Returns: (intent, confidence)
        """
        query_lower = query.lower()
        best_intent = 'general'
        best_score = 0.0
        
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    score = 0.9
                    # Boost score if multiple keywords match
                    if query_lower.count(pattern.split('[')[0][:5]) > 1:
                        score = 1.0
                    
                    if score > best_score:
                        best_score = score
                        best_intent = intent
        
        return best_intent, best_score
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two texts using sequence matching
        Handles typos and variations
        Returns: similarity score (0.0 to 1.0)
        """
        norm1 = self.normalize_text(text1)
        norm2 = self.normalize_text(text2)
        
        # Direct similarity
        direct_similarity = SequenceMatcher(None, norm1, norm2).ratio()
        
        # Expanded similarity (with synonyms)
        exp1 = self.expand_with_synonyms(norm1)
        exp2 = self.expand_with_synonyms(norm2)
        expanded_similarity = SequenceMatcher(None, exp1, exp2).ratio()
        
        # Weighted average: favor expanded similarity
        combined_score = (direct_similarity * 0.4) + (expanded_similarity * 0.6)
        
        return combined_score
    
    def search_faqs(
        self,
        query: str,
        faqs: List[Dict[str, Any]],
        top_k: int = 5,
        threshold: float = 0.3
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Search FAQs semantically
        Returns: List of (faq, similarity_score) tuples, sorted by relevance
        """
        try:
            if not query.strip():
                return []
            
            # Detect intent for context
            intent, intent_confidence = self.detect_intent(query)
            logger.info(f"Detected intent: {intent} (confidence: {intent_confidence:.2f})")
            
            results = []
            
            for faq in faqs:
                question = faq.get('question', '')
                answer = faq.get('answer', '')
                
                # Calculate similarity for question and answer
                q_similarity = self.calculate_similarity(query, question)
                a_similarity = self.calculate_similarity(query, answer) * 0.5  # Weight answer lower
                
                # Combined similarity
                similarity = max(q_similarity, a_similarity)
                
                # Boost score if intent matches FAQ category
                if 'category' in faq:
                    if faq['category'].lower() in intent.lower() or intent in faq['category'].lower():
                        similarity = min(similarity * 1.2, 1.0)  # Cap at 1.0
                
                if similarity >= threshold:
                    results.append((faq, similarity))
            
            # Sort by similarity descending
            results.sort(key=lambda x: x[1], reverse=True)
            
            # Return top_k results
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []
    
    def ground_answer(
        self,
        query: str,
        faq_results: List[Dict[str, Any]],
        answer: str
    ) -> Dict[str, Any]:
        """
        Ground answer in facts from FAQ knowledge base
        Ensures answers are based on real data, not hallucinations
        
        Returns:
        {
            'grounded_answer': str,
            'grounding_faqs': List[Dict],
            'is_grounded': bool,
            'confidence': float
        }
        """
        try:
            is_grounded = len(faq_results) > 0
            confidence = 0.0
            
            if is_grounded:
                # Calculate confidence based on match quality
                best_match_score = max([faq.get('similarity_score', 0) for faq in faq_results])
                confidence = best_match_score
                
                # Add grounding note if answer might contain general knowledge
                grounding_note = ""
                if confidence < 0.6:
                    grounding_note = (
                        "\n\n*Note: This answer is based on available documentation. "
                        "For specific details, please contact our support team.*"
                    )
                
                grounded_answer = answer + grounding_note if grounding_note else answer
            else:
                grounded_answer = (
                    f"I couldn't find specific information about '{query}' in our FAQ database. "
                    f"\n\nPlease contact our support team at support@fleety.com for detailed assistance. "
                    f"We're here to help!"
                )
                confidence = 0.0
            
            return {
                'grounded_answer': grounded_answer,
                'grounding_faqs': faq_results,
                'is_grounded': is_grounded,
                'confidence': confidence
            }
            
        except Exception as e:
            logger.error(f"Error grounding answer: {e}")
            return {
                'grounded_answer': answer,
                'grounding_faqs': faq_results,
                'is_grounded': False,
                'confidence': 0.0
            }
    
    def validate_answer_freshness(self, faq: Dict[str, Any]) -> bool:
        """
        Validate that FAQ is not outdated
        Returns: True if FAQ is current, False if potentially outdated
        """
        try:
            # Check for outdated markers
            answer_lower = faq.get('answer', '').lower()
            
            outdated_markers = [
                'coming soon',
                'will be available',
                'future release',
                'planned for',
                'deprecated',
                'no longer',
                'obsolete'
            ]
            
            for marker in outdated_markers:
                if marker in answer_lower:
                    logger.warning(f"FAQ may be outdated: {faq.get('question', '')}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating freshness: {e}")
            return True  # Assume valid if validation fails
