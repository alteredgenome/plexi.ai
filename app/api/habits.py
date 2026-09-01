import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.session import get_db
from app.db.models import User, Habit
from app.schemas.habit import HabitCreate, HabitRead, HabitUpdate
from app.api.auth import get_current_user

router = APIRouter(prefix="/habits", tags=["Habits & Focus Defense"])

@router.get("/", response_model=List[HabitRead])
async def list_habits(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Habit).where(Habit.user_id == current_user.id))
    return result.scalars().all()

@router.post("/", response_model=HabitRead)
async def create_habit(habit_in: HabitCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    habit = Habit(
        user_id=current_user.id,
        title=habit_in.title,
        description=habit_in.description,
        duration_minutes=habit_in.duration_minutes,
        target_time_window=habit_in.target_time_window,
        days_of_week=habit_in.days_of_week,
        defense_strictness=habit_in.defense_strictness
    )
    db.add(habit)
    await db.commit()
    await db.refresh(habit)
    return habit

@router.post("/{habit_id}/complete", response_model=HabitRead)
async def mark_habit_completed(habit_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Habit).where(Habit.id == habit_id, Habit.user_id == current_user.id))
    habit = result.scalars().first()
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")
    habit.last_completed_at = datetime.datetime.utcnow()
    await db.commit()
    await db.refresh(habit)
    return habit

@router.delete("/{habit_id}")
async def delete_habit(habit_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Habit).where(Habit.id == habit_id, Habit.user_id == current_user.id))
    habit = result.scalars().first()
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")
    await db.delete(habit)
    await db.commit()
    return {"status": "deleted", "id": habit_id}
