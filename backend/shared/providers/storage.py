"""Storage provider implementations for different backends."""

import json
import logging
import os
from typing import Any, Dict, List, Optional
from abc import ABC

from .base import StorageProvider
from .types import QueryResult

logger = logging.getLogger(__name__)


class DynamoDBProvider(StorageProvider):
    """Storage provider using AWS DynamoDB (SHIP_IT)."""
    
    def __init__(self):
        """Initialize DynamoDB resource."""
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            self.dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
            table_name = os.environ.get("DYNAMODB_TABLE", "roomieops-household-state")
            self.table = self.dynamodb.Table(table_name)
            self.ClientError = ClientError
            
            logger.info(f"DynamoDBProvider initialized with table: {table_name}")
        except Exception as e:
            logger.error(f"Failed to initialize DynamoDB provider: {e}")
            raise
    
    def get_item(self, pk: str, sk: str) -> Optional[Dict[str, Any]]:
        """Get item from DynamoDB."""
        try:
            response = self.table.get_item(Key={"pk": pk, "sk": sk})
            return response.get("Item")
        except self.ClientError as e:
            logger.error(f"DynamoDB get_item failed: {e}")
            return None
    
    def put_item(self, item: Dict[str, Any]) -> None:
        """Put item to DynamoDB."""
        try:
            self.table.put_item(Item=item)
        except self.ClientError as e:
            logger.error(f"DynamoDB put_item failed: {e}")
            raise
    
    def query(
        self,
        pk: str,
        sk_prefix: Optional[str] = None,
        limit: int = 100
    ) -> QueryResult:
        """Query items from DynamoDB."""
        try:
            if sk_prefix:
                response = self.table.query(
                    KeyConditionExpression="pk = :pk AND begins_with(#sk, :sk_prefix)",
                    ExpressionAttributeNames={"#sk": "sk"},
                    ExpressionAttributeValues={":pk": pk, ":sk_prefix": sk_prefix},
                    Limit=limit
                )
            else:
                response = self.table.query(
                    KeyConditionExpression="pk = :pk",
                    ExpressionAttributeValues={":pk": pk},
                    Limit=limit
                )
            
            return QueryResult(
                items=response.get("Items", []),
                count=response.get("Count", 0),
                last_evaluated_key=response.get("LastEvaluatedKey")
            )
        except self.ClientError as e:
            logger.error(f"DynamoDB query failed: {e}")
            return QueryResult(items=[], count=0)
    
    def scan(
        self,
        filter_expr: Optional[str] = None,
        filter_values: Optional[Dict[str, Any]] = None,
        limit: int = 100
    ) -> QueryResult:
        """Scan items from DynamoDB."""
        try:
            kwargs = {"Limit": limit}
            if filter_expr and filter_values:
                kwargs["FilterExpression"] = filter_expr
                kwargs["ExpressionAttributeValues"] = filter_values
            
            response = self.table.scan(**kwargs)
            
            return QueryResult(
                items=response.get("Items", []),
                count=response.get("Count", 0),
                last_evaluated_key=response.get("LastEvaluatedKey")
            )
        except self.ClientError as e:
            logger.error(f"DynamoDB scan failed: {e}")
            return QueryResult(items=[], count=0)
    
    def update_item(
        self,
        pk: str,
        sk: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update item in DynamoDB."""
        try:
            # Build update expression
            update_expr_parts = []
            expr_attr_values = {}
            expr_attr_names = {}
            
            for key, value in updates.items():
                placeholder = f":val_{key}"
                expr_attr_values[placeholder] = value
                update_expr_parts.append(f"{key} = {placeholder}")
            
            update_expr = "SET " + ", ".join(update_expr_parts)
            
            response = self.table.update_item(
                Key={"pk": pk, "sk": sk},
                UpdateExpression=update_expr,
                ExpressionAttributeValues=expr_attr_values,
                ReturnValues="ALL_NEW"
            )
            
            return response.get("Attributes", {})
        except self.ClientError as e:
            logger.error(f"DynamoDB update_item failed: {e}")
            raise
    
    def delete_item(self, pk: str, sk: str) -> None:
        """Delete item from DynamoDB."""
        try:
            self.table.delete_item(Key={"pk": pk, "sk": sk})
        except self.ClientError as e:
            logger.error(f"DynamoDB delete_item failed: {e}")
            raise
    
    def batch_put(self, items: List[Dict[str, Any]]) -> None:
        """Batch put items to DynamoDB."""
        try:
            with self.table.batch_writer() as batch:
                for item in items:
                    batch.put_item(Item=item)
        except self.ClientError as e:
            logger.error(f"DynamoDB batch_put failed: {e}")
            raise


class LocalStackProvider(StorageProvider):
    """Storage provider using LocalStack (BUILD_IT)."""
    
    def __init__(self, endpoint: str = "http://localhost:4566"):
        """Initialize LocalStack DynamoDB client.
        
        Args:
            endpoint: LocalStack endpoint (default: localhost:4566)
        """
        try:
            import boto3
            from botocore.exceptions import ClientError
            
            self.endpoint = endpoint
            self.dynamodb = boto3.resource(
                "dynamodb",
                endpoint_url=endpoint,
                region_name="us-east-1",
                aws_access_key_id="test",
                aws_secret_access_key="test"
            )
            table_name = os.environ.get("DYNAMODB_TABLE", "roomieops-household-state")
            self.table = self.dynamodb.Table(table_name)
            self.ClientError = ClientError
            
            # Create table if doesn't exist (LocalStack)
            self._ensure_table_exists(table_name)
            
            logger.info(f"LocalStackProvider initialized with table: {table_name}")
        except ImportError:
            raise ImportError("boto3 library required for LocalStack provider")
        except Exception as e:
            logger.error(f"Failed to initialize LocalStack provider: {e}")
            raise
    
    def _ensure_table_exists(self, table_name: str) -> None:
        """Ensure DynamoDB table exists in LocalStack."""
        try:
            # Check if table exists
            self.table.table_status
            logger.info(f"Table {table_name} exists")
        except self.ClientError as e:
            if "ResourceNotFoundException" in str(e):
                logger.info(f"Creating table {table_name} in LocalStack")
                self.dynamodb.create_table(
                    TableName=table_name,
                    KeySchema=[
                        {"AttributeName": "pk", "KeyType": "HASH"},
                        {"AttributeName": "sk", "KeyType": "RANGE"}
                    ],
                    AttributeDefinitions=[
                        {"AttributeName": "pk", "AttributeType": "S"},
                        {"AttributeName": "sk", "AttributeType": "S"},
                        {"AttributeName": "householdId", "AttributeType": "S"},
                        {"AttributeName": "createdAt", "AttributeType": "S"}
                    ],
                    BillingMode="PAY_PER_REQUEST",
                    GlobalSecondaryIndexes=[
                        {
                            "IndexName": "HouseholdIdCreatedAtIndex",
                            "KeySchema": [
                                {"AttributeName": "householdId", "KeyType": "HASH"},
                                {"AttributeName": "createdAt", "KeyType": "RANGE"}
                            ],
                            "Projection": {"ProjectionType": "ALL"}
                        }
                    ]
                )
                logger.info(f"Table {table_name} created")
            else:
                raise
    
    # Delegate to same implementation as DynamoDB
    def get_item(self, pk: str, sk: str) -> Optional[Dict[str, Any]]:
        try:
            response = self.table.get_item(Key={"pk": pk, "sk": sk})
            return response.get("Item")
        except self.ClientError as e:
            logger.error(f"LocalStack get_item failed: {e}")
            return None
    
    def put_item(self, item: Dict[str, Any]) -> None:
        try:
            self.table.put_item(Item=item)
        except self.ClientError as e:
            logger.error(f"LocalStack put_item failed: {e}")
            raise
    
    def query(
        self,
        pk: str,
        sk_prefix: Optional[str] = None,
        limit: int = 100
    ) -> QueryResult:
        try:
            if sk_prefix:
                response = self.table.query(
                    KeyConditionExpression="pk = :pk AND begins_with(#sk, :sk_prefix)",
                    ExpressionAttributeNames={"#sk": "sk"},
                    ExpressionAttributeValues={":pk": pk, ":sk_prefix": sk_prefix},
                    Limit=limit
                )
            else:
                response = self.table.query(
                    KeyConditionExpression="pk = :pk",
                    ExpressionAttributeValues={":pk": pk},
                    Limit=limit
                )
            
            return QueryResult(
                items=response.get("Items", []),
                count=response.get("Count", 0),
                last_evaluated_key=response.get("LastEvaluatedKey")
            )
        except self.ClientError as e:
            logger.error(f"LocalStack query failed: {e}")
            return QueryResult(items=[], count=0)
    
    def scan(
        self,
        filter_expr: Optional[str] = None,
        filter_values: Optional[Dict[str, Any]] = None,
        limit: int = 100
    ) -> QueryResult:
        try:
            kwargs = {"Limit": limit}
            if filter_expr and filter_values:
                kwargs["FilterExpression"] = filter_expr
                kwargs["ExpressionAttributeValues"] = filter_values
            
            response = self.table.scan(**kwargs)
            
            return QueryResult(
                items=response.get("Items", []),
                count=response.get("Count", 0),
                last_evaluated_key=response.get("LastEvaluatedKey")
            )
        except self.ClientError as e:
            logger.error(f"LocalStack scan failed: {e}")
            return QueryResult(items=[], count=0)
    
    def update_item(
        self,
        pk: str,
        sk: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        try:
            update_expr_parts = []
            expr_attr_values = {}
            
            for key, value in updates.items():
                placeholder = f":val_{key}"
                expr_attr_values[placeholder] = value
                update_expr_parts.append(f"{key} = {placeholder}")
            
            update_expr = "SET " + ", ".join(update_expr_parts)
            
            response = self.table.update_item(
                Key={"pk": pk, "sk": sk},
                UpdateExpression=update_expr,
                ExpressionAttributeValues=expr_attr_values,
                ReturnValues="ALL_NEW"
            )
            
            return response.get("Attributes", {})
        except self.ClientError as e:
            logger.error(f"LocalStack update_item failed: {e}")
            raise
    
    def delete_item(self, pk: str, sk: str) -> None:
        try:
            self.table.delete_item(Key={"pk": pk, "sk": sk})
        except self.ClientError as e:
            logger.error(f"LocalStack delete_item failed: {e}")
            raise
    
    def batch_put(self, items: List[Dict[str, Any]]) -> None:
        try:
            with self.table.batch_writer() as batch:
                for item in items:
                    batch.put_item(Item=item)
        except self.ClientError as e:
            logger.error(f"LocalStack batch_put failed: {e}")
            raise


class InMemoryProvider(StorageProvider):
    """Storage provider using in-memory dict (LOCAL_HEURISTIC / testing)."""
    
    def __init__(self):
        """Initialize in-memory storage."""
        self.storage: Dict[str, Dict[str, Any]] = {}
        logger.info("InMemoryProvider initialized")
    
    def _make_key(self, pk: str, sk: str) -> str:
        """Make composite key from pk and sk."""
        return f"{pk}#{sk}"
    
    def get_item(self, pk: str, sk: str) -> Optional[Dict[str, Any]]:
        """Get item from memory."""
        key = self._make_key(pk, sk)
        return self.storage.get(key)
    
    def put_item(self, item: Dict[str, Any]) -> None:
        """Put item to memory."""
        pk = item.get("pk")
        sk = item.get("sk")
        key = self._make_key(pk, sk)
        self.storage[key] = item
    
    def query(
        self,
        pk: str,
        sk_prefix: Optional[str] = None,
        limit: int = 100
    ) -> QueryResult:
        """Query items from memory."""
        items = []
        for key, item in self.storage.items():
            if item.get("pk") == pk:
                if sk_prefix is None or item.get("sk", "").startswith(sk_prefix):
                    items.append(item)
                    if len(items) >= limit:
                        break
        
        return QueryResult(items=items, count=len(items))
    
    def scan(
        self,
        filter_expr: Optional[str] = None,
        filter_values: Optional[Dict[str, Any]] = None,
        limit: int = 100
    ) -> QueryResult:
        """Scan items from memory."""
        items = list(self.storage.values())[:limit]
        return QueryResult(items=items, count=len(items))
    
    def update_item(
        self,
        pk: str,
        sk: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update item in memory."""
        key = self._make_key(pk, sk)
        if key in self.storage:
            self.storage[key].update(updates)
            return self.storage[key]
        return {}
    
    def delete_item(self, pk: str, sk: str) -> None:
        """Delete item from memory."""
        key = self._make_key(pk, sk)
        if key in self.storage:
            del self.storage[key]
    
    def batch_put(self, items: List[Dict[str, Any]]) -> None:
        """Batch put items to memory."""
        for item in items:
            self.put_item(item)
    
    def clear(self) -> None:
        """Clear all in-memory storage (for testing)."""
        self.storage.clear()
