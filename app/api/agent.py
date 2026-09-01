from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.db.models import User, Task
from app.api.auth import get_current_user
from app.services.agent import OpenRouterAgent
from app.services.integrations.home_assistant import HomeAssistantClient
from app.services.integrations.pavlok import PavlokClient

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
    agent = OpenRouterAgent(model=request.model)

    # Define concrete tool handlers to execute in DB/environment
    async def create_task_handler(title: str, priority: str = "P3", duration_minutes: int = 30, deadline: str = None, momentum_critical: bool = False):
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
        return {"status": "created", "task_id": new_task.id, "title": new_task.title}

    async def trigger_scene_handler(scene_name: str):
        client = HomeAssistantClient()
        return await client.trigger_scene(scene_name)

    async def send_pavlok_handler(stimulus_type: str, intensity: int = 50, reason: str = "Momentum alert"):
        client = PavlokClient()
        return await client.send_nudge(stimulus_type=stimulus_type, intensity=intensity, reason=reason)

    tool_handlers = {
        "create_task": create_task_handler,
        "trigger_home_scene": trigger_scene_handler,
        "send_pavlok_alert": send_pavlok_handler
    }

    messages_payload = [{"role": m.role, "content": m.content} for m in request.messages]
    response = await agent.chat(messages_payload, tool_handlers=tool_handlers)
    return response
