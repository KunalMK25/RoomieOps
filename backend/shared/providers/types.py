"""Data types used across providers."""

from enum import Enum
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


class ExecutionMode(Enum):
    """Execution mode for RoomieOps."""
    SHIP_IT_BEDROCK = "SHIP_IT_BEDROCK"
    BUILD_IT_STRANDS = "BUILD_IT_STRANDS"
    LOCAL_HEURISTIC = "LOCAL_HEURISTIC"


@dataclass
class StorageItem:
    """Generic storage item (works with DynamoDB, LocalStack, etc.)"""
    pk: str  # Partition key
    sk: str  # Sort key
    data: Dict[str, Any]  # All attributes
    ttl: Optional[int] = None  # TTL in seconds (DynamoDB)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format."""
        item = {"pk": self.pk, "sk": self.sk, **self.data}
        if self.ttl:
            item["ttl"] = self.ttl
        return item


@dataclass
class QueryResult:
    """Result of a query operation."""
    items: List[Dict[str, Any]]
    count: int
    last_evaluated_key: Optional[Dict[str, str]] = None


@dataclass
class AuthenticatedUser:
    """Authenticated user information."""
    user_id: str
    username: str
    email: Optional[str] = None
    groups: Optional[List[str]] = None
    attributes: Optional[Dict[str, Any]] = None  # Provider-specific attributes
    
    def __post_init__(self):
        if self.groups is None:
            self.groups = []
        if self.attributes is None:
            self.attributes = {}


@dataclass
class IntentDetectionResult:
    """Result of LLM intent detection."""
    intent: str  # view_balance, create_expense, etc.
    confidence: float  # 0.0-1.0
    entities: Dict[str, Any]  # Extracted entities
    reasoning: str  # Explanation for the intent
    error: Optional[str] = None  # Error message if failed


@dataclass
class PermissionCheckResult:
    """Result of permission check."""
    permitted: bool
    reason: str
    resource: Optional[str] = None
    action: Optional[str] = None
