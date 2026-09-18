"""
RoomieOps Households Lambda Handler

API Gateway routes:
  POST   /households                      - Create household
  GET    /households/{id}                 - Get household details
  GET    /households/{id}/members         - List members
  POST   /households/{id}/members         - Add member
  GET    /households/{id}/expenses        - List expenses
  GET    /households/{id}/balances        - Get all balances
  GET    /households/{id}/chores          - List chores
"""

import json
import os
import sys
import logging
from datetime import datetime

# Add shared layer to path
sys.path.insert(0, "/opt/python")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../shared"))

from dynamodb_ops import DynamoDBOps
from finance_engine import FinanceEngine
from auth import require_auth, verify_household_membership, verify_admin_permission

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """Main Lambda handler for household operations."""
    logger.info(f"Event: {json.dumps(event)}")

    try:
        # Require authentication for all P0 household operations
        user = require_auth(event)
        
        # Extract HTTP method and path
        method = event.get("httpMethod", "GET")
        path = event.get("path", "")
        body = event.get("body", "{}")

        if isinstance(body, str):
            body = json.loads(body) if body else {}

        # Route handling
        if method == "POST" and path == "/households":
            return create_household(user, body)
        elif method == "GET" and path.startswith("/households/") and path.endswith("/members"):
            household_id = extract_id(path, "/households", "/members")
            return get_members(user, household_id)
        elif method == "POST" and path.startswith("/households/") and path.endswith("/members"):
            household_id = extract_id(path, "/households", "/members")
            return add_member(user, household_id, body)
        elif method == "GET" and path.startswith("/households/") and path.endswith("/expenses"):
            household_id = extract_id(path, "/households", "/expenses")
            return get_expenses(user, household_id)
        elif method == "GET" and path.startswith("/households/") and path.endswith("/balances"):
            household_id = extract_id(path, "/households", "/balances")
            return get_balances(user, household_id)
        elif method == "GET" and path.startswith("/households/") and path.endswith("/chores"):
            household_id = extract_id(path, "/households", "/chores")
            return get_chores(user, household_id)
        elif method == "GET" and path.startswith("/households/"):
            household_id = path.split("/")[-1]
            return get_household(user, household_id)
        else:
            return error_response(404, f"Route not found: {method} {path}")

    except ValueError as e:
        # Authentication or authorization failed
        if "Unauthenticated" in str(e):
            return error_response(401, "Unauthenticated request")
        return error_response(403, str(e))
    except Exception as e:
        logger.error(f"Unhandled error: {str(e)}", exc_info=True)
        return error_response(500, f"Internal server error: {str(e)}")


def create_household(user, body):
    """POST /households - Create new household."""
    try:
        name = body.get("name")
        if not name:
            return error_response(400, "Missing required field: name")

        household_id = body.get("household_id") or datetime.utcnow().isoformat()
        description = body.get("description", "")
        policy = body.get("policy")

        # Create household (authenticated user will be added as admin)
        household = DynamoDBOps.create_household(
            household_id=household_id,
            name=name,
            description=description,
            policy=policy,
            created_by=user.user_id,
        )

        # Add creator as admin member
        DynamoDBOps.add_member(
            household_id=household_id,
            user_id=user.user_id,
            name=user.username,
            email=user.email or "",
            role="admin",
        )

        return success_response(201, household)
    except Exception as e:
        logger.error(f"Error creating household: {str(e)}")
        return error_response(500, str(e))


def get_household(user, household_id):
    """GET /households/{id} - Get household details."""
    try:
        household = DynamoDBOps.get_household(household_id)
        if not household:
            return error_response(404, f"Household {household_id} not found")

        # Verify membership
        members = DynamoDBOps.get_members(household_id)
        if not verify_household_membership(user, household_id, members):
            return error_response(403, "Access denied: not a member of this household")

        return success_response(200, household)
    except Exception as e:
        logger.error(f"Error getting household: {str(e)}")
        return error_response(500, str(e))


def get_members(user, household_id):
    """GET /households/{id}/members - List all members."""
    try:
        # Verify membership
        members = DynamoDBOps.get_members(household_id)
        if not verify_household_membership(user, household_id, members):
            return error_response(403, "Access denied: not a member of this household")

        return success_response(200, {"members": members})
    except Exception as e:
        logger.error(f"Error getting members: {str(e)}")
        return error_response(500, str(e))


def add_member(user, household_id, body):
    """POST /households/{id}/members - Add a member (admin only)."""
    try:
        # Verify membership
        members = DynamoDBOps.get_members(household_id)
        if not verify_household_membership(user, household_id, members):
            return error_response(403, "Access denied: not a member of this household")

        # Verify admin permission
        if not verify_admin_permission(user, household_id, members):
            return error_response(403, "Access denied: admin permission required")

        user_id = body.get("user_id")
        name = body.get("name")
        email = body.get("email", "")
        role = body.get("role", "member")

        if not user_id or not name:
            return error_response(400, "Missing required fields: user_id, name")

        member = DynamoDBOps.add_member(
            household_id=household_id,
            user_id=user_id,
            name=name,
            email=email,
            role=role,
        )

        return success_response(201, member)
    except Exception as e:
        logger.error(f"Error adding member: {str(e)}")
        return error_response(500, str(e))


def get_expenses(user, household_id):
    """GET /households/{id}/expenses - List expenses."""
    try:
        # Verify membership
        members = DynamoDBOps.get_members(household_id)
        if not verify_household_membership(user, household_id, members):
            return error_response(403, "Access denied: not a member of this household")

        expenses = DynamoDBOps.get_expenses(household_id)
        return success_response(200, {"expenses": expenses})
    except Exception as e:
        logger.error(f"Error getting expenses: {str(e)}")
        return error_response(500, str(e))


def get_balances(user, household_id):
    """GET /households/{id}/balances - Get all balances."""
    try:
        # Verify membership
        members = DynamoDBOps.get_members(household_id)
        if not verify_household_membership(user, household_id, members):
            return error_response(403, "Access denied: not a member of this household")

        balances = DynamoDBOps.get_all_balances(household_id)
        return success_response(200, {"balances": balances})
    except Exception as e:
        logger.error(f"Error getting balances: {str(e)}")
        return error_response(500, str(e))


def get_chores(user, household_id):
    """GET /households/{id}/chores - List chores."""
    try:
        # Verify membership
        members = DynamoDBOps.get_members(household_id)
        if not verify_household_membership(user, household_id, members):
            return error_response(403, "Access denied: not a member of this household")

        chores = DynamoDBOps.get_chores(household_id)
        return success_response(200, {"chores": chores})
    except Exception as e:
        logger.error(f"Error getting chores: {str(e)}")
        return error_response(500, str(e))


def extract_id(path, prefix, suffix):
    """Extract ID from path like /households/{id}/members."""
    start = len(prefix) + 1
    end = len(path) - len(suffix)
    return path[start:end]


def success_response(status_code, data):
    """Format successful response."""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(data),
    }


def error_response(status_code, message):
    """Format error response."""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": message}),
    }
