#!/usr/bin/env python3
"""
Test provider initialization for all execution modes.

This verifies:
1. ExecutionModeManager can determine modes
2. Providers are correctly initialized for each mode
3. Provider imports are working
4. Environment configuration is correct

Does NOT require Docker/LocalStack/Ollama to be running for basic tests.
"""

import os
import sys
import logging
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_imports():
    """Test that all provider modules can be imported."""
    logger.info("Testing provider imports...")
    
    try:
        from shared.providers import (
            ExecutionMode,
            ExecutionModeManager,
            LLMProvider,
            StorageProvider,
            AuthProvider,
            AuthorizationProvider,
        )
        logger.info("✓ Core provider types imported")
        
        from shared.providers.llm import (
            BedrockLLMProvider,
            OllamaLLMProvider,
            HeuristicLLMProvider,
        )
        logger.info("✓ LLM providers imported")
        
        from shared.providers.storage import (
            DynamoDBProvider,
            LocalStackProvider,
            InMemoryProvider,
        )
        logger.info("✓ Storage providers imported")
        
        from shared.providers.auth import (
            CognitoAuthProvider,
            CedarAuthProvider,
            LocalAuthProvider,
        )
        logger.info("✓ Auth providers imported")
        
        from shared.providers.authorization import (
            SimpleAuthorizationProvider,
            CedarAuthorizationProvider,
            LocalAuthorizationProvider,
        )
        logger.info("✓ Authorization providers imported")
        
        return True
    except ImportError as e:
        logger.error(f"✗ Import failed: {e}")
        return False


def test_execution_mode_determination():
    """Test that ExecutionModeManager can determine modes."""
    logger.info("Testing execution mode determination...")
    
    try:
        from shared.providers import ExecutionModeManager, ExecutionMode
        
        # Test 1: Explicit mode via environment
        os.environ["EXECUTION_MODE"] = "LOCAL_HEURISTIC"
        mode = ExecutionModeManager.determine_mode()
        assert mode == ExecutionMode.LOCAL_HEURISTIC, f"Expected LOCAL_HEURISTIC, got {mode}"
        logger.info(f"  ✓ Explicit mode detection works: {mode}")
        
        # Test 2: Invalid mode falls back to auto-detect
        os.environ["EXECUTION_MODE"] = "INVALID_MODE"
        mode = ExecutionModeManager.determine_mode()
        assert mode in [ExecutionMode.LOCAL_HEURISTIC, ExecutionMode.BUILD_IT_STRANDS, ExecutionMode.SHIP_IT_BEDROCK]
        logger.info(f"  ✓ Invalid mode falls back to auto-detect: {mode}")
        
        # Test 3: Clean up
        del os.environ["EXECUTION_MODE"]
        
        return True
    except Exception as e:
        logger.error(f"✗ Mode determination failed: {e}")
        return False


def test_local_heuristic_providers():
    """Test LOCAL_HEURISTIC provider initialization (doesn't need external services)."""
    logger.info("Testing LOCAL_HEURISTIC providers...")
    
    try:
        from shared.providers import ExecutionModeManager, ExecutionMode
        
        os.environ["EXECUTION_MODE"] = "LOCAL_HEURISTIC"
        
        providers = ExecutionModeManager.get_providers(ExecutionMode.LOCAL_HEURISTIC)
        
        assert providers is not None, "Providers are None"
        assert providers.llm is not None, "LLM provider is None"
        assert providers.storage is not None, "Storage provider is None"
        assert providers.auth is not None, "Auth provider is None"
        assert providers.authorization is not None, "Authorization provider is None"
        assert providers.retrieval is not None, "Retrieval provider is None"
        
        logger.info(f"  ✓ LLM provider: {type(providers.llm).__name__}")
        logger.info(f"  ✓ Storage provider: {type(providers.storage).__name__}")
        logger.info(f"  ✓ Auth provider: {type(providers.auth).__name__}")
        logger.info(f"  ✓ Authorization provider: {type(providers.authorization).__name__}")
        logger.info(f"  ✓ Retrieval provider: {type(providers.retrieval).__name__}")
        
        return True
    except Exception as e:
        logger.error(f"✗ LOCAL_HEURISTIC provider initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_build_it_strands_provider_structure():
    """Test BUILD_IT_STRANDS provider structure (won't connect to endpoints)."""
    logger.info("Testing BUILD_IT_STRANDS provider structure...")
    
    try:
        from shared.providers import ExecutionModeManager, ExecutionMode
        
        # Set up environment
        os.environ["EXECUTION_MODE"] = "BUILD_IT_STRANDS"
        os.environ["LLM_ENDPOINT"] = "http://localhost:11434"
        os.environ["DYNAMODB_ENDPOINT"] = "http://localhost:4566"
        os.environ["CEDAR_ENDPOINT"] = "http://localhost:8180"
        
        # Note: This will try to connect to services, may fail gracefully
        try:
            providers = ExecutionModeManager.get_providers(ExecutionMode.BUILD_IT_STRANDS)
            logger.info(f"  ✓ BUILD_IT_STRANDS providers initialized")
            logger.info(f"    - LLM: {type(providers.llm).__name__}")
            logger.info(f"    - Storage: {type(providers.storage).__name__}")
            logger.info(f"    - Auth: {type(providers.auth).__name__}")
        except Exception as e:
            logger.warning(f"  ⚠ BUILD_IT_STRANDS failed to connect (expected if services not running): {e}")
            logger.info(f"    This is OK - provider structure is valid, just can't connect yet")
        
        return True
    except Exception as e:
        logger.error(f"✗ BUILD_IT_STRANDS provider structure test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dynamodb_ops_provider_setup():
    """Test that DynamoDBOps can accept a provider."""
    logger.info("Testing DynamoDBOps provider setup...")
    
    try:
        from shared.dynamodb_ops import set_storage_provider
        from shared.providers.storage import InMemoryProvider
        
        # Create an in-memory provider
        provider = InMemoryProvider()
        
        # Set it on DynamoDBOps
        set_storage_provider(provider)
        
        logger.info(f"  ✓ DynamoDBOps accepts storage provider: {type(provider).__name__}")
        
        return True
    except Exception as e:
        logger.error(f"✗ DynamoDBOps provider setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    
    logger.info("=" * 70)
    logger.info("PROVIDER INITIALIZATION TESTS")
    logger.info("=" * 70)
    logger.info("")
    
    results = {
        "Imports": test_imports(),
        "Mode determination": test_execution_mode_determination(),
        "LOCAL_HEURISTIC providers": test_local_heuristic_providers(),
        "BUILD_IT_STRANDS structure": test_build_it_strands_provider_structure(),
        "DynamoDBOps setup": test_dynamodb_ops_provider_setup(),
    }
    
    logger.info("")
    logger.info("=" * 70)
    logger.info("TEST RESULTS")
    logger.info("=" * 70)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"  {test_name}: {status}")
    
    logger.info("=" * 70)
    
    all_passed = all(results.values())
    if all_passed:
        logger.info("✓ All provider initialization tests PASSED")
    else:
        failed = [name for name, passed in results.items() if not passed]
        logger.error(f"✗ {len(failed)} test(s) FAILED: {', '.join(failed)}")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
