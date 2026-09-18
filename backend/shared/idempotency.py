"""
RoomieOps Idempotency Layer

Ensures that repeated requests with the same requestId do not create duplicate state.
Uses DynamoDB to store idempotency keys and their results.

Every side-effecting operation must:
1. Accept a client-supplied requestId
2. Check if requestId exists in idempotency table
3. If exists, return cached result
4. If not, execute operation, cache result, return
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "roomieops-household-state")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(DYNAMODB_TABLE)

# Idempotency keys expire after 24 hours
IDEMPOTENCY_TTL_SECONDS = 86400


class IdempotencyError(Exception):
    """Raised when idempotency check fails."""
    pass


class IdempotencyOps:
    """Idempotency key management."""

    @staticmethod
    def store_idempotency_result(
        household_id: str,
        operation_type: str,  # "create_expense", "create_chore", etc.
        request_id: str,
        result: Dict,
    ) -> None:
        """
        Store the result of an operation under its idempotency key.

        Args:
            household_id: Household performing the operation
            operation_type: Type of operation (for tracking)
            request_id: Client-supplied idempotency key
            result: Result to cache

        Raises:
            ClientError: If DynamoDB write fails
        """
        if not request_id:
            logger.warning("No requestId provided, skipping idempotency storage")
            return

        ttl = int((datetime.utcnow() + timedelta(seconds=IDEMPOTENCY_TTL_SECONDS)).timestamp())

        item = {
            "pk": f"HOUSEHOLD#{household_id}",
            "sk": f"IDEMPOTENCY#{request_id}",
            "household_id": household_id,
            "request_id": request_id,
            "operation_type": operation_type,
            "result": result,
            "stored_at": datetime.utcnow().isoformat(),
            "ttl": ttl,  # DynamoDB will auto-delete after TTL
        }

        try:
            table.put_item(Item=item)
            logger.info(f"Idempotency result stored: {request_id}")
        except ClientError as e:
            logger.error(f"Failed to store idempotency result: {e}")
            raise

    @staticmethod
    def get_idempotency_result(
        household_id: str,
        request_id: str,
    ) -> Optional[Dict]:
        """
        Retrieve a cached result for a request_id.

        Args:
            household_id: Household
            request_id: Idempotency key

        Returns:
            Cached result dict if found, None otherwise
        """
        if not request_id:
            return None

        try:
            response = table.get_item(
                Key={
                    "pk": f"HOUSEHOLD#{household_id}",
                    "sk": f"IDEMPOTENCY#{request_id}",
                }
            )
            item = response.get("Item")
            if item:
                logger.info(f"Idempotency hit: returning cached result for {request_id}")
                return item.get("result")
            return None
        except ClientError as e:
            logger.error(f"Failed to check idempotency: {e}")
            raise

    @staticmethod
    def check_and_store(
        household_id: str,
        operation_type: str,
        request_id: str,
        operation_fn,  # Callable that performs the operation
        *args,
        **kwargs,
    ) -> Dict:
        """
        Check if idempotency key exists; if not, execute operation and store result.

        Args:
            household_id: Household
            operation_type: Type of operation
            request_id: Idempotency key
            operation_fn: Callable to execute
            *args: Positional arguments to operation_fn
            **kwargs: Keyword arguments to operation_fn

        Returns:
            Operation result

        Raises:
            Any exception from operation_fn
        """
        # Check for existing result
        cached_result = IdempotencyOps.get_idempotency_result(household_id, request_id)
        if cached_result is not None:
            return cached_result

        # Execute operation
        result = operation_fn(*args, **kwargs)

        # Store result (non-blocking; don't fail the request if storage fails)
        try:
            IdempotencyOps.store_idempotency_result(
                household_id, operation_type, request_id, result
            )
        except Exception as e:
            logger.warning(f"Failed to store idempotency result (operation still succeeded): {e}")

        return result
