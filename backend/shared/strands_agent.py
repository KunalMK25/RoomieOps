"""
RoomieOps Strands Agent

Implements the AI household coordination agent using Strands Agent SDK.

Architecture:
- Agent receives user intent + household context
- Agent selects appropriate tools from registry
- Tools execute deterministic backend operations
- Agent chains multi-step workflows
- Agent generates explanations grounded in actual results

The agent NEVER:
- Performs final arithmetic (delegated to FinanceEngine)
- Mutates state directly (delegated to DynamoDB ops)
- Claims success without backend confirmation
"""

import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

try:
    from strands.agent import Agent, Tool, ToolResult
    STRANDS_AVAILABLE = True
except ImportError:
    STRANDS_AVAILABLE = False

from dynamodb_ops import DynamoDBOps
from finance_engine import FinanceEngine
from auth import AuthenticatedUser

logger = logging.getLogger()
logger.setLevel(logging.INFO)


@dataclass
class ToolExecutionContext:
    """Context for tool execution"""
    user: AuthenticatedUser
    household_id: str
    request_id: str  # For idempotency


class RoomieOpsAgent:
    """
    Strands-based agent for RoomieOps household operations.
    
    Manages:
    - Tool registry
    - Multi-step workflows
    - Tool execution with validation
    - Result explanation
    """
    
    def __init__(self, context: ToolExecutionContext):
        self.context = context
        self.agent = None
        self.tools_registry = self._build_tool_registry()
        
        if STRANDS_AVAILABLE:
            try:
                self.agent = self._initialize_strands_agent()
            except Exception as e:
                logger.warning(f"Strands initialization failed: {e}. Falling back to heuristic mode.")
                self.agent = None
    
    def _build_tool_registry(self) -> Dict[str, Any]:
        """Build the complete tool registry for the agent."""
        return {
            # HOUSEHOLD tools
            "get_household_state": {
                "description": "Retrieve current household state (members, policies, balances, chores)",
                "func": self._tool_get_household_state,
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            "get_household_policy": {
                "description": "Get household expense split policy",
                "func": self._tool_get_household_policy,
                "input_schema": {"type": "object", "properties": {}, "required": []}
            },
            "get_member": {
                "description": "Get member information by user_id",
                "func": self._tool_get_member,
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "user_id": {"type": "string", "description": "Member user_id"}
                    },
                    "required": ["user_id"]
                }
            },
            
            # EXPENSES tools
            "get_expenses": {
                "description": "List recent household expenses",
                "func": self._tool_get_expenses,
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "description": "Max expenses to return"}
                    },
                    "required": []
                }
            },
            "get_balances": {
                "description": "Get current balances for all members",
                "func": self._tool_get_balances,
                "input_schema": {"type": "object", "properties": {}, "required": []}
            },
            "create_expense": {
                "description": "Create a shared expense and calculate split",
                "func": self._tool_create_expense,
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "amount_paise": {"type": "integer", "description": "Amount in paise"},
                        "category": {"type": "string", "description": "Category (groceries, utilities, etc)"},
                        "description": {"type": "string", "description": "Description"},
                        "participant_ids": {"type": "array", "items": {"type": "string"}, "description": "Participant user IDs"},
                        "split_method": {"type": "string", "enum": ["equal"], "description": "Split method (P0: equal only)"}
                    },
                    "required": ["amount_paise", "category", "participant_ids"]
                }
            },
            "record_payment": {
                "description": "Record a payment between members",
                "func": self._tool_record_payment,
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "from_user_id": {"type": "string"},
                        "to_user_id": {"type": "string"},
                        "amount_paise": {"type": "integer"}
                    },
                    "required": ["from_user_id", "to_user_id", "amount_paise"]
                }
            },
            
            # CHORES tools
            "get_chore_rotation": {
                "description": "Get current chore rotation and assignments",
                "func": self._tool_get_chore_rotation,
                "input_schema": {"type": "object", "properties": {}, "required": []}
            },
            "create_chore": {
                "description": "Create a new chore",
                "func": self._tool_create_chore,
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "assigned_to": {"type": "string", "description": "user_id"},
                        "due_date": {"type": "string", "description": "YYYY-MM-DD"},
                        "recurring": {"type": "boolean"}
                    },
                    "required": ["title", "assigned_to"]
                }
            },
            "complete_chore": {
                "description": "Mark a chore as completed",
                "func": self._tool_complete_chore,
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "chore_id": {"type": "string"}
                    },
                    "required": ["chore_id"]
                }
            },
            "assign_chore": {
                "description": "Reassign a chore to a different member",
                "func": self._tool_assign_chore,
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "chore_id": {"type": "string"},
                        "new_assignee_id": {"type": "string"}
                    },
                    "required": ["chore_id", "new_assignee_id"]
                }
            },
            
            # MAINTENANCE tools
            "create_issue": {
                "description": "Report a maintenance issue",
                "func": self._tool_create_issue,
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "location": {"type": "string", "description": "e.g., Room 204, Kitchen"}
                    },
                    "required": ["title", "description", "location"]
                }
            },
            "get_open_issues": {
                "description": "List open maintenance issues",
                "func": self._tool_get_open_issues,
                "input_schema": {"type": "object", "properties": {}, "required": []}
            },
            
            # SHOPPING tools
            "add_shopping_item": {
                "description": "Add item to shopping list",
                "func": self._tool_add_shopping_item,
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "item_name": {"type": "string"},
                        "category": {"type": "string"}
                    },
                    "required": ["item_name"]
                }
            },
            
            # AUDIT tools
            "get_event_history": {
                "description": "Get recent household activity",
                "func": self._tool_get_event_history,
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer"}
                    },
                    "required": []
                }
            }
        }
    
    def _initialize_strands_agent(self):
        """Initialize Strands Agent with tools."""
        if not STRANDS_AVAILABLE:
            return None
        
        try:
            tools = []
            for tool_name, tool_def in self.tools_registry.items():
                tool = Tool(
                    name=tool_name,
                    description=tool_def["description"],
                    input_schema=tool_def["input_schema"],
                )
                tools.append(tool)
            
            agent = Agent(
                tools=tools,
                system_prompt=self._get_system_prompt(),
            )
            logger.info(f"Strands Agent initialized with {len(tools)} tools")
            return agent
        except Exception as e:
            logger.error(f"Failed to initialize Strands Agent: {e}")
            return None
    
    def _get_system_prompt(self) -> str:
        """System prompt for RoomieOps agent."""
        return """You are the RoomieOps household coordination copilot.

You help residents manage shared living: expenses, chores, maintenance, and shopping.

IMPORTANT CONSTRAINTS:
1. You NEVER perform financial calculations. You call calculate_split or similar tools.
2. You NEVER mutate state directly. You use dedicated tools for every change.
3. You NEVER claim success unless the backend tool confirms success.
4. You explain results using actual data from tool responses, never fabricate.
5. For consequential actions, inform the user and ask for confirmation before proceeding.

AVAILABLE TOOLS:
- get_household_state: Current household situation
- get_member: Individual member info
- get_expenses, get_balances: Financial queries
- create_expense: Add shared expense (must use calculate_split)
- record_payment: Record settlement
- get_chore_rotation, create_chore, assign_chore, complete_chore: Chore management
- create_issue, get_open_issues: Maintenance
- add_shopping_item: Shopping list
- get_event_history: Activity log

When a user asks something, select the appropriate tool(s) to retrieve or modify data.
Always respond with actual results, never assumptions.
"""
    
    # ==================== HOUSEHOLD TOOLS ====================
    
    def _tool_get_household_state(self, **kwargs) -> Dict:
        """Get complete household state."""
        try:
            household = DynamoDBOps.get_household(self.context.household_id)
            members = DynamoDBOps.get_members(self.context.household_id)
            balances = DynamoDBOps.get_all_balances(self.context.household_id)
            chores = DynamoDBOps.get_chores(self.context.household_id)
            
            return {
                "status": "success",
                "household": household,
                "members_count": len(members),
                "members": [
                    {"user_id": m.get("user_id"), "name": m.get("name"), "role": m.get("role")}
                    for m in members
                ],
                "balance_summary": {b.get("user_id"): b.get("balance_paise", 0) for b in balances},
                "active_chores": len([c for c in chores if c.get("status") in ["pending", "overdue"]])
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _tool_get_household_policy(self, **kwargs) -> Dict:
        """Get household expense split policy."""
        try:
            household = DynamoDBOps.get_household(self.context.household_id)
            policy = household.get("policy", {"default_split": "equal"})
            return {"status": "success", "policy": policy}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _tool_get_member(self, user_id: str, **kwargs) -> Dict:
        """Get specific member details."""
        try:
            members = DynamoDBOps.get_members(self.context.household_id)
            member = next((m for m in members if m.get("user_id") == user_id), None)
            if member:
                return {"status": "success", "member": member}
            return {"status": "error", "message": f"Member {user_id} not found"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    # ==================== EXPENSES TOOLS ====================
    
    def _tool_get_expenses(self, limit: int = 10, **kwargs) -> Dict:
        """Get recent expenses."""
        try:
            expenses = DynamoDBOps.get_expenses(self.context.household_id)
            return {
                "status": "success",
                "count": len(expenses[:limit]),
                "expenses": expenses[:limit]
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _tool_get_balances(self, **kwargs) -> Dict:
        """Get all member balances."""
        try:
            balances = DynamoDBOps.get_all_balances(self.context.household_id)
            balance_dict = {b.get("user_id"): b.get("balance_paise", 0) for b in balances}
            return {"status": "success", "balances": balance_dict}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _tool_create_expense(self, amount_paise: int, category: str, participant_ids: List[str], 
                            description: str = "", split_method: str = "equal", **kwargs) -> Dict:
        """Create expense with deterministic split."""
        try:
            # Calculate split using deterministic engine
            split_result = FinanceEngine.split_equal(
                total_paise=amount_paise,
                participant_ids=participant_ids
            )
            
            # Create expense record
            expense = DynamoDBOps.create_expense(
                household_id=self.context.household_id,
                payer_id=self.context.user.user_id,
                amount_paise=amount_paise,
                category=category,
                description=description,
                allocations=split_result.allocations,
                request_id=self.context.request_id
            )
            
            return {
                "status": "success",
                "expense_id": expense.get("expense_id"),
                "amount_paise": amount_paise,
                "allocations": [
                    {"user_id": a.user_id, "amount_paise": a.amount_paise}
                    for a in split_result.allocations
                ],
                "message": f"Expense created: {category} ₹{amount_paise/100:.2f}"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _tool_record_payment(self, from_user_id: str, to_user_id: str, amount_paise: int, **kwargs) -> Dict:
        """Record payment between members."""
        try:
            payment = DynamoDBOps.record_payment(
                household_id=self.context.household_id,
                from_user_id=from_user_id,
                to_user_id=to_user_id,
                amount_paise=amount_paise,
                request_id=self.context.request_id
            )
            return {
                "status": "success",
                "payment_id": payment.get("payment_id"),
                "message": f"Payment recorded: {from_user_id} → {to_user_id} ₹{amount_paise/100:.2f}"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    # ==================== CHORES TOOLS ====================
    
    def _tool_get_chore_rotation(self, **kwargs) -> Dict:
        """Get current chore assignments."""
        try:
            chores = DynamoDBOps.get_chores(self.context.household_id)
            return {
                "status": "success",
                "count": len(chores),
                "chores": [
                    {
                        "chore_id": c.get("chore_id"),
                        "title": c.get("title"),
                        "assigned_to": c.get("assigned_to"),
                        "status": c.get("status"),
                        "due_date": c.get("due_date")
                    }
                    for c in chores
                ]
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _tool_create_chore(self, title: str, assigned_to: str, due_date: str = "", recurring: bool = False, **kwargs) -> Dict:
        """Create a new chore."""
        try:
            chore = DynamoDBOps.create_chore(
                household_id=self.context.household_id,
                title=title,
                assigned_to=assigned_to,
                due_date=due_date,
                recurring=recurring,
                request_id=self.context.request_id
            )
            return {
                "status": "success",
                "chore_id": chore.get("chore_id"),
                "message": f"Chore created: {title} assigned to {assigned_to}"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _tool_complete_chore(self, chore_id: str, **kwargs) -> Dict:
        """Mark chore as completed."""
        try:
            chore = DynamoDBOps.complete_chore(
                household_id=self.context.household_id,
                chore_id=chore_id,
                request_id=self.context.request_id
            )
            return {
                "status": "success",
                "chore_id": chore_id,
                "message": f"Chore completed: {chore.get('title', 'Unknown')}"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _tool_assign_chore(self, chore_id: str, new_assignee_id: str, **kwargs) -> Dict:
        """Reassign chore to different member."""
        try:
            chore = DynamoDBOps.assign_chore(
                household_id=self.context.household_id,
                chore_id=chore_id,
                assigned_to=new_assignee_id,
                request_id=self.context.request_id
            )
            return {
                "status": "success",
                "chore_id": chore_id,
                "new_assignee": new_assignee_id,
                "message": f"Chore reassigned to {new_assignee_id}"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    # ==================== MAINTENANCE TOOLS ====================
    
    def _tool_create_issue(self, title: str, description: str, location: str, **kwargs) -> Dict:
        """Create maintenance issue."""
        try:
            issue = DynamoDBOps.create_maintenance_issue(
                household_id=self.context.household_id,
                title=title,
                description=description,
                location=location,
                reported_by=self.context.user.user_id,
                request_id=self.context.request_id
            )
            return {
                "status": "success",
                "issue_id": issue.get("issue_id"),
                "message": f"Issue reported: {title} in {location}"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _tool_get_open_issues(self, **kwargs) -> Dict:
        """Get open maintenance issues."""
        try:
            issues = DynamoDBOps.get_open_maintenance_issues(self.context.household_id)
            return {
                "status": "success",
                "count": len(issues),
                "issues": [
                    {
                        "issue_id": i.get("issue_id"),
                        "title": i.get("title"),
                        "location": i.get("location"),
                        "status": i.get("status"),
                        "reported_by": i.get("reported_by"),
                        "created_at": i.get("created_at")
                    }
                    for i in issues
                ]
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    # ==================== SHOPPING TOOLS ====================
    
    def _tool_add_shopping_item(self, item_name: str, category: str = "", **kwargs) -> Dict:
        """Add item to shopping list."""
        try:
            item = DynamoDBOps.add_shopping_item(
                household_id=self.context.household_id,
                item_name=item_name,
                category=category,
                request_id=self.context.request_id
            )
            return {
                "status": "success",
                "item_id": item.get("item_id"),
                "message": f"Added to shopping list: {item_name}"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    # ==================== AUDIT TOOLS ====================
    
    def _tool_get_event_history(self, limit: int = 20, **kwargs) -> Dict:
        """Get recent household activity."""
        try:
            events = DynamoDBOps.get_audit_records(self.context.household_id, limit=limit)
            return {
                "status": "success",
                "count": len(events),
                "events": [
                    {
                        "timestamp": e.get("created_at"),
                        "actor": e.get("actor"),
                        "action": e.get("action"),
                        "description": e.get("description")
                    }
                    for e in events
                ]
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    # ==================== AGENT EXECUTION ====================
    
    def process_user_request(self, user_message: str) -> Dict:
        """
        Process a user request through the agent.
        
        Returns:
            {
                "status": "success|error",
                "agent_type": "bedrock|strands|heuristic",
                "response": "User-facing explanation",
                "actions_taken": [...],
                "requires_confirmation": bool,
                "action_id": "..." (if confirmation required)
            }
        """
        logger.info(f"Processing request: {user_message}")
        
        if self.agent and STRANDS_AVAILABLE:
            try:
                # Use Strands agent
                logger.info("Using Strands agent")
                return self._process_with_strands(user_message)
            except Exception as e:
                logger.warning(f"Strands processing failed: {e}. Falling back.")
        
        # Fallback: Use heuristic-based intent detection
        logger.info("Using heuristic fallback")
        return self._process_with_heuristic(user_message)
    
    def _process_with_strands(self, user_message: str) -> Dict:
        """Process with Strands agent (if available and initialized)."""
        # Placeholder: Strands integration would go here
        # For now, return heuristic response with "strands" label
        return {
            "status": "not_implemented",
            "agent_type": "strands",
            "message": "Strands local processing not fully implemented yet"
        }
    
    def _process_with_heuristic(self, user_message: str) -> Dict:
        """Process with heuristic keyword matching."""
        msg_lower = user_message.lower()
        
        # Intent detection
        if any(word in msg_lower for word in ["owe", "balance", "how much"]):
            return self._handle_view_balance()
        elif any(word in msg_lower for word in ["chore", "task", "assigned"]):
            return self._handle_view_chores()
        elif any(word in msg_lower for word in ["paid", "groceries", "split", "expense"]):
            return self._handle_create_expense(user_message)
        elif any(word in msg_lower for word in ["broken", "maintenance", "issue", "geyser"]):
            return self._handle_create_maintenance(user_message)
        elif any(word in msg_lower for word in ["shopping", "groceries", "add item"]):
            return self._handle_add_shopping(user_message)
        else:
            return {
                "status": "unclear",
                "agent_type": "heuristic",
                "response": "I didn't understand that. Try asking about: balance, chores, expenses, maintenance, or shopping.",
                "actions_taken": []
            }
    
    def _handle_view_balance(self) -> Dict:
        """Handle 'view balance' intent."""
        try:
            balances = DynamoDBOps.get_all_balances(self.context.household_id)
            my_balance = next(
                (b.get("balance_paise", 0) for b in balances if b.get("user_id") == self.context.user.user_id),
                0
            )
            
            if my_balance > 0:
                response = f"You are owed ₹{my_balance/100:.2f}"
            elif my_balance < 0:
                response = f"You owe ₹{abs(my_balance)/100:.2f}"
            else:
                response = "Your balance is settled"
            
            return {
                "status": "success",
                "agent_type": "heuristic",
                "response": response,
                "actions_taken": ["get_balances"],
                "balance_paise": my_balance
            }
        except Exception as e:
            return {"status": "error", "agent_type": "heuristic", "message": str(e)}
    
    def _handle_view_chores(self) -> Dict:
        """Handle 'view chores' intent."""
        try:
            chores = DynamoDBOps.get_chores(self.context.household_id)
            my_chores = [c for c in chores if c.get("assigned_to") == self.context.user.user_id]
            
            response = f"You have {len(my_chores)} chore(s) assigned"
            
            return {
                "status": "success",
                "agent_type": "heuristic",
                "response": response,
                "actions_taken": ["get_chore_rotation"],
                "chores_count": len(my_chores)
            }
        except Exception as e:
            return {"status": "error", "agent_type": "heuristic", "message": str(e)}
    
    def _handle_create_expense(self, user_message: str) -> Dict:
        """Handle 'create expense' intent."""
        # Heuristic: extract amount if mentioned
        # This is simplified; full parsing would be more sophisticated
        return {
            "status": "requires_confirmation",
            "agent_type": "heuristic",
            "response": "I can help you record this expense. Please specify the amount and who it should be split between.",
            "actions_taken": [],
            "requires_confirmation": True
        }
    
    def _handle_create_maintenance(self, user_message: str) -> Dict:
        """Handle 'create maintenance' intent."""
        return {
            "status": "requires_confirmation",
            "agent_type": "heuristic",
            "response": "I'll report this maintenance issue. Please provide more details about the location and problem.",
            "actions_taken": [],
            "requires_confirmation": True
        }
    
    def _handle_add_shopping(self, user_message: str) -> Dict:
        """Handle 'add shopping' intent."""
        return {
            "status": "requires_confirmation",
            "agent_type": "heuristic",
            "response": "I can add items to the shopping list. What items do you need?",
            "actions_taken": [],
            "requires_confirmation": True
        }
