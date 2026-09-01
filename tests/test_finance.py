import pytest
from app.services.finance import FinanceEngine

def test_equal_split_calculation():
    shares = FinanceEngine.calculate_item_shares(
        total_amount=100.0,
        payer_id=1,
        member_ids=[1, 2, 3],
        split_type="equal"
    )
    assert len(shares) == 3
    assert shares[1] == 33.33
    assert shares[2] == 33.33
    assert shares[3] == 33.34 # Check rounding conservation
    assert sum(shares.values()) == 100.0

def test_custom_ratio_split():
    shares = FinanceEngine.calculate_item_shares(
        total_amount=100.0,
        payer_id=1,
        member_ids=[1, 2],
        split_type="custom_ratio",
        custom_shares={"1": 60.0, "2": 40.0}
    )
    assert shares[1] == 60.0
    assert shares[2] == 40.0

def test_debt_simplification_matrix():
    members = [
        {"id": 1, "full_name": "Alice"},
        {"id": 2, "full_name": "Bob"},
        {"id": 3, "full_name": "Charlie"}
    ]
    # Alice pays $90 for utilities split 3 ways ($30 each)
    # Bob owes Alice $30, Charlie owes Alice $30
    items = [
        {
            "id": 1,
            "total_amount": 90.0,
            "payer_id": 1,
            "split_type": "equal",
            "is_settled": False
        }
    ]

    overview = FinanceEngine.compute_household_balances(members, items)
    assert overview["total_expenses"] == 90.0
    
    balances = {b["user_id"]: b["net_balance"] for b in overview["balances"]}
    assert balances[1] == 60.0 # Alice is owed $60
    assert balances[2] == -30.0 # Bob owes $30
    assert balances[3] == -30.0 # Charlie owes $30

    settlements = overview["suggested_settlements"]
    assert len(settlements) == 2
    for s in settlements:
        assert s["to_user_name"] == "Alice"
        assert s["amount"] == 30.0
