"""Authorization provider implementations."""

import logging
from typing import Any, Dict, List, Optional

from .base import AuthorizationProvider, StorageProvider
from .types import AuthenticatedUser, PermissionCheckResult

logger = logging.getLogger(__name__)


class SimpleAuthorizationProvider(AuthorizationProvider):
    """Simple authorization provider for SHIP_IT (DynamoDB-based membership)."""
    
    def __init__(self, storage: StorageProvider):
        """Initialize with storage provider for membership lookups.
        
        Args:
            storage: StorageProvider for accessing household members
        """
        self.storage = storage
    
    def check_permission(
        self,
        user: AuthenticatedUser,
        action: str,
        resource: str
    ) -> PermissionCheckResult:
        """Check permission (simplified: member can read/write own household)."""
        # For P0: Any active member can perform any action in the household
        # P2: Cedar will introduce fine-grained permissions
        
        if not user:
            return PermissionCheckResult(
                permitted=False,
                reason="User not authenticated",
                resource=resource,
                action=action
            )
        
        # Verify user is member of household (resource format: "household:{household_id}")
        if resource.startswith("household:"):
            household_id = resource.split(":", 1)[1]
            if self.verify_household_membership(user, household_id):
                return PermissionCheckResult(
                    permitted=True,
                    reason="Member of household",
                    resource=resource,
                    action=action
                )
            else:
                return PermissionCheckResult(
                    permitted=False,
                    reason="Not a member of this household",
                    resource=resource,
                    action=action
                )
        
        # Default: deny
        return PermissionCheckResult(
            permitted=False,
            reason="Unknown resource type",
            resource=resource,
            action=action
        )
    
    def verify_household_membership(
        self,
        user: AuthenticatedUser,
        household_id: str
    ) -> bool:
        """Verify user is active member of household."""
        try:
            # Query household members
            result = self.storage.query(
                pk=f"HOUSEHOLD#{household_id}",
                sk_prefix="MEMBER#",
                limit=100
            )
            
            for item in result.items:
                if item.get("user_id") == user.user_id and item.get("status") == "active":
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Failed to verify household membership: {e}")
            return False


class CedarAuthorizationProvider(AuthorizationProvider):
    """Authorization provider using real Cedar Policy CLI (BUILD_IT).
    
    Invokes the official Cedar authorization engine via subprocess.
    No Python authorization logic — Cedar is the source of truth.
    
    Model:
    - Principal: authenticated user (User::user_id)
    - Action: operation (read_household, create_expense, etc.)
    - Resource: target (Household::household_id)
    - Entities: household members from DynamoDB
    """
    
    def __init__(self, storage: StorageProvider = None):
        """Initialize Cedar authorization provider.
        
        Args:
            storage: StorageProvider for retrieving household membership data
            
        Raises:
            CedarCLIError if Cedar CLI not found or misconfigured
        """
        from .cedar_cli import CedarCLIAdapter, CedarCLIError
        
        self.storage = storage
        
        try:
            self.cedar = CedarCLIAdapter()
            logger.info("CedarAuthorizationProvider initialized (real Cedar CLI)")
            
            # Validate policy on startup
            if not self.cedar.validate_policy():
                logger.warning("Cedar policy validation returned false; continuing anyway")
        
        except CedarCLIError as e:
            logger.error(f"Failed to initialize Cedar: {e}")
            raise
    
    def check_permission(
        self,
        user: AuthenticatedUser,
        action: str,
        resource: str
    ) -> PermissionCheckResult:
        """Check permission using real Cedar Policy CLI.
        
        Args:
            user: Authenticated user
            action: Action name (read_household, create_expense, etc.)
            resource: Resource identifier (household:household_id format)
            
        Returns:
            PermissionCheckResult with Cedar's authorization decision
        """
        if not user:
            return PermissionCheckResult(
                permitted=False,
                reason="Cedar: User not authenticated",
                resource=resource,
                action=action
            )
        
        try:
            from .cedar_cli import CedarCLIError
            
            # Parse resource: "household:household_id" → Household::household_id
            if ":" not in resource:
                logger.error(f"Cedar: Invalid resource format: {resource}")
                return PermissionCheckResult(
                    permitted=False,
                    reason="Cedar: Invalid resource format",
                    resource=resource,
                    action=action
                )
            
            resource_type, resource_id = resource.split(":", 1)
            
            # Only household resources for now
            if resource_type != "household":
                logger.error(f"Cedar: Unsupported resource type: {resource_type}")
                return PermissionCheckResult(
                    permitted=False,
                    reason=f"Cedar: Unsupported resource type: {resource_type}",
                    resource=resource,
                    action=action
                )
            
            # Gather household membership state (application responsibility)
            # But Cedar makes the authorization decision (Cedar responsibility)
            is_member = self._is_household_member(user.user_id, resource_id)
            
            # Construct Cedar UIDs with proper escaping for JSON serialization
            principal_uid = f"User::\"{user.user_id}\""
            action_uid = f"Action::\"{action}\""
            resource_uid = f"Household::\"{resource_id}\""
            
            # Build Cedar entities with membership information for Cedar to evaluate
            entities = self._build_cedar_entities(user.user_id, resource_id, is_member)
            
            # Invoke REAL Cedar CLI — Cedar is the sole decision-maker
            # Cedar evaluates membership facts + policy to return ALLOW/DENY
            allowed = self.cedar.authorize(
                principal=principal_uid,
                action=action_uid,
                resource=resource_uid,
                entities=entities
            )
            
            reason = "Cedar: ALLOW" if allowed else "Cedar: DENY"
            logger.info(f"{reason}: {user.user_id} {action} {resource}")
            
            return PermissionCheckResult(
                permitted=allowed,
                reason=reason,
                resource=resource,
                action=action
            )
        
        except Exception as e:
            logger.error(f"Cedar authorization check failed: {e}")
            # Fail closed: deny on error
            return PermissionCheckResult(
                permitted=False,
                reason=f"Cedar: Authorization error: {e}",
                resource=resource,
                action=action
            )
    
    def _is_household_member(self, user_id: str, household_id: str) -> bool:
        """Check if user is an active member of the household.
        
        Uses storage provider to query household membership.
        """
        if not self.storage:
            logger.warning("Cedar: No storage provider; cannot verify membership")
            return False
        
        try:
            result = self.storage.query(
                pk=f"HOUSEHOLD#{household_id}",
                sk_prefix="MEMBER#",
                limit=100
            )
            
            for item in result.items:
                if item.get("user_id") == user_id and item.get("status") == "active":
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Cedar: Failed to verify household membership: {e}")
            return False
    
    def _build_cedar_entities(self, user_id: str, household_id: str, is_member: bool) -> List[Dict[str, Any]]:
        """Build Cedar entity array for authorization check.
        
        Membership is expressed as a parent relationship:
        - If user IS a member: User's parent is Household (principal in resource)
        - If user is NOT a member: User has no Household parent
        
        Cedar policy evaluates: "principal in resource" 
        This checks if the principal (User) is a descendant of the resource (Household).
        In Cedar, A in B means "A has B as a parent/ancestor".
        
        Args:
            user_id: Current user ID
            household_id: Household ID
            is_member: True if user is an active member of household
            
        Returns:
            List of Cedar entities in array format
        """
        entities = []
        
        # User entity with Household as parent ONLY if they're a member
        user_parents = []
        if is_member:
            # User is a member: Household is the user's parent
            # This makes "principal in resource" (User in Household) evaluate to true
            user_parents.append({"type": "Household", "id": household_id})
        
        entities.append({
            "uid": {"type": "User", "id": user_id},
            "attrs": {},
            "parents": user_parents  # Empty if not a member, [Household] if member
        })
        
        # Household entity (no parents needed)
        entities.append({
            "uid": {"type": "Household", "id": household_id},
            "attrs": {},
            "parents": []
        })
        
        return entities
    
    def verify_household_membership(
        self,
        user: AuthenticatedUser,
        household_id: str
    ) -> bool:
        """Verify household membership via Cedar authorization."""
        result = self.check_permission(
            user,
            "read_household",
            f"household:{household_id}"
        )
        return result.permitted


class LocalAuthorizationProvider(AuthorizationProvider):
    """Simple authorization for LOCAL_HEURISTIC (allow all for dev)."""
    
    def check_permission(
        self,
        user: AuthenticatedUser,
        action: str,
        resource: str
    ) -> PermissionCheckResult:
        """Allow all permissions for development."""
        if user:
            return PermissionCheckResult(
                permitted=True,
                reason="Development mode: all permissions allowed",
                resource=resource,
                action=action
            )
        else:
            return PermissionCheckResult(
                permitted=False,
                reason="User not authenticated",
                resource=resource,
                action=action
            )
    
    def verify_household_membership(
        self,
        user: AuthenticatedUser,
        household_id: str
    ) -> bool:
        """Allow all for development."""
        return bool(user)
