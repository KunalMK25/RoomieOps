"""Stage 1: Extract relevant clauses from document."""
import json
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import boto3

from shared.bedrock import BedrockError, call_bedrock, extract_json_from_response
from shared.utils import error_response, log_event, success_response

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")


def lambda_handler(event, context):
    """
    Extract clauses from uploaded document.

    Input from Step Functions:
    {
        "documentId": "d-001",
        "s3Key": "documents/d-001.pdf"
    }

    Output:
    {
        "clauses": [
            {
                "clauseId": "c1",
                "text": "Exact clause text",
                "section": "4.1"
            }
        ]
    }
    """
    try:
        log_event(event, context)

        document_id = event.get("documentId")
        s3_key = event.get("s3Key")
        bucket = os.environ.get("S3_BUCKET")

        if not all([document_id, s3_key, bucket]):
            return error_response(
                "Missing required parameters", 400, "INVALID_REQUEST"
            )

        logger.info(f"Extracting clauses from {s3_key}")

        # Download document from S3
        try:
            response = s3.get_object(Bucket=bucket, Key=s3_key)
            document_content = response["Body"].read().decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to download document: {str(e)}")
            return error_response("Failed to read document", 400, "DOCUMENT_READ_ERROR")

        # Load extraction prompt
        prompt_template = open(
            os.path.join(os.path.dirname(__file__), "..", "..", "prompts", "extract.txt")
        ).read()
        prompt = prompt_template.replace("{document_text}", document_content)

        # Call Bedrock
        try:
            response_text = call_bedrock(prompt, max_tokens=2048)
            result = extract_json_from_response(response_text)
        except BedrockError as e:
            logger.error(f"Bedrock extraction failed: {str(e)}")
            # Retry once with a stricter prompt
            logger.info("Retrying extraction with fallback prompt...")
            try:
                fallback_prompt = f"""Extract all substantive rules from this document into JSON format.

DOCUMENT:
{document_content}

Return ONLY valid JSON with this exact structure:
{{"clauses": [{{"clauseId": "c1", "text": "...", "section": "..."}}]}}

If no valid clauses found, return {{"clauses": []}}"""

                response_text = call_bedrock(fallback_prompt, max_tokens=1024)
                result = extract_json_from_response(response_text)
            except Exception as retry_error:
                logger.error(f"Extraction retry failed: {str(retry_error)}")
                return error_response(
                    "Could not extract clauses from document",
                    422,
                    "EXTRACTION_FAILED",
                )

        # Validate result
        if not isinstance(result, dict) or "clauses" not in result:
            logger.error(f"Invalid extraction result structure: {result}")
            return error_response(
                "Invalid extraction format", 500, "EXTRACTION_FORMAT_ERROR"
            )

        clauses = result.get("clauses", [])
        if not isinstance(clauses, list):
            return error_response(
                "Clauses must be an array", 500, "EXTRACTION_FORMAT_ERROR"
            )

        if len(clauses) == 0:
            logger.warning("No clauses extracted from document")
            # Still return success but with empty clauses
            # Frontend will handle this as a fallback case

        # Validate each clause structure
        for clause in clauses:
            if not all(key in clause for key in ["clauseId", "text", "section"]):
                logger.error(f"Clause missing required fields: {clause}")
                return error_response(
                    "Invalid clause structure", 500, "EXTRACTION_FORMAT_ERROR"
                )

        logger.info(f"Extracted {len(clauses)} clauses successfully")

        return success_response({"clauses": clauses})

    except Exception as e:
        logger.error(f"Unexpected error in extract: {str(e)}")
        return error_response("Internal server error", 500, "INTERNAL_ERROR")
