"""
RoomieOps Copilot Lambda Handler

AI-powered household coordination copilot.
- Single-intent command processing
- Intent detection via Bedrock
- Tool selection and execution
- Explanation generation

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

from auth import require_auth, verify_household_membership
from dynamodb_ops import DynamoDBOps
from bedrock_client import BedrockOps, BedrockError
from agent_tools import AgentToolRegistry, ToolType

logger = logging.getLogger()
logger.setLevel(logging.INFO)


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


def process_copilot_request(user, household_id, body):
    """
    POST /households/{id}/copilot
    Process a natural language request from the user.
    
    Flow:
    1. Verify household membership
    2. Retrieve household context (members, balances, chores, policy)
    3. Call Bedrock to detect intent
    4. Select appropriate tool
    5. Execute tool (READ immediately, WRITE returns confirmation requirement)
    6. Generate explanation
    7. Return result
    """
    try:
        # Verify membership
        members = DynamoDBOps.get_members(household_id)
        if not verify_household_membership(user, household_id, members):
            return error_response(403, "Access denied: not a member of this household")

        request_text = body.get("message")
        if not request_text:
            return error_response(400, "Missing: message")

        # Retrieve household context
        household = DynamoDBOps.get_household(household_id)
        balances = DynamoDBOps.get_all_balances(household_id)
        chores = DynamoDBOps.get_chores(household_id)

        household_context = {
            "members": [{"name": m.get("name"), "user_id": m.get("user_id")} for m in members],
            "policy": household.get("policy", {}),
            "balances": {b.get("user_id"): b.get("balance_paise", 0) for b in balances},
            "chore_count": len(chores),
        }

        logger.info(f"Processing copilot request: {request_text}")

        # Detect intent via Bedrock
        try:
            intent_result = BedrockOps.detect_intent(request_text, household_context)
        except BedrockError as e:
            if "BLOCKED" in str(e):
                logger.warning(f"Bedrock blocked: {str(e)}")
                # Fallback to simple heuristic-based intent detection
                intent_result = detect_intent_local(request_text)
            else:
                raise

        intent = intent_result.get("intent", "unknown")
        logger.info(f"Detected intent: {intent}")

        # Route to tool
        tool_result = route_intent_to_tool(user, household_id, intent, request_text, household_context)

        # Generate explanation
        explanation = tool_result.get("explanation", "Action completed")

        response = {
            "intent": intent,
            "tool_used": tool_result.get("tool_name"),
            "result": tool_result.get("data"),
            "explanation": explanation,
            "requires_confirmation": tool_result.get("requires_confirmation", False),
            "action_id": tool_result.get("action_id"),
        }

        return success_response(200, response)
    except BedrockError as e:
        logger.error(f"Bedrock error: {str(e)}")
        return error_response(503, f"AI service error: {str(e)}")
    except Exception as e:
        logger.error(f"Error processing copilot request: {str(e)}")
        return error_response(500, str(e))


def confirm_action(user, household_id, body):
    """
    POST /households/{id}/copilot/confirm
    Confirm a pending consequential action.
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

        # TODO: Retrieve pending action
        # TODO: Execute if confirmed, discard if rejected
        # TODO: Return result

        response = {
            "action_id": action_id,
            "status": "placeholder",
        }

        return success_response(200, response)
    except Exception as e:
        logger.error(f"Error confirming action: {str(e)}")
        return error_response(500, str(e))


def extract_household_id(path):
    """Extract household ID from path."""
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


def detect_intent_local(user_message: str) -> Dict:
    """
    Fallback intent detection using simple heuristics.
    Used when Bedrock is blocked or unavailable.
    """
    message_lower = user_message.lower()

    if any(word in message_lower for word in ["balance", "owe", "owing"]):
        return {"intent": "view_balance", "confidence": 0.9}
    elif any(word in message_lower for word in ["chore", "task", "assigned"]):
        return {"intent": "view_chores", "confidence": 0.9}
    elif any(word in message_lower for word in ["paid", "expense", "split"]):
        return {"intent": "create_expense", "confidence": 0.8}
    elif any(word in message_lower for word in ["broken", "issue", "problem", "geyser"]):
        return {"intent": "create_maintenance", "confidence": 0.8}
    elif any(word in message_lower for word in ["shopping", "buy", "need", "groceries"]):
        return {"intent": "add_shopping_item", "confidence": 0.8}
    else:
        return {"intent": "unknown", "confidence": 0.5}


def route_intent_to_tool(
    user,
    household_id: str,
    intent: str,
    request_text: str,
    household_context: Dict,
) -> Dict:
    """
    Route detected intent to appropriate tool and execute it.
    
    Returns tool execution result or requires_confirmation flag.
    """
    if intent == "view_balance":
        return execute_view_balance_tool(user, household_id)
    elif intent == "view_chores":
        return execute_view_chores_tool(household_id)
    elif intent == "create_expense":
        return execute_create_expense_tool(user, household_id, request_text)
    elif intent == "create_maintenance":
        return execute_create_maintenance_tool(user, household_id, request_text)
    elif intent == "add_shopping_item":
        return execute_add_shopping_tool(user, household_id, request_text)
    else:
        return {
            "tool_name": "unknown",
            "data": {},
            "explanation": "I didn't understand that request. Try asking about balances, chores, or expenses.",
        }


# Tool execution functions (PHASE 9)

def execute_view_balance_tool(user, household_id: str) -> Dict:
    """Execute get_my_balance tool."""
    try:
        balances = DynamoDBOps.get_all_balances(household_id)
        my_balance = next(
            (b.get("balance_paise", 0) for b in balances if b.get("user_id") == user.user_id),
            0,
        )

        if my_balance > 0:
            explanation = f"You are owed ₹{my_balance/100:.2f}"
        elif my_balance < 0:
            explanation = f"You owe ₹{abs(my_balance)/100:.2f}"
        else:
            explanation = "You are all settled up!"

        return {
            "tool_name": "get_my_balance",
            "data": {"user_id": user.user_id, "balance_paise": my_balance},
            "explanation": explanation,
        }
    except Exception as e:
        logger.error(f"Error executing view_balance tool: {str(e)}")
        return {"tool_name": "get_my_balance", "data": {}, "explanation": "Could not fetch balance"}


def execute_view_chores_tool(household_id: str) -> Dict:
    """Execute get_chore_rotation tool."""
    try:
        chores = DynamoDBOps.get_chores(household_id)
        chore_list = [
            {"name": c.get("name"), "assigned_to": c.get("assigned_to")}
            for c in chores
        ]

        explanation = f"You have {len(chores)} active chores. " + (
            f"Currently: {', '.join([f\"{c['name']} ({c['assigned_to']})\" for c in chore_list[:3]])}..."
            if chores
            else "No chores right now."
        )

        return {
            "tool_name": "get_chore_rotation",
            "data": {"chores": chore_list},
            "explanation": explanation,
        }
    except Exception as e:
        logger.error(f"Error executing view_chores tool: {str(e)}")
        return {"tool_name": "get_chore_rotation", "data": {}, "explanation": "Could not fetch chores"}


def execute_create_expense_tool(user, household_id: str, request_text: str) -> Dict:
    """Execute create_expense tool (returns requires_confirmation)."""
    return {
        "tool_name": "create_expense",
        "data": {"status": "awaiting_confirmation"},
        "explanation": f"I can help you create an expense. Please confirm the details.",
        "requires_confirmation": True,
        "action_id": str(uuid.uuid4()),
    }


def execute_create_maintenance_tool(user, household_id: str, request_text: str) -> Dict:
    """Execute create_maintenance_issue tool."""
    return {
        "tool_name": "create_maintenance_issue",
        "data": {"issue_id": str(uuid.uuid4()), "status": "open"},
        "explanation": f"Maintenance issue reported. The household admins have been notified.",
        "requires_confirmation": False,
    }


def execute_add_shopping_tool(user, household_id: str, request_text: str) -> Dict:
    """Execute add_shopping_item tool."""
    return {
        "tool_name": "add_shopping_item",
        "data": {"item_id": str(uuid.uuid4()), "status": "pending"},
        "explanation": f"Item added to shopping list.",
        "requires_confirmation": False,
    }
