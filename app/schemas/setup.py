from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, Dict, Any

class SetupStatus(BaseModel):
    is_setup_completed: bool
    instance_name: str = "Plexi"
    version: str = "1.0.0"
    admin_exists: bool

class SetupWizardRequest(BaseModel):
    admin_email: str
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

    @field_validator("admin_email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not v or "@" not in v:
            raise ValueError("Please provide a valid email address.")
        return v

    @field_validator("admin_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Administrator name cannot be empty.")
        return v

    @field_validator("admin_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters long.")
        return v

class SetupWizardResponse(BaseModel):
    status: str
    message: str
    access_token: str
    user_id: int
    redirect_url: str = "/"
