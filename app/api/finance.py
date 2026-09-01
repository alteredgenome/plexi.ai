import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.session import get_db
from app.db.models import User, Household, HouseholdMember, LedgerItem
from app.schemas.finance import (
    HouseholdCreate, HouseholdRead, LedgerItemCreate, LedgerItemRead, HouseholdFinanceOverview
)
from app.api.auth import get_current_user
from app.services.finance import FinanceEngine

router = APIRouter(prefix="/finance", tags=["Household Finance & Ledger"])

@router.get("/households", response_model=List[HouseholdRead])
async def list_households(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Household).join(HouseholdMember, Household.id == HouseholdMember.household_id).where(
            HouseholdMember.user_id == current_user.id
        )
    )
    return result.scalars().all()

@router.post("/households", response_model=HouseholdRead)
async def create_household(hh_in: HouseholdCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    hh = Household(name=hh_in.name)
    db.add(hh)
    await db.flush()

    member = HouseholdMember(household_id=hh.id, user_id=current_user.id, role="admin")
    db.add(member)
    await db.commit()
    await db.refresh(hh)
    return hh

@router.get("/items", response_model=List[LedgerItemRead])
async def list_ledger_items(
    household_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(LedgerItem).where(LedgerItem.household_id == household_id).order_by(LedgerItem.date.desc())
    )
    return result.scalars().all()

@router.post("/items", response_model=LedgerItemRead)
async def create_ledger_item(
    item_in: LedgerItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    item = LedgerItem(
        household_id=item_in.household_id,
        creator_id=current_user.id,
        payer_id=item_in.payer_id or current_user.id,
        title=item_in.title,
        category=item_in.category,
        total_amount=item_in.total_amount,
        currency=item_in.currency,
        split_type=item_in.split_type,
        shares_json=item_in.shares_json,
        is_settled=item_in.is_settled,
        date=item_in.date or datetime.datetime.utcnow()
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item

@router.post("/items/{item_id}/settle")
async def settle_ledger_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(LedgerItem).where(LedgerItem.id == item_id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Ledger item not found")
    item.is_settled = True
    await db.commit()
    return {"status": "settled", "id": item_id}

@router.get("/overview", response_model=HouseholdFinanceOverview)
async def get_household_finance_overview(
    household_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    hh = await db.get(Household, household_id)
    if not hh:
        raise HTTPException(status_code=404, detail="Household not found")

    members_res = await db.execute(
        select(User).join(HouseholdMember, User.id == HouseholdMember.user_id).where(
            HouseholdMember.household_id == household_id
        )
    )
    members = [{"id": u.id, "full_name": u.full_name} for u in members_res.scalars().all()]

    items_res = await db.execute(
        select(LedgerItem).where(LedgerItem.household_id == household_id)
    )
    raw_items = [
        {
            "id": i.id,
            "total_amount": i.total_amount,
            "payer_id": i.payer_id,
            "split_type": i.split_type,
            "shares_json": i.shares_json,
            "is_settled": i.is_settled
        } for i in items_res.scalars().all()
    ]

    overview = FinanceEngine.compute_household_balances(members, raw_items)
    return {
        "household_id": household_id,
        "household_name": hh.name,
        "total_expenses": overview["total_expenses"],
        "balances": overview["balances"],
        "suggested_settlements": overview["suggested_settlements"]
    }
