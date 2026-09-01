import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional, List

class TaskBase(BaseModel):
    title: str
    description: Optional[str] = None
    priority: str = "P3" # P1, P2, P3, P4
    duration_minutes: int = 30
    deadline: Optional[datetime.datetime] = None
    auto_schedule: bool = True
    parent_task_id: Optional[int] = None
    sop_template: Optional[str] = None
    momentum_critical: bool = False

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    duration_minutes: Optional[int] = None
    deadline: Optional[datetime.datetime] = None
    auto_schedule: Optional[bool] = None
    scheduled_start: Optional[datetime.datetime] = None
    scheduled_end: Optional[datetime.datetime] = None
    is_completed: Optional[bool] = None
    parent_task_id: Optional[int] = None
    sop_template: Optional[str] = None
    momentum_critical: Optional[bool] = None

class TaskRead(TaskBase):
    id: int
    user_id: int
    status: str
    scheduled_start: Optional[datetime.datetime] = None
    scheduled_end: Optional[datetime.datetime] = None
    is_completed: bool
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)

class TaskDecomposeRequest(BaseModel):
    task_description: str
    context: Optional[str] = None
    target_date: Optional[str] = None
