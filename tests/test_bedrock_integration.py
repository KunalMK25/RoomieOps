"""
Bedrock Integration Tests

Tests Bedrock configuration and model invocation.
If account does not have Bedrock access, reports BLOCKED status.
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend/shared"))

from bedrock_client import BedrockOps, BedrockError


def test_bedrock_invocation():
    """Test Bedrock model invocation."""
    print("\n=== Bedrock Integration Test ===\n")
    
    result = BedrockOps.test_invocation()
    
    print(f"Status: {result['status']}")
    print(f"Model: {result['model']}")
    print(f"Region: {result['region']}")
    
    if result["status"] == "blocked":
        print(f"\n⚠️  BLOCKED — BEDROCK ACCOUNT ACCESS")
        print(f"Reason: {result['reason']}")
        print(f"Error: {result['error']}")
        print("\nNote: This is expected if AWS account has not enabled Bedrock.")
        print("Continuing with locally testable integration boundaries.")
        return False
    elif result["status"] == "success":
        print(f"\n✓ Bedrock invocation successful")
        print(f"Response keys: {result['response_keys']}")
        return True
    else:
        print(f"\n✗ Error: {result['reason']}")
        print(f"Details: {result['error']}")
        return False


def test_intent_detection():
    """Test intent detection (if Bedrock available)."""
    print("\n=== Intent Detection Test ===\n")
    
    try:
        household_context = {
            "members": [
                {"name": "Alice", "user_id": "alice"},
                {"name": "Bob", "user_id": "bob"},
            ],
            "balances": {"alice": 0, "bob": 500},
            "chore_count": 3,
        }
        
        user_message = "How much do I owe?"
        
        result = BedrockOps.detect_intent(user_message, household_context)
        
        print(f"User message: {user_message}")
        print(f"Detected intent: {result.get('intent')}")
        print(f"Confidence: {result.get('confidence')}")
        print(f"Reasoning: {result.get('reasoning', 'N/A')}")
        
        return True
    except BedrockError as e:
        if "BLOCKED" in str(e):
            print(f"⚠️  {str(e)}")
            return False
        else:
            print(f"✗ Error: {str(e)}")
            return False


if __name__ == "__main__":
    invocation_ok = test_bedrock_invocation()
    
    if invocation_ok:
        intent_ok = test_intent_detection()
        if intent_ok:
            print("\n✓ All Bedrock tests passed")
        else:
            print("\n⚠️  Intent detection failed")
    else:
        print("\n⚠️  Bedrock not available (account may not have access)")
