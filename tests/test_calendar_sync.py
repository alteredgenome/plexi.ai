import pytest
import datetime
from app.services.calendar_sync import ICSParser
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.session import init_db

SAMPLE_ICS = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Google Inc//Google Calendar 70.9054//EN
BEGIN:VEVENT
SUMMARY:Google Calendar Strategy Sync
DESCRIPTION:Quarterly executive review
LOCATION:Virtual Zoom Link
DTSTART:20260905T140000Z
DTEND:20260905T150000Z
UID:google-event-12345@google.com
END:VEVENT
BEGIN:VEVENT
SUMMARY:Outlook All Day Workshop
DTSTART;VALUE=DATE:20260906
DTEND;VALUE=DATE:20260907
UID:outlook-event-67890@outlook.com
END:VEVENT
END:VCALENDAR"""

def test_ics_parser_rfc5545():
    events = ICSParser.parse_ics_content(SAMPLE_ICS)
    assert len(events) == 2
    
    ev1 = events[0]
    assert ev1["title"] == "Google Calendar Strategy Sync"
    assert ev1["description"] == "Quarterly executive review"
    assert ev1["location"] == "Virtual Zoom Link"
    assert ev1["start_time"] == datetime.datetime(2026, 9, 5, 14, 0, 0)
    assert ev1["end_time"] == datetime.datetime(2026, 9, 5, 15, 0, 0)
    assert ev1["is_all_day"] is False

    ev2 = events[1]
    assert ev2["title"] == "Outlook All Day Workshop"
    assert ev2["start_time"] == datetime.datetime(2026, 9, 6, 0, 0, 0)
    assert ev2["is_all_day"] is True

@pytest.mark.asyncio
async def test_ics_file_import_api():
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Register user
        reg = await ac.post("/api/v1/auth/register", json={
            "email": "sync.user@plexi.fyi",
            "password": "password123",
            "full_name": "Sync User",
            "timezone": "UTC"
        })
        login = await ac.post("/api/v1/auth/token", data={
            "username": "sync.user@plexi.fyi",
            "password": "password123"
        })
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Import .ics file
        files = {"file": ("calendar.ics", SAMPLE_ICS.encode("utf-8"), "text/calendar")}
        data = {"calendar_name": "My Google Sync"}
        res = await ac.post("/api/v1/calendars/import/ics", headers=headers, files=files, data=data)
        assert res.status_code == 200
        res_data = res.json()
        assert res_data["events_imported_count"] == 2
        assert res_data["calendar_name"] == "My Google Sync"
