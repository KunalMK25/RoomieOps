"""
RoomieOps Agent Tool Registry

Defines all tools available to the AI agent.
Each tool:
- Has a deterministic, server-side implementation
- Is authorized based on household membership
- Returns structured data
- Never directly mutates state (write tools invoke Step Functions)

Tool categories:
- HOUSEHOLD: metadata, policy, members
- EXPENSES: create, calculate, balance
- CHORES: rotation, completion, status
- MAINTENANCE: report issues
- SHOPPING: add items, check inventory
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class ToolCategory(Enum):
    """Tool categories."""
    HOUSEHOLD = "household"
    EXPENSES = "expenses"
    CHORES = "chores"
    MAINTENANCE = "maintenance"
    SHOPPING = "shopping"


class ToolType(Enum):
    """Tool execution type."""
    READ = "read"  # Query only, no side effects
    WRITE = "write"  # Consequential action, goes through Step Functions
    CONFIRM = "confirm"  # Requires user confirmation


@dataclass
class ToolSchema:
    """Tool definition and schema."""
    name: str  # "get_balance", "create_expense", etc.
    category: ToolCategory
    description: str
    input_schema: Dict[str, Any]  # JSON Schema for inputs
    output_schema: Dict[str, Any]  # JSON Schema for outputs
    tool_type: ToolType
    requires_confirmation: bool
    handler: Optional[Callable] = None  # Function to execute the tool


class AgentToolRegistry:
    """Registry of all available agent tools."""

    # Tool definitions (READ tools)
    TOOL_GET_HOUSEHOLD_STATE = ToolSchema(
        name="get_household_state",
        category=ToolCategory.HOUSEHOLD,
        description="Get current household metadata and members",
        input_schema={
            "type": "object",
            "properties": {"household_id": {"type": "string"}},
            "required": ["household_id"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "household_id": {"type": "string"},
                "name": {"type": "string"},
                "members": {"type": "array"},
                "policy": {"type": "object"},
            },
        },
        tool_type=ToolType.READ,
        requires_confirmation=False,
    )

    TOOL_GET_BALANCES = ToolSchema(
        name="get_balances",
        category=ToolCategory.EXPENSES,
        description="Get current balance for all household members (who owes whom)",
        input_schema={
            "type": "object",
            "properties": {"household_id": {"type": "string"}},
            "required": ["household_id"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "balances": {
                    "type": "object",
                    "additionalProperties": {"type": "integer"},
                },
                "explanation": {"type": "string"},
            },
        },
        tool_type=ToolType.READ,
        requires_confirmation=False,
    )

    TOOL_GET_MY_BALANCE = ToolSchema(
        name="get_my_balance",
        category=ToolCategory.EXPENSES,
        description="Get your personal balance (how much you owe/are owed)",
        input_schema={
            "type": "object",
            "properties": {
                "household_id": {"type": "string"},
                "user_id": {"type": "string"},
            },
            "required": ["household_id", "user_id"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "balance_paise": {"type": "integer"},
                "explanation": {"type": "string"},
            },
        },
        tool_type=ToolType.READ,
        requires_confirmation=False,
    )

    TOOL_GET_CHORE_ROTATION = ToolSchema(
        name="get_chore_rotation",
        category=ToolCategory.CHORES,
        description="Get list of all chores and current assignee",
        input_schema={
            "type": "object",
            "properties": {"household_id": {"type": "string"}},
            "required": ["household_id"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "chores": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "chore_id": {"type": "string"},
                            "name": {"type": "string"},
                            "assigned_to": {"type": "string"},
                            "rotation_order": {"type": "array"},
                        },
                    },
                },
            },
        },
        tool_type=ToolType.READ,
        requires_confirmation=False,
    )

    TOOL_GET_HOUSEHOLD_POLICY = ToolSchema(
        name="get_household_policy",
        category=ToolCategory.HOUSEHOLD,
        description="Get household policies (split method, settlement frequency, etc.)",
        input_schema={
            "type": "object",
            "properties": {"household_id": {"type": "string"}},
            "required": ["household_id"],
        },
        output_schema={
            "type": "object",
            "properties": {"policy": {"type": "object"}},
        },
        tool_type=ToolType.READ,
        requires_confirmation=False,
    )

    # Tool definitions (WRITE tools - consequential)
    TOOL_CREATE_EXPENSE = ToolSchema(
        name="create_expense",
        category=ToolCategory.EXPENSES,
        description="Create an expense and split it among participants",
        input_schema={
            "type": "object",
            "properties": {
                "household_id": {"type": "string"},
                "payer_id": {"type": "string"},
                "description": {"type": "string"},
                "amount_paise": {"type": "integer"},
                "split_method": {"type": "string", "enum": ["equal", "exact", "percentage"]},
                "participants": {"type": "array", "items": {"type": "string"}},
                "requestId": {"type": "string"},
            },
            "required": [
                "household_id",
                "payer_id",
                "description",
                "amount_paise",
                "participants",
            ],
        },
        output_schema={
            "type": "object",
            "properties": {
                "expense_id": {"type": "string"},
                "allocations": {"type": "array"},
                "updated_balances": {"type": "object"},
            },
        },
        tool_type=ToolType.WRITE,
        requires_confirmation=True,
    )

    TOOL_COMPLETE_CHORE = ToolSchema(
        name="complete_chore",
        category=ToolCategory.CHORES,
        description="Mark a chore as complete and rotate to next person",
        input_schema={
            "type": "object",
            "properties": {
                "household_id": {"type": "string"},
                "chore_id": {"type": "string"},
                "requestId": {"type": "string"},
            },
            "required": ["household_id", "chore_id"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "chore_id": {"type": "string"},
                "next_assigned": {"type": "string"},
                "message": {"type": "string"},
            },
        },
        tool_type=ToolType.WRITE,
        requires_confirmation=False,
    )

    TOOL_CREATE_MAINTENANCE_ISSUE = ToolSchema(
        name="create_maintenance_issue",
        category=ToolCategory.MAINTENANCE,
        description="Report a maintenance issue",
        input_schema={
            "type": "object",
            "properties": {
                "household_id": {"type": "string"},
                "description": {"type": "string"},
                "severity": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                },
                "requestId": {"type": "string"},
            },
            "required": ["household_id", "description"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "issue_id": {"type": "string"},
                "status": {"type": "string"},
                "message": {"type": "string"},
            },
        },
        tool_type=ToolType.WRITE,
        requires_confirmation=False,
    )

    TOOL_ADD_SHOPPING_ITEM = ToolSchema(
        name="add_shopping_item",
        category=ToolCategory.SHOPPING,
        description="Add an item to the household shopping list",
        input_schema={
            "type": "object",
            "properties": {
                "household_id": {"type": "string"},
                "item_name": {"type": "string"},
                "quantity": {"type": "string"},
                "requestId": {"type": "string"},
            },
            "required": ["household_id", "item_name"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "item_id": {"type": "string"},
                "status": {"type": "string"},
                "message": {"type": "string"},
            },
        },
        tool_type=ToolType.WRITE,
        requires_confirmation=False,
    )

    # Registry
    TOOLS = [
        # READ tools
        TOOL_GET_HOUSEHOLD_STATE,
        TOOL_GET_BALANCES,
        TOOL_GET_MY_BALANCE,
        TOOL_GET_CHORE_ROTATION,
        TOOL_GET_HOUSEHOLD_POLICY,
        # WRITE tools
        TOOL_CREATE_EXPENSE,
        TOOL_COMPLETE_CHORE,
        TOOL_CREATE_MAINTENANCE_ISSUE,
        TOOL_ADD_SHOPPING_ITEM,
    ]

    @staticmethod
    def get_tool_by_name(tool_name: str) -> Optional[ToolSchema]:
        """Look up a tool by name."""
        for tool in AgentToolRegistry.TOOLS:
            if tool.name == tool_name:
                return tool
        return None

    @staticmethod
    def list_tools_by_category(category: ToolCategory) -> List[ToolSchema]:
        """Get all tools in a category."""
        return [t for t in AgentToolRegistry.TOOLS if t.category == category]

    @staticmethod
    def list_read_tools() -> List[ToolSchema]:
        """Get all read-only tools."""
        return [t for t in AgentToolRegistry.TOOLS if t.tool_type == ToolType.READ]

    @staticmethod
    def list_write_tools() -> List[ToolSchema]:
        """Get all write tools."""
        return [t for t in AgentToolRegistry.TOOLS if t.tool_type == ToolType.WRITE]

    @staticmethod
    def generate_tool_descriptions() -> str:
        """Generate tool descriptions for agent context."""
        descriptions = []
        for tool in AgentToolRegistry.TOOLS:
            descriptions.append(f"- {tool.name}: {tool.description}")
        return "\n".join(descriptions)

    @staticmethod
    def format_tool_for_bedrock() -> List[Dict]:
        """
        Format tool registry for Bedrock function calling.
        
        Returns:
            List of tool definitions compatible with Bedrock API
        """
        tools = []
        for tool in AgentToolRegistry.TOOLS:
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            })
        return tools
