"""
RoomieOps Financial Engine

Deterministic, auditable, unit-testable financial calculations.
- Money represented as integer paise (no float arithmetic)
- Split calculations with guaranteed reconciliation
- Balance tracking and settlement
- CRITICAL: This module is independent from AI/Bedrock. All arithmetic is deterministic.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Tuple
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class SplitMethod(Enum):
    """Supported expense split methods."""
    EQUAL = "equal"
    EXACT = "exact"
    PERCENTAGE = "percentage"
    SHARE = "share"
    WEIGHTED = "weighted"
    OCCUPANCY = "occupancy"
    PRORATED = "prorated"


@dataclass
class SplitAllocation:
    """Result of a split calculation for one participant."""
    user_id: str
    amount_paise: int  # Always integer, never float


@dataclass
class SplitResult:
    """Complete result of splitting an expense."""
    total_amount_paise: int
    method: SplitMethod
    allocations: List[SplitAllocation]
    reconciliation_note: str = ""  # Explanation of remainder assignment


class FinanceEngine:
    """Deterministic financial calculations."""

    @staticmethod
    def split_equal(
        total_paise: int,
        participant_ids: List[str],
    ) -> SplitResult:
        """
        Split expense equally among participants.
        
        Args:
            total_paise: Total amount in paise (integer)
            participant_ids: List of user IDs who share this expense
            
        Returns:
            SplitResult with allocations for each participant
            
        Raises:
            ValueError: If inputs invalid
        """
        if total_paise < 0:
            raise ValueError("Total amount cannot be negative")
        if not participant_ids:
            raise ValueError("Must have at least one participant")
        
        participant_count = len(participant_ids)
        per_person = total_paise // participant_count
        remainder = total_paise % participant_count
        
        allocations = []
        for i, user_id in enumerate(participant_ids):
            # Assign remainder to first participant (deterministic)
            amount = per_person + (1 if i == 0 else 0) * (remainder if remainder > 0 else 0)
            allocations.append(SplitAllocation(user_id=user_id, amount_paise=amount))
        
        # Verify reconciliation
        total_allocated = sum(a.amount_paise for a in allocations)
        assert total_allocated == total_paise, \
            f"Reconciliation failed: allocated {total_allocated}, expected {total_paise}"
        
        reconciliation_note = (
            f"Equal split: {per_person} paise per person, "
            f"{remainder} paise remainder assigned to first participant"
            if remainder > 0 else "Equal split with no remainder"
        )
        
        return SplitResult(
            total_amount_paise=total_paise,
            method=SplitMethod.EQUAL,
            allocations=allocations,
            reconciliation_note=reconciliation_note,
        )

    @staticmethod
    def split_exact(
        total_paise: int,
        exact_allocations: Dict[str, int],
    ) -> SplitResult:
        """
        Split using exact amounts specified for each participant.
        
        Args:
            total_paise: Total expense amount
            exact_allocations: {user_id: amount_paise}
            
        Returns:
            SplitResult
            
        Raises:
            ValueError: If allocations don't sum to total
        """
        allocated_total = sum(exact_allocations.values())
        if allocated_total != total_paise:
            raise ValueError(
                f"Exact allocations sum to {allocated_total} paise, "
                f"but total is {total_paise} paise"
            )
        
        allocations = [
            SplitAllocation(user_id=user_id, amount_paise=amount)
            for user_id, amount in exact_allocations.items()
        ]
        
        return SplitResult(
            total_amount_paise=total_paise,
            method=SplitMethod.EXACT,
            allocations=allocations,
            reconciliation_note="Exact split (no adjustment needed)",
        )

    @staticmethod
    def split_percentage(
        total_paise: int,
        percentages: Dict[str, float],
    ) -> SplitResult:
        """
        Split using percentages.
        
        Args:
            total_paise: Total amount
            percentages: {user_id: percentage (0-100)}
            
        Returns:
            SplitResult
            
        Raises:
            ValueError: If percentages don't sum to 100
        """
        total_percentage = sum(percentages.values())
        if abs(total_percentage - 100.0) > 0.01:  # Small float tolerance
            raise ValueError(f"Percentages sum to {total_percentage}, not 100")
        
        allocations = []
        total_allocated = 0
        remainder = 0
        
        sorted_users = sorted(percentages.keys())  # Deterministic order
        
        for user_id in sorted_users:
            percentage = percentages[user_id]
            amount = int((total_paise * percentage) / 100)
            allocations.append(SplitAllocation(user_id=user_id, amount_paise=amount))
            total_allocated += amount
        
        # Assign remainder to first user (deterministic)
        remainder = total_paise - total_allocated
        if remainder > 0 and allocations:
            allocations[0].amount_paise += remainder
        
        # Verify reconciliation
        total_final = sum(a.amount_paise for a in allocations)
        assert total_final == total_paise, \
            f"Reconciliation failed: {total_final} vs {total_paise}"
        
        return SplitResult(
            total_amount_paise=total_paise,
            method=SplitMethod.PERCENTAGE,
            allocations=allocations,
            reconciliation_note=f"Percentage split, {remainder} paise remainder assigned to first participant"
            if remainder > 0 else "Percentage split (exact)",
        )

    @staticmethod
    def calculate_balances(expenses: List[Dict]) -> Dict[str, int]:
        """
        Calculate net balance for each user across all expenses.
        
        Args:
            expenses: List of expense dicts with payer, participants, amount
            
        Returns:
            {user_id: net_balance_paise} (negative = owes, positive = owed)
        """
        balances: Dict[str, int] = {}
        
        for expense in expenses:
            payer_id = expense["payer_id"]
            allocations = expense["allocations"]  # List of {"user_id": id, "amount_paise": amt}
            
            if payer_id not in balances:
                balances[payer_id] = 0
            
            total_expense = sum(a["amount_paise"] for a in allocations)
            balances[payer_id] += total_expense
            
            for alloc in allocations:
                user_id = alloc["user_id"]
                amount = alloc["amount_paise"]
                if user_id not in balances:
                    balances[user_id] = 0
                balances[user_id] -= amount
        
        return balances

    @staticmethod
    def get_balance_explanation(
        user_id: str,
        balances: Dict[str, int],
        expenses: List[Dict],
    ) -> str:
        """
        Generate a human-readable explanation of a user's balance.
        
        Args:
            user_id: User to explain
            balances: Result from calculate_balances
            expenses: Original expenses list
            
        Returns:
            Explanation string
        """
        net = balances.get(user_id, 0)
        
        paid = 0
        owed = 0
        
        for expense in expenses:
            if expense["payer_id"] == user_id:
                paid += sum(a["amount_paise"] for a in expense["allocations"])
            
            for alloc in expense["allocations"]:
                if alloc["user_id"] == user_id:
                    owed += alloc["amount_paise"]
        
        if net > 0:
            return f"User {user_id}: owed ₹{net/100:.2f} (paid ₹{paid/100:.2f}, owes ₹{owed/100:.2f})"
        elif net < 0:
            return f"User {user_id}: owes ₹{abs(net)/100:.2f} (paid ₹{paid/100:.2f}, owes ₹{owed/100:.2f})"
        else:
            return f"User {user_id}: balanced (paid ₹{paid/100:.2f}, owes ₹{owed/100:.2f})"


# Test the engine
if __name__ == "__main__":
    # Evaluation benchmark (Room 302 scenario)
    print("=== RoomieOps Finance Engine Test ===\n")
    
    # Test 1: Equal split
    result = FinanceEngine.split_equal(
        total_paise=240000,  # ₹2400
        participant_ids=["user1", "user2", "user3", "user4"],
    )
    print(f"Test 1: Equal split of ₹2400 among 4 users")
    for alloc in result.allocations:
        print(f"  {alloc.user_id}: ₹{alloc.amount_paise/100:.2f}")
    print(f"  {result.reconciliation_note}\n")
    
    # Test 2: Balance calculation
    expenses = [
        {
            "payer_id": "user1",
            "allocations": [
                {"user_id": "user1", "amount_paise": 60000},
                {"user_id": "user2", "amount_paise": 60000},
                {"user_id": "user3", "amount_paise": 60000},
                {"user_id": "user4", "amount_paise": 60000},
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
    print("Test 2: Balance calculation")
    for user_id in sorted(balances.keys()):
        print(f"  {FinanceEngine.get_balance_explanation(user_id, balances, expenses)}")
    
    # Verify sum = 0
    total = sum(balances.values())
    print(f"\n  Total balance (should be 0): {total} paise")
    assert total == 0, "Balances don't reconcile!"
    print("  ✓ Balances reconciled")
