import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class FleetyAssistantPrompt:
    """
    Fleety AI Assistant System Prompt Manager
    
    Handles:
    - System prompt generation
    - Context-aware instructions
    - Domain-specific guidance
    - Conversation flow management
    - Personalization integration
    """

    # Core system prompt
    SYSTEM_PROMPT = """You are Fleety Assistant, an expert in fleet management software. Provide direct, accurate answers to user questions.

## CRITICAL: DIRECT QUERY HANDLING

For these common questions, provide immediate answers WITHOUT over-clarification:

### 1. REGISTRATION/ACCOUNT CREATION
Query patterns: "how to register", "sign up", "create account", "new account", "get started"
Response: Provide registration steps directly
**CRITICAL:** NEVER redirect to password reset for account creation queries

Response Template:
"To register for Fleety Fleet Management:

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

For login issues, use the 'Forgot Password' option on the login page."

### 2. PASSWORD/LOGIN ISSUES
Query patterns: "forgot password", "can't login", "reset password", "locked out"
Response: Provide password recovery steps

Response Template:
"To reset your password:

1. Go to the Fleety login page
2. Click 'Forgot Password'
3. Enter the email associated with your account
4. Check your email for a reset link (check spam folder if needed)
5. Click the link and follow the instructions to create a new password
6. Use your new password to log in

If you don't receive the email within 5 minutes, please contact support@fleety.com"

### 3. VEHICLE MANAGEMENT
Query patterns: "add vehicle", "new truck", "register vehicle", "add car", "fleet setup"
Response: Provide vehicle addition steps

### 4. MAINTENANCE QUERIES
Query patterns: "maintenance", "service", "oil change", "reminders"
Response: Provide maintenance-specific guidance

## CONTEXT AWARENESS RULES

1. **Trust Explicit Intent Over Semantic Similarity**
   - If user asks about registration, they want registration info
   - If RAG retrieves password reset (high similarity score), IGNORE it for registration queries
   - User's explicit intent > FAQ matching algorithm

2. **Override Irrelevant FAQ Matches**
   - When semantic match is high but contextually wrong, provide direct answer instead
   - Log the mismatch for debugging
   - Explain the difference if relevant

3. **Only Ask Clarification for Truly Ambiguous Queries**
   - "How to register?" = Clear intent (registration)
   - "Help with my account" = Ambiguous (could be password, settings, billing, etc.)
   - BAD: Asking "Do you mean register or something else?" for clear queries
   - GOOD: Asking "Are you having trouble with login or account setup?" for vague queries

## RESPONSE PRIORITY ORDER

1. **Direct Answer** - Address the explicit question immediately
2. **Step-by-Step Guidance** - Numbered instructions if applicable
3. **Fleet Management Context** - Explain why this matters for their fleet
4. **Proactive Next Steps** - "Would you like help with [related task]?"
5. **Support Escalation** - Only if genuinely unable to help

## BAD PATTERNS TO ABSOLUTELY AVOID

❌ "I want to make sure I understand..." (for clear queries like "How to register?")
❌ "I couldn't find information about..." (provide value first)
❌ "Are you asking about X, Y, or Z?" (for explicit queries)
❌ Following irrelevant FAQ matches blindly
❌ Over-clarification on obvious questions
❌ Redirecting registration queries to password reset

## DOMAIN: Fleet Management

Your expertise covers:
- Vehicle management & fleet operations
- Registration & onboarding
- Maintenance scheduling & reminders
- Fuel efficiency & cost tracking
- Record keeping & exports
- Driver management & compliance
- Reporting & analytics
- Account settings & team management

## Key Fleet Management Concepts

**Registration/Onboarding:** Account creation, initial setup, vehicle adding
**Vehicle Management:** Adding vehicles, updating specs, tracking history
**Maintenance:** Scheduling, logging services, setting reminders
**Fuel & Costs:** Tracking consumption, analyzing efficiency, reporting
**Compliance:** Driver licenses, vehicle inspections, regulatory tracking
**Reporting:** Generating reports, exporting data, analyzing trends

## Response Structure (Always Follow)

For every response:
1. **Direct Answer** - 1-2 sentences answering the question
2. **Steps/Details** - Numbered steps if applicable
3. **Context** - Why this matters for fleet management
4. **Next Steps** - Proactive suggestion or follow-up question
5. **Support** - Contact info if escalation needed

## Safety & Accuracy

- Never invent features that don't exist
- If unsure about a Fleety feature, suggest contacting support
- Emphasize security (passwords, data backup)
- Recommend professional help for mechanical issues (not software)
- Be accurate about free trial terms and pricing

---

You are helpful, specific, accurate, and action-oriented. Prioritize direct answers over cautious clarification."""

    # Context-specific prompts
    VEHICLE_MANAGEMENT_CONTEXT = """Additional context: The user is asking about vehicle management. 

Focus on:
- Providing step-by-step guidance for vehicle operations
- Explaining required fields and why they matter
- Offering to help with next steps (e.g., setting up maintenance)
- Personalizing based on their fleet (if available)"""

    MAINTENANCE_CONTEXT = """Additional context: The user is asking about maintenance.

Focus on:
- Explaining maintenance reminder setup
- Guiding through maintenance logging
- Helping interpret maintenance history
- Offering proactive suggestions for service scheduling"""

    FUEL_TRACKING_CONTEXT = """Additional context: The user is asking about fuel tracking or cost analysis.

Focus on:
- Explaining fuel efficiency metrics
- Guiding through cost analysis
- Offering optimization suggestions
- Personalizing based on their vehicle types"""

    EXPORT_CONTEXT = """Additional context: The user is asking about exports or reporting.

Focus on:
- Explaining available formats and options
- Guiding through filtering and customization
- Offering to help with scheduling
- Suggesting relevant metrics to include"""

    # Discovery questions by topic
    DISCOVERY_QUESTIONS = {
        "vehicle": [
            "Are you looking to add a new vehicle to your fleet, or manage existing ones?",
            "Would you like help with vehicle categorization, tagging, or status management?",
            "Are you interested in vehicle specifications, maintenance history, or fuel tracking?"
        ],
        "maintenance": [
            "Are you looking to set up maintenance reminders or log past maintenance?",
            "Would you like help scheduling upcoming services or reviewing maintenance history?",
            "Are you interested in maintenance best practices or predictive maintenance insights?"
        ],
        "fuel": [
            "Are you tracking fuel expenses, analyzing efficiency, or optimizing costs?",
            "Would you like to review fuel consumption patterns or set efficiency targets?",
            "Are you interested in fuel cost comparisons across your fleet?"
        ],
        "export": [
            "What format do you need - spreadsheet, PDF, or scheduled report?",
            "Which data would you like to include - maintenance history, fuel records, or vehicle details?",
            "Would you like a one-time export or recurring automated reports?"
        ],
        "general": [
            "What would you like to manage today - vehicles, maintenance, or fuel tracking?",
            "Are you looking to add a vehicle, schedule maintenance, or analyze costs?",
            "What aspect of your fleet would you like help with?"
        ]
    }

    # Proactive suggestions by detected intent
    PROACTIVE_SUGGESTIONS = {
        "add_vehicle": "Now that you're adding a vehicle, would you like to set up maintenance reminders or configure fuel tracking for it?",
        "maintenance": "Once you've scheduled this maintenance, would you like help setting up automated reminders for future services?",
        "fuel_tracking": "To make the most of fuel tracking, would you like help analyzing your fleet's efficiency or setting consumption targets?",
        "export": "After generating this export, would you like to schedule automated reports for regular delivery?",
        "general_inquiry": "Based on your fleet needs, would you like help with vehicle management, maintenance scheduling, or fuel optimization?"
    }

    @staticmethod
    def get_system_prompt() -> str:
        """Get the full system prompt"""
        return FleetyAssistantPrompt.SYSTEM_PROMPT

    @staticmethod
    def get_contextual_prompt(intent: str) -> str:
        """
        Get context-specific prompt based on detected intent
        
        Args:
            intent: Detected user intent (vehicle, maintenance, fuel, export, etc.)
        
        Returns:
            System prompt with context appended
        """
        base_prompt = FleetyAssistantPrompt.SYSTEM_PROMPT
        
        context_map = {
            "add_vehicle": FleetyAssistantPrompt.VEHICLE_MANAGEMENT_CONTEXT,
            "manage_vehicle": FleetyAssistantPrompt.VEHICLE_MANAGEMENT_CONTEXT,
            "vehicle_info": FleetyAssistantPrompt.VEHICLE_MANAGEMENT_CONTEXT,
            "maintenance": FleetyAssistantPrompt.MAINTENANCE_CONTEXT,
            "schedule_maintenance": FleetyAssistantPrompt.MAINTENANCE_CONTEXT,
            "track_cost": FleetyAssistantPrompt.FUEL_TRACKING_CONTEXT,
            "fuel_tracking": FleetyAssistantPrompt.FUEL_TRACKING_CONTEXT,
            "export": FleetyAssistantPrompt.EXPORT_CONTEXT,
            "report": FleetyAssistantPrompt.EXPORT_CONTEXT,
            "reminder": FleetyAssistantPrompt.MAINTENANCE_CONTEXT,
        }
        
        context = context_map.get(intent, "")
        if context:
            return f"{base_prompt}\n\n{context}"
        return base_prompt

    @staticmethod
    def get_discovery_question(intent: Optional[str] = None) -> str:
        """
        Get a discovery question to understand user needs better
        
        Args:
            intent: Optional detected intent to narrow questions
        
        Returns:
            Relevant discovery question
        """
        import random
        
        if intent and intent in FleetyAssistantPrompt.DISCOVERY_QUESTIONS:
            questions = FleetyAssistantPrompt.DISCOVERY_QUESTIONS[intent]
        else:
            questions = FleetyAssistantPrompt.DISCOVERY_QUESTIONS["general"]
        
        return random.choice(questions)

    @staticmethod
    def get_proactive_suggestion(intent: Optional[str] = None) -> str:
        """
        Get proactive suggestion for next steps
        
        Args:
            intent: Detected intent from the response
        
        Returns:
            Proactive suggestion for next action
        """
        if intent and intent in FleetyAssistantPrompt.PROACTIVE_SUGGESTIONS:
            return FleetyAssistantPrompt.PROACTIVE_SUGGESTIONS[intent]
        return FleetyAssistantPrompt.PROACTIVE_SUGGESTIONS["general_inquiry"]

    @staticmethod
    def build_enhanced_prompt(
        base_query: str,
        intent: str,
        user_context: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[list] = None
    ) -> str:
        """
        Build enhanced prompt with full context
        
        Args:
            base_query: User's original query
            intent: Detected intent
            user_context: User data (name, fleet size, vehicles, etc.)
            conversation_history: Previous messages in conversation
        
        Returns:
            Enhanced prompt for Gemini with full context
        """
        prompt_parts = []

        # System prompt with context
        prompt_parts.append(FleetyAssistantPrompt.get_contextual_prompt(intent))

        # User context
        if user_context:
            prompt_parts.append("\n## User Context:")
            if user_context.get("username"):
                prompt_parts.append(f"User: {user_context['username']}")
            if user_context.get("fleet_info"):
                fleet = user_context["fleet_info"]
                prompt_parts.append(f"Fleet Size: {fleet.get('vehicle_count', 'unknown')} vehicles")
                if fleet.get("vehicle_types"):
                    prompt_parts.append(f"Vehicle Types: {', '.join(fleet['vehicle_types'])}")

        # Conversation context
        if conversation_history and len(conversation_history) > 0:
            prompt_parts.append("\n## Recent Conversation Context:")
            for msg in conversation_history[-2:]:  # Last 2 messages for context
                role = "User" if msg.get("type") == "user" else "Assistant"
                prompt_parts.append(f"{role}: {msg.get('content', '')[:100]}...")

        # Current query
        prompt_parts.append(f"\n## Current User Query:\n{base_query}")

        return "\n".join(prompt_parts)

    @staticmethod
    def format_response_with_guidance(
        answer: str,
        intent: str,
        include_suggestion: bool = True
    ) -> str:
        """
        Format response with proactive guidance
        
        Args:
            answer: Base answer from Gemini
            intent: Detected intent
            include_suggestion: Whether to include proactive suggestion
        
        Returns:
            Formatted response with guidance
        """
        formatted = answer

        if include_suggestion:
            suggestion = FleetyAssistantPrompt.get_proactive_suggestion(intent)
            formatted += f"\n\n{suggestion}"

        return formatted

    @staticmethod
    def validate_response(
        response: str,
        intent: str
    ) -> Dict[str, Any]:
        """
        Validate response adheres to guidelines
        
        Args:
            response: Generated response to validate
            intent: Detected intent
        
        Returns:
            Validation result with compliance status
        """
        issues = []
        warnings = []

        # Check for minimum structure
        if len(response) < 50:
            issues.append("Response too short - may lack sufficient detail")

        # Check for direct answer
        first_50_words = " ".join(response.split()[:50])
        if not any(phrase in first_50_words.lower() for phrase in ["i can help", "yes", "here", "the", "you can", "i recommend"]):
            warnings.append("Consider starting with direct answer")

        # Check for step-by-step guidance if needed
        if intent in ["add_vehicle", "schedule_maintenance", "export"] and "\n" not in response:
            warnings.append("Step-by-step format would improve clarity")

        # Check for proactive offer
        if any(phrase in response.lower() for phrase in ["would you like", "next step", "help with", "shall we"]):
            pass  # Good - includes proactive element
        else:
            warnings.append("Consider adding proactive follow-up question")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "compliance_score": max(0, 100 - (len(issues) * 20 + len(warnings) * 10))
        }
