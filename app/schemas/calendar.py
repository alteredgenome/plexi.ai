import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional, List

class CalendarBase(BaseModel):
    name: str
    color: str = "#4F46E5"
    visibility: str = "full" # full, private_masked, public
    is_default: bool = False

class CalendarCreate(CalendarBase):
    pass

class CalendarRead(CalendarBase):
    id: int
    user_id: int
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)

class EventBase(BaseModel):
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: datetime.datetime
    end_time: datetime.datetime
    is_all_day: bool = False
    travel_buffer_before_minutes: int = 0
    recovery_buffer_after_minutes: int = 0
    is_recurring: bool = False
    rrule: Optional[str] = None

class EventCreate(EventBase):
    calendar_id: int

class EventUpdate(BaseModel):
    calendar_id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: Optional[datetime.datetime] = None
    end_time: Optional[datetime.datetime] = None
    is_all_day: Optional[bool] = None
    travel_buffer_before_minutes: Optional[int] = None
    recovery_buffer_after_minutes: Optional[int] = None

class EventRead(EventBase):
    id: int
    calendar_id: int
    user_id: int
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)

class MaskedEventRead(BaseModel):
    id: int
    calendar_id: int
    user_id: int
    title: str = "Busy"
    start_time: datetime.datetime
    end_time: datetime.datetime
    is_all_day: bool = False
    travel_buffer_before_minutes: int = 0
    recovery_buffer_after_minutes: int = 0
    is_masked: bool = True
