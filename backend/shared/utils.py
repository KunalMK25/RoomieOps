"""Shared utilities for Lambda functions."""
import json
import logging
import os
from typing import Any, Dict

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_env(key: str, default: str = None) -> str:
    """Get environment variable with optional default."""
    return os.environ.get(key, default)


def success_response(body: Any, status_code: int = 200) -> Dict[str, Any]:
    """Create a successful API response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body) if not isinstance(body, str) else body,
    }


def error_response(
    message: str, status_code: int = 500, error_code: str = None
) -> Dict[str, Any]:
    """Create an error API response."""
    body = {"error": message}
    if error_code:
        body["errorCode"] = error_code

    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body),
    }


def extract_user_id(event: Dict[str, Any]) -> str:
    """Extract user ID from API Gateway event."""
    claims = event.get("requestContext", {}).get("authorizer", {}).get("claims", {})
    user_id = claims.get("sub") or claims.get("cognito:username")
    if not user_id:
        raise ValueError("User not authenticated")
    return user_id


def validate_json_body(event: Dict[str, Any]) -> Dict[str, Any]:
    """Extract and validate JSON body from event."""
    try:
        body = json.loads(event.get("body", "{}"))
        return body
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON body: {str(e)}")


def log_event(event: Dict[str, Any], context: Any = None) -> None:
    """Log Lambda event for debugging."""
    logger.info(f"Event: {json.dumps(event)}")
    if context:
        logger.info(f"Request ID: {context.request_id}")
        logger.info(f"Function: {context.function_name}")
