"""
DEPRECATED: Legacy Bedrock integration module.

This module is maintained for backward compatibility only.
New code should use bedrock_client.py which delegates to LLMProvider abstraction.

The provider layer (backend/shared/providers/llm.py) handles:
- SHIP_IT: BedrockLLMProvider
- BUILD_IT: OllamaLLMProvider  
- LOCAL_HEURISTIC: HeuristicLLMProvider

This module will be removed in a future refactor.
"""
import json
import logging
from typing import Any, Dict

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

logger.warning(
    "bedrock.py is DEPRECATED. Use bedrock_client.py with provider abstraction instead."
)

# Try to initialize boto3 client; if it fails (no AWS creds), set to None
# The module will still import successfully, and call_bedrock will raise BedrockError
try:
    bedrock = boto3.client("bedrock-runtime")
except Exception as e:
    logger.warning(f"Failed to initialize boto3 Bedrock client: {e}")
    bedrock = None


class BedrockError(Exception):
    """Custom exception for Bedrock API errors."""

    pass


def call_bedrock(
    prompt: str, model_id: str = None, max_tokens: int = 2048
) -> str:
    """
    Call Bedrock Claude model with the given prompt.

    Args:
        prompt: The full prompt to send to Claude
        model_id: The Bedrock model ID (defaults to env var BEDROCK_MODEL_ID)
        max_tokens: Maximum tokens in response

    Returns:
        The model's text response

    Raises:
        BedrockError: If the API call fails or response is invalid
    """
    if bedrock is None:
        raise BedrockError("Bedrock client not available (no AWS credentials)")
    
    if model_id is None:
        import os

        model_id = os.environ.get(
            "BEDROCK_MODEL_ID", "anthropic.claude-sonnet-4-5-20250929-v1:0"
        )

    try:
        logger.info(f"Calling Bedrock with model: {model_id}")

        response = bedrock.invoke_model(
            modelId=model_id,
            body=json.dumps(
                {
                    "anthropic_version": "bedrock-2023-06-01",
                    "max_tokens": max_tokens,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                }
            ),
        )

        response_body = json.loads(response["body"].read())
        text = response_body["content"][0]["text"]
        logger.info(f"Bedrock response received, length: {len(text)}")
        return text

    except Exception as e:
        logger.error(f"Bedrock API error: {str(e)}")
        raise BedrockError(f"Failed to call Bedrock: {str(e)}")


def extract_json_from_response(response: str) -> Dict[str, Any]:
    """
    Extract JSON from Bedrock response.

    The response might contain markdown code blocks or extra text.
    This extracts the JSON object.

    Args:
        response: The raw response from Bedrock

    Returns:
        Parsed JSON object

    Raises:
        BedrockError: If JSON cannot be extracted or parsed
    """
    try:
        # Try direct JSON parse first
        return json.loads(response)
    except json.JSONDecodeError:
        pass

    # Try to extract from markdown code block
    if "```json" in response:
        start = response.find("```json") + 7
        end = response.find("```", start)
        if end > start:
            try:
                return json.loads(response[start:end].strip())
            except json.JSONDecodeError:
                pass

    # Try to extract from just markdown
    if "```" in response:
        start = response.find("```") + 3
        end = response.find("```", start)
        if end > start:
            try:
                return json.loads(response[start:end].strip())
            except json.JSONDecodeError:
                pass

    # Last resort: look for first { and last }
    start = response.find("{")
    end = response.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(response[start : end + 1])
        except json.JSONDecodeError:
            pass

    raise BedrockError(f"Could not extract JSON from response: {response[:200]}")
