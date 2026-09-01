import re
import datetime
import httpx
from typing import List, Dict, Any, Optional

class ICSParser:
    """
    Lightweight, robust RFC 5545 iCalendar (.ics) parser.
    Parses Google Calendar, Microsoft Outlook, and standard .ics files.
    """
    @staticmethod
    def parse_datetime(dt_str: str) -> Optional[datetime.datetime]:
        """
        Parses iCalendar datetime string (e.g. 20260902T143000Z, 20260902T143000, 20260902).
        """
        dt_str = dt_str.strip()
        # Remove any leading TZID parameter if present in value
        if ":" in dt_str:
            dt_str = dt_str.split(":")[-1]
            
        try:
            if "T" in dt_str:
                clean_dt = dt_str.rstrip("Z")
                if len(clean_dt) == 15: # YYYYMMDDTHHMMSS
                    return datetime.datetime.strptime(clean_dt, "%Y%m%dT%H%M%S")
                elif len(clean_dt) == 13: # YYYYMMDDTHHMM
                    return datetime.datetime.strptime(clean_dt, "%Y%m%dT%H%M")
            elif len(dt_str) == 8: # YYYYMMDD (All Day)
                return datetime.datetime.strptime(dt_str, "%Y%m%d")
        except Exception:
            pass
        return None

    @staticmethod
    def parse_ics_content(ics_text: str) -> List[Dict[str, Any]]:
        """
        Parses .ics raw text into a structured list of event dictionaries.
        """
        events = []
        # Unfold lines (RFC 5545: lines starting with space or tab are continuations)
        unfolded = re.sub(r'\r?\n[ \t]', '', ics_text)
        lines = unfolded.splitlines()

        in_event = False
        current_event: Dict[str, Any] = {}

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line == "BEGIN:VEVENT":
                in_event = True
                current_event = {
                    "title": "Untitled Event",
                    "description": None,
                    "location": None,
                    "start_time": None,
                    "end_time": None,
                    "is_all_day": False,
                    "rrule": None
                }
                continue
            elif line == "END:VEVENT":
                if in_event and current_event.get("start_time"):
                    if not current_event.get("end_time"):
                        # Default 1 hour duration if end time not specified
                        current_event["end_time"] = current_event["start_time"] + datetime.timedelta(hours=1)
                    events.append(current_event)
                in_event = False
                current_event = {}
                continue

            if not in_event:
                continue

            # Parse property key and value
            if ":" in line:
                parts = line.split(":", 1)
                prop_key = parts[0].upper()
                prop_val = parts[1].replace(r'\,', ',').replace(r'\;', ';').replace(r'\n', '\n')

                if prop_key.startswith("SUMMARY"):
                    current_event["title"] = prop_val
                elif prop_key.startswith("DESCRIPTION"):
                    current_event["description"] = prop_val
                elif prop_key.startswith("LOCATION"):
                    current_event["location"] = prop_val
                elif prop_key.startswith("DTSTART"):
                    dt = ICSParser.parse_datetime(prop_val)
                    if dt:
                        current_event["start_time"] = dt
                    if "VALUE=DATE" in prop_key or len(prop_val) == 8:
                        current_event["is_all_day"] = True
                elif prop_key.startswith("DTEND"):
                    dt = ICSParser.parse_datetime(prop_val)
                    if dt:
                        current_event["end_time"] = dt
                elif prop_key.startswith("RRULE"):
                    current_event["rrule"] = prop_val

        return events

class CalendarFeedSyncService:
    """
    Fetches and syncs Google Calendar (secret .ics link), Outlook, or iCloud calendar feeds.
    """
    @staticmethod
    async def fetch_feed_events(feed_url: str) -> List[Dict[str, Any]]:
        # Normalize webcal:// protocol to https://
        if feed_url.startswith("webcal://"):
            feed_url = "https://" + feed_url[9:]
            
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(feed_url)
            resp.raise_for_status()
            return ICSParser.parse_ics_content(resp.text)
