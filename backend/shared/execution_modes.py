"""
Execution mode tracking for RoomieOps.

DEPRECATED: This module is maintained for backward compatibility.
New code should use backend/shared/providers/manager.py ExecutionModeManager.

The provider layer defines execution modes as:
- BUILD_IT_STRANDS (Strands + Ollama + LocalStack + Cedar)
- SHIP_IT_BEDROCK (Bedrock + DynamoDB + Cognito)  
- LOCAL_HEURISTIC (Heuristic + InMemory + Local auth)

This module will be removed in a future refactor.
"""

import logging
from enum import Enum
from typing import Dict, Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)

logger.warning("execution_modes.py is DEPRECATED. Use ExecutionModeManager from providers.manager")


class ExecutionMode(Enum):
    """Execution mode for agent (DEPRECATED - use providers.types.ExecutionMode)."""
    REAL_BEDROCK = "REAL_BEDROCK"
    REAL_STRANDS = "REAL_STRANDS"
    LOCAL_HEURISTIC = "LOCAL_HEURISTIC"


def wrap_response(
    base_response: Dict[str, Any],
    execution_mode: ExecutionMode,
) -> Dict[str, Any]:
    """
    Wrap a base response with execution mode information.
    
    Ensures the frontend and audit trail know which execution path was used.
    """
    return {
        **base_response,
        "execution_mode": execution_mode.value,
        "_mode_note": f"This response was generated via {execution_mode.value}",
    }


def determine_execution_mode() -> ExecutionMode:
    """
    DEPRECATED: Use ExecutionModeManager.determine_mode() instead.
    
    This function is kept for backward compatibility.
    """
    logger.warning("determine_execution_mode() is deprecated. Use ExecutionModeManager.determine_mode()")
    
    # Try to import and use the new manager
    try:
        from .providers.manager import ExecutionModeManager
        from .providers.types import ExecutionMode as NewMode
        
        new_mode = ExecutionModeManager.determine_mode()
        
        # Map new modes to old enum values
        if new_mode == NewMode.SHIP_IT_BEDROCK:
            return ExecutionMode.REAL_BEDROCK
        elif new_mode == NewMode.BUILD_IT_STRANDS:
            return ExecutionMode.REAL_STRANDS
        else:
            return ExecutionMode.LOCAL_HEURISTIC
    except:
        pass
    
    # Fallback: check Bedrock credentials
    try:
        import boto3
        sts = boto3.client('sts', region_name='us-east-1')
        sts.get_caller_identity()
        return ExecutionMode.REAL_BEDROCK
    except:
        pass
    
    # Check Strands SDK
    try:
        from strands.agent import Agent
        return ExecutionMode.REAL_STRANDS
    except:
        pass
    
    # Fall back to heuristic
    return ExecutionMode.LOCAL_HEURISTIC
