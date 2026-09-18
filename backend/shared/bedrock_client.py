"""
RoomieOps LLM Client

Abstraction over AI providers for intent detection and explanation generation.

Supports multiple backends:
- SHIP_IT: AWS Bedrock (Claude Sonnet)
- BUILD_IT: Ollama (local model via Strands)
- LOCAL_HEURISTIC: Simple rule-based fallback

Refactored to use LLMProvider abstraction.
"""

import json
import logging
from typing import Dict, Optional

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# LLM provider (injected at runtime)
_llm_provider = None


def set_llm_provider(provider):
    """Set the LLM provider for BedrockOps."""
    global _llm_provider
    _llm_provider = provider
    logger.info(f"BedrockOps LLM provider set to: {type(provider).__name__}")


def get_llm_provider():
    """Get current LLM provider (initializes if needed)."""
    global _llm_provider
    if _llm_provider is None:
        # Lazy initialization: detect provider based on environment
        try:
            from .providers import ExecutionModeManager
            providers = ExecutionModeManager.get_providers()
            _llm_provider = providers.llm
            logger.info(f"BedrockOps auto-initialized with: {type(_llm_provider).__name__}")
        except Exception as e:
            logger.error(f"Failed to auto-initialize LLM provider: {e}")
            raise
    return _llm_provider


class BedrockError(Exception):
    """Raised when LLM invocation fails."""
    pass


class BedrockOps:
    """LLM operations for RoomieOps (now abstracted over providers).
    
    Legacy name retained for backward compatibility. Delegates all operations
    to get_llm_provider() which returns appropriate implementation based on mode.
    """

    @staticmethod
    def detect_intent(user_message: str, household_context: Dict) -> Dict:
        """
        Detect user intent from natural language message.

        Args:
            user_message: User's NL request
            household_context: Dict with household metadata, members, recent expenses/chores

        Returns:
            {
                "intent": "view_balance|create_expense|complete_chore|...",
                "entities": {...},
                "confidence": 0.0-1.0,
                "reasoning": "explanation",
            }

        Raises:
            BedrockError: If LLM invocation fails
        """
        try:
            result = get_llm_provider().detect_intent(user_message, household_context)
            logger.info(f"Intent detected: {result.intent} (confidence: {result.confidence})")
            
            # Convert IntentDetectionResult to dict format
            return {
                "intent": result.intent,
                "entities": result.entities,
                "confidence": result.confidence,
                "reasoning": result.reasoning,
                "error": result.error,
            }
        except Exception as e:
            logger.error(f"Intent detection failed: {str(e)}")
            raise BedrockError(f"Intent detection error: {str(e)}")

    @staticmethod
    def generate_explanation(
        action_performed: str,
        action_result: Dict,
        user_message: str,
    ) -> str:
        """
        Generate human-readable explanation of action result.

        Args:
            action_performed: What action was executed
            action_result: Result data from the action
            user_message: Original user request

        Returns:
            Explanation string (always grounded in actual result, never fabricated)
        """
        try:
            explanation = get_llm_provider().generate_explanation(
                action_performed, action_result, user_message
            )
            logger.info(f"Explanation generated: {explanation[:100]}...")
            return explanation
        except Exception as e:
            logger.error(f"Failed to generate explanation: {str(e)}")
            # Return a safe fallback based on action_result
            return f"Action completed: {action_performed}"

    @staticmethod
    def test_invocation() -> Dict:
        """
        Test LLM invocation to verify provider is operational.

        Returns:
            Test result dict with status and details
        """
        try:
            logger.info(f"Testing LLM provider: {type(get_llm_provider()).__name__}")
            
            test_result = get_llm_provider().detect_intent(
                "What is RoomieOps?",
                {}
            )
            
            return {
                "status": "success",
                "provider": type(get_llm_provider()).__name__,
                "intent_detected": test_result.intent,
            }
        except Exception as e:
            logger.error(f"LLM provider test failed: {str(e)}")
            return {
                "status": "error",
                "provider": type(get_llm_provider()).__name__,
                "error": str(e),
            }
