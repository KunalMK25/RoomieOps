"""RoomieOps Expenses - Create, track, and manage shared expenses."""
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
    Expenses Handler.

    Manages expense operations:
    - Create expense
    - Get expense list
    - Calculate split
    - Get balances

    Request:
    {
        "operation": "create|list|calculate_split|get_balances",
        "household_id": "h-001",
        "params": {...}
    }
    """
    try:
        log_event(event, context)

        # Extract user ID
        try:
            user_id = extract_user_id(event)
        except ValueError:
            return error_response("Unauthorized", 401, "UNAUTHORIZED")

        # Extract body
        try:
            body = json.loads(event.get("body", "{}"))
        except json.JSONDecodeError as e:
            return error_response(f"Invalid request: {str(e)}", 400, "INVALID_REQUEST")

        operation = body.get("operation")
        household_id = body.get("household_id")

        if not all([operation, household_id]):
            return error_response("Missing required parameters", 400, "INVALID_REQUEST")

        logger.info(f"Expense operation: {operation} for {household_id}")

        # TODO: Implement expense operations
        # - create: Add new expense
        # - list: Get expenses
        # - calculate_split: Compute fair split (MONEY SAFETY: use deterministic backend functions)
        # - get_balances: Calculate who owes whom

        response = {
            "operation": operation,
            "status": "success",
            "data": {}
        }

        logger.info("Expense operation completed")
        return success_response(response)

    except Exception as e:
        logger.error(f"Unexpected error in expenses handler: {str(e)}")
        return error_response("Internal server error", 500, "INTERNAL_ERROR")
