"""Stage 3: Classify risk based on matched clauses."""
import json
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.bedrock import BedrockError, call_bedrock, extract_json_from_response
from shared.utils import error_response, log_event, success_response

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Valid enum values
VALID_RISK_TIERS = {"green", "yellow", "red"}
VALID_CONFIDENCE = {"high", "medium", "low"}


def lambda_handler(event, context):
    """
    Classify risk based on matched clauses.

    Input from Step Functions:
    {
        "documentId": "d-001",
        "matches": [...],
        "situation": "..."
    }

    Output:
    {
        "riskTier": "red",
        "clauseId": "c1",
        "reasoning": "...",
        "confidence": "high"
    }
    """
    try:
        log_event(event, context)

        document_id = event.get("documentId")
        matches = event.get("matches")
        situation = event.get("situation")

        if not all([document_id, matches, situation]):
            return error_response(
                "Missing required parameters", 400, "INVALID_REQUEST"
            )

        if not isinstance(matches, list):
            return error_response("Matches must be an array", 400, "INVALID_REQUEST")

        logger.info(f"Classifying risk for document {document_id} with {len(matches)} matches")

        # Format matches for prompt
        matches_text = json.dumps(matches, indent=2)

        # Load risk classification prompt
        try:
            prompt_template = open(
                os.path.join(os.path.dirname(__file__), "..", "..", "prompts", "classify-risk.txt")
            ).read()
        except:
            prompt_template = """Classify the risk tier based on the matches and situation.
Output ONLY valid JSON:
{"riskTier": "green|yellow|red", "clauseId": "c1", "reasoning": "...", "confidence": "high|medium|low"}"""

        prompt = prompt_template.replace("{matches_json}", matches_text).replace(
            "{situation}", situation
        )

        # Call Bedrock
        try:
            response_text = call_bedrock(prompt, max_tokens=1024)
            result = extract_json_from_response(response_text)
        except BedrockError as e:
            logger.error(f"Bedrock risk classification failed: {str(e)}")
            return error_response(
                "Could not classify risk",
                500,
                "CLASSIFICATION_FAILED",
            )

        # Validate result
        if not isinstance(result, dict):
            return error_response(
                "Invalid classification format", 500, "CLASSIFICATION_FORMAT_ERROR"
            )

        # Validate required fields
        for field in ["riskTier", "clauseId", "reasoning", "confidence"]:
            if field not in result:
                logger.error(f"Missing field in classification: {field}")
                return error_response(
                    f"Missing required field: {field}",
                    500,
                    "CLASSIFICATION_FORMAT_ERROR",
                )

        # Validate enum values
        risk_tier = result.get("riskTier")
        confidence = result.get("confidence")

        if risk_tier not in VALID_RISK_TIERS:
            logger.error(f"Invalid risk tier: {risk_tier}")
            return error_response(
                f"Invalid risk tier: {risk_tier}",
                500,
                "INVALID_RISK_TIER",
            )

        if confidence not in VALID_CONFIDENCE:
            logger.error(f"Invalid confidence: {confidence}")
            return error_response(
                f"Invalid confidence: {confidence}",
                500,
                "INVALID_CONFIDENCE",
            )

        logger.info(
            f"Risk classified as {risk_tier} with {confidence} confidence"
        )

        return success_response(result)

    except Exception as e:
        logger.error(f"Unexpected error in risk classification: {str(e)}")
        return error_response("Internal server error", 500, "INTERNAL_ERROR")
