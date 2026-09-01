import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, Float, DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from app.db.session import Base

class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String(128), primary_key=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)
    timezone = Column(String(64), default="UTC")
    work_start_hour = Column(Integer, default=9)
    work_end_hour = Column(Integer, default=18)
    daily_capacity_minutes = Column(Integer, default=480)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    calendars = relationship("Calendar", back_populates="user", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    habits = relationship("Habit", back_populates="user", cascade="all, delete-orphan")
    biometrics = relationship("BiometricLog", back_populates="user", cascade="all, delete-orphan")
    integrations = relationship("IntegrationCredential", back_populates="user", cascade="all, delete-orphan")
    booking_rules = relationship("MeetingBookingRule", back_populates="user", cascade="all, delete-orphan")

class Household(Base):
    __tablename__ = "households"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    members = relationship("HouseholdMember", back_populates="household", cascade="all, delete-orphan")
    ledger_items = relationship("LedgerItem", back_populates="household", cascade="all, delete-orphan")

class HouseholdMember(Base):
    __tablename__ = "household_members"

    id = Column(Integer, primary_key=True, index=True)
    household_id = Column(Integer, ForeignKey("households.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(32), default="member")

    household = relationship("Household", back_populates="members")
    user = relationship("User")

class Calendar(Base):
    __tablename__ = "calendars"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    color = Column(String(32), default="#4F46E5")
    visibility = Column(String(32), default="full") # full, private_masked, public
    is_default = Column(Boolean, default=False)
    
    # External Feed Syncing (Google Calendar, Outlook, iCloud)
    is_synced = Column(Boolean, default=False)
    feed_url = Column(String(1024), nullable=True)
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="calendars")
    events = relationship("Event", back_populates="calendar", cascade="all, delete-orphan")

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    calendar_id = Column(Integer, ForeignKey("calendars.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String(255), nullable=True)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False, index=True)
    is_all_day = Column(Boolean, default=False)
    
    # Dynamic Buffer Windows
    travel_buffer_before_minutes = Column(Integer, default=0)
    recovery_buffer_after_minutes = Column(Integer, default=0)
    
    is_recurring = Column(Boolean, default=False)
    rrule = Column(String(255), nullable=True)
    external_uid = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    calendar = relationship("Calendar", back_populates="events")
    user = relationship("User")

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String(8), default="P3")
    status = Column(String(32), default="todo")
    duration_minutes = Column(Integer, default=30)
    deadline = Column(DateTime, nullable=True)
    
    auto_schedule = Column(Boolean, default=True)
    scheduled_start = Column(DateTime, nullable=True, index=True)
    scheduled_end = Column(DateTime, nullable=True, index=True)
    is_completed = Column(Boolean, default=False)
    
    parent_task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    sop_template = Column(String(255), nullable=True)
    momentum_critical = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="tasks")
    subtasks = relationship("Task", backref="parent_task", remote_side=[id])

class Habit(Base):
    __tablename__ = "habits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    duration_minutes = Column(Integer, default=30)
    target_time_window = Column(String(32), default="morning")
    days_of_week = Column(String(64), default="mon,tue,wed,thu,fri,sat,sun")
    defense_strictness = Column(String(32), default="protected")
    last_completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="habits")

class BiometricLog(Base):
    __tablename__ = "biometric_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(String(10), nullable=False)
    sleep_score = Column(Float, nullable=True)
    readiness_score = Column(Float, nullable=True)
    hrv = Column(Float, nullable=True)
    recovery_status = Column(String(32), default="optimal")
    fatigue_scaling_factor = Column(Float, default=1.0)
    source = Column(String(64), default="ringconn")
    raw_data = Column(JSON, nullable=True)
    recorded_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="biometrics")

class LedgerItem(Base):
    __tablename__ = "ledger_items"

    id = Column(Integer, primary_key=True, index=True)
    household_id = Column(Integer, ForeignKey("households.id"), nullable=False)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    payer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    category = Column(String(64), default="general")
    total_amount = Column(Float, nullable=False)
    currency = Column(String(8), default="USD")
    split_type = Column(String(32), default="equal")
    shares_json = Column(JSON, nullable=True)
    is_settled = Column(Boolean, default=False)
    date = Column(DateTime, default=datetime.datetime.utcnow)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    household = relationship("Household", back_populates="ledger_items")
    creator = relationship("User", foreign_keys=[creator_id])
    payer = relationship("User", foreign_keys=[payer_id])

class IntegrationCredential(Base):
    __tablename__ = "integration_credentials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider = Column(String(64), nullable=False)
    credentials_json = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="integrations")

class MeetingBookingRule(Base):
    __tablename__ = "meeting_booking_rules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    slug = Column(String(128), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    duration_minutes = Column(Integer, default=30)
    buffer_before = Column(Integer, default=10)
    buffer_after = Column(Integer, default=10)
    max_bookings_per_day = Column(Integer, default=6)
    availability_days_json = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)

    user = relationship("User", back_populates="booking_rules")
