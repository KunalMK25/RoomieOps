"""ExecutionModeManager - Orchestrates provider selection based on execution mode."""

import os
import logging
from typing import Optional

from .types import ExecutionMode
from .base import ProviderSet, LLMProvider, StorageProvider, AuthProvider, AuthorizationProvider, RetrievalProvider

logger = logging.getLogger(__name__)


class ExecutionModeManager:
    """
    Determines execution mode and provides appropriate provider set.
    
    Priority for mode determination:
    1. Explicit ENV: EXECUTION_MODE
    2. Auto-detect: Bedrock > Strands > Heuristic
    
    Each mode uses specific provider implementations.
    """
    
    _current_mode: Optional[ExecutionMode] = None
    _providers: Optional[ProviderSet] = None
    
    @staticmethod
    def determine_mode() -> ExecutionMode:
        """Determine execution mode.
        
        Priority:
        1. ENV variable EXECUTION_MODE
        2. Auto-detect (check if Bedrock creds available, then Strands SDK, then heuristic)
        
        Returns:
            ExecutionMode
        """
        # Check explicit ENV variable first
        env_mode = os.environ.get("EXECUTION_MODE")
        if env_mode:
            try:
                return ExecutionMode(env_mode)
            except ValueError:
                logger.warning(f"Invalid EXECUTION_MODE: {env_mode}. Auto-detecting...")
        
        # Auto-detect: Bedrock > Strands > Heuristic
        if ExecutionModeManager._can_reach_bedrock():
            logger.info("Auto-detect: Bedrock credentials available")
            return ExecutionMode.SHIP_IT_BEDROCK
        
        if ExecutionModeManager._can_reach_strands():
            logger.info("Auto-detect: Strands SDK available")
            return ExecutionMode.BUILD_IT_STRANDS
        
        logger.info("Auto-detect: Falling back to heuristic")
        return ExecutionMode.LOCAL_HEURISTIC
    
    @staticmethod
    def _can_reach_bedrock() -> bool:
        """Check if AWS Bedrock is accessible."""
        try:
            import boto3
            from botocore.exceptions import NoCredentialsError
            
            sts = boto3.client("sts", region_name="us-east-1")
            sts.get_caller_identity()
            return True
        except (NoCredentialsError, Exception):
            return False
    
    @staticmethod
    def _can_reach_strands() -> bool:
        """Check if Strands SDK is installed."""
        try:
            from strands import Agent
            return True
        except ImportError:
            return False
    
    @staticmethod
    def get_providers(mode: Optional[ExecutionMode] = None) -> ProviderSet:
        """Get provider set for execution mode.
        
        Args:
            mode: ExecutionMode. If None, uses determined/cached mode.
            
        Returns:
            ProviderSet with all providers configured for the mode
        """
        if mode is None:
            mode = ExecutionModeManager.determine_mode()
        
        ExecutionModeManager._current_mode = mode
        
        if mode == ExecutionMode.SHIP_IT_BEDROCK:
            return ExecutionModeManager._get_ship_it_providers()
        elif mode == ExecutionMode.BUILD_IT_STRANDS:
            return ExecutionModeManager._get_build_it_providers()
        else:
            return ExecutionModeManager._get_heuristic_providers()
    
    @staticmethod
    def _get_ship_it_providers() -> ProviderSet:
        """Return provider set for SHIP_IT_BEDROCK mode."""
        from .llm import BedrockLLMProvider
        from .storage import DynamoDBProvider
        from .auth import CognitoAuthProvider
        from .authorization import SimpleAuthorizationProvider
        from .retrieval import DynamoDBRetrievalProvider
        
        logger.info("Initializing SHIP_IT_BEDROCK providers")
        
        storage = DynamoDBProvider()
        return ProviderSet(
            llm=BedrockLLMProvider(),
            storage=storage,
            auth=CognitoAuthProvider(),
            authorization=SimpleAuthorizationProvider(storage=storage),
            retrieval=DynamoDBRetrievalProvider(storage=storage),
        )
    
    @staticmethod
    def _get_build_it_providers() -> ProviderSet:
        """Return provider set for BUILD_IT_STRANDS mode."""
        from .llm import OllamaLLMProvider
        from .storage import LocalStackProvider
        from .auth import CedarAuthProvider
        from .authorization import CedarAuthorizationProvider
        from .retrieval import InMemoryRetrievalProvider
        
        logger.info("Initializing BUILD_IT_STRANDS providers")
        
        llm_endpoint = os.environ.get("LLM_ENDPOINT", "http://localhost:11434")
        storage_endpoint = os.environ.get("DYNAMODB_ENDPOINT", "http://localhost:4566")
        cedar_endpoint = os.environ.get("CEDAR_ENDPOINT", "http://localhost:8180")
        
        storage = LocalStackProvider(endpoint=storage_endpoint)
        
        return ProviderSet(
            llm=OllamaLLMProvider(endpoint=llm_endpoint),
            storage=storage,
            auth=CedarAuthProvider(endpoint=cedar_endpoint),
            authorization=CedarAuthorizationProvider(storage=storage),
            retrieval=InMemoryRetrievalProvider(),
        )
    
    @staticmethod
    def _get_heuristic_providers() -> ProviderSet:
        """Return provider set for LOCAL_HEURISTIC mode."""
        from .llm import HeuristicLLMProvider
        from .storage import InMemoryProvider
        from .auth import LocalAuthProvider
        from .authorization import LocalAuthorizationProvider
        from .retrieval import InMemoryRetrievalProvider
        
        logger.info("Initializing LOCAL_HEURISTIC providers")
        
        return ProviderSet(
            llm=HeuristicLLMProvider(),
            storage=InMemoryProvider(),
            auth=LocalAuthProvider(),
            authorization=LocalAuthorizationProvider(),
            retrieval=InMemoryRetrievalProvider(),
        )
    
    @staticmethod
    def current_mode() -> Optional[ExecutionMode]:
        """Get currently active execution mode."""
        return ExecutionModeManager._current_mode
    
    @staticmethod
    def init(mode: Optional[ExecutionMode] = None) -> ProviderSet:
        """Initialize providers and cache them.
        
        Args:
            mode: Optional explicit mode. If None, auto-detects.
            
        Returns:
            ProviderSet ready for use
        """
        providers = ExecutionModeManager.get_providers(mode)
        ExecutionModeManager._providers = providers
        logger.info(f"Providers initialized for mode: {ExecutionModeManager._current_mode}")
        return providers
    
    @staticmethod
    def get_cached_providers() -> Optional[ProviderSet]:
        """Get cached provider set (must call init() first)."""
        return ExecutionModeManager._providers
