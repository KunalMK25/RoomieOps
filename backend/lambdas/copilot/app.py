"""
RoomieOps Copilot Lambda Handler

AI-powered household coordination copilot using Strands Agent.
- Intent detection with Bedrock fallback
- Tool selection and execution
- Multi-step workflow support
- Explanation generation
- Confirmation flow management

API routes:
  POST /households/{id}/copilot             - Send natural language request
  POST /households/{id}/copilot/confirm     - Confirm pending consequential action
"""

import json
import os
import sys
import logging
from datetime import datetime
import uuid

sys.path.insert(0, "/opt/python")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../shared"))

from auth import require_auth, verify_household_membership, AuthenticatedUser
from dynamodb_ops import DynamoDBOps
from bedrock_client import BedrockOps, BedrockError
from strands_agent import RoomieOpsAgent, ToolExecutionContext
from confirmation import ConfirmationManager, ActionType

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize confirmation manager with DynamoDB table
try:
    dynamodb = __import__("boto3").resource("dynamodb")
    table_name = os.environ.get("DYNAMODB_TABLE", "roomieops-household-state")
    table = dynamodb.Table(table_name)
    ConfirmationManager.set_table(table)
except Exception as e:
    logger.warning(f"Failed to initialize ConfirmationManager: {e}")



def lambda_handler(event, context):
    """Main Lambda handler for copilot operations."""
    logger.info(f"Event: {json.dumps(event)}")

    try:
        user = require_auth(event)

        method = event.get("httpMethod", "POST")
        path = event.get("path", "")
        body = event.get("body", "{}")

        if isinstance(body, str):
            body = json.loads(body) if body else {}

        # Route handling
        if method == "POST" and path.endswith("/copilot/confirm"):
            household_id = extract_household_id(path)
            return confirm_action(user, household_id, body)
        elif method == "POST" and path.endswith("/copilot"):
            household_id = extract_household_id(path)
            return process_copilot_request(user, household_id, body)
        else:
            return error_response(404, f"Route not found: {method} {path}")

    except ValueError as e:
        if "Unauthenticated" in str(e):
            return error_response(401, "Unauthenticated request")
        return error_response(403, str(e))
    except Exception as e:
        logger.error(f"Unhandled error: {str(e)}", exc_info=True)
        return error_response(500, str(e))


def process_copilot_request(user: AuthenticatedUser, household_id: str, body: dict):
    """
    POST /households/{id}/copilot
    
    Process a natural language request using the RoomieOps agent.
    
    Flow:
    1. Verify membership
    2. Create agent with user context
    3. Agent processes request (may use Bedrock or heuristic)
    4. Agent executes tools
    5. Return result with explanation
    """
    try:
        # Verify membership
        members = DynamoDBOps.get_members(household_id)
        if not verify_household_membership(user, household_id, members):
            return error_response(403, "Access denied: not a member of this household")

        request_text = body.get("message")
        if not request_text:
            return error_response(400, "Missing: message")

        # Create agent context
        request_id = str(uuid.uuid4())
        context = ToolExecutionContext(
            user=user,
            household_id=household_id,
            request_id=request_id
        )

        # Initialize agent
        agent = RoomieOpsAgent(context)

        # Process request
        logger.info(f"Agent processing: {request_text}")
        result = agent.process_user_request(request_text)

        logger.info(f"Agent result: {json.dumps(result)}")

        return success_response(200, {
            "message": request_text,
            "agent_response": result.get("response", ""),
            "agent_type": result.get("agent_type", "unknown"),
            "actions_taken": result.get("actions_taken", []),
            "status": result.get("status", "unknown"),
            "requires_confirmation": result.get("requires_confirmation", False),
            "action_id": result.get("action_id"),
            "data": result
        })

    except Exception as e:
        logger.error(f"Error processing copilot request: {str(e)}", exc_info=True)
        return error_response(500, str(e))


def confirm_action(user: AuthenticatedUser, household_id: str, body: dict):
    """
    POST /households/{id}/copilot/confirm
    
    Confirm or reject a pending consequential action.
    
    Request:
    {
        "action_id": "...",
        "confirmed": true/false
    }
    
    Response:
    {
        "status": "executed|rejected|failed",
        "action_id": "...",
        "result": {...} if executed,
        "message": "..."
    }
    """
    try:
        # Verify membership
        members = DynamoDBOps.get_members(household_id)
        if not verify_household_membership(user, household_id, members):
            return error_response(403, "Access denied")

        action_id = body.get("action_id")
        confirmed = body.get("confirmed", False)

        if not action_id:
            return error_response(400, "Missing: action_id")

        logger.info(f"Confirmation request: action_id={action_id}, confirmed={confirmed}, user={user.user_id}")

        # Use ConfirmationManager to execute
        result = ConfirmationManager.confirm_and_execute(
            household_id=household_id,
            action_id=action_id,
            user_id=user.user_id,
            confirmed=confirmed
        )

        if result.get("status") == "failed":
            return error_response(400, result.get("error", "Confirmation failed"))
        
        return success_response(200, {
            "status": result.get("status"),
            "action_id": action_id,
            "confirmed": confirmed,
            "result": result.get("result"),
            "message": "Action executed" if result.get("status") == "executed" else "Action cancelled"
        })

    except Exception as e:
        logger.error(f"Error confirming action: {str(e)}", exc_info=True)
        return error_response(500, str(e))



def extract_household_id(path: str) -> str:
    """Extract household_id from API path."""
    # Path format: /households/{id}/copilot
    parts = path.split("/")
    if len(parts) >= 2:
        return parts[2]
    raise ValueError("Could not extract household_id from path")


def success_response(status_code: int, data: dict) -> dict:
    """Return a successful API response."""
    return {
        "statusCode": status_code,
        "body": json.dumps(data),
        "headers": {"Content-Type": "application/json"},
    }


def error_response(status_code: int, message: str) -> dict:
    """Return an error API response."""
    return {
        "statusCode": status_code,
        "body": json.dumps({"error": message}),
        "headers": {"Content-Type": "application/json"},
    }
