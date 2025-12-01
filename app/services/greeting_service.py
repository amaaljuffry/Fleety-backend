import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class GreetingService:
    """
    Personalized Greeting Service using Memory System & Fleety Domain
    
    Protocol:
    1. Check Long-Term Memory for user profile
    2. Extract name (preferred_name → full_name → username)
    3. Validate name quality
    4. Generate personalized greeting with Fleety context
    5. Include contextual discovery questions
    
    Greetings:
    - With name: "Hi Sarah! Welcome to Fleety Assistant. How can I help you today?"
    - Without name: "Hello! I'm your Fleety Assistant. How can I help?"
    - Welcome back: "Welcome back, Sarah! Ready to manage your fleet?"
    """

    def __init__(self, memory_service=None):
        from app.services.memory_service import MemoryService
        from app.services.fleety_assistant_prompt import FleetyAssistantPrompt
        
        self.memory_service = memory_service or MemoryService()
        self.fleety_prompt = FleetyAssistantPrompt()
        
        # Fleety-specific greeting templates
        self.greeting_templates = {
            "friendly": {
                "with_name": "Hi {name}! Welcome to Fleety Assistant. I'm here to help with your fleet management needs. What would you like to do today?",
                "without_name": "Hello! I'm your Fleety Assistant. I can help with vehicle management, maintenance, fuel tracking, and more. What brings you here?",
                "welcome_back": "Welcome back, {name}! Ready to manage your fleet? What can I help you with?",
                "returning_frequent": "Hey {name}! Great to see you again. Your fleet is looking good. What would you like to focus on today?"
            },
            "professional": {
                "with_name": "Good to see you, {name}. I'm your Fleety Assistant, here to support your fleet operations. How may I assist you?",
                "without_name": "Hello. I'm Fleety Assistant, your fleet management partner. How may I assist you today?",
                "welcome_back": "Welcome back, {name}. I'm ready to help with your fleet needs. What would you like to work on?",
                "returning_frequent": "Hello {name}. Welcome back to Fleety. I'm here to support your fleet operations. What's on your agenda today?"
            },
            "technical": {
                "with_name": "Hi {name}. I'm Fleety Assistant. What fleet management operations can I help you with?",
                "without_name": "Hello. Fleety Assistant here. Ready to optimize your fleet management. What do you need?",
                "welcome_back": "Welcome back, {name}. Ready to continue with fleet operations?",
                "returning_frequent": "Hi {name}! Back with more fleet data? Let's optimize. What would you like to analyze?"
            }
        }
        
        # Default persona

        self.default_persona = "friendly"

    async def generate_greeting(
        self,
        user_id: Optional[str] = None,
        user_memory: Optional[Dict[str, Any]] = None,
        persona: str = "friendly"
    ) -> Dict[str, Any]:
        """
        Generate personalized greeting
        
        Args:
            user_id: User identifier (to fetch memory if not provided)
            user_memory: Pre-fetched user memory object
            persona: Greeting tone (friendly, professional, technical)
        
        Returns: greeting response with personalization metadata
        """
        try:
            # Validate persona
            if persona not in self.greeting_templates:
                logger.warning(f"Invalid persona '{persona}', using default")
                persona = self.default_persona

            # Get user memory if not provided
            if not user_memory and user_id:
                user_memory = await self.memory_service.get_user_memory(user_id)

            # Extract name if memory available
            name = ""
            is_personalized = False
            username = ""
            interaction_count = 0
            last_seen = None
            
            if user_memory:
                name = self.memory_service.extract_name(user_memory)
                is_personalized = self.memory_service.is_valid_name(name)
                username = user_memory.get("preferred_name") or user_memory.get("username", "")
                interaction_count = user_memory.get("interaction_count", 0)
                last_seen = user_memory.get("last_interaction")

            # Select greeting template
            template_key = self._select_template_key(is_personalized, interaction_count)
            template = self.greeting_templates[persona][template_key]

            # Generate greeting
            if is_personalized:
                greeting = template.format(name=name)
            else:
                greeting = template

            logger.info(
                f"Generated greeting for user {user_id or 'anonymous'}: "
                f"personalized={is_personalized}, template={template_key}"
            )

            return {
                "greeting": greeting,
                "personalized": is_personalized,
                "username": name if is_personalized else "",
                "persona": persona,
                "interaction_count": interaction_count,
                "last_seen": last_seen,
                "template_used": template_key,
                "discovery_question": self.fleety_prompt.get_discovery_question()
            }

        except Exception as e:
            logger.error(f"Error generating greeting: {str(e)}")
            # Fallback to generic greeting
            return {
                "greeting": "Hello! How can I help you today?",
                "personalized": False,
                "username": "",
                "persona": persona,
                "interaction_count": 0,
                "last_seen": None,
                "template_used": "without_name",
                "error": str(e)
            }

    def _select_template_key(self, is_personalized: bool, interaction_count: int) -> str:
        """
        Select appropriate greeting template
        
        Logic:
        - No name available: use 'without_name'
        - First interaction: use 'with_name'
        - Returning user (2-10 visits): use 'welcome_back'
        - Frequent user (10+ visits): use 'returning_frequent'
        """
        if not is_personalized:
            return "without_name"
        
        if interaction_count <= 1:
            return "with_name"
        elif interaction_count < 10:
            return "welcome_back"
        else:
            return "returning_frequent"

    async def generate_contextual_greeting(
        self,
        user_id: Optional[str] = None,
        user_memory: Optional[Dict[str, Any]] = None,
        recent_topic: Optional[str] = None,
        persona: str = "friendly"
    ) -> Dict[str, Any]:
        """
        Generate context-aware greeting based on recent interactions
        
        Args:
            user_id: User identifier
            user_memory: Pre-fetched user memory
            recent_topic: Last topic user inquired about
            persona: Greeting tone
        
        Returns:
            Greeting with context awareness
        """
        try:
            # Get base greeting
            greeting_data = await self.generate_greeting(user_id, user_memory, persona)

            # Add context if available
            if recent_topic and user_memory and greeting_data["personalized"]:
                name = greeting_data["username"]
                if persona == "friendly":
                    context_addition = f" I see you were looking at {recent_topic} last time - want to continue?"
                elif persona == "professional":
                    context_addition = f" I notice you were researching {recent_topic}. Would you like to continue?"
                else:  # technical
                    context_addition = f" Last topic: {recent_topic}. Continue?"
                
                greeting_data["greeting"] += context_addition
                greeting_data["includes_context"] = True
            else:
                greeting_data["includes_context"] = False

            return greeting_data

        except Exception as e:
            logger.error(f"Error generating contextual greeting: {str(e)}")
            return await self.generate_greeting(user_id, user_memory, persona)

    def get_help_phrases(self, persona: str = "friendly") -> list:
        """Get list of help phrases for a persona"""
        help_phrases = {
            "friendly": [
                "How can I help you today?",
                "What can I assist you with?",
                "What do you need help with?",
                "How can I be of service?"
            ],
            "professional": [
                "How may I assist you?",
                "What can I help you with?",
                "How can I be of service?",
                "What assistance do you require?"
            ],
            "technical": [
                "What queries do you have?",
                "What can I help with?",
                "What do you need?",
                "Ready to proceed?"
            ]
        }
        
        return help_phrases.get(persona, help_phrases["friendly"])

    def get_farewell_phrases(self, persona: str = "friendly") -> list:
        """Get list of farewell phrases for a persona"""
        farewells = {
            "friendly": [
                "Happy to help! Feel free to reach out anytime.",
                "Glad I could help! See you soon.",
                "Anything else I can help with? Always here!",
                "Take care! Come back if you need anything."
            ],
            "professional": [
                "Thank you for using our service. Feel free to reach out with any questions.",
                "I'm here if you need further assistance.",
                "Have a great day! Contact us anytime.",
                "Thank you. We're here to help whenever you need."
            ],
            "technical": [
                "Process complete. Let me know if you need anything else.",
                "Done. Reach out if you need further assistance.",
                "Available for additional queries.",
                "Ready for the next task."
            ]
        }
        
        return farewells.get(persona, farewells["friendly"])
