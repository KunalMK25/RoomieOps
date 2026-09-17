"""API: GET /documents/{id} - Fetch document processing status and results."""
import json
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import boto3

from shared.utils import error_response, extract_user_id, log_event, success_response

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")


def lambda_handler(event, context):
    """
    Fetch document status and processing results.

    Request:
    GET /documents/{id}

    Response:
    {
        "documentId": "d-...",
        "status": "complete|processing|failed",
        "extractedClauses": [...],
        "riskResult": {...},
        "explanations": {...},
        "error": null
    }
    """
    try:
        log_event(event, context)

        # Extract user ID
        try:
            user_id = extract_user_id(event)
        except ValueError:
            return error_response("Unauthorized", 401, "UNAUTHORIZED")

        # Extract document ID from path
        path_params = event.get("pathParameters", {})
        document_id = path_params.get("id") if path_params else None

        if not document_id:
            return error_response("Missing document ID", 400, "INVALID_REQUEST")

        logger.info(f"Fetching document {document_id} for user {user_id}")

        # Get DynamoDB table
        table_name = os.environ.get("DYNAMODB_TABLE")
        if not table_name:
            logger.error("DYNAMODB_TABLE not configured")
            return error_response("Server configuration error", 500, "CONFIG_ERROR")

        table = dynamodb.Table(table_name)

        # Query document
        try:
            response = table.get_item(Key={"documentId": document_id})
        except Exception as e:
            logger.error(f"DynamoDB query failed: {str(e)}")
            return error_response(
                "Could not fetch document", 500, "DYNAMODB_ERROR"
            )

        if "Item" not in response:
            logger.warning(f"Document not found: {document_id}")
            return error_response("Document not found", 404, "NOT_FOUND")

        item = response["Item"]

        # Verify ownership
        if item.get("ownerId") != user_id:
            logger.warning(f"Unauthorized access to document {document_id}")
            return error_response(
                "Not authorized to access this document", 403, "FORBIDDEN"
            )

        # Build response
        result = {
            "documentId": item.get("documentId"),
            "status": item.get("status", "unknown"),
            "createdAt": item.get("createdAt"),
            "extractedClauses": item.get("extractedClauses"),
            "riskResult": item.get("riskResult"),
            "explanations": item.get("explanations", {}),
            "error": item.get("error"),
        }

        logger.info(f"Document retrieved with status: {result['status']}")
        return success_response(result)

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return error_response("Internal server error", 500, "INTERNAL_ERROR")
