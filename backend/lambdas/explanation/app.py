"""Stage 4: Generate explanation in target language."""
import json
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shared.bedrock import BedrockError, call_bedrock, extract_json_from_response
from shared.utils import error_response, log_event, success_response

logger = logging.getLogger()
logger.setLevel(logging.INFO)

VALID_LANGUAGES = {"en", "kn"}


def lambda_handler(event, context):
    """
    Generate explanation in target language.

    Input from Step Functions:
    {
        "documentId": "d-001",
        "riskResult": {...},
        "clauses": [...],
        "language": "en"
    }

    Output:
    {
        "explanation": "...",
        "language": "en"
    }
    """
    try:
        log_event(event, context)

        document_id = event.get("documentId")
        risk_result = event.get("riskResult")
        clauses = event.get("clauses")
        language = event.get("language", "en")

        if not all([document_id, risk_result, clauses]):
            return error_response(
                "Missing required parameters", 400, "INVALID_REQUEST"
            )

        if language not in VALID_LANGUAGES:
            return error_response(
                f"Unsupported language: {language}", 400, "INVALID_LANGUAGE"
            )

        # If confidence is low, return a generic "needs manual check" explanation
        confidence = risk_result.get("confidence")
        if confidence == "low":
            if language == "kn":
                generic_explanation = "ಈ ಫಲಿತಾಂಶವು ವಿವರವಾದ ಪರಿಶೀಲನೆ ಅಗತ್ಯವಿದೆ. ದಯವಿಟ್ಟು ಮೂಲ ಡಾಕ್ಯುಮೆಂಟ್ ಮತ್ತು ಸಂಸ್ಥಾಯ ಪೌಳಿಸೇಯು ಪರಿಶೀಲಿಸಿ."
            else:
                generic_explanation = "This result requires manual verification. Please review the source document and official institutional guidance."
            logger.info(f"Skipping explanation generation due to low confidence")
            return success_response({
                "explanation": generic_explanation,
                "language": language,
                "lowConfidence": True
            })

        logger.info(f"Generating explanation in {language} for document {document_id}")

        # Find source clause
        source_clause_id = risk_result.get("clauseId")
        source_clause = None
        for clause in clauses:
            if clause.get("clauseId") == source_clause_id:
                source_clause = clause
                break

        if not source_clause:
            logger.warning(f"Could not find source clause: {source_clause_id}")

        # Load explanation prompt
        try:
            prompt_template = open(
                os.path.join(os.path.dirname(__file__), "..", "..", "prompts", "explain-translate.txt")
            ).read()
        except:
            prompt_template = """Generate a clear explanation of the risk result.
Output ONLY valid JSON:
{"explanation": "...", "language": "{language}"}"""

        source_clause_text = json.dumps(source_clause) if source_clause else ""
        prompt = (
            prompt_template
            .replace("{risk_result_json}", json.dumps(risk_result))
            .replace("{source_clause_text}", source_clause_text)
            .replace("{language}", language)
        )

        # Call Bedrock
        try:
            response_text = call_bedrock(prompt, max_tokens=512)
            result = extract_json_from_response(response_text)
        except BedrockError as e:
            logger.error(f"Bedrock explanation failed: {str(e)}")
            return error_response(
                "Could not generate explanation",
                500,
                "EXPLANATION_FAILED",
            )

        # Validate result
        if not isinstance(result, dict) or "explanation" not in result:
            return error_response(
                "Invalid explanation format", 500, "EXPLANATION_FORMAT_ERROR"
            )

        # Ensure language is set
        if "language" not in result:
            result["language"] = language

        logger.info(f"Explanation generated successfully")

        return success_response(result)

    except Exception as e:
        logger.error(f"Unexpected error in explanation generation: {str(e)}")
        return error_response("Internal server error", 500, "INTERNAL_ERROR")
