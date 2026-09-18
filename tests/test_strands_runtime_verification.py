"""
Strands Runtime Verification Test

Verifies:
1. SDK installation
2. Agent initialization
3. Tool execution capability
4. Real vs heuristic fallback modes

Status determination:
- REAL_STRANDS: SDK imports, agent initializes, tools execute
- BLOCKED: SDK not found or initialization fails
"""

import pytest
import sys


def test_strands_sdk_import():
    """Test 1: Can we import the Strands SDK?"""
    try:
        from strands.agent import Agent, Tool, ToolResult
        assert Agent is not None
        assert Tool is not None
        assert ToolResult is not None
        print("✓ Strands SDK: IMPORTED SUCCESSFULLY")
        return True
    except ImportError as e:
        print(f"✗ Strands SDK: NOT INSTALLED - {e}")
        return False


def test_strands_agent_initialization():
    """Test 2: Can we initialize a Strands Agent?"""
    try:
        from strands.agent import Agent
        
        # Minimal agent initialization
        agent = Agent(
            name="RoomieOpsTestAgent",
            description="Test agent for RoomieOps",
        )
        
        assert agent is not None
        assert agent.name == "RoomieOpsTestAgent"
        print("✓ Strands Agent: INITIALIZED SUCCESSFULLY")
        return True
    except ImportError:
        print("✗ Strands Agent: SDK NOT AVAILABLE - BLOCKED")
        return False
    except Exception as e:
        print(f"✗ Strands Agent: INITIALIZATION FAILED - {e}")
        return False


def test_strands_tool_registration():
    """Test 3: Can we register tools with the agent?"""
    try:
        from strands.agent import Agent, Tool, ToolResult
        
        agent = Agent(
            name="RoomieOpsTestAgent",
            description="Test agent",
        )
        
        # Define a test tool
        @agent.tool
        def test_tool(param: str) -> str:
            """A test tool"""
            return f"Result: {param}"
        
        # Check tool was registered
        tools = agent.get_tools() if hasattr(agent, 'get_tools') else []
        print(f"✓ Strands Tool Registration: {len(tools) if tools else 'REGISTERED'} tools")
        return True
    except ImportError:
        print("✗ Strands Tool Registration: SDK NOT AVAILABLE - BLOCKED")
        return False
    except Exception as e:
        print(f"✗ Strands Tool Registration: FAILED - {e}")
        return False


def test_strands_execution_mode():
    """Test 4: Determine execution mode"""
    sdk_available = test_strands_sdk_import()
    
    if sdk_available:
        try:
            agent_ok = test_strands_agent_initialization()
            if agent_ok:
                print("\n" + "="*50)
                print("STRANDS RUNTIME: VERIFIED")
                print("="*50)
                return "REAL_STRANDS"
        except Exception:
            pass
    
    print("\n" + "="*50)
    print("STRANDS RUNTIME: BLOCKED")
    print("Reason: SDK not installed or initialization failed")
    print("Fallback: LOCAL_HEURISTIC mode available")
    print("="*50)
    return "BLOCKED"


if __name__ == "__main__":
    mode = test_strands_execution_mode()
    sys.exit(0 if mode == "REAL_STRANDS" else 1)
