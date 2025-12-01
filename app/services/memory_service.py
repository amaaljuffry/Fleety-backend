import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from app.models.user import User

logger = logging.getLogger(__name__)


class MemoryService:
    """
    Long-Term Memory Service for personalized user interactions
    
    Tracks:
    - User profile data (name, preferences)
    - Interaction history (topics, frequency)
    - User preferences (tone, style preferences)
    - Conversation context (recent topics)
    
    Used for:
    - Personalized greetings
    - Context-aware responses
    - User preference adaptation
    - Conversation continuity
    """

    def __init__(self):
        self.cache = {}  # Simple in-memory cache for performance
        self.cache_ttl = 3600  # 1 hour cache TTL
        self.user_model = User

    async def get_user_memory(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve user memory from MongoDB
        
        Returns:
        {
            "user_id": "...",
            "username": "Sarah",
            "full_name": "Sarah Johnson",
            "email": "sarah@example.com",
            "preferred_name": "Sarah",
            "interaction_count": 42,
            "last_interaction": "2025-11-20T14:30:00",
            "conversation_topics": ["maintenance", "reminders", "reports"],
            "preferences": {
                "tone": "friendly",
                "detail_level": "medium",
                "language": "en"
            },
            "recent_queries": [
                {"topic": "maintenance", "timestamp": "..."},
                {"topic": "reminders", "timestamp": "..."}
            ]
        }
        """
        try:
            # Check cache first
            if user_id in self.cache:
                cached_data, timestamp = self.cache[user_id]
                if datetime.utcnow() - timestamp < timedelta(seconds=self.cache_ttl):
                    logger.debug(f"Memory cache hit for user {user_id}")
                    return cached_data

            # Query MongoDB for user data
            try:
                user = await User.find_one({"_id": user_id})
            except:
                # Fallback: try email-based lookup
                user = None

            if not user:
                logger.info(f"No user found for ID {user_id}")
                return None

            # Build memory object
            memory = {
                "user_id": str(user.get("_id")),
                "username": user.get("email", "").split("@")[0],  # Email prefix as username
                "full_name": user.get("full_name", ""),
                "email": user.get("email", ""),
                "preferred_name": user.get("preferred_name") or user.get("full_name", "").split()[0],
                "interaction_count": user.get("interaction_count", 0),
                "last_interaction": user.get("last_interaction"),
                "conversation_topics": user.get("conversation_topics", []),
                "preferences": user.get("preferences", {
                    "tone": "friendly",
                    "detail_level": "medium",
                    "language": "en"
                }),
                "recent_queries": user.get("recent_queries", [])
            }

            # Cache the memory
            self.cache[user_id] = (memory, datetime.utcnow())

            logger.info(f"Retrieved memory for user {user_id}: {memory.get('preferred_name')}")
            return memory

        except Exception as e:
            logger.error(f"Error retrieving user memory: {str(e)}")
            return None

    async def update_interaction(
        self,
        user_id: str,
        topic: str,
        query: str,
        response_quality: Optional[float] = None
    ) -> bool:
        """
        Update user interaction history after each query
        
        Args:
            user_id: User identifier
            topic: Topic/intent of the interaction
            query: User's query text
            response_quality: Quality score 0.0-1.0 of the response
        
        Returns:
            True if update successful
        """
        try:
            timestamp = datetime.utcnow()
            
            # Update user in MongoDB
            update_data = {
                "interaction_count": {"$inc": 1},
                "last_interaction": timestamp,
                "$push": {
                    "recent_queries": {
                        "topic": topic,
                        "query": query[:100],  # Store first 100 chars
                        "timestamp": timestamp,
                        "response_quality": response_quality
                    }
                }
            }
            
            # Keep only last 20 queries
            try:
                await User.update_one(
                    {"_id": user_id},
                    {
                        "$set": {
                            "interaction_count": (await self.get_user_memory(user_id) or {}).get("interaction_count", 0) + 1,
                            "last_interaction": timestamp
                        },
                        "$push": {
                            "recent_queries": {
                                "$each": [{
                                    "topic": topic,
                                    "query": query[:100],
                                    "timestamp": timestamp,
                                    "response_quality": response_quality
                                }],
                                "$slice": -20  # Keep last 20
                            }
                        }
                    }
                )
            except:
                logger.warning(f"Could not update interaction for user {user_id}")
            
            # Invalidate cache
            if user_id in self.cache:
                del self.cache[user_id]

            logger.info(f"Updated interaction for user {user_id}: topic={topic}")
            return True

        except Exception as e:
            logger.error(f"Error updating interaction: {str(e)}")
            return False

    async def record_preference(
        self,
        user_id: str,
        preference_key: str,
        preference_value: Any
    ) -> bool:
        """
        Store user preference (tone, detail_level, language, etc.)
        
        Args:
            user_id: User identifier
            preference_key: Key like 'tone', 'detail_level', 'language'
            preference_value: Value for preference
        
        Returns:
            True if successful
        """
        try:
            # Update in MongoDB
            try:
                await User.update_one(
                    {"_id": user_id},
                    {"$set": {f"preferences.{preference_key}": preference_value}}
                )
            except:
                logger.warning(f"Could not update preference for user {user_id}")
            
            # Invalidate cache
            if user_id in self.cache:
                del self.cache[user_id]

            logger.info(f"Updated preference for user {user_id}: {preference_key}={preference_value}")
            return True

        except Exception as e:
            logger.error(f"Error recording preference: {str(e)}")
            return False

    def extract_name(self, memory: Dict[str, Any]) -> str:
        """
        Extract a valid name from user memory
        
        Priority:
        1. Preferred name
        2. Full name (first word)
        3. Username (email prefix)
        4. Empty string if no valid name
        
        Returns:
            Valid name string or empty string
        """
        if not memory:
            return ""

        # Try preferred_name first
        preferred = memory.get("preferred_name", "").strip()
        if preferred and len(preferred) > 1 and not any(char.isdigit() for char in preferred[:3]):
            return preferred

        # Try full_name
        full_name = memory.get("full_name", "").strip()
        if full_name:
            first_name = full_name.split()[0]
            if first_name and len(first_name) > 1 and not any(char.isdigit() for char in first_name[:3]):
                return first_name

        # Try username (email prefix)
        username = memory.get("username", "").strip()
        if username and len(username) > 1 and not any(char.isdigit() for char in username[:3]):
            return username

        return ""

    def is_valid_name(self, name: str) -> bool:
        """
        Validate if a name string is suitable for personalized greeting
        
        Checks:
        - Not empty
        - At least 2 characters
        - No leading/trailing whitespace
        - Not mostly numbers
        
        Returns:
            True if valid
        """
        if not name or not isinstance(name, str):
            return False
        
        name = name.strip()
        
        # Too short
        if len(name) < 2:
            return False
        
        # Too many numbers
        digit_count = sum(1 for c in name if c.isdigit())
        if digit_count > len(name) / 2:
            return False
        
        # Valid characters (letters, spaces, hyphens, apostrophes)
        valid_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ '-")
        if not all(c in valid_chars for c in name):
            return False
        
        return True

    def clear_cache(self, user_id: Optional[str] = None):
        """Clear cache for specific user or all users"""
        if user_id:
            if user_id in self.cache:
                del self.cache[user_id]
                logger.info(f"Cleared cache for user {user_id}")
        else:
            self.cache.clear()
            logger.info("Cleared all memory cache")
