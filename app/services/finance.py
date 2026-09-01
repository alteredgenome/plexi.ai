from typing import List, Dict, Any, Tuple
from collections import defaultdict
import heapq

class FinanceEngine:
    @staticmethod
    def calculate_item_shares(
        total_amount: float,
        payer_id: int,
        member_ids: List[int],
        split_type: str = "equal",
        custom_shares: Dict[str, float] = None
    ) -> Dict[int, float]:
        """
        Calculates how much each member owes for an item.
        Returns a dict mapping user_id -> amount owed.
        """
        shares: Dict[int, float] = {}
        n = len(member_ids)
        if n == 0:
            return {}

        if split_type == "equal" or not custom_shares:
            per_person = round(total_amount / n, 2)
            # Fix rounding drift on the last person
            total_allocated = per_person * (n - 1)
            last_person_share = round(total_amount - total_allocated, 2)
            
            for i, uid in enumerate(member_ids):
                shares[uid] = per_person if i < n - 1 else last_person_share
        elif split_type == "exact":
            for uid_str, amt in custom_shares.items():
                shares[int(uid_str)] = float(amt)
        elif split_type == "custom_ratio":
            # custom_shares holds ratios/weights
            total_ratio = sum(custom_shares.values())
            if total_ratio <= 0:
                total_ratio = 1.0
            running_sum = 0.0
            for i, uid in enumerate(member_ids):
                weight = custom_shares.get(str(uid), 0.0)
                if i == n - 1:
                    shares[uid] = round(total_amount - running_sum, 2)
                else:
                    amt = round(total_amount * (weight / total_ratio), 2)
                    shares[uid] = amt
                    running_sum += amt

        return shares

    @staticmethod
    def compute_household_balances(
        members: List[Dict[str, Any]], # [{"id": 1, "name": "Alice"}, ...]
        ledger_items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Computes net balances and simplifies debt settlements across household members.
        """
        user_names = {m["id"]: m.get("full_name", f"User {m['id']}") for m in members}
        net_balances = defaultdict(float) # user_id -> balance (positive = owed money, negative = owes money)

        for item in ledger_items:
            if item.get("is_settled", False):
                continue

            total = float(item.get("total_amount", 0.0))
            payer_id = item.get("payer_id")
            split_type = item.get("split_type", "equal")
            shares_json = item.get("shares_json") or {}

            # The payer paid the entire total upfront (+total)
            net_balances[payer_id] += total

            # Compute individual obligations
            all_uids = list(user_names.keys())
            shares = FinanceEngine.calculate_item_shares(
                total_amount=total,
                payer_id=payer_id,
                member_ids=all_uids,
                split_type=split_type,
                custom_shares=shares_json
            )

            for uid, owed_amt in shares.items():
                net_balances[uid] -= owed_amt

        balance_summaries = []
        for uid, name in user_names.items():
            bal = round(net_balances[uid], 2)
            balance_summaries.append({
                "user_id": uid,
                "user_name": name,
                "net_balance": bal
            })

        # Simplify Debt Settlements using Greedy Min/Max Heuristic
        suggested_settlements = FinanceEngine.simplify_debts(net_balances, user_names)

        total_expenses = sum(float(i.get("total_amount", 0.0)) for i in ledger_items if not i.get("is_settled", False))

        return {
            "total_expenses": round(total_expenses, 2),
            "balances": balance_summaries,
            "suggested_settlements": suggested_settlements
        }

    @staticmethod
    def simplify_debts(
        net_balances: Dict[int, float],
        user_names: Dict[int, str]
    ) -> List[Dict[str, Any]]:
        """
        Simplifies debts to minimize the number of cash transactions between roommates.
        """
        # Debtors owe money (balance < 0), Creditors are owed money (balance > 0)
        debtors = [] # max heap for largest debt (stored as negative for Python min-heap)
        creditors = [] # max heap for largest credit

        for uid, bal in net_balances.items():
            bal_rounded = round(bal, 2)
            if bal_rounded < -0.01:
                # uid owes abs(bal_rounded)
                heapq.heappush(debtors, (bal_rounded, uid)) # bal_rounded is negative
            elif bal_rounded > 0.01:
                # uid is owed bal_rounded
                heapq.heappush(creditors, (-bal_rounded, uid))

        settlements = []

        while debtors and creditors:
            debt_val, debtor_id = heapq.heappop(debtors)
            credit_val, creditor_id = heapq.heappop(creditors)

            debt_amt = abs(debt_val)
            credit_amt = abs(credit_val)

            settle_amt = min(debt_amt, credit_amt)
            if settle_amt > 0.01:
                settlements.append({
                    "from_user_id": debtor_id,
                    "from_user_name": user_names.get(debtor_id, f"User {debtor_id}"),
                    "to_user_id": creditor_id,
                    "to_user_name": user_names.get(creditor_id, f"User {creditor_id}"),
                    "amount": round(settle_amt, 2)
                })

            remaining_debt = debt_amt - settle_amt
            remaining_credit = credit_amt - settle_amt

            if remaining_debt > 0.01:
                heapq.heappush(debtors, (-remaining_debt, debtor_id))
            if remaining_credit > 0.01:
                heapq.heappush(creditors, (-remaining_credit, creditor_id))

        return settlements
