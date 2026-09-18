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

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """Main Lambda handler for expense operations."""
    logger.info(f"Event: {json.dumps(event)}")

    try:
        method = event.get("httpMethod", "GET")
        path = event.get("path", "")
        body = event.get("body", "{}")

        if isinstance(body, str):
            body = json.loads(body) if body else {}

        # Route handling
        if method == "POST" and "/expenses/calculate" in path:
            household_id = extract_household_id(path)
            return calculate_split(household_id, body)
        elif method == "POST" and "/expenses" in path and "/expenses/" not in path:
            household_id = extract_household_id(path)
            return create_expense(household_id, body)
        elif method == "GET" and "/expenses/" in path:
            household_id = extract_household_id(path)
            expense_id = path.split("/expenses/")[-1]
            return get_expense(household_id, expense_id)
        else:
            return error_response(404, f"Route not found: {method} {path}")

    except Exception as e:
        logger.error(f"Unhandled error: {str(e)}", exc_info=True)
        return error_response(500, str(e))


def calculate_split(household_id, body):
    """
    POST /households/{id}/expenses/calculate
    Calculate expense split without persisting.
    
    Request body:
    {
        "amount_paise": 10000,
        "split_method": "equal",
        "participants": ["user1", "user2", "user3"],
        "split_params": {...}  // Optional: for exact/percentage splits
    }
    """
    try:
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


def create_expense(household_id, body):
    """
    POST /households/{id}/expenses
    Create and persist an expense with automatic split calculation.
    
    Request body:
    {
        "payer_id": "user1",
        "description": "Groceries",
        "amount_paise": 50000,
        "split_method": "equal",
        "participants": ["user1", "user2", "user3"],
        "split_params": {}  // Optional
    }
    """
    try:
        payer_id = body.get("payer_id")
        description = body.get("description")
        total_paise = body.get("amount_paise")
        split_method = body.get("split_method", "equal")
        participants = body.get("participants", [])

        if not payer_id or not description or not total_paise:
            return error_response(400, "Missing: payer_id, description, amount_paise")

        if not participants:
            participants = [payer_id]

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

        return success_response(201, {
            "expense": expense,
            "allocations": allocations,
            "updated_balances": balances,
        })
    except ValueError as e:
        return error_response(400, str(e))
    except Exception as e:
        logger.error(f"Error creating expense: {str(e)}")
        return error_response(500, str(e))


def get_expense(household_id, expense_id):
    """GET /households/{id}/expenses/{exp_id}"""
    try:
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
