"""
RoomieOps DynamoDB Operations Layer

Low-level CRUD for all household entities using composite pk/sk schema.
Schema (per spec §15):
  - pk/sk composite keys
  - Entities: HOUSEHOLD#<id>/META, MEMBER#<id>, ROOM#<id>, CHORE#<id>, EXPENSE#<id>, BALANCE#<id>, ISSUE#<id>, ITEM#<id>, AUDIT#<ts>#<id>
  - All writes include audit trail

Refactored to use StorageProvider abstraction for BUILD_IT/SHIP_IT support.
- DynamoDBOps is now a facade over StorageProvider
- Calls get_storage_provider() to delegate all operations
- SHIP_IT uses DynamoDBStorageProvider (via boto3)
- BUILD_IT uses LocalStackStorageProvider (via boto3 with endpoint override)
- Tests can inject InMemoryStorageProvider
"""

import os
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Storage provider (injected at runtime)
# Default: DynamoDBProvider, but can be LocalStackProvider or InMemoryProvider
_storage_provider = None


def set_storage_provider(provider):
    """Set the storage provider for DynamoDBOps."""
    global _storage_provider
    _storage_provider = provider
    logger.info(f"DynamoDBOps storage provider set to: {type(provider).__name__}")


def get_storage_provider():
    """Get current storage provider (initializes if needed)."""
    global _storage_provider
    if _storage_provider is None:
        # Lazy initialization: detect provider based on environment
        try:
            from .providers import ExecutionModeManager
            providers = ExecutionModeManager.get_providers()
            _storage_provider = providers.storage
            logger.info(f"DynamoDBOps auto-initialized with: {type(_storage_provider).__name__}")
        except Exception as e:
            logger.error(f"Failed to auto-initialize storage provider: {e}")
            raise
    return _storage_provider


class DynamoDBOps:
    """All DynamoDB operations for RoomieOps.
    
    This class is now a facade over StorageProvider abstraction.
    All storage operations are delegated to get_storage_provider().
    """

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
            get_storage_provider().put_item(item)
            DynamoDBOps._audit_log(
                "HOUSEHOLD_CREATE", household_id, {"household_id": household_id, "name": name}
            )
            return item
        except Exception as e:
            logger.error(f"Failed to create household: {e}")
            raise

    @staticmethod
    def get_household(household_id: str) -> Optional[Dict]:
        """Retrieve household metadata."""
        try:
            item = get_storage_provider().get_item(
                pk=f"HOUSEHOLD#{household_id}", sk="META"
            )
            return item
        except Exception as e:
            logger.error(f"Failed to get household: {e}")
            raise

    @staticmethod
    def list_households() -> List[Dict]:
        """List all active households."""
        try:
            result = get_storage_provider().scan(limit=1000)
            # Filter for META items with active status (client-side filtering)
            items = [
                item for item in result.items 
                if item.get("sk") == "META" and item.get("status") == "active"
            ]
            return items
        except Exception as e:
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
            get_storage_provider().put_item(item)
            DynamoDBOps._audit_log(
                "MEMBER_ADD",
                household_id,
                {"user_id": user_id, "name": name, "role": role},
            )
            return item
        except Exception as e:
            logger.error(f"Failed to add member: {e}")
            raise

    @staticmethod
    def get_members(household_id: str) -> List[Dict]:
        """Get all members of a household."""
        try:
            result = get_storage_provider().query(
                pk=f"HOUSEHOLD#{household_id}",
                sk_prefix="MEMBER#"
            )
            return result.items
        except Exception as e:
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
            get_storage_provider().put_item(item)
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
        except Exception as e:
            logger.error(f"Failed to create expense: {e}")
            raise

    @staticmethod
    def get_expenses(household_id: str, limit: int = 50) -> List[Dict]:
        """Get recent expenses for a household."""
        try:
            result = get_storage_provider().query(
                pk=f"HOUSEHOLD#{household_id}",
                sk_prefix="EXPENSE#",
                limit=limit
            )
            # Return in reverse chronological order (most recent first)
            return sorted(result.items, key=lambda x: x.get("created_at", ""), reverse=True)
        except Exception as e:
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
            get_storage_provider().put_item(item)
            return item
        except Exception as e:
            logger.error(f"Failed to set balance: {e}")
            raise

    @staticmethod
    def get_balance(household_id: str, user_id: str) -> Optional[Dict]:
        """Get current balance for a user."""
        try:
            item = get_storage_provider().get_item(
                pk=f"HOUSEHOLD#{household_id}",
                sk=f"BALANCE#{user_id}"
            )
            return item
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            raise

    @staticmethod
    def get_all_balances(household_id: str) -> List[Dict]:
        """Get all current balances for a household."""
        try:
            result = get_storage_provider().query(
                pk=f"HOUSEHOLD#{household_id}",
                sk_prefix="BALANCE#"
            )
            return result.items
        except Exception as e:
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
            get_storage_provider().put_item(item)
            DynamoDBOps._audit_log(
                "CHORE_CREATE",
                household_id,
                {"chore_id": chore_id, "assigned_to": assigned_to},
            )
            return item
        except Exception as e:
            logger.error(f"Failed to create chore: {e}")
            raise

    @staticmethod
    def get_chores(household_id: str) -> List[Dict]:
        """Get all chores for a household."""
        try:
            result = get_storage_provider().query(
                pk=f"HOUSEHOLD#{household_id}",
                sk_prefix="CHORE#"
            )
            return result.items
        except Exception as e:
            logger.error(f"Failed to get chores: {e}")
            raise

    @staticmethod
    def complete_chore(household_id: str, chore_id: str) -> Dict:
        """Mark a chore as completed and rotate to next person."""
        chore = get_storage_provider().get_item(
            pk=f"HOUSEHOLD#{household_id}",
            sk=f"CHORE#{chore_id}"
        )

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
            get_storage_provider().put_item(chore)
            DynamoDBOps._audit_log(
                "CHORE_COMPLETE",
                household_id,
                {"chore_id": chore_id, "next_assigned": next_assigned},
            )
            return chore
        except Exception as e:
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
            get_storage_provider().put_item(audit_item)
        except Exception as e:
            logger.warning(f"Failed to write audit log: {e}")

    @staticmethod
    def get_audit_log(household_id: str, limit: int = 100) -> List[Dict]:
        """Get audit log entries for a household."""
        try:
            result = get_storage_provider().query(
                pk=f"HOUSEHOLD#{household_id}",
                sk_prefix="AUDIT#",
                limit=limit
            )
            # Return in reverse chronological order (most recent first)
            return sorted(result.items, key=lambda x: x.get("timestamp", ""), reverse=True)
        except Exception as e:
            logger.error(f"Failed to get audit log: {e}")
            raise

    # ==================== MAINTENANCE ISSUES ====================

    @staticmethod
    def create_maintenance_issue(
        household_id: str,
        issue_id: str,
        title: str,
        description: str,
        location: str,
        reported_by: str,
        request_id: str = "",
    ) -> Dict:
        """Create a maintenance issue."""
        item = {
            "pk": f"HOUSEHOLD#{household_id}",
            "sk": f"ISSUE#{issue_id}",
            "household_id": household_id,
            "issue_id": issue_id,
            "title": title,
            "description": description,
            "location": location,
            "reported_by": reported_by,
            "status": "open",
            "created_at": datetime.utcnow().isoformat(),
            "request_id": request_id,
        }

        try:
            get_storage_provider().put_item(item)
            DynamoDBOps._audit_log(
                "MAINTENANCE_ISSUE_CREATE",
                household_id,
                {"issue_id": issue_id, "title": title, "location": location},
            )
            return item
        except Exception as e:
            logger.error(f"Failed to create maintenance issue: {e}")
            raise

    @staticmethod
    def get_open_maintenance_issues(household_id: str) -> List[Dict]:
        """Get open maintenance issues."""
        try:
            result = get_storage_provider().query(
                pk=f"HOUSEHOLD#{household_id}",
                sk_prefix="ISSUE#"
            )
            return [i for i in result.items if i.get("status") == "open"]
        except Exception as e:
            logger.error(f"Failed to get maintenance issues: {e}")
            raise

    # ==================== SHOPPING ITEMS ====================

    @staticmethod
    def add_shopping_item(
        household_id: str,
        item_id: str,
        item_name: str,
        category: str = "",
        request_id: str = "",
    ) -> Dict:
        """Add item to shopping list."""
        item = {
            "pk": f"HOUSEHOLD#{household_id}",
            "sk": f"SHOPPING#{item_id}",
            "household_id": household_id,
            "item_id": item_id,
            "item_name": item_name,
            "category": category,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "request_id": request_id,
        }

        try:
            get_storage_provider().put_item(item)
            DynamoDBOps._audit_log(
                "SHOPPING_ITEM_ADD",
                household_id,
                {"item_name": item_name, "category": category},
            )
            return item
        except Exception as e:
            logger.error(f"Failed to add shopping item: {e}")
            raise

    @staticmethod
    def get_shopping_items(household_id: str) -> List[Dict]:
        """Get pending shopping items."""
        try:
            result = get_storage_provider().query(
                pk=f"HOUSEHOLD#{household_id}",
                sk_prefix="SHOPPING#"
            )
            return [i for i in result.items if i.get("status") == "pending"]
        except Exception as e:
            logger.error(f"Failed to get shopping items: {e}")
            raise

    # ==================== ADDITIONAL HELPERS ====================

    @staticmethod
    def record_payment(
        household_id: str,
        from_user_id: str,
        to_user_id: str,
        amount_paise: int,
        request_id: str = "",
    ) -> Dict:
        """Record a payment between members."""
        payment_id = str(uuid.uuid4())[:8]
        item = {
            "pk": f"HOUSEHOLD#{household_id}",
            "sk": f"PAYMENT#{payment_id}",
            "household_id": household_id,
            "payment_id": payment_id,
            "from_user_id": from_user_id,
            "to_user_id": to_user_id,
            "amount_paise": amount_paise,
            "created_at": datetime.utcnow().isoformat(),
            "request_id": request_id,
        }

        try:
            get_storage_provider().put_item(item)
            DynamoDBOps._audit_log(
                "PAYMENT_RECORD",
                household_id,
                {
                    "from": from_user_id,
                    "to": to_user_id,
                    "amount_paise": amount_paise,
                },
            )
            return item
        except Exception as e:
            logger.error(f"Failed to record payment: {e}")
            raise

    @staticmethod
    def assign_chore(
        household_id: str,
        chore_id: str,
        assigned_to: str,
        request_id: str = "",
    ) -> Dict:
        """Reassign a chore to a different member."""
        chore = get_storage_provider().get_item(
            pk=f"HOUSEHOLD#{household_id}",
            sk=f"CHORE#{chore_id}"
        )

        if not chore:
            raise ValueError(f"Chore {chore_id} not found")

        chore["assigned_to"] = assigned_to
        chore["request_id"] = request_id

        try:
            get_storage_provider().put_item(chore)
            DynamoDBOps._audit_log(
                "CHORE_REASSIGN",
                household_id,
                {"chore_id": chore_id, "new_assignee": assigned_to},
            )
            return chore
        except Exception as e:
            logger.error(f"Failed to reassign chore: {e}")
            raise

    @staticmethod
    def get_audit_records(household_id: str, limit: int = 20) -> List[Dict]:
        """Get recent audit records."""
        try:
            result = get_storage_provider().query(
                pk=f"HOUSEHOLD#{household_id}",
                sk_prefix="AUDIT#",
                limit=limit
            )
            return sorted(result.items, key=lambda x: x.get("timestamp", ""), reverse=True)
        except Exception as e:
            logger.error(f"Failed to get audit records: {e}")
            raise
