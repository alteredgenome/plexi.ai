import datetime
from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, List, Dict, Any

class AdminUserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    role: str = "member" # superadmin, admin, manager, member
    department: str = "Operations"
    timezone: str = "America/New_York"
    work_start_hour: int = 9
    work_end_hour: int = 18
    daily_capacity_minutes: int = 480

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not v or "@" not in v:
            raise ValueError("Please provide a valid email address.")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters.")
        return v

class AdminUserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None # active, suspended
    department: Optional[str] = None
    timezone: Optional[str] = None
    work_start_hour: Optional[int] = None
    work_end_hour: Optional[int] = None
    daily_capacity_minutes: Optional[int] = None

class AdminPasswordReset(BaseModel):
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters.")
        return v

class ConnectedDeviceSummary(BaseModel):
    id: int
    provider: str # pavlok, ringconn, home_assistant
    device_name: Optional[str] = None
    device_id: Optional[str] = None
    is_active: bool
    created_at: datetime.datetime
    model_config = ConfigDict(from_attributes=True)

class AdminUserDetail(BaseModel):
    id: int
    email: str
    full_name: str
    is_admin: bool
    role: str
    status: str
    department: str
    timezone: str
    work_start_hour: int
    work_end_hour: int
    daily_capacity_minutes: int
    devices: List[ConnectedDeviceSummary] = []
    created_at: datetime.datetime
    model_config = ConfigDict(from_attributes=True)

class DeviceAssignRequest(BaseModel):
    user_id: int
    provider: str # pavlok, ringconn, home_assistant
    device_name: str = "Default Device"
    device_id: Optional[str] = None
    credentials: Dict[str, Any] # e.g. {"api_key": "...", "auth_token": "...", "base_url": "..."}

class DeviceTestRequest(BaseModel):
    user_id: int
    provider: str
    stimulus_type: Optional[str] = "vibration" # for pavlok: vibration, beep, shock
    intensity: Optional[int] = 50

class TeamCapacityMember(BaseModel):
    user_id: int
    full_name: str
    email: str
    role: str
    department: str
    daily_capacity_minutes: int
    scheduled_minutes: int
    utilization_percentage: float
    burnout_risk: str # low, moderate, high, overloaded
    readiness_score: Optional[float] = None
    recovery_status: Optional[str] = None
