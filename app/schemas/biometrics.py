import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional, Any, Dict

class BiometricLogBase(BaseModel):
    date: str # YYYY-MM-DD
    sleep_score: Optional[float] = None
    readiness_score: Optional[float] = None
    hrv: Optional[float] = None
    recovery_status: str = "optimal"
    fatigue_scaling_factor: float = 1.0
    source: str = "ringconn"
    raw_data: Optional[Dict[str, Any]] = None

class BiometricLogCreate(BiometricLogBase):
    pass

class BiometricLogRead(BiometricLogBase):
    id: int
    user_id: int
    recorded_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)

class CapacityEvaluationResponse(BaseModel):
    date: str
    readiness_score: float
    recovery_status: str
    fatigue_scaling_factor: float
    base_capacity_minutes: int
    adjusted_capacity_minutes: int
    recommendation: str
