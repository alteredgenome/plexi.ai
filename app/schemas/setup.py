from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Optional, Dict, Any

class SetupStatus(BaseModel):
    is_setup_completed: bool
    instance_name: str = "Plexi"
    version: str = "1.0.0"
    admin_exists: bool

class SetupWizardRequest(BaseModel):
    admin_email: EmailStr
    admin_password: str
    admin_name: str
    timezone: str = "America/New_York"
    work_start_hour: int = 9
    work_end_hour: int = 18
    daily_capacity_minutes: int = 480
    
    # Optional LLM Config
    openrouter_api_key: Optional[str] = None
    openrouter_model: Optional[str] = "google/gemma-2-9b-it:free"
    
    # Optional Smart Home Config
    home_assistant_url: Optional[str] = None
    home_assistant_token: Optional[str] = None
    
    # Optional Pavlok Config
    pavlok_api_key: Optional[str] = None

class SetupWizardResponse(BaseModel):
    status: str
    message: str
    access_token: str
    user_id: int
    redirect_url: str = "/"
