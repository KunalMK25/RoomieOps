"""API: POST /documents/{id}/process - Start document processing pipeline."""
import json
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import boto3

from shared.utils import (
    error_response,
    extract_user_id,
    log_event,
    success_response,
    validate_json_body,
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

stepfunctions = boto3.client("stepfunctions")
dynamodb = boto3.resource("dynamodb")


def lambda_handler(event, context):
    """
    Start the processing pipeline via Step Functions.

    Request:
    {
        "situation": "I have 72% attendance...",
        "language": "en"
    }

    Response:
    {
        "status": "processing",
        "executionArn": "arn:aws:states:..."
    }
    """
    try:
        log_event(event, context)

        # Extract user ID
        try:
            user_id = extract_user_id(event)
        except ValueError:
            return error_response("Unauthorized", 401, "UNAUTHORIZED")

        # Extract document ID from path
        path_params = event.get("pathParameters", {})
        document_id = path_params.get("id") if path_params else None

        if not document_id:
            return error_response("Missing document ID", 400, "INVALID_REQUEST")

        # Extract body
        try:
            body = validate_json_body(event)
        except ValueError as e:
            return error_response(f"Invalid request: {str(e)}", 400, "INVALID_REQUEST")

        situation = body.get("situation")
        language = body.get("language", "en")

        if not situation:
            return error_response("Missing situation", 400, "INVALID_REQUEST")

        # Validate language
        if language not in {"en", "kn"}:
            return error_response("Invalid language", 400, "INVALID_REQUEST")

        logger.info(f"Starting processing for document {document_id}")

        # Get Step Functions state machine ARN from environment
        state_machine_arn = os.environ.get("STATE_MACHINE_ARN")
        if not state_machine_arn:
            logger.error("STATE_MACHINE_ARN not configured")
            return error_response("Server configuration error", 500, "CONFIG_ERROR")

        # Prepare input for Step Functions
        sf_input = {
            "documentId": document_id,
            "ownerId": user_id,
            "situation": situation,
            "language": language,
            "s3Key": f"documents/{user_id}/{document_id}/document",
        }

        # Start execution
        try:
            execution_response = stepfunctions.start_execution(
                stateMachineArn=state_machine_arn,
                name=f"{document_id}-{int(__import__('time').time() * 1000)}",
                input=json.dumps(sf_input),
            )
            execution_arn = execution_response["executionArn"]
        except Exception as e:
            logger.error(f"Failed to start Step Functions execution: {str(e)}")
            return error_response(
                "Could not start processing", 500, "STEPFUNCTIONS_ERROR"
            )

        # Create initial record in DynamoDB
        table_name = os.environ.get("DYNAMODB_TABLE")
        if table_name:
            try:
                table = dynamodb.Table(table_name)
                table.put_item(
                    Item={
                        "documentId": document_id,
                        "ownerId": user_id,
                        "status": "processing",
                        "situation": situation,
                        "language": language,
                        "executionArn": execution_arn,
                        "createdAt": __import__("datetime").datetime.utcnow().isoformat(),
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to create DynamoDB record: {str(e)}")
                # Continue anyway, not critical

        response = {
            "documentId": document_id,
            "status": "processing",
            "executionArn": execution_arn,
        }

        logger.info(f"Processing started with execution {execution_arn}")
        return success_response(response)

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return error_response("Internal server error", 500, "INTERNAL_ERROR")
