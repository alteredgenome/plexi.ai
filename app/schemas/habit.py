import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional

class HabitBase(BaseModel):
    title: str
    description: Optional[str] = None
    duration_minutes: int = 30
    target_time_window: str = "morning" # morning, afternoon, evening, anytime
    days_of_week: str = "mon,tue,wed,thu,fri,sat,sun"
    defense_strictness: str = "protected" # flexible, protected, lock

class HabitCreate(HabitBase):
    pass

class HabitUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    duration_minutes: Optional[int] = None
    target_time_window: Optional[str] = None
    days_of_week: Optional[str] = None
    defense_strictness: Optional[str] = None
    last_completed_at: Optional[datetime.datetime] = None

class HabitRead(HabitBase):
    id: int
    user_id: int
    last_completed_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)
