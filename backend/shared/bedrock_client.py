"""
RoomieOps Bedrock Client

Wrapper around AWS Bedrock API for intent detection and explanation generation.
Uses Claude Sonnet (current model, per spec §37).

Model: anthropic.claude-sonnet-4-5-20250929-v1:0
"""

import json
import os
import logging
from typing import Dict, Optional, List

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configuration
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
BEDROCK_MODEL_ID = os.environ.get(
    "BEDROCK_MODEL_ID", "anthropic.claude-sonnet-4-5-20250929-v1:0"
)

bedrock_client = boto3.client("bedrock-runtime", region_name=AWS_REGION)


class BedrockError(Exception):
    """Raised when Bedrock invocation fails."""
    pass


class BedrockOps:
    """Bedrock operations for RoomieOps."""

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
                "requires_confirmation": bool,
            }

        Raises:
            BedrockError: If Bedrock invocation fails
        """
        try:
            prompt = f"""You are the RoomieOps household copilot assistant.

Analyze this user message and detect their intent.

User message: "{user_message}"

Household context:
- Members: {', '.join([m.get('name', 'unknown') for m in household_context.get('members', [])])}
- Recent balances: {household_context.get('balances', {})}
- Active chores: {household_context.get('chore_count', 0)}

Respond in JSON format only:
{{
  "intent": "view_balance" | "view_chores" | "create_expense" | "create_maintenance" | "add_shopping_item" | "other",
  "entities": {{}},
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation"
}}

Examples:
- "How much do I owe?" → intent: view_balance
- "What chores do I have?" → intent: view_chores
- "I paid ₹1200 for groceries, split equally" → intent: create_expense, entities: {{payer_id, amount_paise, split_method}}
- "The geyser is broken" → intent: create_maintenance, entities: {{description}}
"""

            response = bedrock_client.invoke_model(
                modelId=BEDROCK_MODEL_ID,
                contentType="application/json",
                accept="application/json",
                body=json.dumps({"prompt": prompt, "max_tokens": 500}),
            )

            response_body = json.loads(response["body"].read())
            
            # Parse Claude response
            if "completion" in response_body:
                text = response_body["completion"]
            elif "content" in response_body:
                text = response_body["content"][0]["text"] if response_body["content"] else ""
            else:
                text = str(response_body)

            # Extract JSON from response
            try:
                # Try to find JSON block
                import re
                json_match = re.search(r"\{.*\}", text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(0))
                else:
                    result = json.loads(text)
            except (json.JSONDecodeError, AttributeError):
                logger.warning(f"Failed to parse Bedrock response as JSON: {text}")
                result = {
                    "intent": "other",
                    "entities": {},
                    "confidence": 0.0,
                    "reasoning": "Failed to parse response",
                }

            logger.info(f"Intent detected: {result.get('intent')} (confidence: {result.get('confidence')})")
            return result

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "AccessDenied":
                logger.error(f"BLOCKED: Bedrock access denied - {str(e)}")
                raise BedrockError(f"BLOCKED — BEDROCK ACCOUNT ACCESS: {str(e)}")
            else:
                logger.error(f"Bedrock invocation failed: {str(e)}")
                raise BedrockError(f"Bedrock error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during intent detection: {str(e)}", exc_info=True)
            raise BedrockError(f"Unexpected error: {str(e)}")

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
            prompt = f"""Generate a brief, friendly explanation of this action result.

User asked: "{user_message}"
Action performed: {action_performed}
Result data: {json.dumps(action_result)}

Explain the result in 1-2 sentences, referencing actual numbers/data from the result.
Do NOT fabricate or exaggerate. Be factual."""

            response = bedrock_client.invoke_model(
                modelId=BEDROCK_MODEL_ID,
                contentType="application/json",
                accept="application/json",
                body=json.dumps({"prompt": prompt, "max_tokens": 200}),
            )

            response_body = json.loads(response["body"].read())
            
            if "completion" in response_body:
                text = response_body["completion"]
            elif "content" in response_body:
                text = response_body["content"][0]["text"] if response_body["content"] else ""
            else:
                text = str(response_body)

            logger.info(f"Explanation generated: {text[:100]}...")
            return text.strip()

        except Exception as e:
            logger.error(f"Failed to generate explanation: {str(e)}")
            # Return a safe fallback based on action_result
            return f"Action completed: {action_performed}"

    @staticmethod
    def test_invocation() -> Dict:
        """
        Test Bedrock invocation to verify configuration.

        Returns:
            Test result dict with status and details
        """
        try:
            logger.info(f"Testing Bedrock invocation with model: {BEDROCK_MODEL_ID}")
            
            test_prompt = "What is RoomieOps?"
            response = bedrock_client.invoke_model(
                modelId=BEDROCK_MODEL_ID,
                contentType="application/json",
                accept="application/json",
                body=json.dumps({"prompt": test_prompt, "max_tokens": 100}),
            )

            response_body = json.loads(response["body"].read())
            
            return {
                "status": "success",
                "model": BEDROCK_MODEL_ID,
                "region": AWS_REGION,
                "response_keys": list(response_body.keys()),
            }

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "AccessDenied":
                return {
                    "status": "blocked",
                    "reason": "AccessDenied - AWS account does not have Bedrock access",
                    "model": BEDROCK_MODEL_ID,
                    "region": AWS_REGION,
                    "error": str(e),
                }
            else:
                return {
                    "status": "error",
                    "reason": error_code,
                    "model": BEDROCK_MODEL_ID,
                    "region": AWS_REGION,
                    "error": str(e),
                }
        except Exception as e:
            return {
                "status": "error",
                "reason": "Unexpected error",
                "model": BEDROCK_MODEL_ID,
                "region": AWS_REGION,
                "error": str(e),
            }
