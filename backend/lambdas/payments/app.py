"""
RoomieOps Payments Lambda Handler

Handles payment recording and settlement operations.
P0: record_payment, get_balance_history
P2: settlement simplification algorithm
"""

import json
import os
import sys
import logging
from datetime import datetime
import uuid

sys.path.insert(0, "/opt/python")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../shared"))

from dynamodb_ops import DynamoDBOps
from auth import require_auth, verify_household_membership

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """Main Lambda handler for payment operations."""
    logger.info(f"Event: {json.dumps(event)}")

    try:
        user = require_auth(event)

        method = event.get("httpMethod", "GET")
        path = event.get("path", "")
        body = event.get("body", "{}")

        if isinstance(body, str):
            body = json.loads(body) if body else {}

        # Route handling
        if method == "POST" and "/payments" in path and "/payments/" not in path:
            household_id = extract_household_id(path)
            return record_payment(user, household_id, body)
        elif method == "GET" and "/payments/history" in path:
            household_id = extract_household_id(path)
            return get_payment_history(user, household_id)
        else:
            return error_response(404, f"Route not found: {method} {path}")

    except ValueError as e:
        if "Unauthenticated" in str(e):
            return error_response(401, "Unauthenticated request")
        return error_response(403, str(e))
    except Exception as e:
        logger.error(f"Unhandled error: {str(e)}", exc_info=True)
        return error_response(500, str(e))


def record_payment(user, household_id, body):
    """
    POST /households/{id}/payments
    Record a payment between household members.
    """
    try:
        members = DynamoDBOps.get_members(household_id)
        if not verify_household_membership(user, household_id, members):
            return error_response(403, "Access denied")

        from_user = body.get("from_user_id")
        to_user = body.get("to_user_id")
        amount_paise = body.get("amount_paise")
        description = body.get("description", "Payment")
        request_id = body.get("requestId", str(uuid.uuid4()))

        if not from_user or not to_user or not amount_paise:
            return error_response(400, "Missing: from_user_id, to_user_id, amount_paise")

        # Idempotency: Check if this payment already recorded
        existing_payment = DynamoDBOps.get_payment(household_id, request_id)
        if existing_payment:
            return success_response(200, existing_payment)

        # Record payment
        payment_id = str(uuid.uuid4())
        payment = {
            "payment_id": payment_id,
            "from_user_id": from_user,
            "to_user_id": to_user,
            "amount_paise": amount_paise,
            "description": description,
            "created_by": user.user_id,
            "created_at": datetime.utcnow().isoformat(),
            "request_id": request_id,
        }

        DynamoDBOps.record_payment(household_id, payment)

        # Update balances
        # from_user balance decreases (owes less)
        from_balance = DynamoDBOps.get_balance(household_id, from_user) or 0
        DynamoDBOps.set_balance(household_id, from_user, from_balance - amount_paise)

        # to_user balance increases (owed more)
        to_balance = DynamoDBOps.get_balance(household_id, to_user) or 0
        DynamoDBOps.set_balance(household_id, to_user, to_balance + amount_paise)

        # Audit
        DynamoDBOps._audit_log(
            household_id,
            "PAYMENT_RECORDED",
            {
                "payment_id": payment_id,
                "from_user": from_user,
                "to_user": to_user,
                "amount_paise": amount_paise,
                "request_id": request_id,
            }
        )

        return success_response(201, payment)
    except Exception as e:
        logger.error(f"Error recording payment: {str(e)}")
        return error_response(500, str(e))


def get_payment_history(user, household_id):
    """GET /households/{id}/payments/history"""
    try:
        members = DynamoDBOps.get_members(household_id)
        if not verify_household_membership(user, household_id, members):
            return error_response(403, "Access denied")

        # TODO: Query payments from DynamoDB
        return success_response(200, {"payments": []})
    except Exception as e:
        logger.error(f"Error getting payment history: {str(e)}")
        return error_response(500, str(e))


def extract_household_id(path):
    parts = path.split("/")
    for i, part in enumerate(parts):
        if part == "households" and i + 1 < len(parts):
            return parts[i + 1]
    raise ValueError("Could not extract household_id")


def success_response(status_code, data):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(data),
    }


def error_response(status_code, message):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": message}),
    }
