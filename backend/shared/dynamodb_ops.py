"""
RoomieOps DynamoDB Operations Layer

Low-level CRUD for all household entities using composite pk/sk schema.
Schema (per spec §15):
  - pk/sk composite keys
  - Entities: HOUSEHOLD#<id>/META, MEMBER#<id>, ROOM#<id>, CHORE#<id>, EXPENSE#<id>, BALANCE#<id>, ISSUE#<id>, ITEM#<id>, AUDIT#<ts>#<id>
  - All writes include audit trail
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "roomieops-household-state")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(DYNAMODB_TABLE)


class DynamoDBOps:
    """All DynamoDB operations for RoomieOps."""

    # ==================== HOUSEHOLD CRUD ====================

    @staticmethod
    def create_household(
        household_id: str,
        name: str,
        description: str = "",
        policy: Optional[Dict] = None,
        created_by: Optional[str] = None,
    ) -> Dict:
        """Create a new household."""
        if not policy:
            policy = {
                "split_method": "equal",
                "settlement_frequency": "monthly",
                "chore_rotation_method": "round_robin",
            }

        item = {
            "pk": f"HOUSEHOLD#{household_id}",
            "sk": "META",
            "household_id": household_id,
            "name": name,
            "description": description,
            "policy": policy,
            "created_by": created_by or "system",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "status": "active",
        }

        try:
            table.put_item(Item=item)
            DynamoDBOps._audit_log(
                "HOUSEHOLD_CREATE", household_id, {"household_id": household_id, "name": name}
            )
            return item
        except ClientError as e:
            logger.error(f"Failed to create household: {e}")
            raise

    @staticmethod
    def get_household(household_id: str) -> Optional[Dict]:
        """Retrieve household metadata."""
        try:
            response = table.get_item(
                Key={"pk": f"HOUSEHOLD#{household_id}", "sk": "META"}
            )
            return response.get("Item")
        except ClientError as e:
            logger.error(f"Failed to get household: {e}")
            raise

    @staticmethod
    def list_households() -> List[Dict]:
        """List all active households."""
        try:
            response = table.scan(
                FilterExpression="sk = :sk AND #status = :status",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={":sk": "META", ":status": "active"},
            )
            return response.get("Items", [])
        except ClientError as e:
            logger.error(f"Failed to list households: {e}")
            raise

    # ==================== MEMBER CRUD ====================

    @staticmethod
    def add_member(
        household_id: str, user_id: str, name: str, email: str = "", role: str = "member"
    ) -> Dict:
        """Add a member to a household."""
        item = {
            "pk": f"HOUSEHOLD#{household_id}",
            "sk": f"MEMBER#{user_id}",
            "household_id": household_id,
            "user_id": user_id,
            "name": name,
            "email": email,
            "role": role,  # admin, member
            "joined_at": datetime.utcnow().isoformat(),
            "status": "active",
        }

        try:
            table.put_item(Item=item)
            DynamoDBOps._audit_log(
                "MEMBER_ADD",
                household_id,
                {"user_id": user_id, "name": name, "role": role},
            )
            return item
        except ClientError as e:
            logger.error(f"Failed to add member: {e}")
            raise

    @staticmethod
    def get_members(household_id: str) -> List[Dict]:
        """Get all members of a household."""
        try:
            response = table.query(
                KeyConditionExpression="pk = :pk AND begins_with(#sk, :sk_prefix)",
                ExpressionAttributeNames={"#sk": "sk"},
                ExpressionAttributeValues={
                    ":pk": f"HOUSEHOLD#{household_id}",
                    ":sk_prefix": "MEMBER#",
                },
            )
            return response.get("Items", [])
        except ClientError as e:
            logger.error(f"Failed to get members: {e}")
            raise

    # ==================== EXPENSE CRUD ====================

    @staticmethod
    def create_expense(
        household_id: str,
        expense_id: str,
        payer_id: str,
        description: str,
        total_paise: int,
        allocations: List[Dict],  # [{"user_id": id, "amount_paise": amt}, ...]
        split_method: str = "equal",
        created_by: Optional[str] = None,
    ) -> Dict:
        """
        Record an expense and its allocations.
        
        Args:
            allocations: List of dicts with user_id and amount_paise
        """
        item = {
            "pk": f"HOUSEHOLD#{household_id}",
            "sk": f"EXPENSE#{expense_id}",
            "household_id": household_id,
            "expense_id": expense_id,
            "payer_id": payer_id,
            "description": description,
            "total_paise": total_paise,
            "allocations": allocations,
            "split_method": split_method,
            "created_by": created_by or "system",
            "created_at": datetime.utcnow().isoformat(),
            "status": "settled",
        }

        try:
            table.put_item(Item=item)
            DynamoDBOps._audit_log(
                "EXPENSE_CREATE",
                household_id,
                {
                    "expense_id": expense_id,
                    "payer_id": payer_id,
                    "total_paise": total_paise,
                },
            )
            return item
        except ClientError as e:
            logger.error(f"Failed to create expense: {e}")
            raise

    @staticmethod
    def get_expenses(household_id: str, limit: int = 50) -> List[Dict]:
        """Get recent expenses for a household."""
        try:
            response = table.query(
                KeyConditionExpression="pk = :pk AND begins_with(#sk, :sk_prefix)",
                ExpressionAttributeNames={"#sk": "sk"},
                ExpressionAttributeValues={
                    ":pk": f"HOUSEHOLD#{household_id}",
                    ":sk_prefix": "EXPENSE#",
                },
                Limit=limit,
                ScanIndexForward=False,  # Most recent first
            )
            return response.get("Items", [])
        except ClientError as e:
            logger.error(f"Failed to get expenses: {e}")
            raise

    # ==================== BALANCE CRUD ====================

    @staticmethod
    def set_balance(
        household_id: str, user_id: str, balance_paise: int, timestamp: Optional[str] = None
    ) -> Dict:
        """Record the current balance for a user."""
        if not timestamp:
            timestamp = datetime.utcnow().isoformat()

        item = {
            "pk": f"HOUSEHOLD#{household_id}",
            "sk": f"BALANCE#{user_id}",
            "household_id": household_id,
            "user_id": user_id,
            "balance_paise": balance_paise,
            "timestamp": timestamp,
        }

        try:
            table.put_item(Item=item)
            return item
        except ClientError as e:
            logger.error(f"Failed to set balance: {e}")
            raise

    @staticmethod
    def get_balance(household_id: str, user_id: str) -> Optional[Dict]:
        """Get current balance for a user."""
        try:
            response = table.get_item(
                Key={"pk": f"HOUSEHOLD#{household_id}", "sk": f"BALANCE#{user_id}"}
            )
            return response.get("Item")
        except ClientError as e:
            logger.error(f"Failed to get balance: {e}")
            raise

    @staticmethod
    def get_all_balances(household_id: str) -> List[Dict]:
        """Get all current balances for a household."""
        try:
            response = table.query(
                KeyConditionExpression="pk = :pk AND begins_with(#sk, :sk_prefix)",
                ExpressionAttributeNames={"#sk": "sk"},
                ExpressionAttributeValues={
                    ":pk": f"HOUSEHOLD#{household_id}",
                    ":sk_prefix": "BALANCE#",
                },
            )
            return response.get("Items", [])
        except ClientError as e:
            logger.error(f"Failed to get all balances: {e}")
            raise

    # ==================== CHORE CRUD ====================

    @staticmethod
    def create_chore(
        household_id: str,
        chore_id: str,
        name: str,
        assigned_to: str,
        frequency: str = "weekly",
        rotation_order: Optional[List[str]] = None,
        created_by: Optional[str] = None,
    ) -> Dict:
        """Create a chore."""
        item = {
            "pk": f"HOUSEHOLD#{household_id}",
            "sk": f"CHORE#{chore_id}",
            "household_id": household_id,
            "chore_id": chore_id,
            "name": name,
            "assigned_to": assigned_to,
            "frequency": frequency,
            "rotation_order": rotation_order or [],
            "rotation_index": 0,
            "created_by": created_by or "system",
            "created_at": datetime.utcnow().isoformat(),
            "status": "active",
        }

        try:
            table.put_item(Item=item)
            DynamoDBOps._audit_log(
                "CHORE_CREATE",
                household_id,
                {"chore_id": chore_id, "assigned_to": assigned_to},
            )
            return item
        except ClientError as e:
            logger.error(f"Failed to create chore: {e}")
            raise

    @staticmethod
    def get_chores(household_id: str) -> List[Dict]:
        """Get all chores for a household."""
        try:
            response = table.query(
                KeyConditionExpression="pk = :pk AND begins_with(#sk, :sk_prefix)",
                ExpressionAttributeNames={"#sk": "sk"},
                ExpressionAttributeValues={
                    ":pk": f"HOUSEHOLD#{household_id}",
                    ":sk_prefix": "CHORE#",
                },
            )
            return response.get("Items", [])
        except ClientError as e:
            logger.error(f"Failed to get chores: {e}")
            raise

    @staticmethod
    def complete_chore(household_id: str, chore_id: str) -> Dict:
        """Mark a chore as completed and rotate to next person."""
        chore = table.get_item(
            Key={"pk": f"HOUSEHOLD#{household_id}", "sk": f"CHORE#{chore_id}"}
        ).get("Item")

        if not chore:
            raise ValueError(f"Chore {chore_id} not found")

        rotation_order = chore.get("rotation_order", [])
        if not rotation_order:
            raise ValueError(f"Chore {chore_id} has no rotation order")

        rotation_index = (chore.get("rotation_index", 0) + 1) % len(rotation_order)
        next_assigned = rotation_order[rotation_index]

        chore["assigned_to"] = next_assigned
        chore["rotation_index"] = rotation_index
        chore["last_completed_at"] = datetime.utcnow().isoformat()

        try:
            table.put_item(Item=chore)
            DynamoDBOps._audit_log(
                "CHORE_COMPLETE",
                household_id,
                {"chore_id": chore_id, "next_assigned": next_assigned},
            )
            return chore
        except ClientError as e:
            logger.error(f"Failed to complete chore: {e}")
            raise

    # ==================== AUDIT LOG ====================

    @staticmethod
    def _audit_log(action: str, household_id: str, details: Dict) -> None:
        """Record an action in the audit log."""
        timestamp = datetime.utcnow().isoformat()
        audit_id = f"{timestamp}#{action}"

        audit_item = {
            "pk": f"HOUSEHOLD#{household_id}",
            "sk": f"AUDIT#{audit_id}",
            "action": action,
            "details": details,
            "timestamp": timestamp,
        }

        try:
            table.put_item(Item=audit_item)
        except ClientError as e:
            logger.warning(f"Failed to write audit log: {e}")

    @staticmethod
    def get_audit_log(household_id: str, limit: int = 100) -> List[Dict]:
        """Get audit log entries for a household."""
        try:
            response = table.query(
                KeyConditionExpression="pk = :pk AND begins_with(#sk, :sk_prefix)",
                ExpressionAttributeNames={"#sk": "sk"},
                ExpressionAttributeValues={
                    ":pk": f"HOUSEHOLD#{household_id}",
                    ":sk_prefix": "AUDIT#",
                },
                Limit=limit,
                ScanIndexForward=False,
            )
            return response.get("Items", [])
        except ClientError as e:
            logger.error(f"Failed to get audit log: {e}")
            raise
