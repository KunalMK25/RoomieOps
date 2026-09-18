"""
Execution mode tracking for RoomieOps agent.

Distinguishes between:
- REAL_BEDROCK: Live Claude model via AWS Bedrock
- REAL_STRANDS: Local Strands Agent SDK
- LOCAL_HEURISTIC: Keyword-based fallback for testing
"""

from enum import Enum
from typing import Dict, Any

class ExecutionMode(Enum):
    """Execution mode for agent."""
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
    Determine which execution mode is available.
    
    Priority:
    1. Bedrock (if credentials available)
    2. Strands (if SDK installed)
    3. Heuristic (always available)
    """
    # Check Bedrock credentials
    try:
        import boto3
        from botocore.exceptions import NoCredentialsError
        
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
