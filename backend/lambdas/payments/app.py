"""RoomieOps Payments - Record payments and settlement."""
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
    Payments Handler.

    Manages payment operations:
    - Record payment
    - Get payment history
    - Simplify settlement

    Request:
    {
        "operation": "record|history|simplify_settlement",
        "household_id": "h-001",
        "params": {...}
    }
    """
    try:
        log_event(event, context)

        try:
            user_id = extract_user_id(event)
        except ValueError:
            return error_response("Unauthorized", 401, "UNAUTHORIZED")

        try:
            body = json.loads(event.get("body", "{}"))
        except json.JSONDecodeError as e:
            return error_response(f"Invalid request: {str(e)}", 400, "INVALID_REQUEST")

        operation = body.get("operation")
        household_id = body.get("household_id")

        if not all([operation, household_id]):
            return error_response("Missing required parameters", 400, "INVALID_REQUEST")

        logger.info(f"Payment operation: {operation} for {household_id}")

        # TODO: Implement payment operations with MONEY SAFETY
        # - record: Record payment (integer paise, deterministic)
        # - history: Get payment records
        # - simplify_settlement: Calculate minimal settlement transactions

        response = {
            "operation": operation,
            "status": "success",
            "data": {}
        }

        return success_response(response)

    except Exception as e:
        logger.error(f"Unexpected error in payments handler: {str(e)}")
        return error_response("Internal server error", 500, "INTERNAL_ERROR")
