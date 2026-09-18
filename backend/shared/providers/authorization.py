"""Authorization provider implementations."""

import logging
from typing import Any, Dict, Optional

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
    """Authorization provider using Cedar (BUILD_IT)."""
    
    def __init__(self, endpoint: str = "http://localhost:8180"):
        """Initialize Cedar authorization provider.
        
        Args:
            endpoint: Cedar PDP endpoint (default: localhost:8180)
        """
        try:
            import requests
            self.requests = requests
            self.endpoint = endpoint
            self.timeout = 5
            
            logger.info(f"CedarAuthorizationProvider initialized with endpoint: {endpoint}")
        except ImportError:
            raise ImportError("requests library required for Cedar provider")
    
    def check_permission(
        self,
        user: AuthenticatedUser,
        action: str,
        resource: str
    ) -> PermissionCheckResult:
        """Check permission via Cedar PDP."""
        try:
            response = self.requests.post(
                f"{self.endpoint}/is-authorized",
                json={
                    "principal": {
                        "type": "User",
                        "id": user.user_id
                    },
                    "action": {
                        "type": "Action",
                        "id": action
                    },
                    "resource": {
                        "type": "Resource",
                        "id": resource
                    },
                    "context": {}
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                permitted = result.get("allowed", False)
                reason = result.get("reason", "")
                
                return PermissionCheckResult(
                    permitted=permitted,
                    reason=reason or ("Permitted by Cedar" if permitted else "Denied by Cedar"),
                    resource=resource,
                    action=action
                )
            else:
                logger.error(f"Cedar returned error: {response.status_code}")
                return PermissionCheckResult(
                    permitted=False,
                    reason=f"Cedar error: {response.status_code}",
                    resource=resource,
                    action=action
                )
        
        except Exception as e:
            logger.error(f"Failed to check permission via Cedar: {e}")
            # Fail closed (deny by default)
            return PermissionCheckResult(
                permitted=False,
                reason=f"Authorization check failed: {e}",
                resource=resource,
                action=action
            )
    
    def verify_household_membership(
        self,
        user: AuthenticatedUser,
        household_id: str
    ) -> bool:
        """Verify household membership via Cedar."""
        result = self.check_permission(
            user,
            "read",
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
