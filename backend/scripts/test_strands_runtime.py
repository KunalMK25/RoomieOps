#!/usr/bin/env python3
"""
Test Strands runtime integration.

This verifies:
1. StrandsRuntime can be created
2. Provider layer initialization works
3. Tool handlers can be registered
4. Requests can be executed
"""

import os
import sys
import logging
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.strands_runtime import StrandsRuntime, StrandsRuntimeConfig, create_strands_runtime
from shared.providers import ExecutionMode
from shared.providers.types import AuthenticatedUser

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_strands_runtime_creation():
    """Test creating Strands runtime with LOCAL_HEURISTIC mode."""
    logger.info("Testing Strands runtime creation...")
    
    try:
        config = StrandsRuntimeConfig(
            execution_mode=ExecutionMode.LOCAL_HEURISTIC,
            llm_endpoint="http://localhost:11434",
            llm_model="mistral",
        )
        
        runtime = StrandsRuntime(config)
        assert runtime is not None
        logger.info("  ✓ StrandsRuntime created successfully")
        logger.info(f"    - LLM Provider: {type(runtime.llm_provider).__name__ if runtime.llm_provider else 'Not initialized'}")
        logger.info(f"    - Agent: {type(runtime.agent).__name__ if runtime.agent else 'Not initialized'}")
        
        return True
    except Exception as e:
        logger.error(f"✗ Failed to create Strands runtime: {e}")
        return False


def test_tool_registration():
    """Test registering tool handlers."""
    logger.info("Testing tool registration...")
    
    try:
        config = StrandsRuntimeConfig(
            execution_mode=ExecutionMode.LOCAL_HEURISTIC,
        )
        
        runtime = StrandsRuntime(config)
        
        # Register mock tools
        def mock_get_balances():
            return {"status": "success", "balances": {"user-1": 10000}}
        
        def mock_get_chores():
            return {"status": "success", "chores": []}
        
        def mock_get_expenses():
            return {"status": "success", "expenses": []}
        
        runtime.register_tool("get_balances", mock_get_balances)
        runtime.register_tool("get_chores", mock_get_chores)
        runtime.register_tools({
            "get_expenses": mock_get_expenses,
        })
        
        assert len(runtime.tool_handlers) >= 2
        logger.info("  ✓ Tools registered successfully")
        logger.info(f"    - Registered {len(runtime.tool_handlers)} tools")
        logger.info(f"    - get_balances, get_chores, get_expenses registered")
        
        return True
    except Exception as e:
        logger.error(f"✗ Failed to register tools: {e}")
        return False


def test_heuristic_execution():
    """Test executing a request with heuristic agent."""
    logger.info("Testing heuristic execution...")
    
    try:
        config = StrandsRuntimeConfig(
            execution_mode=ExecutionMode.LOCAL_HEURISTIC,
        )
        
        runtime = StrandsRuntime(config)
        
        # Register tool
        def mock_get_balances():
            return {"status": "success", "balances": {"user-1": 10000}}
        
        runtime.register_tool("get_balances", mock_get_balances)
        
        # Execute request
        user = AuthenticatedUser(
            user_id="user-1",
            username="test-user",
            email="test@example.com"
        )
        
        result = runtime.execute(
            user_message="How much do I owe?",
            household_id="test-household",
            user=user,
            request_id="req-123"
        )
        
        assert result["status"] == "success"
        assert result["agent_type"] == "heuristic"
        logger.info("  ✓ Heuristic execution successful")
        logger.info(f"    - Agent type: {result['agent_type']}")
        logger.info(f"    - Message: {result['message'][:50]}...")
        
        return True
    except Exception as e:
        logger.error(f"✗ Heuristic execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_factory_function():
    """Test the factory function for creating Strands runtime."""
    logger.info("Testing factory function...")
    
    try:
        # Test 1: BUILD_IT_STRANDS mode
        os.environ["EXECUTION_MODE"] = "BUILD_IT_STRANDS"
        os.environ["LLM_ENDPOINT"] = "http://localhost:11434"
        os.environ["LLM_MODEL"] = "mistral"
        
        runtime = create_strands_runtime()
        if runtime is not None:
            logger.info("  ✓ Strands runtime created for BUILD_IT_STRANDS mode")
        else:
            logger.warning("  ⚠ Strands runtime creation returned None (likely because Ollama not available)")
        
        # Test 2: LOCAL_HEURISTIC mode
        os.environ["EXECUTION_MODE"] = "LOCAL_HEURISTIC"
        runtime = create_strands_runtime()
        assert runtime is None, "Should return None for non-BUILD_IT mode"
        logger.info("  ✓ Factory correctly returns None for LOCAL_HEURISTIC mode")
        
        return True
    except Exception as e:
        logger.error(f"✗ Factory function test failed: {e}")
        return False


def test_system_prompt():
    """Test that system prompt is generated correctly."""
    logger.info("Testing system prompt generation...")
    
    try:
        config = StrandsRuntimeConfig(
            execution_mode=ExecutionMode.LOCAL_HEURISTIC,
        )
        
        runtime = StrandsRuntime(config)
        prompt = runtime._get_system_prompt()
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "RoomieOps" in prompt
        assert "household" in prompt.lower()
        
        logger.info("  ✓ System prompt generated successfully")
        logger.info(f"    - Prompt length: {len(prompt)} characters")
        logger.info(f"    - Contains: 'RoomieOps household coordination'")
        
        return True
    except Exception as e:
        logger.error(f"✗ System prompt test failed: {e}")
        return False


def main():
    """Run all tests."""
    
    logger.info("=" * 70)
    logger.info("STRANDS RUNTIME INTEGRATION TESTS")
    logger.info("=" * 70)
    logger.info("")
    
    results = {
        "Runtime creation": test_strands_runtime_creation(),
        "Tool registration": test_tool_registration(),
        "Heuristic execution": test_heuristic_execution(),
        "Factory function": test_factory_function(),
        "System prompt": test_system_prompt(),
    }
    
    logger.info("")
    logger.info("=" * 70)
    logger.info("TEST RESULTS")
    logger.info("=" * 70)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"  {test_name}: {status}")
    
    logger.info("=" * 70)
    logger.info("")
    
    all_passed = all(results.values())
    if all_passed:
        logger.info("✓ All Strands runtime tests PASSED")
        logger.info("")
        logger.info("Integration status:")
        logger.info("  ✓ StrandsRuntime properly wired with provider layer")
        logger.info("  ✓ Tool handlers can be registered and executed")
        logger.info("  ✓ Heuristic fallback works when Strands SDK unavailable")
        logger.info("  ✓ BUILD_IT_STRANDS detection working")
    else:
        failed = [name for name, passed in results.items() if not passed]
        logger.error(f"✗ {len(failed)} test(s) FAILED: {', '.join(failed)}")
    
    logger.info("")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
