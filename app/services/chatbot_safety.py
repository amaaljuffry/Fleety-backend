"""
Safety & Compliance Module for FAQ Chatbot
Handles spam, abuse, prompt injection, and malicious requests
"""
import logging
import re
from typing import Tuple
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class ChatbotSafety:
    """
    Safety layer for FAQ chatbot to prevent abuse and ensure compliance
    """
    
    def __init__(self):
        """Initialize safety tracking"""
        self.user_message_history = defaultdict(list)  # Track user messages
        self.user_warnings = defaultdict(int)  # Track warnings per user
        self.blocked_users = set()  # Temporarily blocked users
        
        # Patterns for detection
        self.abuse_patterns = [
            r'damn', r'hell', r'bastard', r'idiot', r'stupid',
            r'kill', r'die', r'suck', r'f\*ck', r'f##k', r'ass'
        ]
        
        self.spam_keywords = ['viagra', 'casino', 'lottery', 'free money', 'click here']
        self.prompt_injection_keywords = [
            'ignore', 'forget', 'bypass', 'override', 'system prompt',
            'you are', 'pretend', 'roleplay', 'act as', 'forget instructions'
        ]
    
    def check_spam(self, user_id: str, message: str) -> Tuple[bool, str]:
        """
        Detect spam: repeated messages, spam keywords
        Returns: (is_spam, message)
        """
        try:
            # Check for repeated messages (same message 3+ times in 5 minutes)
            now = datetime.now()
            recent_messages = [
                msg for msg, timestamp in self.user_message_history[user_id]
                if now - timestamp < timedelta(minutes=5)
            ]
            
            # Count identical messages
            identical_count = sum(1 for msg in recent_messages if msg.lower() == message.lower())
            
            if identical_count >= 3:
                return True, "⚠️ Please avoid sending the same question repeatedly. Try rephrasing or ask something new."
            
            # Check for spam keywords
            message_lower = message.lower()
            if any(keyword in message_lower for keyword in self.spam_keywords):
                logger.warning(f"Spam detected from {user_id}: {message}")
                return True, "❌ This message contains spam. Please ask legitimate questions about Fleety."
            
            return False, ""
            
        except Exception as e:
            logger.error(f"Error checking spam: {e}")
            return False, ""
    
    def check_abusive_language(self, message: str) -> Tuple[bool, str]:
        """
        Detect abusive or offensive language
        Returns: (is_abusive, message)
        """
        try:
            message_lower = message.lower()
            
            # Check against abuse patterns
            for pattern in self.abuse_patterns:
                if re.search(pattern, message_lower, re.IGNORECASE):
                    logger.warning(f"Abusive language detected: {message}")
                    return True, (
                        "😊 I'm here to help! Please keep our conversation respectful and family-friendly. "
                        "Let me know how I can assist you with Fleety."
                    )
            
            return False, ""
            
        except Exception as e:
            logger.error(f"Error checking abuse: {e}")
            return False, ""
    
    def check_prompt_injection(self, message: str) -> Tuple[bool, str]:
        """
        Detect prompt injection attempts
        Returns: (is_injection, message)
        """
        try:
            message_lower = message.lower()
            
            # Check for prompt injection keywords
            injection_detected = any(
                keyword in message_lower 
                for keyword in self.prompt_injection_keywords
            )
            
            if injection_detected:
                logger.warning(f"Potential prompt injection detected: {message}")
                return True, (
                    "🔒 I'm here to help with Fleety questions only. "
                    "I can't modify my instructions or behavior beyond helping with Fleety support."
                )
            
            return False, ""
            
        except Exception as e:
            logger.error(f"Error checking prompt injection: {e}")
            return False, ""
    
    def check_malicious_request(self, message: str) -> Tuple[bool, str]:
        """
        Detect malicious requests (SQL injection, code execution, etc.)
        Returns: (is_malicious, message)
        """
        try:
            message_lower = message.lower()
            
            # Patterns for malicious intent
            malicious_patterns = [
                r'drop\s+table',  # SQL injection
                r'delete\s+from',  # SQL injection
                r'exec\(',  # Code execution
                r'eval\(',  # Code execution
                r'__import__',  # Python import
                r'subprocess',  # Process execution
                r'os\.system',  # System call
            ]
            
            for pattern in malicious_patterns:
                if re.search(pattern, message_lower):
                    logger.warning(f"Malicious request detected: {message}")
                    return True, (
                        "🚫 I've detected a potentially harmful request. "
                        "For security reasons, this conversation has been reset. "
                        "Please ask legitimate questions about Fleety."
                    )
            
            return False, ""
            
        except Exception as e:
            logger.error(f"Error checking malicious request: {e}")
            return False, ""
    
    def record_message(self, user_id: str, message: str) -> None:
        """Record message for tracking"""
        try:
            self.user_message_history[user_id].append((message, datetime.now()))
            
            # Cleanup old messages (keep only last 50 messages per user)
            if len(self.user_message_history[user_id]) > 50:
                self.user_message_history[user_id] = self.user_message_history[user_id][-50:]
        except Exception as e:
            logger.error(f"Error recording message: {e}")
    
    def add_warning(self, user_id: str) -> int:
        """
        Add warning to user
        Returns: current warning count
        """
        self.user_warnings[user_id] += 1
        warning_count = self.user_warnings[user_id]
        
        if warning_count >= 3:
            self.blocked_users.add(user_id)
            logger.warning(f"User {user_id} blocked after 3 warnings")
        
        return warning_count
    
    def is_user_blocked(self, user_id: str) -> bool:
        """Check if user is temporarily blocked"""
        return user_id in self.blocked_users
    
    def reset_user(self, user_id: str) -> None:
        """Reset user data (unblock, clear warnings, history)"""
        try:
            self.blocked_users.discard(user_id)
            self.user_warnings[user_id] = 0
            self.user_message_history[user_id] = []
            logger.info(f"User {user_id} data reset")
        except Exception as e:
            logger.error(f"Error resetting user: {e}")
    
    async def validate_query(self, user_id: str, query: str) -> Tuple[bool, str]:
        """
        Complete validation pipeline
        Returns: (is_valid, response_message)
        """
        try:
            # Check if user is blocked
            if self.is_user_blocked(user_id):
                return False, "⛔ Your access has been temporarily restricted due to policy violations."
            
            # Check for spam
            is_spam, spam_msg = self.check_spam(user_id, query)
            if is_spam:
                self.add_warning(user_id)
                return False, spam_msg
            
            # Check for abusive language
            is_abusive, abuse_msg = self.check_abusive_language(query)
            if is_abusive:
                self.add_warning(user_id)
                return False, abuse_msg
            
            # Check for prompt injection
            is_injection, injection_msg = self.check_prompt_injection(query)
            if is_injection:
                self.add_warning(user_id)
                return False, injection_msg
            
            # Check for malicious requests
            is_malicious, malicious_msg = self.check_malicious_request(query)
            if is_malicious:
                self.reset_user(user_id)  # Reset conversation
                return False, malicious_msg
            
            # Record valid message
            self.record_message(user_id, query)
            
            return True, ""
            
        except Exception as e:
            logger.error(f"Error validating query: {e}")
            return True, ""  # Allow message if validation fails


# Global safety instance
safety = ChatbotSafety()
