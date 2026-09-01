import datetime
from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Optional

class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    timezone: str = "UTC"
    work_start_hour: int = 9
    work_end_hour: int = 18
    daily_capacity_minutes: int = 480

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    timezone: Optional[str] = None
    work_start_hour: Optional[int] = None
    work_end_hour: Optional[int] = None
    daily_capacity_minutes: Optional[int] = None

class UserRead(UserBase):
    id: int
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserRead

class TokenData(BaseModel):
    user_id: Optional[int] = None
