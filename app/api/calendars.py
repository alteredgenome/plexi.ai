import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.session import get_db
from app.db.models import User, Calendar, Event
from app.schemas.calendar import (
    CalendarCreate, CalendarRead, EventCreate, EventRead, EventUpdate
)
from app.api.auth import get_current_user
from app.services.scheduler import DynamicScheduler

router = APIRouter(prefix="/calendars", tags=["Calendars & Events"])

@router.get("/", response_model=List[CalendarRead])
async def list_calendars(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Calendar).where(Calendar.user_id == current_user.id))
    return result.scalars().all()

@router.post("/", response_model=CalendarRead)
async def create_calendar(cal_in: CalendarCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    calendar = Calendar(
        user_id=current_user.id,
        name=cal_in.name,
        color=cal_in.color,
        visibility=cal_in.visibility,
        is_default=cal_in.is_default
    )
    db.add(calendar)
    await db.commit()
    await db.refresh(calendar)
    return calendar

@router.get("/events", response_model=List[EventRead])
async def list_user_events(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Event).where(Event.user_id == current_user.id)
    if start_date:
        s_dt = datetime.datetime.fromisoformat(start_date)
        query = query.where(Event.start_time >= s_dt)
    if end_date:
        e_dt = datetime.datetime.fromisoformat(end_date)
        query = query.where(Event.end_time <= e_dt)

    result = await db.execute(query.order_by(Event.start_time))
    return result.scalars().all()

@router.post("/events", response_model=EventRead)
async def create_event(
    ev_in: EventCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify calendar ownership
    cal_res = await db.execute(select(Calendar).where(Calendar.id == ev_in.calendar_id, Calendar.user_id == current_user.id))
    calendar = cal_res.scalars().first()
    if not calendar:
        raise HTTPException(status_code=404, detail="Calendar not found")

    event = Event(
        calendar_id=ev_in.calendar_id,
        user_id=current_user.id,
        title=ev_in.title,
        description=ev_in.description,
        location=ev_in.location,
        start_time=ev_in.start_time,
        end_time=ev_in.end_time,
        is_all_day=ev_in.is_all_day,
        travel_buffer_before_minutes=ev_in.travel_buffer_before_minutes,
        recovery_buffer_after_minutes=ev_in.recovery_buffer_after_minutes,
        is_recurring=ev_in.is_recurring,
        rrule=ev_in.rrule
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event

@router.delete("/events/{event_id}")
async def delete_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Event).where(Event.id == event_id, Event.user_id == current_user.id))
    event = result.scalars().first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    await db.delete(event)
    await db.commit()
    return {"status": "deleted", "id": event_id}

@router.get("/shared-view")
async def get_shared_calendar_view(
    target_user_id: int = Query(...),
    start_date: str = Query(...),
    end_date: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns events for a partner or roommate, masking private events with 'Busy' tags.
    """
    s_dt = datetime.datetime.fromisoformat(start_date)
    e_dt = datetime.datetime.fromisoformat(end_date)

    query = select(Event, Calendar.visibility).join(Calendar, Event.calendar_id == Calendar.id).where(
        Event.user_id == target_user_id,
        Event.start_time >= s_dt,
        Event.end_time <= e_dt
    )
    result = await db.execute(query)
    raw_events = []
    for ev, vis in result.all():
        raw_events.append({
            "id": ev.id,
            "calendar_id": ev.calendar_id,
            "user_id": ev.user_id,
            "title": ev.title,
            "description": ev.description,
            "location": ev.location,
            "start_time": ev.start_time.isoformat(),
            "end_time": ev.end_time.isoformat(),
            "is_all_day": ev.is_all_day,
            "visibility": vis
        })

    masked_events = DynamicScheduler.mask_private_events(raw_events, current_user.id)
    return {"user_id": target_user_id, "events": masked_events}
