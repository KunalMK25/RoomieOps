"""
Unit tests for RoomieOps finance engine.

Tests validate reconciliation correctness against Room 302 seed data.
All calculations must use integer paise (no floats).
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend/shared"))

from finance_engine import FinanceEngine, SplitMethod


def test_equal_split_no_remainder():
    """Test equal split with no remainder."""
    result = FinanceEngine.split_equal(
        total_paise=240000,  # ₹2400
        participant_ids=["user1", "user2", "user3", "user4"],
    )
    
    assert result.total_amount_paise == 240000
    assert result.method == SplitMethod.EQUAL
    assert len(result.allocations) == 4
    
    for alloc in result.allocations:
        assert alloc.amount_paise == 60000  # ₹600 each
    
    total_allocated = sum(a.amount_paise for a in result.allocations)
    assert total_allocated == 240000, f"Reconciliation failed: {total_allocated} != {240000}"
    print("✓ test_equal_split_no_remainder passed")


def test_equal_split_with_remainder():
    """Test equal split where remainder is assigned to first participant."""
    result = FinanceEngine.split_equal(
        total_paise=100000,  # ₹1000
        participant_ids=["user1", "user2", "user3"],
    )
    
    assert result.total_amount_paise == 100000
    allocations = sorted(result.allocations, key=lambda a: a.user_id)
    
    # 100000 / 3 = 33333 per person, remainder = 1
    # First user gets 33333 + 1 = 33334
    assert allocations[0].amount_paise == 33334  # user1
    assert allocations[1].amount_paise == 33333  # user2
    assert allocations[2].amount_paise == 33333  # user3
    
    total_allocated = sum(a.amount_paise for a in allocations)
    assert total_allocated == 100000, f"Reconciliation failed: {total_allocated}"
    print("✓ test_equal_split_with_remainder passed")


def test_exact_split():
    """Test exact split with specified amounts."""
    exact_allocations = {
        "user1": 100000,
        "user2": 50000,
        "user3": 30000,
    }
    
    result = FinanceEngine.split_exact(
        total_paise=180000,
        exact_allocations=exact_allocations,
    )
    
    assert result.total_amount_paise == 180000
    assert result.method == SplitMethod.EXACT
    assert len(result.allocations) == 3
    
    allocation_dict = {a.user_id: a.amount_paise for a in result.allocations}
    assert allocation_dict["user1"] == 100000
    assert allocation_dict["user2"] == 50000
    assert allocation_dict["user3"] == 30000
    
    total_allocated = sum(a.amount_paise for a in result.allocations)
    assert total_allocated == 180000
    print("✓ test_exact_split passed")


def test_exact_split_mismatch_fails():
    """Test that exact split fails if amounts don't match."""
    try:
        FinanceEngine.split_exact(
            total_paise=200000,
            exact_allocations={"user1": 100000, "user2": 50000},  # Only 150000
        )
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "sum to" in str(e).lower()
        print("✓ test_exact_split_mismatch_fails passed")


def test_percentage_split():
    """Test percentage-based split."""
    result = FinanceEngine.split_percentage(
        total_paise=100000,  # ₹1000
        percentages={"user1": 50.0, "user2": 30.0, "user3": 20.0},
    )
    
    assert result.total_amount_paise == 100000
    assert result.method == SplitMethod.PERCENTAGE
    
    allocation_dict = {a.user_id: a.amount_paise for a in result.allocations}
    assert allocation_dict["user1"] == 50000
    assert allocation_dict["user2"] == 30000
    assert allocation_dict["user3"] == 20000
    
    total_allocated = sum(a.amount_paise for a in result.allocations)
    assert total_allocated == 100000
    print("✓ test_percentage_split passed")


def test_percentage_split_remainder_reconciliation():
    """Test percentage split with remainder reconciliation."""
    result = FinanceEngine.split_percentage(
        total_paise=100000,
        percentages={"user1": 33.33, "user2": 33.33, "user3": 33.34},
    )
    
    assert result.total_amount_paise == 100000
    total_allocated = sum(a.amount_paise for a in result.allocations)
    assert total_allocated == 100000, f"Reconciliation failed: {total_allocated}"
    print("✓ test_percentage_split_remainder_reconciliation passed")


def test_balance_calculation_single_expense():
    """Test balance calculation with a single expense."""
    expenses = [
        {
            "payer_id": "user1",
            "allocations": [
                {"user_id": "user1", "amount_paise": 60000},
                {"user_id": "user2", "amount_paise": 60000},
                {"user_id": "user3", "amount_paise": 60000},
            ],
        }
    ]
    
    balances = FinanceEngine.calculate_balances(expenses)
    
    # user1 paid ₹1800, owes ₹600 → net +₹1200
    # user2 paid ₹0, owes ₹600 → net -₹600
    # user3 paid ₹0, owes ₹600 → net -₹600
    assert balances["user1"] == 120000
    assert balances["user2"] == -60000
    assert balances["user3"] == -60000
    
    total_balance = sum(balances.values())
    assert total_balance == 0, f"Balances don't reconcile: {total_balance}"
    print("✓ test_balance_calculation_single_expense passed")


def test_balance_calculation_multiple_expenses():
    """Test balance calculation with multiple expenses."""
    expenses = [
        {
            "payer_id": "user1",
            "allocations": [
                {"user_id": "user1", "amount_paise": 60000},
                {"user_id": "user2", "amount_paise": 60000},
                {"user_id": "user3", "amount_paise": 60000},
            ],
        },
        {
            "payer_id": "user2",
            "allocations": [
                {"user_id": "user2", "amount_paise": 50000},
                {"user_id": "user3", "amount_paise": 50000},
            ],
        },
    ]
    
    balances = FinanceEngine.calculate_balances(expenses)
    
    # user1: paid ₹1800, owes ₹600 → net +₹1200
    # user2: paid ₹1000, owes (₹600 + ₹500) = ₹1100 → net -₹100
    # user3: paid ₹0, owes (₹600 + ₹500) = ₹1100 → net -₹1100
    assert balances["user1"] == 120000
    assert balances["user2"] == -10000
    assert balances["user3"] == -110000
    
    total_balance = sum(balances.values())
    assert total_balance == 0, f"Balances don't reconcile: {total_balance}"
    print("✓ test_balance_calculation_multiple_expenses passed")


def test_room_302_seed_data():
    """
    Evaluation benchmark: Room 302 household.
    Fixed scenario with known-correct balances.
    """
    # Room 302: 4 residents (Aman, Bela, Charan, Diana)
    # Expense 1: Aman paid ₹5000 for groceries, split equally
    # Expense 2: Bela paid ₹3000 for utilities, split equally
    # Expected: Each person owes/is owed deterministic amount
    
    expenses = [
        {
            "payer_id": "aman",
            "allocations": [
                {"user_id": "aman", "amount_paise": 125000},   # ₹1250
                {"user_id": "bela", "amount_paise": 125000},
                {"user_id": "charan", "amount_paise": 125000},
                {"user_id": "diana", "amount_paise": 125000},
            ],
        },
        {
            "payer_id": "bela",
            "allocations": [
                {"user_id": "aman", "amount_paise": 75000},    # ₹750
                {"user_id": "bela", "amount_paise": 75000},
                {"user_id": "charan", "amount_paise": 75000},
                {"user_id": "diana", "amount_paise": 75000},
            ],
        },
    ]
    
    balances = FinanceEngine.calculate_balances(expenses)
    
    # Aman: paid ₹5000, owes ₹1250 + ₹750 = ₹2000 → net +₹3000
    assert balances["aman"] == 300000
    
    # Bela: paid ₹3000, owes ₹1250 + ₹750 = ₹2000 → net +₹1000
    assert balances["bela"] == 100000
    
    # Charan: paid ₹0, owes ₹1250 + ₹750 = ₹2000 → net -₹2000
    assert balances["charan"] == -200000
    
    # Diana: paid ₹0, owes ₹1250 + ₹750 = ₹2000 → net -₹2000
    assert balances["diana"] == -200000
    
    total_balance = sum(balances.values())
    assert total_balance == 0, f"Room 302 balances don't reconcile: {total_balance}"
    print("✓ test_room_302_seed_data passed (seed data verified)")


if __name__ == "__main__":
    print("Running RoomieOps Finance Engine Tests\n")
    
    test_equal_split_no_remainder()
    test_equal_split_with_remainder()
    test_exact_split()
    test_exact_split_mismatch_fails()
    test_percentage_split()
    test_percentage_split_remainder_reconciliation()
    test_balance_calculation_single_expense()
    test_balance_calculation_multiple_expenses()
    test_room_302_seed_data()
    
    print("\n✓ All tests passed!")
