"""
RoomieOps Notifications Lambda Handler

Handles event notifications, reminders, and alerts.
P0: audit event logging
P1: EventBridge-triggered reminders for bills/chores
P2: SLA escalation
"""

import json
import os
import sys
import logging
from datetime import datetime

sys.path.insert(0, "/opt/python")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../shared"))

from dynamodb_ops import DynamoDBOps

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """Main Lambda handler for notification operations."""
    logger.info(f"Event: {json.dumps(event)}")

    try:
        # Check if this is an EventBridge event or API request
        if "source" in event and event.get("source") == "aws.events":
            # EventBridge scheduled reminder
            return handle_eventbridge_event(event)
        else:
            # Direct API call
            return error_response(400, "Use EventBridge for notifications")

    except Exception as e:
        logger.error(f"Unhandled error: {str(e)}", exc_info=True)
        return error_response(500, str(e))


def handle_eventbridge_event(event):
    """Handle EventBridge scheduled reminders."""
    detail = event.get("detail", {})
    event_type = detail.get("event_type")

    if event_type == "chore_reminder":
        return handle_chore_reminder(detail)
    elif event_type == "bill_due":
        return handle_bill_reminder(detail)
    else:
        logger.warning(f"Unknown event type: {event_type}")
        return {"status": "ignored"}


def handle_chore_reminder(detail):
    """Send chore completion reminder."""
    household_id = detail.get("household_id")
    chore_id = detail.get("chore_id")
    assigned_to = detail.get("assigned_to")

    logger.info(f"Chore reminder: {assigned_to} for chore {chore_id}")
    # TODO: Send notification to user

    return {"status": "reminder_sent"}


def handle_bill_reminder(detail):
    """Send bill due reminder."""
    household_id = detail.get("household_id")
    bill_amount = detail.get("amount_paise")

    logger.info(f"Bill reminder for household {household_id}: ₹{bill_amount/100:.2f}")
    # TODO: Send notification to admins

    return {"status": "reminder_sent"}


def error_response(status_code, message):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": message}),
    }
