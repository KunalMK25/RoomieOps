"""LLM provider implementations for different backends."""

import json
import logging
import os
import re
from typing import Any, Dict
from abc import ABC

from .base import LLMProvider
from .types import IntentDetectionResult

logger = logging.getLogger(__name__)


class BedrockLLMProvider(LLMProvider):
    """LLM provider using Amazon Bedrock (SHIP_IT)."""
    
    def __init__(self):
        """Initialize Bedrock client."""
        try:
            import boto3
            self.client = boto3.client("bedrock-runtime", region_name=os.environ.get("AWS_REGION", "us-east-1"))
            self.model_id = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-sonnet-4-5-20250929-v1:0")
            logger.info(f"BedrockLLMProvider initialized with model: {self.model_id}")
        except Exception as e:
            logger.error(f"Failed to initialize Bedrock client: {e}")
            raise
    
    def detect_intent(
        self,
        user_message: str,
        household_context: Dict[str, Any]
    ) -> IntentDetectionResult:
        """Detect intent using Bedrock."""
        try:
            prompt = self._build_intent_prompt(user_message, household_context)
            
            response = self.client.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps({"prompt": prompt, "max_tokens": 500}),
            )
            
            response_body = json.loads(response["body"].read())
            text = self._extract_text_from_response(response_body)
            
            # Parse JSON response
            result = self._parse_intent_json(text)
            return result
            
        except Exception as e:
            logger.error(f"Bedrock intent detection failed: {e}")
            return IntentDetectionResult(
                intent="other",
                confidence=0.0,
                entities={},
                reasoning="Error detecting intent",
                error=str(e)
            )
    
    def generate_explanation(
        self,
        action_performed: str,
        action_result: Dict[str, Any],
        user_message: str
    ) -> str:
        """Generate explanation using Bedrock."""
        try:
            prompt = f"""Generate a brief, friendly explanation (1-2 sentences) of this action result.

User asked: "{user_message}"
Action performed: {action_performed}
Result data: {json.dumps(action_result)}

Explain using actual numbers/data. Be factual, never fabricate."""
            
            response = self.client.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps({"prompt": prompt, "max_tokens": 200}),
            )
            
            response_body = json.loads(response["body"].read())
            text = self._extract_text_from_response(response_body)
            return text.strip()[:500]
            
        except Exception as e:
            logger.error(f"Bedrock explanation generation failed: {e}")
            return f"Action completed: {action_performed}"
    
    @staticmethod
    def _build_intent_prompt(user_message: str, context: Dict[str, Any]) -> str:
        """Build prompt for intent detection."""
        return f"""Analyze this user message and detect their intent.

User message: "{user_message}"

Household context:
- Members: {', '.join([m.get('name', 'unknown') for m in context.get('members', [])])}
- Recent balances: {context.get('balances', {})}
- Active chores: {context.get('chore_count', 0)}

Respond ONLY with JSON:
{{
  "intent": "view_balance" | "view_chores" | "create_expense" | "create_maintenance" | "add_shopping_item" | "other",
  "entities": {{}},
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation"
}}"""
    
    @staticmethod
    def _extract_text_from_response(response_body: Dict) -> str:
        """Extract text from Bedrock response."""
        if "completion" in response_body:
            return response_body["completion"]
        elif "content" in response_body and response_body["content"]:
            return response_body["content"][0].get("text", "")
        return str(response_body)
    
    @staticmethod
    def _parse_intent_json(text: str) -> IntentDetectionResult:
        """Parse intent JSON from response."""
        try:
            # Try to find JSON block
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                result = json.loads(match.group(0))
            else:
                result = json.loads(text)
            
            return IntentDetectionResult(
                intent=result.get("intent", "other"),
                confidence=result.get("confidence", 0.0),
                entities=result.get("entities", {}),
                reasoning=result.get("reasoning", "")
            )
        except Exception as e:
            logger.warning(f"Failed to parse intent JSON: {e}")
            return IntentDetectionResult(
                intent="other",
                confidence=0.0,
                entities={},
                reasoning="Failed to parse response",
                error=str(e)
            )


class OllamaLLMProvider(LLMProvider):
    """LLM provider using Ollama local model (BUILD_IT)."""
    
    def __init__(self, endpoint: str = "http://localhost:11434"):
        """Initialize Ollama client.
        
        Args:
            endpoint: Ollama API endpoint (default: localhost:11434)
        """
        try:
            import requests
            self.requests = requests
            self.endpoint = endpoint
            self.model = os.environ.get("LLM_MODEL", "llama3.2:3b")
            self.timeout = 30
            
            # Verify Ollama is reachable
            response = self.requests.get(f"{self.endpoint}/api/tags", timeout=5)
            if response.status_code != 200:
                raise Exception(f"Ollama not responding: {response.status_code}")
            
            logger.info(f"OllamaLLMProvider initialized with model: {self.model} at {self.endpoint}")
        except ImportError:
            raise ImportError("requests library required for Ollama provider")
        except Exception as e:
            logger.error(f"Failed to initialize Ollama client: {e}")
            raise
    
    def detect_intent(
        self,
        user_message: str,
        household_context: Dict[str, Any]
    ) -> IntentDetectionResult:
        """Detect intent using Ollama."""
        try:
            prompt = self._build_intent_prompt(user_message, household_context)
            
            response = self.requests.post(
                f"{self.endpoint}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.3,
                },
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama error: {response.status_code}")
            
            result_data = response.json()
            text = result_data.get("response", "")
            
            # Parse JSON response
            result = self._parse_intent_json(text)
            return result
            
        except Exception as e:
            logger.error(f"Ollama intent detection failed: {e}")
            return IntentDetectionResult(
                intent="other",
                confidence=0.0,
                entities={},
                reasoning="Error detecting intent",
                error=str(e)
            )
    
    def generate_explanation(
        self,
        action_performed: str,
        action_result: Dict[str, Any],
        user_message: str
    ) -> str:
        """Generate explanation using Ollama."""
        try:
            prompt = f"""Generate a brief explanation of this action result (1-2 sentences).

User asked: "{user_message}"
Action: {action_performed}
Result: {json.dumps(action_result)}

Be factual using actual data only."""
            
            response = self.requests.post(
                f"{self.endpoint}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.3,
                },
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                raise Exception(f"Ollama error: {response.status_code}")
            
            result_data = response.json()
            text = result_data.get("response", "")
            return text.strip()[:500]
            
        except Exception as e:
            logger.error(f"Ollama explanation generation failed: {e}")
            return f"Action completed: {action_performed}"
    
    @staticmethod
    def _build_intent_prompt(user_message: str, context: Dict[str, Any]) -> str:
        """Build prompt for intent detection."""
        return f"""Analyze user intent.

Message: "{user_message}"
Members: {', '.join([m.get('name', 'unknown') for m in context.get('members', [])])}
Balances: {context.get('balances', {{}})}

Respond ONLY with JSON:
{{"intent": "view_balance"|"view_chores"|"create_expense"|"create_maintenance"|"add_shopping_item"|"other", "confidence": 0.0-1.0, "entities": {{}}, "reasoning": "brief"}}"""
    
    @staticmethod
    def _parse_intent_json(text: str) -> IntentDetectionResult:
        """Parse intent JSON from response."""
        try:
            # Try to find JSON block
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                result = json.loads(match.group(0))
            else:
                result = json.loads(text)
            
            return IntentDetectionResult(
                intent=result.get("intent", "other"),
                confidence=result.get("confidence", 0.0),
                entities=result.get("entities", {}),
                reasoning=result.get("reasoning", "")
            )
        except Exception as e:
            logger.warning(f"Failed to parse Ollama intent JSON: {e}")
            return IntentDetectionResult(
                intent="other",
                confidence=0.0,
                entities={},
                reasoning="Failed to parse response",
                error=str(e)
            )


class HeuristicLLMProvider(LLMProvider):
    """LLM provider using heuristic keyword matching (LOCAL_HEURISTIC fallback)."""
    
    def detect_intent(
        self,
        user_message: str,
        household_context: Dict[str, Any]
    ) -> IntentDetectionResult:
        """Detect intent using keyword matching."""
        msg_lower = user_message.lower()
        
        # Simple keyword-based detection
        if any(word in msg_lower for word in ["owe", "balance", "how much", "settled"]):
            return IntentDetectionResult(
                intent="view_balance",
                confidence=0.8,
                entities={},
                reasoning="Keywords: owe, balance, how much"
            )
        elif any(word in msg_lower for word in ["chore", "task", "assigned", "my task"]):
            return IntentDetectionResult(
                intent="view_chores",
                confidence=0.8,
                entities={},
                reasoning="Keywords: chore, task, assigned"
            )
        elif any(word in msg_lower for word in ["paid", "groceries", "split", "expense", "cost"]):
            return IntentDetectionResult(
                intent="create_expense",
                confidence=0.7,
                entities={},
                reasoning="Keywords: paid, expense, split"
            )
        elif any(word in msg_lower for word in ["broken", "maintenance", "issue", "geyser", "problem"]):
            return IntentDetectionResult(
                intent="create_maintenance",
                confidence=0.8,
                entities={},
                reasoning="Keywords: broken, maintenance, issue"
            )
        elif any(word in msg_lower for word in ["shopping", "add item", "buy", "groceries"]):
            return IntentDetectionResult(
                intent="add_shopping_item",
                confidence=0.7,
                entities={},
                reasoning="Keywords: shopping, add item"
            )
        else:
            return IntentDetectionResult(
                intent="other",
                confidence=0.0,
                entities={},
                reasoning="No matching keywords"
            )
    
    def generate_explanation(
        self,
        action_performed: str,
        action_result: Dict[str, Any],
        user_message: str
    ) -> str:
        """Generate explanation using heuristic."""
        status = action_result.get("status", "unknown")
        if status == "success":
            return f"Action completed successfully: {action_performed}"
        elif status == "error":
            error = action_result.get("message", "Unknown error")
            return f"Action failed: {error}"
        else:
            return f"Action executed: {action_performed}"
