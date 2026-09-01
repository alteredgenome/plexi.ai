import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.db.session import get_db
from app.db.models import User, Task, Event, Calendar, IntegrationCredential, BiometricLog, LedgerItem, HouseholdMember
from app.api.auth import get_current_user
from app.services.agent import OpenRouterAgent
from app.services.scheduler import DynamicScheduler
from app.services.integrations.home_assistant import HomeAssistantClient
from app.services.integrations.pavlok import PavlokClient
from app.services.integrations.ringconn import RingConnService
from app.config import settings

router = APIRouter(prefix="/agent", tags=["OpenRouter Agent & AI Operations"])

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None

@router.post("/chat")
async def chat_with_assistant(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Direct conversational interface with OpenRouter LLM and real tool calling execution.
    """
    # 1. Fetch OpenRouter credentials from DB or config
    res = await db.execute(
        select(IntegrationCredential).where(
            IntegrationCredential.user_id == current_user.id,
            IntegrationCredential.provider == "openrouter"
        )
    )
    cred = res.scalars().first()
    
    api_key = None
    model_name = request.model or settings.OPENROUTER_MODEL

    if cred and cred.credentials_json:
        api_key = cred.credentials_json.get("api_key")
        model_name = request.model or cred.credentials_json.get("model") or model_name

    agent = OpenRouterAgent(api_key=api_key, model=model_name)

    # 2. Define concrete tool handlers connected to live DB models
    async def create_task_handler(title: str, priority: str = "P3", duration_minutes: int = 30, momentum_critical: bool = False):
        new_task = Task(
            user_id=current_user.id,
            title=title,
            priority=priority,
            duration_minutes=duration_minutes,
            momentum_critical=momentum_critical
        )
        db.add(new_task)
        await db.commit()
        await db.refresh(new_task)
        return {"status": "created", "task_id": new_task.id, "title": new_task.title, "priority": priority}

    async def auto_schedule_handler(target_date: Optional[str] = None):
        target = target_date or datetime.datetime.utcnow().strftime("%Y-%m-%d")
        t_start = datetime.datetime.strptime(target, "%Y-%m-%d")
        t_end = t_start + datetime.timedelta(days=1)

        # Get events and pending tasks
        ev_res = await db.execute(
            select(Event).where(Event.user_id == current_user.id, Event.start_time >= t_start, Event.start_time < t_end)
        )
        events = ev_res.scalars().all()

        task_res = await db.execute(
            select(Task).where(Task.user_id == current_user.id, Task.is_completed == False)
        )
        tasks = task_res.scalars().all()

        # Get RingConn readiness scaling
        bio_res = await db.execute(
            select(BiometricLog).where(BiometricLog.user_id == current_user.id, BiometricLog.date == target)
        )
        bio = bio_res.scalars().first()
        factor = bio.fatigue_scaling_factor if bio else 1.0

        ev_dicts = [{
            "id": e.id,
            "title": e.title,
            "start_time": e.start_time,
            "end_time": e.end_time,
            "travel_buffer_before_minutes": e.travel_buffer_before_minutes,
            "recovery_buffer_after_minutes": e.recovery_buffer_after_minutes
        } for e in events]

        task_dicts = [{
            "id": t.id,
            "title": t.title,
            "priority": t.priority,
            "duration_minutes": t.duration_minutes
        } for t in tasks]

        scheduled = DynamicScheduler.auto_schedule_tasks(
            events=ev_dicts,
            tasks=task_dicts,
            work_start_hour=current_user.work_start_hour or 9,
            work_end_hour=current_user.work_end_hour or 18,
            target_date=t_start,
            daily_capacity_minutes=int((current_user.daily_capacity_minutes or 480) * factor)
        )

        for item in scheduled:
            t_obj = await db.get(Task, item["task_id"])
            if t_obj:
                t_obj.scheduled_start = item["scheduled_start"]
                t_obj.scheduled_end = item["scheduled_end"]

        await db.commit()
        return {"status": "success", "tasks_scheduled_count": len(scheduled)}

    async def trigger_scene_handler(scene_name: str):
        # Fetch user's HA credentials if available
        ha_res = await db.execute(
            select(IntegrationCredential).where(
                IntegrationCredential.user_id == current_user.id,
                IntegrationCredential.provider == "home_assistant"
            )
        )
        ha_cred = ha_res.scalars().first()
        base_url = ha_cred.credentials_json.get("base_url") if ha_cred else None
        token = ha_cred.credentials_json.get("token") if ha_cred else None

        client = HomeAssistantClient(base_url=base_url, token=token)
        return await client.trigger_scene(scene_name)

    async def send_pavlok_handler(stimulus_type: str, intensity: int = 50, reason: str = "Assistant alert"):
        pvk_res = await db.execute(
            select(IntegrationCredential).where(
                IntegrationCredential.user_id == current_user.id,
                IntegrationCredential.provider == "pavlok"
            )
        )
        pvk_cred = pvk_res.scalars().first()
        api_key = pvk_cred.credentials_json.get("api_key") if pvk_cred else None

        client = PavlokClient(api_key=api_key)
        return await client.send_nudge(stimulus_type=stimulus_type, intensity=intensity, reason=reason)

    async def get_biometrics_handler():
        today_str = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        bio_res = await db.execute(
            select(BiometricLog).where(BiometricLog.user_id == current_user.id, BiometricLog.date == today_str)
        )
        bio = bio_res.scalars().first()
        if bio:
            return {
                "readiness_score": bio.readiness_score,
                "sleep_score": bio.sleep_score,
                "recovery_status": bio.recovery_status,
                "fatigue_scaling_factor": bio.fatigue_scaling_factor,
                "adjusted_capacity_minutes": int((current_user.daily_capacity_minutes or 480) * bio.fatigue_scaling_factor)
            }
        return {
            "readiness_score": 90.0,
            "sleep_score": 85.0,
            "recovery_status": "optimal",
            "fatigue_scaling_factor": 1.0,
            "adjusted_capacity_minutes": current_user.daily_capacity_minutes or 480
        }

    async def log_expense_handler(title: str, total_amount: float, category: str = "general", split_type: str = "equal"):
        # Get user's first household
        hh_member_res = await db.execute(
            select(HouseholdMember).where(HouseholdMember.user_id == current_user.id)
        )
        member = hh_member_res.scalars().first()
        hh_id = member.household_id if member else 1

        ledger_item = LedgerItem(
            household_id=hh_id,
            creator_id=current_user.id,
            payer_id=current_user.id,
            title=title,
            category=category,
            total_amount=total_amount,
            split_type=split_type
        )
        db.add(ledger_item)
        await db.commit()
        return {"status": "logged", "title": title, "amount": total_amount, "household_id": hh_id}

    async def get_team_capacity_handler():
        users_res = await db.execute(select(User).options(selectinload(User.tasks), selectinload(User.biometrics)))
        users = users_res.scalars().all()
        team_out = []
        for u in users:
            sched = sum(t.duration_minutes for t in u.tasks if not t.is_completed and t.duration_minutes)
            cap = u.daily_capacity_minutes or 480
            util = (sched / cap) * 100 if cap > 0 else 0
            risk = "overloaded" if util > 120 else ("high" if util > 90 else ("moderate" if util > 50 else "low"))
            team_out.append({
                "user_id": u.id,
                "full_name": u.full_name,
                "role": u.role,
                "department": u.department,
                "scheduled_minutes": sched,
                "daily_capacity_minutes": cap,
                "utilization_percentage": round(util, 1),
                "burnout_risk": risk
            })
        return team_out

    async def list_today_events_handler():
        today_str = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        t_start = datetime.datetime.strptime(today_str, "%Y-%m-%d")
        t_end = t_start + datetime.timedelta(days=1)
        ev_res = await db.execute(
            select(Event).where(Event.user_id == current_user.id, Event.start_time >= t_start, Event.start_time < t_end)
        )
        events = ev_res.scalars().all()
        return [{
            "id": e.id,
            "title": e.title,
            "start": e.start_time.strftime("%H:%M"),
            "end": e.end_time.strftime("%H:%M"),
            "travel_buffer": e.travel_buffer_before_minutes,
            "recovery_buffer": e.recovery_buffer_after_minutes
        } for e in events]

    tool_handlers = {
        "create_task": create_task_handler,
        "auto_schedule_day": auto_schedule_handler,
        "trigger_home_scene": trigger_scene_handler,
        "send_pavlok_alert": send_pavlok_handler,
        "get_biometric_readiness": get_biometrics_handler,
        "log_shared_expense": log_expense_handler,
        "get_team_capacity": get_team_capacity_handler,
        "list_today_events": list_today_events_handler
    }

    messages_payload = [{"role": m.role, "content": m.content} for m in request.messages]
    response = await agent.chat(messages_payload, tool_handlers=tool_handlers)
    return response

@router.post("/decompose")
async def decompose_task_endpoint(
    payload: Dict[str, str],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Decomposes a project into actionable subtasks with SOP steps.
    """
    desc = payload.get("task_description", "")
    agent = OpenRouterAgent()
    subtasks = await agent.decompose_task(desc)

    created = []
    for st in subtasks:
        task = Task(
            user_id=current_user.id,
            title=st["title"],
            duration_minutes=st["duration_minutes"],
            priority=st.get("priority", "P2"),
            sop_template=st.get("sop", "")
        )
        db.add(task)
        created.append(task)

    await db.commit()
    return {"status": "success", "subtasks_created": len(created)}
