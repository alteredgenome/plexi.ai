import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, List

class HouseholdBase(BaseModel):
    name: str

class HouseholdCreate(HouseholdBase):
    pass

class HouseholdRead(HouseholdBase):
    id: int
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)

class LedgerItemBase(BaseModel):
    household_id: int
    payer_id: int
    title: str
    category: str = "general"
    total_amount: float
    currency: str = "USD"
    split_type: str = "equal" # equal, custom_ratio, exact
    shares_json: Optional[Dict[str, float]] = None # {"user_id": amount}
    is_settled: bool = False
    date: Optional[datetime.datetime] = None

class LedgerItemCreate(LedgerItemBase):
    pass

class LedgerItemRead(LedgerItemBase):
    id: int
    creator_id: int
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)

class BalanceSummary(BaseModel):
    user_id: int
    user_name: str
    net_balance: float # positive means they are owed money, negative means they owe

class SettlementTransaction(BaseModel):
    from_user_id: int
    from_user_name: str
    to_user_id: int
    to_user_name: str
    amount: float

class HouseholdFinanceOverview(BaseModel):
    household_id: int
    household_name: str
    total_expenses: float
    balances: List[BalanceSummary]
    suggested_settlements: List[SettlementTransaction]
