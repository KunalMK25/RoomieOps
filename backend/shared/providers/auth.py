"""Authentication provider implementations for different backends."""

import logging
import os
from typing import Any, Dict, Optional

from .base import AuthProvider
from .types import AuthenticatedUser

logger = logging.getLogger(__name__)


class CognitoAuthProvider(AuthProvider):
    """Authentication provider using AWS Cognito (SHIP_IT)."""
    
    def extract_user(self, event: Dict[str, Any]) -> Optional[AuthenticatedUser]:
        """Extract authenticated user from Cognito authorizer claims."""
        try:
            # API Gateway with Cognito authorizer populates requestContext.authorizer.claims
            authorizer = event.get("requestContext", {}).get("authorizer")
            if not authorizer:
                logger.warning("No authorizer in request context")
                return None
            
            claims = authorizer.get("claims")
            if not claims:
                logger.warning("No claims in authorizer")
                return None
            
            # Extract essential claims
            user_id = claims.get("sub")  # Cognito subject (unique user ID)
            username = claims.get("cognito:username")
            email = claims.get("email")
            
            if not user_id or not username:
                logger.warning("Missing required claims (sub, username)")
                return None
            
            # Extract groups if present
            groups = []
            if "cognito:groups" in claims:
                group_str = claims.get("cognito:groups", "")
                groups = group_str.split(",") if group_str else []
            
            logger.info(f"Authenticated user: {username} (sub={user_id})")
            
            return AuthenticatedUser(
                user_id=user_id,
                username=username,
                email=email,
                groups=groups,
                attributes=claims
            )
        
        except Exception as e:
            logger.error(f"Failed to extract Cognito user: {e}")
            return None


class CedarAuthProvider(AuthProvider):
    """Authentication provider using Cedar (BUILD_IT)."""
    
    def __init__(self, endpoint: str = "http://localhost:8180"):
        """Initialize Cedar auth provider.
        
        Args:
            endpoint: Cedar PDP endpoint (default: localhost:8180)
        """
        try:
            import requests
            self.requests = requests
            self.endpoint = endpoint
            self.timeout = 10
            
            logger.info(f"CedarAuthProvider initialized with endpoint: {endpoint}")
        except ImportError:
            raise ImportError("requests library required for Cedar provider")
    
    def extract_user(self, event: Dict[str, Any]) -> Optional[AuthenticatedUser]:
        """Extract authenticated user from JWT token in Authorization header."""
        try:
            # Get Authorization header
            auth_header = event.get("headers", {}).get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                logger.warning("Missing or invalid Authorization header")
                return None
            
            token = auth_header[7:]  # Remove "Bearer " prefix
            
            # Decode JWT (in production, validate signature via Cedar or external provider)
            # For now, extract basic claims from JWT payload
            import json
            import base64
            
            parts = token.split(".")
            if len(parts) != 3:
                logger.warning("Invalid JWT format")
                return None
            
            # Decode payload (add padding if needed)
            payload_str = parts[1]
            padding = 4 - len(payload_str) % 4
            if padding != 4:
                payload_str += "=" * padding
            
            payload = json.loads(base64.urlsafe_b64decode(payload_str))
            
            user_id = payload.get("sub")
            username = payload.get("name", "unknown")
            email = payload.get("email")
            groups = payload.get("groups", [])
            
            if not user_id:
                logger.warning("No 'sub' claim in JWT")
                return None
            
            logger.info(f"Authenticated user via Cedar: {username} (sub={user_id})")
            
            return AuthenticatedUser(
                user_id=user_id,
                username=username,
                email=email,
                groups=groups,
                attributes=payload
            )
        
        except Exception as e:
            logger.error(f"Failed to extract Cedar user: {e}")
            return None


class LocalAuthProvider(AuthProvider):
    """Authentication provider using simple headers (LOCAL_HEURISTIC / dev)."""
    
    def extract_user(self, event: Dict[str, Any]) -> Optional[AuthenticatedUser]:
        """Extract user from simple dev headers."""
        try:
            headers = event.get("headers", {})
            
            # Look for x-user-id header
            user_id = headers.get("x-user-id") or headers.get("X-User-Id")
            if not user_id:
                logger.warning("Missing x-user-id header")
                return None
            
            # Optional: x-user-name and x-user-groups
            username = headers.get("x-user-name", "dev-user")
            email = headers.get("x-user-email", f"{user_id}@local.dev")
            groups_str = headers.get("x-user-groups", "")
            groups = groups_str.split(",") if groups_str else ["member"]
            
            logger.info(f"Authenticated dev user: {username} (id={user_id})")
            
            return AuthenticatedUser(
                user_id=user_id,
                username=username,
                email=email,
                groups=groups
            )
        
        except Exception as e:
            logger.error(f"Failed to extract local user: {e}")
            return None
