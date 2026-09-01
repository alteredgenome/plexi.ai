from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models import User, Task
from app.schemas.integrations import PavlokNudgeRequest, HomeAssistantSceneTrigger
from app.api.auth import get_current_user
from app.services.integrations.home_assistant import HomeAssistantClient
from app.services.integrations.pavlok import PavlokClient
from app.services.integrations.pixel_watch import PixelWatchService

router = APIRouter(prefix="/integrations", tags=["Hardware & Smart Home Integrations"])

@router.post("/pavlok/nudge")
async def trigger_pavlok_nudge(
    req: PavlokNudgeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Dispatches a haptic vibration, beep, or zap stimulus via Pavlok 3.
    """
    reason = req.reason
    if req.task_id:
        task = await db.get(Task, req.task_id)
        if task:
            reason = f"Momentum overdue: {task.title}"

    client = PavlokClient()
    result = await client.send_nudge(
        stimulus_type=req.stimulus_type,
        intensity=req.intensity,
        reason=reason
    )
    return result

@router.post("/home-assistant/scene")
async def trigger_ha_scene(
    req: HomeAssistantSceneTrigger,
    current_user: User = Depends(get_current_user)
):
    """
    Triggers smart home focus, meeting, or deep work lighting scenes in Home Assistant.
    """
    scene_name = req.scene_id or "focus_time"
    client = HomeAssistantClient()
    result = await client.trigger_scene(scene_name)
    return result

@router.get("/pixel-watch/next-task-notification")
async def get_pixel_watch_notification(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    start_str = task.scheduled_start.strftime("%H:%M") if task.scheduled_start else "Today"
    notification = PixelWatchService.format_task_notification(
        task_title=task.title,
        priority=task.priority,
        start_time=start_str
    )
    return notification
