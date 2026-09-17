"""Stage 2: Match user situation against extracted clauses."""
import json
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.bedrock import BedrockError, call_bedrock, extract_json_from_response
from shared.utils import error_response, log_event, success_response

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Match user's situation against extracted clauses.

    Input from Step Functions:
    {
        "documentId": "d-001",
        "clauses": [...],
        "situation": "I have 72% attendance..."
    }

    Output:
    {
        "matches": [
            {
                "clauseId": "c1",
                "relevance": "direct",
                "userFact": "72% attendance"
            }
        ]
    }
    """
    try:
        log_event(event, context)

        document_id = event.get("documentId")
        clauses = event.get("clauses")
        situation = event.get("situation")

        if not all([document_id, clauses, situation]):
            return error_response(
                "Missing required parameters", 400, "INVALID_REQUEST"
            )

        if not isinstance(clauses, list):
            return error_response("Clauses must be an array", 400, "INVALID_REQUEST")

        logger.info(f"Matching {len(clauses)} clauses for document {document_id}")

        # Format clauses for prompt
        clauses_text = json.dumps(clauses, indent=2)

        # Load matching prompt
        try:
            prompt_template = open(
                os.path.join(os.path.dirname(__file__), "..", "..", "prompts", "match-situation.txt")
            ).read()
        except:
            prompt_template = """Determine which clauses are relevant to the user's situation.
Output ONLY valid JSON with this structure:
{"matches": [{"clauseId": "c1", "relevance": "direct", "userFact": "..."}]}"""

        prompt = prompt_template.replace("{clauses_json}", clauses_text).replace(
            "{situation}", situation
        )

        # Call Bedrock
        try:
            response_text = call_bedrock(prompt, max_tokens=1024)
            result = extract_json_from_response(response_text)
        except BedrockError as e:
            logger.error(f"Bedrock matching failed: {str(e)}")
            return error_response(
                "Could not match clauses to situation",
                500,
                "MATCHING_FAILED",
            )

        # Validate result
        if not isinstance(result, dict) or "matches" not in result:
            return error_response(
                "Invalid matching format", 500, "MATCHING_FORMAT_ERROR"
            )

        matches = result.get("matches", [])
        if not isinstance(matches, list):
            return error_response(
                "Matches must be an array", 500, "MATCHING_FORMAT_ERROR"
            )

        # Validate clause IDs exist
        clause_ids = {c["clauseId"] for c in clauses}
        for match in matches:
            if match.get("clauseId") not in clause_ids:
                logger.error(f"Invalid clause ID in match: {match.get('clauseId')}")
                return error_response(
                    "Match references non-existent clause",
                    500,
                    "INVALID_CLAUSE_REFERENCE",
                )

        logger.info(f"Matched {len(matches)} clauses successfully")

        return success_response({"matches": matches})

    except Exception as e:
        logger.error(f"Unexpected error in matching: {str(e)}")
        return error_response("Internal server error", 500, "INTERNAL_ERROR")
