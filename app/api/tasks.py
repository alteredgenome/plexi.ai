import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.session import get_db
from app.db.models import User, Task, Event, Habit, BiometricLog
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate, TaskDecomposeRequest
from app.api.auth import get_current_user
from app.services.scheduler import DynamicScheduler
from app.services.agent import OpenRouterAgent

router = APIRouter(prefix="/tasks", tags=["Tasks & Workflows"])

@router.get("/", response_model=List[TaskRead])
async def list_tasks(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Task).where(Task.user_id == current_user.id)
    if status:
        query = query.where(Task.status == status)
    if priority:
        query = query.where(Task.priority == priority)
    
    result = await db.execute(query.order_by(Task.created_at.desc()))
    return result.scalars().all()

@router.post("/", response_model=TaskRead)
async def create_task(
    task_in: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    task = Task(
        user_id=current_user.id,
        title=task_in.title,
        description=task_in.description,
        priority=task_in.priority,
        duration_minutes=task_in.duration_minutes,
        deadline=task_in.deadline,
        auto_schedule=task_in.auto_schedule,
        parent_task_id=task_in.parent_task_id,
        sop_template=task_in.sop_template,
        momentum_critical=task_in.momentum_critical
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task

@router.patch("/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: int,
    task_in: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Task).where(Task.id == task_id, Task.user_id == current_user.id))
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = task_in.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(task, field, val)

    if task.is_completed:
        task.status = "completed"

    await db.commit()
    await db.refresh(task)
    return task

@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Task).where(Task.id == task_id, Task.user_id == current_user.id))
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await db.delete(task)
    await db.commit()
    return {"status": "deleted", "id": task_id}

@router.post("/auto-schedule")
async def run_auto_scheduler(
    target_date: str = Query(..., description="YYYY-MM-DD"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Executes the dynamic scheduling engine:
    1. Fetches events, habits, and active biometric fatigue scaling.
    2. Auto-places tasks into collision-free slots with travel/recovery buffers.
    3. Persists scheduled start and end timestamps.
    """
    t_date = datetime.date.fromisoformat(target_date)
    start_dt = datetime.datetime.combine(t_date, datetime.time.min)
    end_dt = datetime.datetime.combine(t_date, datetime.time.max)

    # 1. Fetch events
    ev_res = await db.execute(select(Event).where(
        Event.user_id == current_user.id,
        Event.start_time >= start_dt,
        Event.end_time <= end_dt
    ))
    raw_events = [
        {
            "id": e.id,
            "title": e.title,
            "start_time": e.start_time,
            "end_time": e.end_time,
            "travel_buffer_before_minutes": e.travel_buffer_before_minutes,
            "recovery_buffer_after_minutes": e.recovery_buffer_after_minutes
        } for e in ev_res.scalars().all()
    ]

    # 2. Fetch habits
    hb_res = await db.execute(select(Habit).where(Habit.user_id == current_user.id))
    raw_habits = [
        {
            "id": h.id,
            "title": h.title,
            "duration_minutes": h.duration_minutes,
            "target_time_window": h.target_time_window,
            "days_of_week": h.days_of_week,
            "defense_strictness": h.defense_strictness
        } for h in hb_res.scalars().all()
    ]

    # 3. Fetch latest biometric log for date
    bio_res = await db.execute(select(BiometricLog).where(
        BiometricLog.user_id == current_user.id,
        BiometricLog.date == target_date
    ))
    bio_log = bio_res.scalars().first()
    fatigue_factor = bio_log.fatigue_scaling_factor if bio_log else 1.0

    # 4. Fetch pending tasks
    task_res = await db.execute(select(Task).where(
        Task.user_id == current_user.id,
        Task.is_completed == False
    ))
    tasks = [
        {
            "id": t.id,
            "title": t.title,
            "priority": t.priority,
            "duration_minutes": t.duration_minutes,
            "deadline": t.deadline,
            "auto_schedule": t.auto_schedule,
            "momentum_critical": t.momentum_critical,
            "is_completed": t.is_completed
        } for t in task_res.scalars().all()
    ]

    scheduler = DynamicScheduler(
        work_start_hour=current_user.work_start_hour,
        work_end_hour=current_user.work_end_hour,
        base_capacity_minutes=current_user.daily_capacity_minutes
    )

    scheduled = scheduler.auto_schedule_tasks(
        tasks=tasks,
        events=raw_events,
        habits=raw_habits,
        target_date=t_date,
        fatigue_scaling_factor=fatigue_factor
    )

    # Persist scheduled slots to database
    for item in scheduled:
        if item.get("schedule_status") == "scheduled":
            t_obj = await db.get(Task, item["id"])
            if t_obj:
                t_obj.scheduled_start = datetime.datetime.fromisoformat(item["scheduled_start"])
                t_obj.scheduled_end = datetime.datetime.fromisoformat(item["scheduled_end"])

    await db.commit()

    return {
        "date": target_date,
        "fatigue_factor_applied": fatigue_factor,
        "tasks_scheduled_count": len([s for s in scheduled if s.get("schedule_status") == "scheduled"]),
        "schedule": scheduled
    }

@router.post("/decompose")
async def decompose_task_workflow(
    request: TaskDecomposeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Decomposes a complex project into subtasks with SOP steps using AI.
    """
    agent = OpenRouterAgent()
    subtasks = await agent.decompose_task(request.task_description)

    # Parent task
    parent = Task(
        user_id=current_user.id,
        title=request.task_description,
        priority="P2",
        duration_minutes=sum(st["duration_minutes"] for st in subtasks),
        sop_template="Auto-Decomposed Workflow"
    )
    db.add(parent)
    await db.flush()

    created_subtasks = []
    for st in subtasks:
        sub = Task(
            user_id=current_user.id,
            title=st["title"],
            priority=st.get("priority", "P3"),
            duration_minutes=st.get("duration_minutes", 30),
            parent_task_id=parent.id,
            sop_template=st.get("sop")
        )
        db.add(sub)
        created_subtasks.append(sub)

    await db.commit()
    await db.refresh(parent)

    return {
        "parent_task": TaskRead.model_validate(parent),
        "subtasks": [TaskRead.model_validate(s) for s in created_subtasks]
    }
