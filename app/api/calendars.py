import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.session import get_db
from app.db.models import User, Calendar, Event
from app.schemas.calendar import (
    CalendarCreate, CalendarRead, EventCreate, EventRead, EventUpdate,
    CalendarSyncFeedRequest, CalendarImportResponse
)
from app.api.auth import get_current_user
from app.services.scheduler import DynamicScheduler
from app.services.calendar_sync import ICSParser, CalendarFeedSyncService

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

@router.post("/import/ics", response_model=CalendarImportResponse)
async def import_ics_file(
    file: UploadFile = File(...),
    calendar_name: Optional[str] = Form(None),
    calendar_id: Optional[int] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Imports events from a standard .ics / iCalendar file (Google Calendar, Outlook export, or standard .ics).
    """
    content = await file.read()
    ics_text = content.decode("utf-8", errors="ignore")
    parsed_events = ICSParser.parse_ics_content(ics_text)

    target_cal = None
    if calendar_id:
        target_cal = await db.get(Calendar, calendar_id)
    
    if not target_cal:
        cal_name = calendar_name or file.filename.replace(".ics", "") or "Imported Calendar"
        target_cal = Calendar(
            user_id=current_user.id,
            name=cal_name,
            color="#059669",
            visibility="full"
        )
        db.add(target_cal)
        await db.flush()

    for ev in parsed_events:
        new_event = Event(
            calendar_id=target_cal.id,
            user_id=current_user.id,
            title=ev.get("title", "Imported Event"),
            description=ev.get("description"),
            location=ev.get("location"),
            start_time=ev["start_time"],
            end_time=ev["end_time"],
            is_all_day=ev.get("is_all_day", False),
            rrule=ev.get("rrule")
        )
        db.add(new_event)

    await db.commit()
    return {
        "calendar_id": target_cal.id,
        "calendar_name": target_cal.name,
        "events_imported_count": len(parsed_events),
        "status": "success"
    }

@router.post("/sync/feed", response_model=CalendarImportResponse)
async def sync_external_feed(
    req: CalendarSyncFeedRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Subscribes to and imports a live Google Calendar or Outlook iCal feed URL.
    """
    try:
        events = await CalendarFeedSyncService.fetch_feed_events(req.feed_url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch calendar feed: {str(e)}")

    calendar = Calendar(
        user_id=current_user.id,
        name=req.name,
        color=req.color,
        visibility="full",
        is_synced=True,
        feed_url=req.feed_url,
        last_synced_at=datetime.datetime.utcnow()
    )
    db.add(calendar)
    await db.flush()

    for ev in events:
        new_event = Event(
            calendar_id=calendar.id,
            user_id=current_user.id,
            title=ev.get("title", "Synced Event"),
            description=ev.get("description"),
            location=ev.get("location"),
            start_time=ev["start_time"],
            end_time=ev["end_time"],
            is_all_day=ev.get("is_all_day", False),
            rrule=ev.get("rrule")
        )
        db.add(new_event)

    await db.commit()
    return {
        "calendar_id": calendar.id,
        "calendar_name": calendar.name,
        "events_imported_count": len(events),
        "status": "success"
    }

@router.post("/{calendar_id}/sync", response_model=CalendarImportResponse)
async def refresh_calendar_sync(
    calendar_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Refreshes an existing synced Google/Outlook/iCloud calendar feed.
    """
    result = await db.execute(select(Calendar).where(Calendar.id == calendar_id, Calendar.user_id == current_user.id))
    calendar = result.scalars().first()
    if not calendar or not calendar.is_synced or not calendar.feed_url:
        raise HTTPException(status_code=404, detail="Synced calendar feed not found")

    events = await CalendarFeedSyncService.fetch_feed_events(calendar.feed_url)

    # Clean old synced events
    ev_del_query = select(Event).where(Event.calendar_id == calendar.id)
    old_events = (await db.execute(ev_del_query)).scalars().all()
    for ev in old_events:
        await db.delete(ev)

    for ev in events:
        new_event = Event(
            calendar_id=calendar.id,
            user_id=current_user.id,
            title=ev.get("title", "Synced Event"),
            description=ev.get("description"),
            location=ev.get("location"),
            start_time=ev["start_time"],
            end_time=ev["end_time"],
            is_all_day=ev.get("is_all_day", False),
            rrule=ev.get("rrule")
        )
        db.add(new_event)

    calendar.last_synced_at = datetime.datetime.utcnow()
    await db.commit()

    return {
        "calendar_id": calendar.id,
        "calendar_name": calendar.name,
        "events_imported_count": len(events),
        "status": "success"
    }

@router.get("/shared-view")
async def get_shared_calendar_view(
    target_user_id: int = Query(...),
    start_date: str = Query(...),
    end_date: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
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
