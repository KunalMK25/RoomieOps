"""
RoomieOps Authentication Layer

Abstracts user identity extraction and validation across execution modes:
- SHIP_IT: JWT extraction from API Gateway Cognito authorizer
- BUILD_IT: Local development identity
- LOCAL_HEURISTIC: Mock identity for testing

IMPORTANT: Cedar is NOT authentication. This layer only identifies the user.
Authorization (Cedar) happens separately after identity is established.

Refactored to use AuthProvider abstraction.
"""

import logging
from typing import Dict, Optional, List

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Authentication provider (injected at runtime)
_auth_provider = None


def set_auth_provider(provider):
    """Set the authentication provider."""
    global _auth_provider
    _auth_provider = provider
    logger.info(f"Auth layer provider set to: {type(provider).__name__}")


def get_auth_provider():
    """Get current authentication provider (initializes if needed)."""
    global _auth_provider
    if _auth_provider is None:
        # Lazy initialization: detect provider based on environment
        try:
            from .providers import ExecutionModeManager
            providers = ExecutionModeManager.get_providers()
            _auth_provider = providers.auth
            logger.info(f"Auth layer auto-initialized with: {type(_auth_provider).__name__}")
        except Exception as e:
            logger.error(f"Failed to auto-initialize auth provider: {e}")
            raise
    return _auth_provider


def get_authenticated_user(event: Dict) -> Optional['AuthenticatedUser']:
    """
    Extract and normalize authenticated user from API event.

    Delegates to the configured authentication provider (Cognito, Local, etc.).

    Args:
        event: API Gateway event (or equivalent)

    Returns:
        AuthenticatedUser if valid, None if unauthenticated/invalid

    Raises:
        ValueError: If authentication is missing (should trigger 401)
    """
    try:
        user = get_auth_provider().extract_user(event)
        if user:
            logger.info(f"Authenticated user: {user.username} (user_id={user.user_id})")
        return user
    except Exception as e:
        logger.warning(f"Authentication extraction failed: {str(e)}")
        return None


def require_auth(event: Dict) -> 'AuthenticatedUser':
    """
    Require authentication, raising an exception if not present.

    Use this in handlers that must be authenticated.

    Args:
        event: API event

    Returns:
        AuthenticatedUser

    Raises:
        ValueError: If not authenticated (caller should catch and return 401)
    """
    user = get_authenticated_user(event)
    if not user:
        raise ValueError("Unauthenticated request")
    return user


def is_admin(user: 'AuthenticatedUser') -> bool:
    """Check if user has admin group membership."""
    return "admin" in (user.groups or [])


def is_household_admin(
    user: 'AuthenticatedUser',
    household_id: str,
    members_map: Dict[str, Dict],  # {household_id: {user_id: member_record}}
) -> bool:
    """
    Check if user is an admin of a specific household.

    Args:
        user: Authenticated user
        household_id: Household to check
        members_map: Mapping of household members to their roles

    Returns:
        True if user is admin in that household
    """
    if household_id not in members_map:
        return False

    household_members = members_map[household_id]
    if user.user_id not in household_members:
        return False

    member_record = household_members[user.user_id]
    return member_record.get("role") == "admin"


def verify_household_membership(
    user: 'AuthenticatedUser',
    household_id: str,
    members_list: List[Dict],  # [{user_id, role, ...}, ...]
) -> bool:
    """
    Verify that user is a member of the household.

    Args:
        user: Authenticated user
        household_id: Household to verify
        members_list: List of household members from storage

    Returns:
        True if user is in the household
    """
    for member in members_list:
        if member.get("user_id") == user.user_id and member.get("status") == "active":
            return True
    return False


def verify_write_permission(
    user: 'AuthenticatedUser',
    household_id: str,
    members_list: List[Dict],
) -> bool:
    """
    Verify that user can write to a household.

    For P0, any active member can write (no fine-grained resource ownership yet).
    P2: Cedar will introduce more granular permissions.

    Args:
        user: Authenticated user
        household_id: Household to write to
        members_list: List of household members

    Returns:
        True if user has write permission
    """
    return verify_household_membership(user, household_id, members_list)


def verify_admin_permission(
    user: 'AuthenticatedUser',
    household_id: str,
    members_list: List[Dict],
) -> bool:
    """
    Verify that user has admin permission in a household.

    Args:
        user: Authenticated user
        household_id: Household to verify admin status
        members_list: List of household members

    Returns:
        True if user is admin
    """
    for member in members_list:
        if member.get("user_id") == user.user_id:
            return member.get("role") == "admin" and member.get("status") == "active"
    return False
