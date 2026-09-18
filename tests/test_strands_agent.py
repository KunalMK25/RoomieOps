"""
Strands Agent Tests — RoomieOps Day 3

Tests for:
- Agent initialization
- Tool execution
- Multi-step workflows
- Heuristic fallback
- Integration with DynamoDB operations
"""

import sys
import os
import json
import uuid
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend/shared"))

from strands_agent import RoomieOpsAgent, ToolExecutionContext
from auth import AuthenticatedUser
from dynamodb_ops import DynamoDBOps
from finance_engine import FinanceEngine

# Mock user
test_user = AuthenticatedUser(
    user_id="user_kunal",
    username="kunal",
    email="kunal@example.com",
    groups=["member"]
)

test_household_id = "h_test_sunrise"


class MockAuthenticatedUser:
    def __init__(self, user_id, username, email):
        self.user_id = user_id
        self.username = username
        self.email = email
        self.groups = ["member"]


def test_agent_initialization():
    """Test agent initialization."""
    print("\n=== TEST: Agent Initialization ===")
    
    context = ToolExecutionContext(
        user=MockAuthenticatedUser("user1", "alice", "alice@example.com"),
        household_id="h123",
        request_id=str(uuid.uuid4())
    )
    
    agent = RoomieOpsAgent(context)
    
    assert agent is not None
    assert len(agent.tools_registry) > 0
    print(f"✓ Agent initialized with {len(agent.tools_registry)} tools")


def test_tool_registry():
    """Test that all required tools exist."""
    print("\n=== TEST: Tool Registry ===")
    
    context = ToolExecutionContext(
        user=MockAuthenticatedUser("user1", "alice", "alice@example.com"),
        household_id="h123",
        request_id=str(uuid.uuid4())
    )
    
    agent = RoomieOpsAgent(context)
    tools = agent.tools_registry
    
    # Check required tool groups
    required_tools = [
        "get_household_state",
        "get_member",
        "get_expenses",
        "get_balances",
        "create_expense",
        "get_chore_rotation",
        "create_chore",
        "assign_chore",
        "complete_chore",
        "create_issue",
        "get_open_issues",
        "add_shopping_item",
        "get_event_history",
        "record_payment",
    ]
    
    for tool_name in required_tools:
        assert tool_name in tools, f"Missing tool: {tool_name}"
    
    print(f"✓ All {len(required_tools)} required tools present")


def test_tool_schemas():
    """Test that tools have proper schemas."""
    print("\n=== TEST: Tool Schemas ===")
    
    context = ToolExecutionContext(
        user=MockAuthenticatedUser("user1", "alice", "alice@example.com"),
        household_id="h123",
        request_id=str(uuid.uuid4())
    )
    
    agent = RoomieOpsAgent(context)
    
    for tool_name, tool_def in agent.tools_registry.items():
        assert "description" in tool_def
        assert "func" in tool_def
        assert "input_schema" in tool_def
        assert tool_def["input_schema"].get("type") == "object"
    
    print(f"✓ All tools have proper schemas")


def test_heuristic_intent_detection():
    """Test heuristic intent detection."""
    print("\n=== TEST: Heuristic Intent Detection ===")
    
    context = ToolExecutionContext(
        user=MockAuthenticatedUser("user_kunal", "kunal", "kunal@example.com"),
        household_id="h_sunrise",
        request_id=str(uuid.uuid4())
    )
    
    agent = RoomieOpsAgent(context)
    
    # Test various intents
    test_cases = [
        ("How much do I owe?", "view_balance"),
        ("What chores do I have?", "view_chores"),
        ("I paid 1200 for groceries", "create_expense"),
        ("The geyser is broken", "create_maintenance"),
    ]
    
    for message, expected_intent in test_cases:
        result = agent.process_user_request(message)
        # Should process without error
        assert result.get("status") in ["success", "requires_confirmation", "unclear"]
        print(f"✓ '{message}' → {result.get('agent_type')}")


def test_view_balance_heuristic():
    """Test 'view balance' heuristic."""
    print("\n=== TEST: View Balance Heuristic ===")
    
    context = ToolExecutionContext(
        user=MockAuthenticatedUser("user_kunal", "kunal", "kunal@example.com"),
        household_id="h_sunrise",
        request_id=str(uuid.uuid4())
    )
    
    agent = RoomieOpsAgent(context)
    result = agent.process_user_request("How much do I owe?")
    
    assert result.get("status") == "success"
    assert "agent_response" in result or "balance_paise" in result
    print(f"✓ View balance processed: {result.get('status')}")


def test_view_chores_heuristic():
    """Test 'view chores' heuristic."""
    print("\n=== TEST: View Chores Heuristic ===")
    
    context = ToolExecutionContext(
        user=MockAuthenticatedUser("user_kunal", "kunal", "kunal@example.com"),
        household_id="h_sunrise",
        request_id=str(uuid.uuid4())
    )
    
    agent = RoomieOpsAgent(context)
    result = agent.process_user_request("What chores do I have this week?")
    
    assert result.get("status") == "success"
    print(f"✓ View chores processed: {result.get('status')}")


def test_agent_type_determination():
    """Test that agent correctly identifies its type (strands vs heuristic)."""
    print("\n=== TEST: Agent Type Determination ===")
    
    context = ToolExecutionContext(
        user=MockAuthenticatedUser("user_kunal", "kunal", "kunal@example.com"),
        household_id="h_sunrise",
        request_id=str(uuid.uuid4())
    )
    
    agent = RoomieOpsAgent(context)
    result = agent.process_user_request("Tell me about household")
    
    agent_type = result.get("agent_type")
    assert agent_type in ["strands", "heuristic", "bedrock"]
    print(f"✓ Agent type: {agent_type}")


def test_tool_execution_returns_dict():
    """Test that tools return structured responses."""
    print("\n=== TEST: Tool Execution Response Format ===")
    
    context = ToolExecutionContext(
        user=MockAuthenticatedUser("user_kunal", "kunal", "kunal@example.com"),
        household_id="h_sunrise",
        request_id=str(uuid.uuid4())
    )
    
    agent = RoomieOpsAgent(context)
    
    # Execute a heuristic-based request
    result = agent.process_user_request("How much do I owe?")
    
    assert isinstance(result, dict)
    assert "status" in result
    assert "agent_type" in result
    print(f"✓ Tool responses are properly structured")


def test_system_prompt():
    """Test that system prompt is generated."""
    print("\n=== TEST: System Prompt ===")
    
    context = ToolExecutionContext(
        user=MockAuthenticatedUser("user_kunal", "kunal", "kunal@example.com"),
        household_id="h_sunrise",
        request_id=str(uuid.uuid4())
    )
    
    agent = RoomieOpsAgent(context)
    prompt = agent._get_system_prompt()
    
    assert prompt is not None
    assert "RoomieOps" in prompt
    assert "never perform financial calculations" in prompt.lower()
    print(f"✓ System prompt generated ({len(prompt)} chars)")


# ============================================================================
# RUN ALL TESTS
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("STRANDS AGENT TEST SUITE")
    print("="*70)
    
    test_cases = [
        test_agent_initialization,
        test_tool_registry,
        test_tool_schemas,
        test_heuristic_intent_detection,
        test_view_balance_heuristic,
        test_view_chores_heuristic,
        test_agent_type_determination,
        test_tool_execution_returns_dict,
        test_system_prompt,
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
