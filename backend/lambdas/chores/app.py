"""
RoomieOps Chores Lambda Handler

API Gateway routes:
  POST   /households/{id}/chores           - Create chore
  GET    /households/{id}/chores           - List chores
  POST   /households/{id}/chores/{c_id}/complete - Complete chore (rotate)
"""

import json
import os
import sys
import logging
import uuid

sys.path.insert(0, "/opt/python")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../shared"))

from dynamodb_ops import DynamoDBOps
from auth import require_auth, verify_household_membership

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """Main Lambda handler for chore operations."""
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
        if method == "POST" and "/complete" in path:
            household_id, chore_id = extract_ids(path, "/chores/", "/complete")
            return complete_chore(user, household_id, chore_id)
        elif method == "POST" and "/chores" in path and "/chores/" not in path:
            household_id = extract_household_id(path)
            return create_chore(user, household_id, body)
        elif method == "GET" and "/chores" in path and "/chores/" not in path:
            household_id = extract_household_id(path)
            return list_chores(user, household_id)
        else:
            return error_response(404, f"Route not found: {method} {path}")

    except ValueError as e:
        if "Unauthenticated" in str(e):
            return error_response(401, "Unauthenticated request")
        return error_response(403, str(e))
    except Exception as e:
        logger.error(f"Unhandled error: {str(e)}", exc_info=True)
        return error_response(500, str(e))


def create_chore(user, household_id, body):
    """
    POST /households/{id}/chores
    Create a chore with round-robin rotation.
    """
    try:
        # Verify membership
        members = DynamoDBOps.get_members(household_id)
        if not verify_household_membership(user, household_id, members):
            return error_response(403, "Access denied: not a member of this household")

        name = body.get("name")
        rotation_order = body.get("rotation_order", [])
        frequency = body.get("frequency", "weekly")

        if not name or not rotation_order:
            return error_response(400, "Missing: name, rotation_order")

        if len(rotation_order) < 2:
            return error_response(400, "rotation_order must have at least 2 people")

        chore_id = str(uuid.uuid4())
        assigned_to = rotation_order[0]  # Start with first person

        chore = DynamoDBOps.create_chore(
            household_id=household_id,
            chore_id=chore_id,
            name=name,
            assigned_to=assigned_to,
            frequency=frequency,
            rotation_order=rotation_order,
            created_by=user.user_id,
        )

        return success_response(201, chore)
    except Exception as e:
        logger.error(f"Error creating chore: {str(e)}")
        return error_response(500, str(e))


def list_chores(user, household_id):
    """GET /households/{id}/chores - List all chores."""
    try:
        # Verify membership
        members = DynamoDBOps.get_members(household_id)
        if not verify_household_membership(user, household_id, members):
            return error_response(403, "Access denied: not a member of this household")

        chores = DynamoDBOps.get_chores(household_id)
        return success_response(200, {"chores": chores})
    except Exception as e:
        logger.error(f"Error listing chores: {str(e)}")
        return error_response(500, str(e))


def complete_chore(user, household_id, chore_id):
    """
    POST /households/{id}/chores/{c_id}/complete
    Mark chore complete and rotate to next person in round-robin.
    """
    try:
        # Verify membership
        members = DynamoDBOps.get_members(household_id)
        if not verify_household_membership(user, household_id, members):
            return error_response(403, "Access denied: not a member of this household")

        chore = DynamoDBOps.complete_chore(household_id, chore_id)
        return success_response(200, {
            "message": f"Chore rotated to {chore['assigned_to']}",
            "chore": chore,
        })
    except ValueError as e:
        return error_response(400, str(e))
    except Exception as e:
        logger.error(f"Error completing chore: {str(e)}")
        return error_response(500, str(e))


def extract_household_id(path):
    """Extract household ID from path."""
    parts = path.split("/")
    for i, part in enumerate(parts):
        if part == "households" and i + 1 < len(parts):
            return parts[i + 1]
    raise ValueError("Could not extract household_id")


def extract_ids(path, middle, suffix):
    """Extract household_id and chore_id from /households/{id}/chores/{c_id}/complete"""
    start_idx = path.find("/households/") + len("/households/")
    end_idx = path.find(middle)
    household_id = path[start_idx:end_idx]

    chore_start = path.find(middle) + len(middle)
    chore_end = path.find(suffix)
    chore_id = path[chore_start:chore_end]

    return household_id, chore_id


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
