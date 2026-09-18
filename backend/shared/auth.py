"""
RoomieOps Authentication and Authorization Layer

- JWT extraction and validation from API Gateway Cognito authorizer
- Identity normalization
- Household membership verification
- Role-based authorization
- NEVER trust client-supplied userId as authoritative
"""

import logging
from typing import Dict, Optional, List
from dataclasses import dataclass

logger = logging.getLogger()
logger.setLevel(logging.INFO)


@dataclass
class AuthenticatedUser:
    """Normalized authenticated user identity."""
    user_id: str  # Cognito sub claim
    username: str
    email: Optional[str] = None
    groups: List[str] = None  # Cognito groups

    def __post_init__(self):
        if self.groups is None:
            self.groups = []


def get_authenticated_user(event: Dict) -> Optional[AuthenticatedUser]:
    """
    Extract and normalize authenticated user from API Gateway + Cognito authorizer.

    API Gateway with Cognito authorizer provides claims in:
    event['requestContext']['authorizer']['claims']

    Args:
        event: Lambda event from API Gateway

    Returns:
        AuthenticatedUser if valid, None if unauthenticated/invalid

    Raises:
        ValueError: If authentication is missing (should trigger 401)
    """
    try:
        # Cognito authorizer populates requestContext.authorizer.claims
        authorizer = event.get("requestContext", {}).get("authorizer")
        if not authorizer:
            raise ValueError("No authorizer in request context")

        claims = authorizer.get("claims")
        if not claims:
            raise ValueError("No claims in authorizer")

        # Extract essential claims
        user_id = claims.get("sub")  # Cognito subject (unique user ID)
        username = claims.get("cognito:username")
        email = claims.get("email")

        if not user_id or not username:
            raise ValueError("Missing required claims (sub, username)")

        # Extract groups if present (from Cognito group membership)
        groups = []
        if "cognito:groups" in claims:
            groups = claims.get("cognito:groups", "").split(",") if claims.get("cognito:groups") else []

        logger.info(f"Authenticated user: {username} (sub={user_id})")

        return AuthenticatedUser(
            user_id=user_id,
            username=username,
            email=email,
            groups=groups,
        )

    except (KeyError, ValueError, AttributeError) as e:
        logger.warning(f"Authentication extraction failed: {str(e)}")
        return None


def require_auth(event: Dict) -> AuthenticatedUser:
    """
    Require authentication, raising an exception if not present.

    Use this in handlers that must be authenticated.

    Args:
        event: Lambda event

    Returns:
        AuthenticatedUser

    Raises:
        ValueError: If not authenticated (caller should catch and return 401)
    """
    user = get_authenticated_user(event)
    if not user:
        raise ValueError("Unauthenticated request")
    return user


def is_admin(user: AuthenticatedUser) -> bool:
    """Check if user has admin group membership."""
    return "admin" in (user.groups or [])


def is_household_admin(
    user: AuthenticatedUser,
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
    user: AuthenticatedUser,
    household_id: str,
    members_list: List[Dict],  # [{user_id, role, ...}, ...]
) -> bool:
    """
    Verify that user is a member of the household.

    Args:
        user: Authenticated user
        household_id: Household to verify
        members_list: List of household members from DynamoDB

    Returns:
        True if user is in the household
    """
    for member in members_list:
        if member.get("user_id") == user.user_id and member.get("status") == "active":
            return True
    return False


def verify_write_permission(
    user: AuthenticatedUser,
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
    user: AuthenticatedUser,
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
