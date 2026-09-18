"""
Strands Runtime Verification

Tests whether the actual Strands Agents SDK is available and functional.
Distinguishes from heuristic fallback.
"""

import sys
import os

print("=== STRANDS RUNTIME VERIFICATION ===\n")

# Check if Strands SDK is installed
try:
    import strands
    print("✓ Strands package found")
    print(f"  Version: {strands.__version__ if hasattr(strands, '__version__') else 'unknown'}")
except ImportError as e:
    print(f"✗ Strands package NOT found: {e}")
    print("  → STRANDS RUNTIME = BLOCKED")
    sys.exit(1)

# Check specific Strands Agent class
try:
    from strands.agent import Agent, Tool
    print("✓ Strands Agent classes importable")
except ImportError as e:
    print(f"✗ Cannot import Agent/Tool: {e}")
    print("  → STRANDS RUNTIME = BLOCKED")
    sys.exit(1)

# Attempt to instantiate an Agent with tools
try:
    # Create a simple test tool
    test_tool = Tool(
        name="test_tool",
        description="Test tool for verification",
        input_schema={
            "type": "object",
            "properties": {
                "param1": {"type": "string"}
            },
            "required": ["param1"]
        }
    )
    
    print("✓ Tool schema constructed")
    
    # Attempt Agent initialization
    agent = Agent(
        tools=[test_tool],
        system_prompt="You are a test agent."
    )
    
    print("✓ Agent initialized with tool")
    print(f"  Tools available: {len(agent.tools) if hasattr(agent, 'tools') else 'unknown'}")
    
except Exception as e:
    print(f"✗ Agent initialization failed: {e}")
    print("  → STRANDS RUNTIME = BLOCKED")
    sys.exit(1)

# Attempt tool selection/execution simulation
try:
    # This is a basic structural test — not a full reasoning loop
    # (Full reasoning requires a working LLM)
    
    if hasattr(agent, 'tools'):
        print(f"✓ Agent has tools attribute: {len(agent.tools)} tools registered")
    
    if hasattr(agent, 'system_prompt'):
        print(f"✓ Agent has system_prompt")
    
    print("\n✓ STRANDS RUNTIME = VERIFIED (SDK operational)")
    
except Exception as e:
    print(f"✗ Tool execution test failed: {e}")
    print("  → STRANDS RUNTIME = PARTIALLY BLOCKED")
    sys.exit(1)

print("\nCONCLUSION: Strands SDK is installed and Agent initialization works.")
print("Note: Full reasoning loop requires LLM access (Bedrock or OpenAI).")
