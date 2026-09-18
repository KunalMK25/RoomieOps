#!/usr/bin/env python3
"""
Initialize LocalStack DynamoDB table for BUILD_IT_STRANDS development.

This script:
1. Connects to LocalStack DynamoDB (http://localhost:4566)
2. Creates the roomieops-household-state table
3. Uses the same schema as SHIP_IT

The table schema mirrors production for compatibility.
"""

import os
import sys
import logging
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import boto3
from botocore.exceptions import ClientError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_dynamodb_table():
    """Create the RoomieOps household state table in LocalStack."""
    
    # Get LocalStack endpoint from environment or use default
    endpoint_url = os.environ.get("DYNAMODB_ENDPOINT", "http://localhost:4566")
    table_name = os.environ.get("DYNAMODB_TABLE", "roomieops-household-state")
    region = os.environ.get("AWS_REGION", "us-east-1")
    
    logger.info(f"Connecting to LocalStack at {endpoint_url}")
    logger.info(f"Table name: {table_name}")
    logger.info(f"Region: {region}")
    
    try:
        # Create DynamoDB client pointing to LocalStack
        dynamodb = boto3.client(
            'dynamodb',
            endpoint_url=endpoint_url,
            region_name=region,
            aws_access_key_id='test',  # LocalStack doesn't validate these
            aws_secret_access_key='test',
        )
        
        # Check if table already exists
        try:
            response = dynamodb.describe_table(TableName=table_name)
            logger.info(f"✓ Table '{table_name}' already exists")
            logger.info(f"  Status: {response['Table']['TableStatus']}")
            logger.info(f"  Item count: {response['Table']['ItemCount']}")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceNotFoundException':
                raise
            logger.info(f"Table '{table_name}' does not exist, creating...")
        
        # Create table with composite key (PK + SK)
        # This matches the schema from ROOMIEOPS_BUILD_SPEC.md §15
        response = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'pk',  # Partition key
                    'KeyType': 'HASH'
                },
                {
                    'AttributeName': 'sk',  # Sort key
                    'KeyType': 'RANGE'
                },
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'pk',
                    'AttributeType': 'S'  # String
                },
                {
                    'AttributeName': 'sk',
                    'AttributeType': 'S'  # String
                },
            ],
            BillingMode='PAY_PER_REQUEST',  # On-demand billing (good for local dev)
            Tags=[
                {
                    'Key': 'Environment',
                    'Value': 'build-it-local'
                },
                {
                    'Key': 'Purpose',
                    'Value': 'RoomieOps household state'
                },
            ]
        )
        
        table_status = response['TableDescription']['TableStatus']
        logger.info(f"✓ Table created successfully")
        logger.info(f"  Status: {table_status}")
        logger.info(f"  ARN: {response['TableDescription']['TableArn']}")
        
        # Wait for table to be active (LocalStack is usually immediate)
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(TableName=table_name)
        logger.info(f"✓ Table is now active and ready for use")
        
        return True
    
    except Exception as e:
        logger.error(f"✗ Failed to create table: {e}")
        logger.error("\nMake sure LocalStack is running:")
        logger.error("  docker-compose up localstack")
        return False


def verify_table_access():
    """Verify we can access the table."""
    
    endpoint_url = os.environ.get("DYNAMODB_ENDPOINT", "http://localhost:4566")
    table_name = os.environ.get("DYNAMODB_TABLE", "roomieops-household-state")
    region = os.environ.get("AWS_REGION", "us-east-1")
    
    try:
        dynamodb = boto3.resource(
            'dynamodb',
            endpoint_url=endpoint_url,
            region_name=region,
            aws_access_key_id='test',
            aws_secret_access_key='test',
        )
        
        table = dynamodb.Table(table_name)
        
        # Try to read (will fail if table doesn't exist, which is fine)
        response = table.item_count
        logger.info(f"✓ Table access verified")
        logger.info(f"  Current items: {response}")
        
        # Put a test item to verify write access
        test_item = {
            "pk": "TEST#item",
            "sk": "test",
            "message": "LocalStack DynamoDB is working!",
        }
        
        table.put_item(Item=test_item)
        logger.info(f"✓ Write access verified (test item stored)")
        
        # Read it back
        response = table.get_item(Key={"pk": "TEST#item", "sk": "test"})
        if 'Item' in response:
            logger.info(f"✓ Read access verified (test item retrieved)")
            
            # Clean up
            table.delete_item(Key={"pk": "TEST#item", "sk": "test"})
            logger.info(f"✓ Test item cleaned up")
        
        return True
    
    except Exception as e:
        logger.error(f"✗ Failed to verify table access: {e}")
        return False


def main():
    """Main function."""
    
    logger.info("=" * 70)
    logger.info("LOCALSTACK DYNAMODB INITIALIZATION")
    logger.info("=" * 70)
    
    # Create table
    if not create_dynamodb_table():
        logger.error("\n✗ Failed to create table")
        return False
    
    logger.info("")
    
    # Verify access
    if not verify_table_access():
        logger.error("\n✗ Failed to verify table access")
        return False
    
    logger.info("")
    logger.info("=" * 70)
    logger.info("✓ LocalStack DynamoDB initialization COMPLETE")
    logger.info("=" * 70)
    logger.info("")
    logger.info("Schema details:")
    logger.info("  Partition Key (PK): String")
    logger.info("  Sort Key (SK): String")
    logger.info("  Billing Mode: PAY_PER_REQUEST (on-demand)")
    logger.info("")
    logger.info("Usage:")
    logger.info("  - RoomieOps core logic uses: backend/shared/dynamodb_ops.py")
    logger.info("  - StorageProvider handles: backend/shared/providers/storage.py")
    logger.info("  - LocalStackProvider routes: to LocalStack endpoint")
    logger.info("")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
