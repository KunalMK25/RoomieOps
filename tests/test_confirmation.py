"""
Confirmation Flow Tests — RoomieOps Day 4

Tests for:
- Pending action creation
- Action proposal
- Confirmation/rejection
- Execution
- Audit trail
"""

import sys
import os
import json
import uuid
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend/shared"))

from confirmation import (
    PendingAction,
    ConfirmationManager,
    ActionType,
    ActionStatus,
)


def test_pending_action_creation():
    """Test creating a pending action."""
    print("\n=== TEST: Pending Action Creation ===")
    
    proposal = {
        "category": "groceries",
        "amount": 1200,
        "participants": ["kunal", "priya", "rahul"]
    }
    
    parameters = {
        "amount_paise": 120000,
        "participant_ids": ["kunal", "priya", "rahul"],
        "description": "Groceries from market"
    }
    
    expires_at = (datetime.utcnow() + timedelta(minutes=15)).isoformat()
    
    pending = PendingAction(
        action_id="act_test_001",
        action_type=ActionType.CREATE_EXPENSE,
        user_id="user_kunal",
        household_id="h_sunrise",
        proposal=proposal,
        parameters=parameters,
        expires_at=expires_at
    )
    
    assert pending.action_id == "act_test_001"
    assert pending.status == ActionStatus.PENDING
    assert pending.user_id == "user_kunal"
    assert pending.action_type == ActionType.CREATE_EXPENSE
    
    print(f"✓ Pending action created: {pending.action_id}")


def test_pending_action_serialization():
    """Test serializing/deserializing pending action."""
    print("\n=== TEST: Pending Action Serialization ===")
    
    proposal = {"amount": 1200}
    parameters = {"amount_paise": 120000}
    expires_at = (datetime.utcnow() + timedelta(minutes=15)).isoformat()
    
    pending1 = PendingAction(
        action_id="act_test_002",
        action_type=ActionType.CREATE_EXPENSE,
        user_id="user_kunal",
        household_id="h_sunrise",
        proposal=proposal,
        parameters=parameters,
        expires_at=expires_at
    )
    
    # Serialize
    data = pending1.to_dict()
    assert isinstance(data, dict)
    assert data["action_id"] == "act_test_002"
    assert data["action_type"] == "create_expense"
    
    # Deserialize
    pending2 = PendingAction.from_dict(data)
    assert pending2.action_id == pending1.action_id
    assert pending2.action_type == pending1.action_type
    assert pending2.user_id == pending1.user_id
    
    print(f"✓ Action serialization round-trip successful")


def test_action_expiry_check():
    """Test that expired actions are handled."""
    print("\n=== TEST: Action Expiry Check ===")
    
    # Create action that expires in the past
    expires_at = (datetime.utcnow() - timedelta(minutes=1)).isoformat()
    
    pending = PendingAction(
        action_id="act_expired",
        action_type=ActionType.CREATE_EXPENSE,
        user_id="user_kunal",
        household_id="h_sunrise",
        proposal={},
        parameters={},
        expires_at=expires_at
    )
    
    # Check if expired
    is_expired = datetime.fromisoformat(pending.expires_at) < datetime.utcnow()
    assert is_expired, "Action should be expired"
    
    print(f"✓ Expired action correctly identified")


def test_action_status_transitions():
    """Test action status transitions."""
    print("\n=== TEST: Action Status Transitions ===")
    
    pending = PendingAction(
        action_id="act_status",
        action_type=ActionType.CREATE_EXPENSE,
        user_id="user_kunal",
        household_id="h_sunrise",
        proposal={},
        parameters={},
        expires_at=(datetime.utcnow() + timedelta(minutes=15)).isoformat()
    )
    
    # Initial status
    assert pending.status == ActionStatus.PENDING
    
    # Transition to confirmed
    pending.status = ActionStatus.CONFIRMED
    assert pending.status == ActionStatus.CONFIRMED
    
    # Transition to executed
    pending.status = ActionStatus.EXECUTED
    pending.executed_at = datetime.utcnow().isoformat()
    assert pending.status == ActionStatus.EXECUTED
    
    print(f"✓ Status transitions working correctly")


def test_action_type_enum():
    """Test all action types are defined."""
    print("\n=== TEST: Action Type Enum ===")
    
    required_types = [
        ActionType.CREATE_EXPENSE,
        ActionType.RECORD_PAYMENT,
        ActionType.ASSIGN_CHORE,
        ActionType.CREATE_ISSUE,
        ActionType.ADD_SHOPPING_ITEM,
    ]
    
    for action_type in required_types:
        assert action_type is not None
        assert action_type.value is not None
    
    print(f"✓ All {len(required_types)} action types defined")


def test_confirmation_manager_no_table():
    """Test ConfirmationManager works without table (for testing)."""
    print("\n=== TEST: ConfirmationManager Without Table ===")
    
    # Manager should work without table set (will skip storage)
    assert ConfirmationManager._table is None
    
    # Create action (should not crash)
    try:
        action_id = ConfirmationManager.create_pending_action(
            action_type=ActionType.CREATE_EXPENSE,
            user_id="user_kunal",
            household_id="h_sunrise",
            proposal={"amount": 1200},
            parameters={"amount_paise": 120000},
        )
        
        # Will log warning but not crash
        assert action_id is not None
        print(f"✓ ConfirmationManager works without table: {action_id}")
    
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        raise


def test_get_pending_action_not_found():
    """Test retrieving non-existent action."""
    print("\n=== TEST: Get Pending Action Not Found ===")
    
    action = ConfirmationManager.get_pending_action("h_fake", "act_notfound")
    assert action is None
    
    print(f"✓ Non-existent action returns None")


# ============================================================================
# RUN ALL TESTS
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("CONFIRMATION FLOW TEST SUITE")
    print("="*70)
    
    test_cases = [
        test_pending_action_creation,
        test_pending_action_serialization,
        test_action_expiry_check,
        test_action_status_transitions,
        test_action_type_enum,
        test_confirmation_manager_no_table,
        test_get_pending_action_not_found,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in test_cases:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ FAILED: {str(e)}")
            failed += 1
        except Exception as e:
            print(f"✗ ERROR: {str(e)}")
            failed += 1
    
    print("\n" + "="*70)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("="*70 + "\n")
    
    if failed > 0:
        sys.exit(1)
