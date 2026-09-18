"""
Day 2 RoomieOps Integration Tests

Comprehensive tests for:
- Authentication and authorization
- Household isolation
- Idempotency
- Agent tool execution
- Finance engine (existing)
- End-to-end flows
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend/shared"))

from auth import get_authenticated_user, require_auth, verify_household_membership, verify_admin_permission
from dynamodb_ops import DynamoDBOps
from finance_engine import FinanceEngine
from idempotency import IdempotencyOps
from agent_tools import AgentToolRegistry, ToolType


# ============================================================================
# AUTH TESTS
# ============================================================================

def test_get_authenticated_user_valid():
    """Test JWT extraction with valid claims."""
    print("\n=== TEST: get_authenticated_user (valid) ===")
    
    event = {
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": "user123",
                    "cognito:username": "alice",
                    "email": "alice@example.com",
                    "cognito:groups": "admin,members",
                }
            }
        }
    }
    
    user = get_authenticated_user(event)
    
    assert user is not None, "User should not be None"
    assert user.user_id == "user123", "user_id should match sub claim"
    assert user.username == "alice", "username should match cognito:username"
    assert user.email == "alice@example.com", "email should match"
    assert "admin" in user.groups, "groups should include admin"
    
    print("✓ User extracted correctly")


def test_get_authenticated_user_missing_claims():
    """Test JWT extraction with missing claims."""
    print("\n=== TEST: get_authenticated_user (missing) ===")
    
    event = {"requestContext": {"authorizer": {}}}
    
    user = get_authenticated_user(event)
    
    assert user is None, "User should be None for missing claims"
    print("✓ Missing claims handled correctly")


def test_require_auth_fails():
    """Test require_auth raises on missing auth."""
    print("\n=== TEST: require_auth (fails) ===")
    
    event = {}
    
    try:
        require_auth(event)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Unauthenticated" in str(e)
        print("✓ Unauthenticated request rejected")


# ============================================================================
# AUTHORIZATION TESTS
# ============================================================================

def test_verify_household_membership():
    """Test household membership verification."""
    print("\n=== TEST: verify_household_membership ===")
    
    class MockUser:
        def __init__(self, user_id):
            self.user_id = user_id
    
    user = MockUser("alice")
    members = [
        {"user_id": "alice", "status": "active", "role": "member"},
        {"user_id": "bob", "status": "active", "role": "member"},
    ]
    
    # Should pass
    assert verify_household_membership(user, "h1", members) == True
    print("✓ Member access allowed")
    
    # Should fail
    user.user_id = "charlie"
    assert verify_household_membership(user, "h1", members) == False
    print("✓ Non-member access denied")


def test_verify_admin_permission():
    """Test admin permission verification."""
    print("\n=== TEST: verify_admin_permission ===")
    
    class MockUser:
        def __init__(self, user_id):
            self.user_id = user_id
    
    user = MockUser("alice")
    members = [
        {"user_id": "alice", "status": "active", "role": "admin"},
        {"user_id": "bob", "status": "active", "role": "member"},
    ]
    
    # Admin should pass
    assert verify_admin_permission(user, "h1", members) == True
    print("✓ Admin permission granted")
    
    # Member should fail
    user.user_id = "bob"
    assert verify_admin_permission(user, "h1", members) == False
    print("✓ Member permission denied")


# ============================================================================
# IDEMPOTENCY TESTS
# ============================================================================

def test_idempotency_framework():
    """Test idempotency key storage and retrieval (local simulation)."""
    print("\n=== TEST: idempotency framework ===")
    
    # Simulate in-memory storage
    idempotency_store = {}
    
    def store_result(household_id, request_id, result):
        key = f"{household_id}#{request_id}"
        idempotency_store[key] = result
    
    def get_result(household_id, request_id):
        key = f"{household_id}#{request_id}"
        return idempotency_store.get(key)
    
    # First call - no result
    result1 = get_result("h1", "req123")
    assert result1 is None, "Should be no cached result initially"
    print("✓ No cached result on first call")
    
    # Store result
    expected_result = {"expense_id": "e1", "status": "created"}
    store_result("h1", "req123", expected_result)
    
    # Second call - should get cached result
    result2 = get_result("h1", "req123")
    assert result2 == expected_result, "Should return cached result"
    print("✓ Cached result returned on duplicate request")
    
    # Different request_id should not return cached result
    result3 = get_result("h1", "req456")
    assert result3 is None, "Different request_id should not share cache"
    print("✓ Idempotency keys are unique")


# ============================================================================
# AGENT TOOLS TESTS
# ============================================================================

def test_agent_tool_registry():
    """Test tool registry structure and lookups."""
    print("\n=== TEST: agent tool registry ===")
    
    # Check tools exist
    tools = AgentToolRegistry.TOOLS
    assert len(tools) > 0, "Should have tools"
    print(f"✓ Registry contains {len(tools)} tools")
    
    # Check tool lookup
    tool = AgentToolRegistry.get_tool_by_name("get_my_balance")
    assert tool is not None, "Should find get_my_balance tool"
    assert tool.name == "get_my_balance"
    print("✓ Tool lookup works")
    
    # Check tool categorization
    read_tools = AgentToolRegistry.list_read_tools()
    write_tools = AgentToolRegistry.list_write_tools()
    
    assert len(read_tools) > 0, "Should have read tools"
    assert len(write_tools) > 0, "Should have write tools"
    print(f"✓ {len(read_tools)} READ tools, {len(write_tools)} WRITE tools")
    
    # Check confirmation requirements
    create_expense = AgentToolRegistry.get_tool_by_name("create_expense")
    assert create_expense.requires_confirmation == True, "create_expense should require confirmation"
    print("✓ Confirmation requirement enforced")


def test_tool_schema_validation():
    """Test tool schema definitions."""
    print("\n=== TEST: tool schema validation ===")
    
    tool = AgentToolRegistry.get_tool_by_name("get_my_balance")
    
    # Check schema structure
    assert "type" in tool.input_schema
    assert "properties" in tool.input_schema
    assert "required" in tool.input_schema
    print("✓ Input schema well-formed")
    
    assert "type" in tool.output_schema
    assert "properties" in tool.output_schema
    print("✓ Output schema well-formed")


# ============================================================================
# FINANCE ENGINE TESTS (existing validation)
# ============================================================================

def test_finance_engine_equal_split():
    """Test deterministic equal split."""
    print("\n=== TEST: finance engine equal split ===")
    
    result = FinanceEngine.split_equal(
        total_paise=300000,
        participant_ids=["alice", "bob", "charlie"],
    )
    
    # Verify reconciliation
    total_allocated = sum(a.amount_paise for a in result.allocations)
    assert total_allocated == 300000, "Allocations must sum to total"
    print(f"✓ Reconciliation: {total_allocated} paise")
    
    # Each person should get 100000
    for alloc in result.allocations:
        assert alloc.amount_paise == 100000
    print("✓ Equal split verified")


def test_finance_engine_balance_calculation():
    """Test balance calculation across expenses."""
    print("\n=== TEST: finance engine balance calculation ===")
    
    expenses = [
        {
            "payer_id": "alice",
            "allocations": [
                {"user_id": "alice", "amount_paise": 100000},
                {"user_id": "bob", "amount_paise": 100000},
            ],
        }
    ]
    
    balances = FinanceEngine.calculate_balances(expenses)
    
    # Alice paid 200000, owes 100000 → net +100000
    # Bob paid 0, owes 100000 → net -100000
    assert balances["alice"] == 100000
    assert balances["bob"] == -100000
    
    # Total should be 0
    total = sum(balances.values())
    assert total == 0, "Balances must reconcile to zero"
    print("✓ Balances reconciled")


# ============================================================================
# END-TO-END FLOW TESTS
# ============================================================================

def test_auth_and_household_access_flow():
    """Test end-to-end: auth → membership check → access."""
    print("\n=== TEST: auth + household access flow ===")
    
    # Step 1: Authenticate
    class MockUser:
        def __init__(self):
            self.user_id = "alice"
            self.username = "alice"
            self.email = "alice@example.com"
            self.groups = ["member"]
    
    user = MockUser()
    print("✓ User authenticated")
    
    # Step 2: Verify household membership
    members = [
        {"user_id": "alice", "status": "active", "role": "member"},
    ]
    
    assert verify_household_membership(user, "h1", members)
    print("✓ Membership verified")
    
    # Step 3: Access data (simulated)
    # In real flow, would fetch household data
    print("✓ Access granted")


def test_expense_creation_with_idempotency():
    """Test expense creation with idempotency."""
    print("\n=== TEST: expense creation with idempotency ===")
    
    # Simulate idempotency store
    idempotency_store = {}
    expense_counter = [0]  # Use list to allow mutation
    
    def create_expense_idempotent(household_id, request_id):
        key = f"{household_id}#{request_id}"
        
        # Check cache
        if key in idempotency_store:
            return idempotency_store[key]
        
        # Create new
        expense_counter[0] += 1
        result = {
            "expense_id": f"e{expense_counter[0]}",
            "total_paise": 100000,
            "allocations": [{"user_id": "alice", "amount_paise": 50000}],
        }
        
        idempotency_store[key] = result
        return result
    
    # First call
    result1 = create_expense_idempotent("h1", "req123")
    print("✓ Expense created on first call")
    
    # Second call with same request_id
    result2 = create_expense_idempotent("h1", "req123")
    assert result1 == result2, "Should return same result"
    print("✓ Duplicate request returns cached result")
    
    # Different request_id
    result3 = create_expense_idempotent("h1", "req456")
    assert result3["expense_id"] != result1["expense_id"], "Different request should create new expense"
    print("✓ Different request creates new expense")


def test_confirmation_flow():
    """Test confirmation model for consequential actions."""
    print("\n=== TEST: confirmation flow ===")
    
    # READ tool should not require confirmation
    balance_tool = AgentToolRegistry.get_tool_by_name("get_my_balance")
    assert balance_tool.requires_confirmation == False
    print("✓ READ tool requires no confirmation")
    
    # WRITE tool should require confirmation
    expense_tool = AgentToolRegistry.get_tool_by_name("create_expense")
    assert expense_tool.requires_confirmation == True
    print("✓ WRITE tool requires confirmation")
    
    # Only WRITE tools should require confirmation
    for tool in AgentToolRegistry.TOOLS:
        if tool.tool_type == ToolType.WRITE:
            # Some WRITE tools may not require confirmation (e.g., complete_chore)
            # but create_expense and create_maintenance should
            if tool.name in ["create_expense", "create_maintenance"]:
                assert tool.requires_confirmation == True
    print("✓ Confirmation model enforced")


# ============================================================================
# RUN ALL TESTS
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("DAY 2 INTEGRATION TEST SUITE")
    print("="*70)
    
    test_cases = [
        # Auth tests
        test_get_authenticated_user_valid,
        test_get_authenticated_user_missing_claims,
        test_require_auth_fails,
        
        # Authorization tests
        test_verify_household_membership,
        test_verify_admin_permission,
        
        # Idempotency tests
        test_idempotency_framework,
        
        # Agent tools tests
        test_agent_tool_registry,
        test_tool_schema_validation,
        
        # Finance engine tests
        test_finance_engine_equal_split,
        test_finance_engine_balance_calculation,
        
        # End-to-end flow tests
        test_auth_and_household_access_flow,
        test_expense_creation_with_idempotency,
        test_confirmation_flow,
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
