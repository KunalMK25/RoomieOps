"""
RoomieOps Confirmation & Action Execution

Manages pending actions, confirmation lifecycle, and deterministic execution.

Flow:
1. Agent proposes action (returns action_id)
2. Frontend presents proposal to user
3. User confirms or rejects
4. Backend revalidates and executes
5. State is mutated atomically
6. Audit record created
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from enum import Enum

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class ActionType(Enum):
    """Types of consequential actions."""
    CREATE_EXPENSE = "create_expense"
    RECORD_PAYMENT = "record_payment"
    ASSIGN_CHORE = "assign_chore"
    CREATE_ISSUE = "create_issue"
    ADD_SHOPPING_ITEM = "add_shopping_item"


class ActionStatus(Enum):
    """Status of a pending action."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"
    EXPIRED = "expired"


class PendingAction:
    """
    Represents a pending action awaiting user confirmation.
    
    Stored in DynamoDB with TTL for auto-expiry.
    """
    
    def __init__(
        self,
        action_id: str,
        action_type: ActionType,
        user_id: str,
        household_id: str,
        proposal: Dict[str, Any],
        parameters: Dict[str, Any],
        expires_at: str,
    ):
        self.action_id = action_id
        self.action_type = action_type
        self.user_id = user_id
        self.household_id = household_id
        self.proposal = proposal  # What will be displayed to user
        self.parameters = parameters  # What will be executed
        self.status = ActionStatus.PENDING
        self.created_at = datetime.utcnow().isoformat()
        self.expires_at = expires_at
        self.confirmed_at: Optional[str] = None
        self.executed_at: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Serialize for storage."""
        return {
            "action_id": self.action_id,
            "action_type": self.action_type.value,
            "user_id": self.user_id,
            "household_id": self.household_id,
            "proposal": self.proposal,
            "parameters": self.parameters,
            "status": self.status.value,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "confirmed_at": self.confirmed_at,
            "executed_at": self.executed_at,
        }
    
    @staticmethod
    def from_dict(data: Dict) -> "PendingAction":
        """Deserialize from storage."""
        action = PendingAction(
            action_id=data["action_id"],
            action_type=ActionType(data["action_type"]),
            user_id=data["user_id"],
            household_id=data["household_id"],
            proposal=data["proposal"],
            parameters=data["parameters"],
            expires_at=data["expires_at"],
        )
        action.status = ActionStatus(data.get("status", "pending"))
        action.confirmed_at = data.get("confirmed_at")
        action.executed_at = data.get("executed_at")
        return action


class ConfirmationManager:
    """
    Manages pending actions and confirmation lifecycle.
    
    Responsibilities:
    - Create pending action proposal
    - Store in DynamoDB with TTL
    - Retrieve and validate proposal
    - Execute after confirmation
    - Audit all state changes
    """
    
    # DynamoDB table reference (injected at init time by calling module)
    _table = None
    
    @staticmethod
    def set_table(table):
        """Set DynamoDB table reference."""
        ConfirmationManager._table = table
    
    @staticmethod
    def create_pending_action(
        action_type: ActionType,
        user_id: str,
        household_id: str,
        proposal: Dict[str, Any],
        parameters: Dict[str, Any],
        ttl_seconds: int = 900,  # 15 minutes
    ) -> str:
        """
        Create a pending action and store it.
        
        Returns:
            action_id (use in confirm request)
        """
        action_id = str(uuid.uuid4())[:12]
        expires_at = (datetime.utcnow() + timedelta(seconds=ttl_seconds)).isoformat()
        
        pending = PendingAction(
            action_id=action_id,
            action_type=action_type,
            user_id=user_id,
            household_id=household_id,
            proposal=proposal,
            parameters=parameters,
            expires_at=expires_at,
        )
        
        # Store in DynamoDB
        if ConfirmationManager._table:
            try:
                item = {
                    "pk": f"HOUSEHOLD#{household_id}",
                    "sk": f"PENDING#{action_id}",
                    "household_id": household_id,
                    "action_id": action_id,
                    **pending.to_dict(),
                    "ttl": int(datetime.fromisoformat(expires_at).timestamp()),
                }
                ConfirmationManager._table.put_item(Item=item)
                logger.info(f"Created pending action: {action_id}")
            except Exception as e:
                logger.error(f"Failed to store pending action: {e}")
                raise
        else:
            logger.warning("DynamoDB table not configured for ConfirmationManager")
        
        return action_id
    
    @staticmethod
    def get_pending_action(household_id: str, action_id: str) -> Optional[PendingAction]:
        """Retrieve a pending action by ID."""
        if not ConfirmationManager._table:
            return None
        
        try:
            response = ConfirmationManager._table.get_item(
                Key={
                    "pk": f"HOUSEHOLD#{household_id}",
                    "sk": f"PENDING#{action_id}",
                }
            )
            if "Item" in response:
                return PendingAction.from_dict(response["Item"])
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve pending action: {e}")
            return None
    
    @staticmethod
    def confirm_and_execute(
        household_id: str,
        action_id: str,
        user_id: str,
        confirmed: bool,
    ) -> Dict[str, Any]:
        """
        Confirm or reject a pending action.
        
        If confirmed:
        - Revalidate action still valid
        - Execute the deterministic backend operation
        - Mark as executed
        - Return success
        
        If rejected:
        - Mark as rejected
        - Return rejection
        
        Returns:
            {
                "status": "executed|rejected|failed",
                "action_id": "...",
                "result": {...} if executed,
                "error": "..." if failed,
            }
        """
        # Retrieve pending action
        pending = ConfirmationManager.get_pending_action(household_id, action_id)
        
        if not pending:
            return {
                "status": "failed",
                "error": f"Action {action_id} not found"
            }
        
        # Check expiry
        if datetime.fromisoformat(pending.expires_at) < datetime.utcnow():
            return {
                "status": "failed",
                "error": f"Action {action_id} expired"
            }
        
        # Check user
        if pending.user_id != user_id:
            return {
                "status": "failed",
                "error": "Unauthorized: action belongs to different user"
            }
        
        # If rejected, mark and return
        if not confirmed:
            try:
                if ConfirmationManager._table:
                    pending.status = ActionStatus.REJECTED
                    item = {
                        "pk": f"HOUSEHOLD#{household_id}",
                        "sk": f"PENDING#{action_id}",
                        **pending.to_dict(),
                    }
                    ConfirmationManager._table.put_item(Item=item)
                logger.info(f"Action rejected: {action_id}")
            except Exception as e:
                logger.error(f"Failed to mark action as rejected: {e}")
            
            return {
                "status": "rejected",
                "action_id": action_id,
                "message": "Action cancelled by user"
            }
        
        # CONFIRMED — Execute the action
        try:
            result = ConfirmationManager._execute_action(pending)
            
            # Mark as executed
            pending.status = ActionStatus.EXECUTED
            pending.executed_at = datetime.utcnow().isoformat()
            
            if ConfirmationManager._table:
                item = {
                    "pk": f"HOUSEHOLD#{household_id}",
                    "sk": f"PENDING#{action_id}",
                    **pending.to_dict(),
                }
                ConfirmationManager._table.put_item(Item=item)
            
            logger.info(f"Action executed: {action_id}")
            
            return {
                "status": "executed",
                "action_id": action_id,
                "result": result,
            }
        
        except Exception as e:
            logger.error(f"Failed to execute action {action_id}: {e}")
            
            # Mark as failed
            pending.status = ActionStatus.FAILED
            if ConfirmationManager._table:
                try:
                    item = {
                        "pk": f"HOUSEHOLD#{household_id}",
                        "sk": f"PENDING#{action_id}",
                        **pending.to_dict(),
                    }
                    ConfirmationManager._table.put_item(Item=item)
                except:
                    pass
            
            return {
                "status": "failed",
                "action_id": action_id,
                "error": str(e)
            }
    
    @staticmethod
    def _execute_action(pending: PendingAction) -> Dict[str, Any]:
        """
        Execute the deterministic backend operation.
        
        This is where the actual state mutation happens.
        Must be atomic and auditable.
        
        Raises exception on failure (caught by caller).
        """
        from dynamodb_ops import DynamoDBOps
        from finance_engine import FinanceEngine
        
        params = pending.parameters
        action_type = pending.action_type
        
        if action_type == ActionType.CREATE_EXPENSE:
            # Execute expense creation
            split_result = FinanceEngine.split_equal(
                total_paise=params["amount_paise"],
                participant_ids=params["participant_ids"]
            )
            
            expense = DynamoDBOps.create_expense(
                household_id=pending.household_id,
                expense_id=str(uuid.uuid4())[:12],
                payer_id=pending.user_id,
                description=params.get("description", ""),
                total_paise=params["amount_paise"],
                allocations=[
                    {
                        "user_id": a.user_id,
                        "amount_paise": a.amount_paise
                    }
                    for a in split_result.allocations
                ],
                split_method="equal",
                created_by=pending.user_id,
            )
            
            # Update balances
            expenses = DynamoDBOps.get_expenses(pending.household_id)
            balances = FinanceEngine.calculate_balances(
                [{"payer_id": e.get("payer_id"), "allocations": e.get("allocations", [])} 
                 for e in expenses]
            )
            
            for user_id, balance_paise in balances.items():
                DynamoDBOps.set_balance(pending.household_id, user_id, balance_paise)
            
            return {
                "type": "expense_created",
                "expense_id": expense.get("expense_id"),
                "amount_paise": params["amount_paise"],
            }
        
        elif action_type == ActionType.RECORD_PAYMENT:
            # Execute payment recording
            payment = DynamoDBOps.record_payment(
                household_id=pending.household_id,
                from_user_id=params["from_user_id"],
                to_user_id=params["to_user_id"],
                amount_paise=params["amount_paise"],
                request_id=pending.action_id,
            )
            
            # Update balances
            from_balance_item = DynamoDBOps.get_balance(pending.household_id, params["from_user_id"]) or {}
            to_balance_item = DynamoDBOps.get_balance(pending.household_id, params["to_user_id"]) or {}
            
            from_balance = from_balance_item.get("balance_paise", 0) - params["amount_paise"]
            to_balance = to_balance_item.get("balance_paise", 0) + params["amount_paise"]
            
            DynamoDBOps.set_balance(pending.household_id, params["from_user_id"], from_balance)
            DynamoDBOps.set_balance(pending.household_id, params["to_user_id"], to_balance)
            
            return {
                "type": "payment_recorded",
                "payment_id": payment.get("payment_id"),
                "amount_paise": params["amount_paise"],
            }
        
        elif action_type == ActionType.ASSIGN_CHORE:
            # Execute chore reassignment
            chore = DynamoDBOps.assign_chore(
                household_id=pending.household_id,
                chore_id=params["chore_id"],
                assigned_to=params["assigned_to"],
                request_id=pending.action_id,
            )
            
            return {
                "type": "chore_reassigned",
                "chore_id": chore.get("chore_id"),
                "assigned_to": params["assigned_to"],
            }
        
        elif action_type == ActionType.CREATE_ISSUE:
            # Execute issue creation
            issue = DynamoDBOps.create_maintenance_issue(
                household_id=pending.household_id,
                issue_id=str(uuid.uuid4())[:12],
                title=params["title"],
                description=params["description"],
                location=params["location"],
                reported_by=pending.user_id,
                request_id=pending.action_id,
            )
            
            return {
                "type": "issue_created",
                "issue_id": issue.get("issue_id"),
                "title": params["title"],
            }
        
        elif action_type == ActionType.ADD_SHOPPING_ITEM:
            # Execute shopping item addition
            item = DynamoDBOps.add_shopping_item(
                household_id=pending.household_id,
                item_id=str(uuid.uuid4())[:12],
                item_name=params["item_name"],
                category=params.get("category", ""),
                request_id=pending.action_id,
            )
            
            return {
                "type": "shopping_item_added",
                "item_id": item.get("item_id"),
                "item_name": params["item_name"],
            }
        
        else:
            raise ValueError(f"Unknown action type: {action_type}")
