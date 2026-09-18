#!/usr/bin/env python3
"""
Seed BUILD_IT_STRANDS with Sunrise PG household data.

This script creates:
- Household: "Sunrise PG" (Room 302)
- Members: Kunal, Priya, Rahul, Arjun
- Initial state: Expenses, balances, chores, etc.

This provides realistic test data for BUILD_IT development.
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta
import uuid

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.dynamodb_ops import DynamoDBOps, set_storage_provider
from shared.providers import ExecutionModeManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def initialize_provider():
    """Initialize storage provider based on EXECUTION_MODE."""
    
    mode_str = os.environ.get("EXECUTION_MODE", "BUILD_IT_STRANDS")
    logger.info(f"Using execution mode: {mode_str}")
    
    # Force BUILD_IT_STRANDS for local development
    os.environ["EXECUTION_MODE"] = "BUILD_IT_STRANDS"
    os.environ["LLM_ENDPOINT"] = os.environ.get("LLM_ENDPOINT", "http://localhost:11434")
    os.environ["DYNAMODB_ENDPOINT"] = os.environ.get("DYNAMODB_ENDPOINT", "http://localhost:4566")
    os.environ["CEDAR_ENDPOINT"] = os.environ.get("CEDAR_ENDPOINT", "http://localhost:8180")
    
    try:
        providers = ExecutionModeManager.get_providers()
        set_storage_provider(providers.storage)
        logger.info(f"✓ Storage provider initialized: {type(providers.storage).__name__}")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to initialize provider: {e}")
        return False


def create_household():
    """Create Sunrise PG household."""
    
    household_id = "sunrise-pg-room-302"
    
    try:
        household = DynamoDBOps.create_household(
            household_id=household_id,
            name="Sunrise PG - Room 302",
            description="Shared PG accommodation in Bangalore",
            policy={
                "split_method": "equal",
                "settlement_frequency": "monthly",
                "chore_rotation_method": "round_robin",
            },
            created_by="system"
        )
        
        logger.info(f"✓ Household created: {household_id}")
        return household_id
    except Exception as e:
        logger.error(f"✗ Failed to create household: {e}")
        return None


def add_members(household_id: str):
    """Add household members."""
    
    members = [
        {"name": "Kunal", "email": "kunal@example.com", "role": "admin"},
        {"name": "Priya", "email": "priya@example.com", "role": "member"},
        {"name": "Rahul", "email": "rahul@example.com", "role": "member"},
        {"name": "Arjun", "email": "arjun@example.com", "role": "member"},
    ]
    
    member_ids = {}
    
    try:
        for i, member_data in enumerate(members):
            user_id = f"user-{i+1}"  # Simplified user IDs
            member = DynamoDBOps.add_member(
                household_id=household_id,
                user_id=user_id,
                name=member_data["name"],
                email=member_data["email"],
                role=member_data["role"]
            )
            
            member_ids[member_data["name"]] = user_id
            logger.info(f"  ✓ Added member: {member_data['name']} ({user_id})")
        
        return member_ids
    except Exception as e:
        logger.error(f"✗ Failed to add members: {e}")
        return {}


def create_initial_expenses(household_id: str, member_ids: dict):
    """Create some initial expenses for realistic balances."""
    
    expenses = [
        {
            "payer": "Kunal",
            "description": "Groceries - Week 1",
            "amount_paise": 350000,  # ₹3500
            "split_with": ["Kunal", "Priya", "Rahul", "Arjun"],
        },
        {
            "payer": "Priya",
            "description": "Internet and utilities",
            "amount_paise": 120000,  # ₹1200
            "split_with": ["Kunal", "Priya", "Rahul", "Arjun"],
        },
        {
            "payer": "Rahul",
            "description": "Household cleaning supplies",
            "amount_paise": 80000,  # ₹800
            "split_with": ["Kunal", "Priya", "Rahul", "Arjun"],
        },
    ]
    
    try:
        for expense_data in expenses:
            payer_id = member_ids.get(expense_data["payer"])
            if not payer_id:
                logger.warning(f"  ⚠ Payer not found: {expense_data['payer']}")
                continue
            
            # Equal split among all members
            num_members = len(expense_data["split_with"])
            per_person = expense_data["amount_paise"] // num_members
            remainder = expense_data["amount_paise"] % num_members
            
            allocations = []
            for i, member_name in enumerate(expense_data["split_with"]):
                amount = per_person + (1 if i == 0 else 0) * remainder  # Payer gets remainder
                allocations.append({
                    "user_id": member_ids[member_name],
                    "amount_paise": amount
                })
            
            expense = DynamoDBOps.create_expense(
                household_id=household_id,
                expense_id=str(uuid.uuid4())[:8],
                payer_id=payer_id,
                description=expense_data["description"],
                total_paise=expense_data["amount_paise"],
                allocations=allocations,
                split_method="equal",
                created_by=payer_id
            )
            
            logger.info(f"  ✓ Expense created: {expense_data['description']} (₹{expense_data['amount_paise']/100:.0f})")
        
        return True
    except Exception as e:
        logger.error(f"✗ Failed to create expenses: {e}")
        return False


def create_chores(household_id: str, member_ids: dict):
    """Create recurring chores with rotation."""
    
    member_list = list(member_ids.keys())
    
    chores = [
        {"name": "Kitchen cleaning", "members": member_list},
        {"name": "Bathroom cleaning", "members": member_list},
        {"name": "Living room tidying", "members": member_list},
        {"name": "Trash collection", "members": member_list},
    ]
    
    try:
        for chore_data in chores:
            rotation_ids = [member_ids[name] for name in chore_data["members"]]
            
            chore = DynamoDBOps.create_chore(
                household_id=household_id,
                chore_id=str(uuid.uuid4())[:8],
                name=chore_data["name"],
                assigned_to=rotation_ids[0],  # Start with first member
                frequency="weekly",
                rotation_order=rotation_ids,
                created_by="system"
            )
            
            logger.info(f"  ✓ Chore created: {chore_data['name']} (rotation: {len(rotation_ids)} members)")
        
        return True
    except Exception as e:
        logger.error(f"✗ Failed to create chores: {e}")
        return False


def main():
    """Main function."""
    
    logger.info("=" * 70)
    logger.info("SEED HOUSEHOLD DATA FOR BUILD_IT_STRANDS")
    logger.info("=" * 70)
    logger.info("")
    
    # Initialize provider
    logger.info("Step 1: Initialize storage provider")
    if not initialize_provider():
        logger.error("✗ Provider initialization failed")
        return False
    logger.info("")
    
    # Create household
    logger.info("Step 2: Create household")
    household_id = create_household()
    if not household_id:
        logger.error("✗ Household creation failed")
        return False
    logger.info("")
    
    # Add members
    logger.info("Step 3: Add household members")
    member_ids = add_members(household_id)
    if not member_ids:
        logger.error("✗ Member creation failed")
        return False
    logger.info("")
    
    # Create expenses
    logger.info("Step 4: Create initial expenses")
    if not create_initial_expenses(household_id, member_ids):
        logger.error("✗ Expense creation failed")
        return False
    logger.info("")
    
    # Create chores
    logger.info("Step 5: Create household chores")
    if not create_chores(household_id, member_ids):
        logger.error("✗ Chore creation failed")
        return False
    logger.info("")
    
    # Summary
    logger.info("=" * 70)
    logger.info("✓ SEED DATA COMPLETE")
    logger.info("=" * 70)
    logger.info("")
    logger.info("Household Summary:")
    logger.info(f"  ID: {household_id}")
    logger.info(f"  Members: {', '.join(member_ids.keys())}")
    logger.info("")
    logger.info("You can now test RoomieOps with:")
    logger.info(f"  - User ID: user-1 (Kunal - admin)")
    logger.info(f"  - User ID: user-2 (Priya)")
    logger.info(f"  - User ID: user-3 (Rahul)")
    logger.info(f"  - User ID: user-4 (Arjun)")
    logger.info("")
    logger.info("Test the API:")
    logger.info(f'  curl -H "x-user-id: user-1" http://localhost:5000/households/{household_id}/balances')
    logger.info("")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
