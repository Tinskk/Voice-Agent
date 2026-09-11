"""Sanity-check Google Calendar access before relying on it elsewhere.

Confirms the service account can (1) read freebusy on the target calendar and
(2) create and immediately delete a test event — proving both read and write
scopes actually work, not just that the ID is well-formed.

    python tools/verify_google_calendar_access.py
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from googleapiclient.errors import HttpError

from calendar_common import calendar_error_hint, get_calendar_id, get_calendar_service
from common import emit, fail, log


def main() -> None:
    calendar_id = get_calendar_id()
    service = get_calendar_service()

    now = datetime.now(timezone.utc)
    window_start = now
    window_end = now + timedelta(days=1)

    log(f"checking freebusy on {calendar_id!r}...")
    try:
        freebusy = (
            service.freebusy()
            .query(
                body={
                    "timeMin": window_start.isoformat(),
                    "timeMax": window_end.isoformat(),
                    "items": [{"id": calendar_id}],
                }
            )
            .execute()
        )
    except HttpError as exc:
        fail(f"Google Calendar freebusy query failed: {exc}", hint=calendar_error_hint(exc))

    busy_blocks = freebusy["calendars"].get(calendar_id, {}).get("busy", [])
    log(f"freebusy read ok — {len(busy_blocks)} busy block(s) in the next 24h")

    log("creating a test event...")
    test_start = now + timedelta(minutes=5)
    test_end = test_start + timedelta(minutes=15)
    try:
        created = (
            service.events()
            .insert(
                calendarId=calendar_id,
                body={
                    "summary": "Voice Agent access test — safe to ignore/delete",
                    "start": {"dateTime": test_start.isoformat()},
                    "end": {"dateTime": test_end.isoformat()},
                },
            )
            .execute()
        )
    except HttpError as exc:
        fail(f"Google Calendar event creation failed: {exc}", hint=calendar_error_hint(exc))

    event_id = created["id"]
    log(f"created test event {event_id!r}, deleting it now...")
    try:
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
    except HttpError as exc:
        fail(
            f"Test event was created but could not be deleted: {exc}",
            hint=f"Delete event {event_id!r} manually from the calendar.",
        )

    emit(
        {
            "calendar_id": calendar_id,
            "freebusy_read": True,
            "busy_blocks_next_24h": len(busy_blocks),
            "event_create_delete": True,
        }
    )


if __name__ == "__main__":
    main()
