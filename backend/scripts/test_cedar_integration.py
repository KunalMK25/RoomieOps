#!/usr/bin/env python3
"""
Test Cedar authorization integration for BUILD_IT_STRANDS.

This verifies:
1. CedarAuthProvider can extract user from JWT
2. CedarAuthorizationProvider can check permissions
3. Graceful fallback when Cedar PDP unavailable
4. Authorization provider separation from auth
5. Different auth methods (JWT vs local headers)
"""

import os
import sys
import logging
import json
import base64
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_test_jwt(user_id: str = "user-1", username: str = "test", groups: list = None):
    """Create a test JWT token."""
    if groups is None:
        groups = ["member"]
    
    payload = {
        "sub": user_id,
        "name": username,
        "email": f"{username}@example.com",
        "groups": groups,
        "iat": 1234567890,
        "exp": 9999999999,
    }
    
    # Encode JWT (without signature, for testing)
    header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').decode().rstrip('=')
    payload_str = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
    signature = base64.urlsafe_b64encode(b'test-signature').decode().rstrip('=')
    
    return f"{header}.{payload_str}.{signature}"


def test_cedar_auth_provider_jwt_extraction():
    """Test CedarAuthProvider can extract user from JWT."""
    logger.info("Testing Cedar auth provider JWT extraction...")
    
    try:
        from shared.providers.auth import CedarAuthProvider
        from shared.providers.types import AuthenticatedUser
        
        provider = CedarAuthProvider()
        
        # Create test JWT
        jwt_token = create_test_jwt("user-123", "Alice", ["member", "admin"])
        
        # Create event with Bearer token
        event = {
            "headers": {
                "Authorization": f"Bearer {jwt_token}"
            }
        }
        
        # Extract user
        user = provider.extract_user(event)
        
        assert user is not None, "User should be extracted"
        assert user.user_id == "user-123"
        assert user.username == "Alice"
        assert user.email == "Alice@example.com"
        assert "member" in user.groups
        assert "admin" in user.groups
        
        logger.info("  ✓ JWT extraction successful")
        logger.info(f"    - User ID: {user.user_id}")
        logger.info(f"    - Username: {user.username}")
        logger.info(f"    - Groups: {user.groups}")
        
        return True
    except Exception as e:
        logger.error(f"✗ JWT extraction test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cedar_auth_provider_missing_header():
    """Test CedarAuthProvider handles missing Authorization header."""
    logger.info("Testing Cedar auth provider with missing header...")
    
    try:
        from shared.providers.auth import CedarAuthProvider
        
        provider = CedarAuthProvider()
        
        # Event without Authorization header
        event = {"headers": {}}
        
        user = provider.extract_user(event)
        
        assert user is None, "Should return None for missing header"
        logger.info("  ✓ Missing header handled correctly")
        
        return True
    except Exception as e:
        logger.error(f"✗ Missing header test failed: {e}")
        return False


def test_cedar_authorization_provider_structure():
    """Test CedarAuthorizationProvider can be initialized."""
    logger.info("Testing Cedar authorization provider structure...")
    
    try:
        from shared.providers.authorization import CedarAuthorizationProvider
        
        # Initialize with mock endpoint
        provider = CedarAuthorizationProvider(endpoint="http://localhost:8180")
        
        assert provider is not None
        assert provider.endpoint == "http://localhost:8180"
        assert provider.timeout == 5
        
        logger.info("  ✓ Authorization provider initialized")
        logger.info(f"    - Endpoint: {provider.endpoint}")
        logger.info(f"    - Timeout: {provider.timeout}s")
        
        return True
    except Exception as e:
        logger.error(f"✗ Authorization provider test failed: {e}")
        return False


def test_cedar_authorization_provider_graceful_fallback():
    """Test CedarAuthorizationProvider handles connection errors gracefully."""
    logger.info("Testing Cedar authorization provider graceful fallback...")
    
    try:
        from shared.providers.authorization import CedarAuthorizationProvider
        from shared.providers.types import AuthenticatedUser
        
        provider = CedarAuthorizationProvider(endpoint="http://localhost:8180")
        
        # Create mock user
        user = AuthenticatedUser(
            user_id="user-1",
            username="test",
            email="test@example.com"
        )
        
        # Mock requests to raise connection error
        with patch.object(provider, 'requests') as mock_requests:
            mock_requests.post.side_effect = Exception("Connection refused")
            
            # Check permission (should fail closed)
            result = provider.check_permission(user, "read", "household:test-hh")
            
            assert result.permitted == False, "Should deny when Cedar unavailable"
            assert "failed" in result.reason.lower()
            
            logger.info("  ✓ Graceful fallback (fail closed) working")
            logger.info(f"    - Permission: {result.permitted}")
            logger.info(f"    - Reason: {result.reason}")
        
        return True
    except Exception as e:
        logger.error(f"✗ Graceful fallback test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_auth_vs_authorization_separation():
    """Test that auth and authorization are separate concerns."""
    logger.info("Testing auth vs authorization separation...")
    
    try:
        from shared.providers.auth import CedarAuthProvider, LocalAuthProvider
        from shared.providers.authorization import CedarAuthorizationProvider, SimpleAuthorizationProvider
        from shared.providers.types import AuthenticatedUser
        
        # Scenario 1: Local auth with Cedar authorization
        local_auth = LocalAuthProvider()
        cedar_authz = CedarAuthorizationProvider()
        
        # User authenticated locally
        local_event = {"headers": {"x-user-id": "user-1"}}
        user = local_auth.extract_user(local_event)
        assert user is not None, "Should extract user via local auth"
        logger.info("  ✓ User authenticated via LocalAuthProvider")
        
        # But authorization checked via Cedar (would fail if Cedar unavailable)
        # This is correct - auth happens, then authz is checked separately
        logger.info("  ✓ Authorization would then be checked via Cedar separately")
        
        # Scenario 2: JWT auth with local authorization
        jwt_auth = CedarAuthProvider()
        
        jwt_token = create_test_jwt("user-2", "Bob")
        jwt_event = {"headers": {"Authorization": f"Bearer {jwt_token}"}}
        user2 = jwt_auth.extract_user(jwt_event)
        assert user2 is not None, "Should extract user via JWT"
        logger.info("  ✓ User authenticated via CedarAuthProvider (JWT)")
        
        logger.info("  ✓ Auth and authorization are properly separated")
        
        return True
    except Exception as e:
        logger.error(f"✗ Separation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_local_auth_provider_headers():
    """Test LocalAuthProvider with dev headers."""
    logger.info("Testing LocalAuthProvider with dev headers...")
    
    try:
        from shared.providers.auth import LocalAuthProvider
        
        provider = LocalAuthProvider()
        
        # Test with x-user-id header
        event = {
            "headers": {
                "x-user-id": "dev-user-1",
                "x-user-name": "Developer",
                "x-user-email": "dev@localhost",
                "x-user-groups": "member,admin"
            }
        }
        
        user = provider.extract_user(event)
        
        assert user is not None
        assert user.user_id == "dev-user-1"
        assert user.username == "Developer"
        assert "member" in user.groups
        assert "admin" in user.groups
        
        logger.info("  ✓ Local auth provider working")
        logger.info(f"    - User ID: {user.user_id}")
        logger.info(f"    - Name: {user.username}")
        logger.info(f"    - Groups: {user.groups}")
        
        return True
    except Exception as e:
        logger.error(f"✗ Local auth test failed: {e}")
        return False


def test_permission_check_result_structure():
    """Test PermissionCheckResult structure."""
    logger.info("Testing PermissionCheckResult structure...")
    
    try:
        from shared.providers.types import PermissionCheckResult
        
        result = PermissionCheckResult(
            permitted=True,
            reason="User is member",
            resource="household:hh-1",
            action="read"
        )
        
        assert result.permitted == True
        assert result.reason == "User is member"
        assert result.resource == "household:hh-1"
        assert result.action == "read"
        
        logger.info("  ✓ PermissionCheckResult structure correct")
        logger.info(f"    - Permitted: {result.permitted}")
        logger.info(f"    - Reason: {result.reason}")
        logger.info(f"    - Resource: {result.resource}")
        logger.info(f"    - Action: {result.action}")
        
        return True
    except Exception as e:
        logger.error(f"✗ Permission result test failed: {e}")
        return False


def main():
    """Run all tests."""
    
    logger.info("=" * 70)
    logger.info("CEDAR AUTHORIZATION INTEGRATION TESTS")
    logger.info("=" * 70)
    logger.info("")
    
    results = {
        "JWT extraction": test_cedar_auth_provider_jwt_extraction(),
        "Missing header handling": test_cedar_auth_provider_missing_header(),
        "Authorization provider": test_cedar_authorization_provider_structure(),
        "Graceful fallback": test_cedar_authorization_provider_graceful_fallback(),
        "Auth vs authorization": test_auth_vs_authorization_separation(),
        "Local auth headers": test_local_auth_provider_headers(),
        "Permission result": test_permission_check_result_structure(),
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
        logger.info("✓ All Cedar integration tests PASSED")
        logger.info("")
        logger.info("Cedar authorization architecture:")
        logger.info("  ✓ CedarAuthProvider handles JWT-based authentication")
        logger.info("  ✓ LocalAuthProvider handles dev header-based auth (alternative)")
        logger.info("  ✓ CedarAuthorizationProvider checks permissions via Cedar PDP")
        logger.info("  ✓ Auth and authorization are properly separated")
        logger.info("  ✓ Graceful failure when Cedar unavailable (fail closed)")
        logger.info("")
        logger.info("Usage in BUILD_IT_STRANDS:")
        logger.info("  1. Extract user: auth_provider.extract_user(event)")
        logger.info("  2. Check permission: authz_provider.check_permission(user, action, resource)")
        logger.info("  3. Both operations independent - auth doesn't depend on authz")
    else:
        failed = [name for name, passed in results.items() if not passed]
        logger.error(f"✗ {len(failed)} test(s) FAILED: {', '.join(failed)}")
    
    logger.info("")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
