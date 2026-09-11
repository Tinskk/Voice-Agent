"""Google Calendar access for the always-on agent server.

Self-contained — does not import from tools/. Same service account as
sheets_client.py, Calendar scope; the target calendar must be shared with the
service account's client_email ("Make changes to events") — see
workflows/setup_google_service_account.md.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

import config

SCOPES = ["https://www.googleapis.com/auth/calendar"]

_WEEKDAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


@lru_cache(maxsize=1)
def _service():
    info = json.loads(base64.b64decode(config.GOOGLE_SERVICE_ACCOUNT_JSON_B64))
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def _tz() -> ZoneInfo:
    return ZoneInfo(config.BUSINESS_TIMEZONE)


def _business_hours_for(date_obj) -> tuple[str, str] | None:
    key = _WEEKDAY_KEYS[date_obj.weekday()]
    raw = config.BUSINESS_HOURS.get(key, "closed")
    if not raw or raw == "closed":
        return None
    start, end = raw.split("-")
    return start.strip(), end.strip()


def _busy_blocks(day_start: datetime, day_end: datetime) -> list[tuple[datetime, datetime]]:
    freebusy = (
        _service()
        .freebusy()
        .query(
            body={
                "timeMin": day_start.isoformat(),
                "timeMax": day_end.isoformat(),
                "items": [{"id": config.GOOGLE_CALENDAR_ID}],
            }
        )
        .execute()
    )
    blocks = freebusy["calendars"].get(config.GOOGLE_CALENDAR_ID, {}).get("busy", [])
    return [
        (datetime.fromisoformat(b["start"]), datetime.fromisoformat(b["end"]))
        for b in blocks
    ]


def _overlaps(slot_start: datetime, slot_end: datetime, busy: list[tuple[datetime, datetime]]) -> bool:
    return any(slot_start < b_end and slot_end > b_start for b_start, b_end in busy)


def get_free_slots(date_str: str, party_size: int | None = None) -> dict:
    tz = _tz()
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return {"date": date_str, "open_slots": [], "business_hours": None, "error": "invalid_date_format"}

    hours = _business_hours_for(date_obj)
    if hours is None:
        return {"date": date_str, "open_slots": [], "business_hours": "closed"}

    open_str, close_str = hours
    day_start = datetime.combine(date_obj, datetime.strptime(open_str, "%H:%M").time(), tzinfo=tz)
    day_end = datetime.combine(date_obj, datetime.strptime(close_str, "%H:%M").time(), tzinfo=tz)

    busy = _busy_blocks(day_start, day_end)

    duration = timedelta(minutes=config.RESERVATION_DEFAULT_DURATION_MINUTES)
    step = timedelta(minutes=config.RESERVATION_SLOT_MINUTES)

    open_slots = []
    cursor = day_start
    while cursor + duration <= day_end:
        if not _overlaps(cursor, cursor + duration, busy):
            open_slots.append(cursor.strftime("%H:%M"))
        cursor += step

    return {"date": date_str, "open_slots": open_slots, "business_hours": f"{open_str}-{close_str}"}


def is_slot_free(date_str: str, time_str: str, duration_minutes: int) -> bool:
    tz = _tz()
    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    time_obj = datetime.strptime(time_str, "%H:%M").time()
    slot_start = datetime.combine(date_obj, time_obj, tzinfo=tz)
    slot_end = slot_start + timedelta(minutes=duration_minutes)

    busy = _busy_blocks(slot_start - timedelta(minutes=1), slot_end + timedelta(minutes=1))
    return not _overlaps(slot_start, slot_end, busy)


def create_event(
    *,
    date_str: str,
    time_str: str,
    duration_minutes: int,
    customer_name: str,
    phone: str,
    party_size: int | None,
    notes: str | None,
) -> dict:
    tz = _tz()
    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    time_obj = datetime.strptime(time_str, "%H:%M").time()
    start = datetime.combine(date_obj, time_obj, tzinfo=tz)
    end = start + timedelta(minutes=duration_minutes)

    size_label = f" ({party_size})" if party_size else ""
    description_lines = [f"Phone: {phone}"]
    if notes:
        description_lines.append(f"Notes: {notes}")

    event = (
        _service()
        .events()
        .insert(
            calendarId=config.GOOGLE_CALENDAR_ID,
            body={
                "summary": f"Reservation: {customer_name}{size_label}",
                "description": "\n".join(description_lines),
                "start": {"dateTime": start.isoformat()},
                "end": {"dateTime": end.isoformat()},
            },
        )
        .execute()
    )
    return {"event_id": event["id"], "date": date_str, "time": time_str, "duration_minutes": duration_minutes}
