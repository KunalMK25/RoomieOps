"""
RoomieOps Expenses Lambda Handler

API Gateway routes:
  POST   /households/{id}/expenses               - Create expense
  POST   /households/{id}/expenses/calculate     - Calculate split (no persistence)
  GET    /households/{id}/expenses/{exp_id}      - Get expense details
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
from finance_engine import FinanceEngine, SplitMethod
from auth import require_auth, verify_household_membership
from idempotency import IdempotencyOps

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """Main Lambda handler for expense operations."""
    logger.info(f"Event: {json.dumps(event)}")

    try:
        # Require authentication
        user = require_auth(event)

        method = event.get("httpMethod", "GET")
        path = event.get("path", "")
        body = event.get("body", "{}")

        if isinstance(body, str):
            body = json.loads(body) if body else {}

        # Route handling
        if method == "POST" and "/expenses/calculate" in path:
            household_id = extract_household_id(path)
            return calculate_split(user, household_id, body)
        elif method == "POST" and "/expenses" in path and "/expenses/" not in path:
            household_id = extract_household_id(path)
            return create_expense(user, household_id, body)
        elif method == "GET" and "/expenses/" in path:
            household_id = extract_household_id(path)
            expense_id = path.split("/expenses/")[-1]
            return get_expense(user, household_id, expense_id)
        else:
            return error_response(404, f"Route not found: {method} {path}")

    except ValueError as e:
        if "Unauthenticated" in str(e):
            return error_response(401, "Unauthenticated request")
        return error_response(403, str(e))
    except Exception as e:
        logger.error(f"Unhandled error: {str(e)}", exc_info=True)
        return error_response(500, str(e))


def calculate_split(user, household_id, body):
    """
    POST /households/{id}/expenses/calculate
    Calculate expense split without persisting.
    """
    try:
        # Verify membership
        members = DynamoDBOps.get_members(household_id)
        if not verify_household_membership(user, household_id, members):
            return error_response(403, "Access denied: not a member of this household")

        total_paise = body.get("amount_paise")
        if not total_paise:
            return error_response(400, "Missing: amount_paise")

        split_method = body.get("split_method", "equal")
        participants = body.get("participants", [])

        if not participants:
            return error_response(400, "Must have at least one participant")

        # Route to appropriate split method
        if split_method == "equal":
            result = FinanceEngine.split_equal(total_paise, participants)
        elif split_method == "exact":
            exact_allocations = body.get("split_params", {}).get("allocations", {})
            result = FinanceEngine.split_exact(total_paise, exact_allocations)
        elif split_method == "percentage":
            percentages = body.get("split_params", {}).get("percentages", {})
            result = FinanceEngine.split_percentage(total_paise, percentages)
        else:
            return error_response(400, f"Unknown split method: {split_method}")

        response_data = {
            "total_paise": result.total_amount_paise,
            "method": result.method.value,
            "allocations": [
                {"user_id": a.user_id, "amount_paise": a.amount_paise}
                for a in result.allocations
            ],
            "reconciliation_note": result.reconciliation_note,
        }

        return success_response(200, response_data)
    except ValueError as e:
        return error_response(400, str(e))
    except Exception as e:
        logger.error(f"Error calculating split: {str(e)}")
        return error_response(500, str(e))


def create_expense(user, household_id, body):
    """
    POST /households/{id}/expenses
    Create and persist an expense with automatic split calculation.
    Idempotent: same requestId returns cached result.
    """
    try:
        # Verify membership
        members = DynamoDBOps.get_members(household_id)
        if not verify_household_membership(user, household_id, members):
            return error_response(403, "Access denied: not a member of this household")

        payer_id = body.get("payer_id")
        description = body.get("description")
        total_paise = body.get("amount_paise")
        split_method = body.get("split_method", "equal")
        participants = body.get("participants", [])
        request_id = body.get("requestId")

        if not payer_id or not description or not total_paise:
            return error_response(400, "Missing: payer_id, description, amount_paise")

        if not participants:
            participants = [payer_id]

        # Check idempotency
        cached = IdempotencyOps.get_idempotency_result(household_id, request_id)
        if cached:
            return success_response(201, cached)

        # Calculate split
        if split_method == "equal":
            result = FinanceEngine.split_equal(total_paise, participants)
        elif split_method == "exact":
            exact_allocations = body.get("split_params", {}).get("allocations", {})
            result = FinanceEngine.split_exact(total_paise, exact_allocations)
        elif split_method == "percentage":
            percentages = body.get("split_params", {}).get("percentages", {})
            result = FinanceEngine.split_percentage(total_paise, percentages)
        else:
            return error_response(400, f"Unknown split method: {split_method}")

        # Convert allocations to DynamoDB format
        allocations = [
            {"user_id": a.user_id, "amount_paise": a.amount_paise}
            for a in result.allocations
        ]

        # Persist to DynamoDB
        expense_id = str(uuid.uuid4())
        expense = DynamoDBOps.create_expense(
            household_id=household_id,
            expense_id=expense_id,
            payer_id=payer_id,
            description=description,
            total_paise=total_paise,
            allocations=allocations,
            split_method=split_method,
            created_by=user.user_id,
        )

        # Update balances for all participants
        expenses = [
            {
                "payer_id": payer_id,
                "allocations": allocations,
            }
        ]
        balances = FinanceEngine.calculate_balances(expenses)

        for user_id, balance_paise in balances.items():
            DynamoDBOps.set_balance(household_id, user_id, balance_paise)

        response_data = {
            "expense": expense,
            "allocations": allocations,
            "updated_balances": balances,
        }

        # Store idempotency result
        if request_id:
            try:
                IdempotencyOps.store_idempotency_result(
                    household_id, "create_expense", request_id, response_data
                )
            except Exception as e:
                logger.warning(f"Failed to store idempotency result: {e}")

        return success_response(201, response_data)
    except ValueError as e:
        return error_response(400, str(e))
    except Exception as e:
        logger.error(f"Error creating expense: {str(e)}")
        return error_response(500, str(e))


def get_expense(user, household_id, expense_id):
    """GET /households/{id}/expenses/{exp_id}"""
    try:
        # Verify membership
        members = DynamoDBOps.get_members(household_id)
        if not verify_household_membership(user, household_id, members):
            return error_response(403, "Access denied: not a member of this household")

        # TODO: Implement get_expense in DynamoDBOps
        return error_response(501, "Not yet implemented")
    except Exception as e:
        logger.error(f"Error getting expense: {str(e)}")
        return error_response(500, str(e))


def extract_household_id(path):
    """Extract household ID from path."""
    parts = path.split("/")
    for i, part in enumerate(parts):
        if part == "households" and i + 1 < len(parts):
            return parts[i + 1]
    raise ValueError("Could not extract household_id from path")


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
