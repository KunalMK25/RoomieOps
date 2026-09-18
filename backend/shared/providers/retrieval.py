"""Retrieval provider implementations."""

import logging
from typing import Any, Dict, List

from .base import RetrievalProvider

logger = logging.getLogger(__name__)


class DynamoDBRetrievalProvider(RetrievalProvider):
    """Retrieval provider using DynamoDB queries (SHIP_IT / P1)."""
    
    def __init__(self, storage=None):
        """Initialize with optional storage provider reference.
        
        Args:
            storage: StorageProvider for queries (optional, can use global)
        """
        self.storage = storage
        logger.info("DynamoDBRetrievalProvider initialized")
    
    def search(
        self,
        query: str,
        household_id: str,
        index: str = "household_data",
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Search using DynamoDB query (P0: simple prefix matching).
        
        P2: Will integrate OpenSearch for full-text search.
        """
        try:
            if not self.storage:
                logger.warning("No storage provider for retrieval")
                return []
            
            # Query recent items for household (simple retrieval)
            result = self.storage.query(
                pk=f"HOUSEHOLD#{household_id}",
                sk_prefix="EXPENSE#",
                limit=top_k
            )
            
            return result.items
        
        except Exception as e:
            logger.error(f"DynamoDB retrieval search failed: {e}")
            return []
    
    def index_document(
        self,
        document: Dict[str, Any],
        household_id: str,
        index: str = "household_data"
    ) -> None:
        """Index document (P0: stored via normal DynamoDB operations)."""
        # P0: Indexing happens as part of normal put_item
        # P2: Will integrate OpenSearch for advanced indexing
        logger.debug(f"Document indexed for household {household_id}")


class InMemoryRetrievalProvider(RetrievalProvider):
    """Retrieval provider using in-memory search (BUILD_IT / LOCAL_HEURISTIC)."""
    
    def __init__(self):
        """Initialize in-memory retrieval."""
        self.documents: Dict[str, List[Dict[str, Any]]] = {}
        logger.info("InMemoryRetrievalProvider initialized")
    
    def search(
        self,
        query: str,
        household_id: str,
        index: str = "household_data",
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Simple in-memory search (keyword matching)."""
        try:
            key = f"{household_id}:{index}"
            if key not in self.documents:
                return []
            
            # Simple keyword matching
            query_lower = query.lower()
            results = []
            
            for doc in self.documents[key]:
                # Check if query keywords match document content
                if any(
                    word in str(doc).lower()
                    for word in query_lower.split()
                ):
                    results.append(doc)
                
                if len(results) >= top_k:
                    break
            
            return results
        
        except Exception as e:
            logger.error(f"In-memory retrieval search failed: {e}")
            return []
    
    def index_document(
        self,
        document: Dict[str, Any],
        household_id: str,
        index: str = "household_data"
    ) -> None:
        """Index document in memory."""
        key = f"{household_id}:{index}"
        if key not in self.documents:
            self.documents[key] = []
        
        self.documents[key].append(document)
    
    def clear(self) -> None:
        """Clear all indexed documents (for testing)."""
        self.documents.clear()
