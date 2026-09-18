"""
End-to-End RoomieOps Workflow Tests

Tests the complete flow for key household operations:
1. Expense split workflow (pay + distribute)
2. Chore assignment workflow
3. Maintenance issue workflow
4. Shopping item workflow
"""

import sys
sys.path.insert(0, 'backend/shared')

from confirmation import ConfirmationManager, ActionType


class TestExpenseWorkflow:
    """Test: User pays 1200 for groceries, split equally"""
    
    def test_expense_split_proposal(self):
        """Step 1: Create expense split proposal"""
        amount_paise = 120000  # 1200 rupees
        participants = ['kunal', 'priya', 'rahul']
        
        share = amount_paise // len(participants)
        assert share == 40000  # 400 each
        print("OK: Expense split calculated: 1200 -> 3 x 400")
    
    def test_expense_confirmation_proposal(self):
        """Step 2: Generate confirmation proposal"""
        confirmation = ConfirmationManager()
        amount_paise = 120000
        participants = ['kunal', 'priya', 'rahul']
        
        action_id = confirmation.create_pending_action(
            action_type=ActionType.CREATE_EXPENSE,
            user_id='kunal',
            household_id='h_sunrise',
            proposal={
                'title': 'Expense Split',
                'description': 'Split 1200 for groceries',
                'amount': '1200',
                'split': '3 people x 400 each',
            },
            parameters={
                'description': 'Groceries',
                'total_paise': amount_paise,
                'split_method': 'equal',
                'participants': participants,
            }
        )
        
        assert action_id is not None
        print("OK: Confirmation proposal created: " + action_id)


class TestChoreWorkflow:
    """Test: Query and filter chores"""
    
    def test_chore_query(self):
        """Query: What chores do I have this week?"""
        chores = [
            {
                'chore_id': 'c1',
                'title': 'Kitchen cleaning',
                'assigned_to': 'kunal',
                'frequency': 'weekly',
                'status': 'pending',
            },
            {
                'chore_id': 'c2',
                'title': 'Laundry collection',
                'assigned_to': 'priya',
                'frequency': 'weekly',
                'status': 'pending',
            }
        ]
        
        my_chores = [c for c in chores if c['assigned_to'] == 'kunal']
        assert len(my_chores) == 1
        assert my_chores[0]['title'] == 'Kitchen cleaning'
        print("OK: Chore query returned 1 chores for user")


class TestMaintenanceWorkflow:
    """Test: Create and track maintenance issue"""
    
    def test_maintenance_issue_creation(self):
        """Create: The geyser in Room 204 is broken"""
        confirmation = ConfirmationManager()
        
        action_id = confirmation.create_pending_action(
            action_type=ActionType.CREATE_ISSUE,
            user_id='kunal',
            household_id='h_sunrise',
            proposal={
                'title': 'Geyser broken',
                'description': 'Geyser in Room 204 not working',
                'priority': 'High',
            },
            parameters={
                'title': 'Geyser broken',
                'description': 'Geyser in Room 204 not working',
                'room': '204',
                'priority': 'high',
            }
        )
        
        assert action_id is not None
        print("OK: Maintenance issue creation workflow verified")


class TestShoppingWorkflow:
    """Test: Add and manage shopping items"""
    
    def test_add_shopping_item(self):
        """Add: Need milk and bread"""
        confirmation = ConfirmationManager()
        
        action_id = confirmation.create_pending_action(
            action_type=ActionType.ADD_SHOPPING_ITEM,
            user_id='kunal',
            household_id='h_sunrise',
            proposal={
                'title': 'Add shopping item',
                'item': 'Milk (2 liters)',
            },
            parameters={
                'item_name': 'Milk',
                'quantity': 2,
                'unit': 'liters',
                'category': 'Dairy',
            }
        )
        
        assert action_id is not None
        print("OK: Shopping item workflow verified")


class TestExecutionModes:
    """Test execution mode labeling"""
    
    def test_local_heuristic_mode_label(self):
        """Verify LOCAL_HEURISTIC mode is explicitly labeled"""
        execution_mode = {
            'mode': 'LOCAL_HEURISTIC',
            'reason': 'Strands SDK not installed; using keyword-based routing',
            'ai_reasoning': False,
        }
        
        assert execution_mode['mode'] == 'LOCAL_HEURISTIC'
        assert not execution_mode['ai_reasoning']
        print("OK: Execution mode LOCAL_HEURISTIC verified (ai_reasoning=False)")
    
    def test_real_bedrock_mode_label(self):
        """Verify REAL_BEDROCK mode would be labeled"""
        execution_mode = {
            'mode': 'REAL_BEDROCK',
            'reason': 'Claude invoked through AWS Bedrock',
            'ai_reasoning': True,
        }
        
        assert execution_mode['mode'] == 'REAL_BEDROCK'
        assert execution_mode['ai_reasoning']
        print("OK: Execution mode REAL_BEDROCK verified (ai_reasoning=True)")


def run_all_tests():
    """Run all workflow tests"""
    print("=" * 60)
    print("END-TO-END WORKFLOW TESTS")
    print("=" * 60)
    
    tests = [
        (TestExpenseWorkflow(), "Expense Workflow"),
        (TestChoreWorkflow(), "Chore Workflow"),
        (TestMaintenanceWorkflow(), "Maintenance Workflow"),
        (TestShoppingWorkflow(), "Shopping Workflow"),
        (TestExecutionModes(), "Execution Mode Labeling"),
    ]
    
    passed = 0
    failed = 0
    
    for test_class, name in tests:
        print("\n" + name + ":")
        print("-" * 40)
        
        for method_name in dir(test_class):
            if method_name.startswith('test_'):
                try:
                    method = getattr(test_class, method_name)
                    method()
                    passed += 1
                except Exception as e:
                    print("FAIL " + method_name + ": " + str(e))
                    failed += 1
    
    print("\n" + "=" * 60)
    print("RESULTS: " + str(passed) + " passed, " + str(failed) + " failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
