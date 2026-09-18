"""
Provider abstraction layer for RoomieOps.

Enables running the same business logic against different backends:
- SHIP_IT_BEDROCK: AWS Bedrock, DynamoDB, Cognito
- BUILD_IT_STRANDS: Ollama, LocalStack, Cedar
- LOCAL_HEURISTIC: Heuristic, In-memory, Simple auth
"""

from .base import (
    LLMProvider,
    StorageProvider,
    AuthProvider,
    AuthorizationProvider,
    RetrievalProvider,
    ProviderSet,
)

from .types import (
    ExecutionMode,
    StorageItem,
    QueryResult,
    AuthenticatedUser,
    IntentDetectionResult,
)

from .llm import (
    BedrockLLMProvider,
    OllamaLLMProvider,
    HeuristicLLMProvider,
)

from .storage import (
    DynamoDBProvider,
    LocalStackProvider,
    InMemoryProvider,
)

from .auth import (
    CognitoAuthProvider,
    CedarAuthProvider,
    LocalAuthProvider,
)

from .retrieval import (
    DynamoDBRetrievalProvider,
    InMemoryRetrievalProvider,
)

from .manager import ExecutionModeManager

__all__ = [
    # Base classes
    "LLMProvider",
    "StorageProvider",
    "AuthProvider",
    "AuthorizationProvider",
    "RetrievalProvider",
    "ProviderSet",
    # Types
    "ExecutionMode",
    "StorageItem",
    "QueryResult",
    "AuthenticatedUser",
    "IntentDetectionResult",
    # Implementations
    "BedrockLLMProvider",
    "OllamaLLMProvider",
    "HeuristicLLMProvider",
    "DynamoDBProvider",
    "LocalStackProvider",
    "InMemoryProvider",
    "CognitoAuthProvider",
    "CedarAuthProvider",
    "LocalAuthProvider",
    "DynamoDBRetrievalProvider",
    "InMemoryRetrievalProvider",
    # Manager
    "ExecutionModeManager",
]
