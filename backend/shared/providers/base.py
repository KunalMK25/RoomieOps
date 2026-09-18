"""Abstract base classes for all providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import logging

from .types import (
    ExecutionMode,
    StorageItem,
    QueryResult,
    AuthenticatedUser,
    IntentDetectionResult,
    PermissionCheckResult,
)

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base for LLM/AI providers."""
    
    @abstractmethod
    def detect_intent(
        self,
        user_message: str,
        household_context: Dict[str, Any]
    ) -> IntentDetectionResult:
        """Detect user intent from natural language message.
        
        Args:
            user_message: User's request in natural language
            household_context: Dict with household metadata, members, balances, etc.
            
        Returns:
            IntentDetectionResult with intent, confidence, entities
        """
        pass
    
    @abstractmethod
    def generate_explanation(
        self,
        action_performed: str,
        action_result: Dict[str, Any],
        user_message: str
    ) -> str:
        """Generate human-readable explanation of action result.
        
        Args:
            action_performed: What action was executed
            action_result: Result data from the action
            user_message: Original user request
            
        Returns:
            Explanation string (always grounded in actual result)
        """
        pass


class StorageProvider(ABC):
    """Abstract base for data storage providers."""
    
    @abstractmethod
    def get_item(self, pk: str, sk: str) -> Optional[Dict[str, Any]]:
        """Get single item by partition and sort key.
        
        Args:
            pk: Partition key
            sk: Sort key
            
        Returns:
            Item dict or None if not found
        """
        pass
    
    @abstractmethod
    def put_item(self, item: Dict[str, Any]) -> None:
        """Put/update item.
        
        Args:
            item: Item dict with 'pk', 'sk', and other attributes
        """
        pass
    
    @abstractmethod
    def query(
        self,
        pk: str,
        sk_prefix: Optional[str] = None,
        limit: int = 100
    ) -> QueryResult:
        """Query items by partition key (and optional sort key prefix).
        
        Args:
            pk: Partition key
            sk_prefix: Optional sort key prefix to filter
            limit: Max items to return
            
        Returns:
            QueryResult with items list
        """
        pass
    
    @abstractmethod
    def scan(
        self,
        filter_expr: Optional[str] = None,
        filter_values: Optional[Dict[str, Any]] = None,
        limit: int = 100
    ) -> QueryResult:
        """Scan all items (optionally filtered).
        
        Args:
            filter_expr: Optional filter expression
            filter_values: Values for filter expression
            limit: Max items to return
            
        Returns:
            QueryResult with items list
        """
        pass
    
    @abstractmethod
    def update_item(
        self,
        pk: str,
        sk: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update item attributes.
        
        Args:
            pk: Partition key
            sk: Sort key
            updates: Attributes to update
            
        Returns:
            Updated item
        """
        pass
    
    @abstractmethod
    def delete_item(self, pk: str, sk: str) -> None:
        """Delete item by key.
        
        Args:
            pk: Partition key
            sk: Sort key
        """
        pass
    
    @abstractmethod
    def batch_put(self, items: List[Dict[str, Any]]) -> None:
        """Batch put multiple items.
        
        Args:
            items: List of item dicts
        """
        pass


class AuthProvider(ABC):
    """Abstract base for authentication providers."""
    
    @abstractmethod
    def extract_user(self, event: Dict[str, Any]) -> Optional[AuthenticatedUser]:
        """Extract authenticated user from API event.
        
        Args:
            event: API Gateway event (or equivalent)
            
        Returns:
            AuthenticatedUser if valid, None if unauthenticated
        """
        pass


class AuthorizationProvider(ABC):
    """Abstract base for authorization/policy providers."""
    
    @abstractmethod
    def check_permission(
        self,
        user: AuthenticatedUser,
        action: str,
        resource: str
    ) -> PermissionCheckResult:
        """Check if user has permission for action on resource.
        
        Args:
            user: Authenticated user
            action: Action to perform (read, write, delete, etc.)
            resource: Resource identifier
            
        Returns:
            PermissionCheckResult with permit/deny decision
        """
        pass
    
    @abstractmethod
    def verify_household_membership(
        self,
        user: AuthenticatedUser,
        household_id: str
    ) -> bool:
        """Verify user is member of household.
        
        Args:
            user: Authenticated user
            household_id: Household to check
            
        Returns:
            True if member, False otherwise
        """
        pass


class RetrievalProvider(ABC):
    """Abstract base for retrieval/search providers."""
    
    @abstractmethod
    def search(
        self,
        query: str,
        household_id: str,
        index: str = "household_data",
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for documents matching query.
        
        Args:
            query: Search query
            household_id: Household to search in
            index: Index to search
            top_k: Number of top results to return
            
        Returns:
            List of matching documents
        """
        pass
    
    @abstractmethod
    def index_document(
        self,
        document: Dict[str, Any],
        household_id: str,
        index: str = "household_data"
    ) -> None:
        """Index a document for retrieval.
        
        Args:
            document: Document to index
            household_id: Household to associate with
            index: Index to add to
        """
        pass


@dataclass
class ProviderSet:
    """Complete set of providers for an execution mode."""
    llm: LLMProvider
    storage: StorageProvider
    auth: AuthProvider
    authorization: AuthorizationProvider
    retrieval: RetrievalProvider
