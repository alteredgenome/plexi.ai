import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any, List

class IntegrationCredentialBase(BaseModel):
    provider: str # home_assistant, pavlok, ringconn, pixel_watch, openrouter
    device_name: Optional[str] = None
    device_id: Optional[str] = None
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
    stimulus_type: str = "vibration" # beep, vibration, shock
    intensity: int = 50 # 1 - 100

class HomeAssistantSceneTrigger(BaseModel):
    scene_id: Optional[str] = None # e.g. "focus_time", "deep_work", "meeting", "relax"
    state: str = "active" # active, idle
    entity_id: Optional[str] = None

class HomeAssistantConfigRequest(BaseModel):
    base_url: str = "http://homeassistant.local:8123"
    token: str
    focus_scene: Optional[str] = "scene.focus_time"
    relax_scene: Optional[str] = "scene.relax"

class PavlokConfigRequest(BaseModel):
    api_key: str
    device_id: Optional[str] = None
    default_stimulus: Optional[str] = "vibration"
    default_intensity: Optional[int] = 50
    overdue_threshold_minutes: Optional[int] = 15

class RingConnConfigRequest(BaseModel):
    account_token: str
    device_id: Optional[str] = None
    auto_scale_capacity: bool = True
