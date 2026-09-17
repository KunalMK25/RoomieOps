"""API: POST /documents - Generate presigned S3 URL for document upload."""
import json
import logging
import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import boto3

from shared.utils import error_response, extract_user_id, log_event, success_response

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")


def lambda_handler(event, context):
    """
    Generate a presigned S3 URL for document upload.

    Request:
    {
        "docType": "academic_regulation"
    }

    Response:
    {
        "documentId": "d-...",
        "uploadUrl": "https://s3.../..."
    }
    """
    try:
        log_event(event, context)

        # Extract user ID from auth context
        try:
            user_id = extract_user_id(event)
        except ValueError as e:
            logger.warning(f"Unauthorized: {str(e)}")
            return error_response("Unauthorized", 401, "UNAUTHORIZED")

        # Extract request body
        body = json.loads(event.get("body", "{}"))
        doc_type = body.get("docType", "unknown")

        bucket = os.environ.get("S3_BUCKET")
        if not bucket:
            logger.error("S3_BUCKET not configured")
            return error_response("Server configuration error", 500, "CONFIG_ERROR")

        # Generate document ID
        document_id = f"doc-{uuid.uuid4().hex[:12]}"
        s3_key = f"documents/{user_id}/{document_id}/document"

        logger.info(f"Generating presigned URL for {s3_key}")

        # Generate presigned URL (5 minutes)
        try:
            upload_url = s3.generate_presigned_url(
                "put_object",
                Params={"Bucket": bucket, "Key": s3_key},
                ExpiresIn=300,  # 5 minutes
            )
        except Exception as e:
            logger.error(f"Failed to generate presigned URL: {str(e)}")
            return error_response(
                "Could not generate upload URL", 500, "PRESIGNED_URL_ERROR"
            )

        response = {
            "documentId": document_id,
            "uploadUrl": upload_url,
            "s3Key": s3_key,
            "bucket": bucket,
        }

        logger.info(f"Presigned URL generated for document {document_id}")
        return success_response(response)

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return error_response("Internal server error", 500, "INTERNAL_ERROR")
