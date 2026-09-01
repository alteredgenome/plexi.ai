import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any, List

class IntegrationCredentialBase(BaseModel):
    provider: str # home_assistant, pavlok, ringconn, pixel_watch
    credentials_json: Dict[str, Any]
    is_active: bool = True

class IntegrationCredentialCreate(IntegrationCredentialBase):
    pass

class IntegrationCredentialRead(IntegrationCredentialBase):
    id: int
    user_id: int
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)

class PavlokNudgeRequest(BaseModel):
    task_id: Optional[int] = None
    reason: str = "Critical task overdue"
    stimulus_type: str = "beep" # beep, vibration, shock
    intensity: int = 50 # 1 - 100

class HomeAssistantSceneTrigger(BaseModel):
    scene_id: Optional[str] = None # e.g. "focus_time", "deep_work", "meeting"
    state: str = "active" # active, idle
    entity_id: Optional[str] = None
