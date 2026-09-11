"""Google Calendar access shared by tools/ scripts.

Same service account as sheets_common.py, different scope — the target
calendar must additionally be shared with the service account's client_email
("Make changes to events"). See workflows/setup_google_service_account.md.

Reads GOOGLE_SERVICE_ACCOUNT_JSON_B64 and GOOGLE_CALENDAR_ID from .env.
"""

from __future__ import annotations

import base64
import json

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from common import env, fail

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_calendar_service():
    encoded = env("GOOGLE_SERVICE_ACCOUNT_JSON_B64", required=True)
    try:
        info = json.loads(base64.b64decode(encoded))
    except Exception:
        fail(
            "GOOGLE_SERVICE_ACCOUNT_JSON_B64 is not valid base64-encoded JSON",
            hint="Re-encode the service account key file — see workflows/setup_google_service_account.md",
        )
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def get_calendar_id() -> str:
    return env("GOOGLE_CALENDAR_ID", required=True)


def calendar_error_hint(exc: HttpError) -> str:
    if exc.resp.status == 404:
        return "Check GOOGLE_CALENDAR_ID is correct — it's the calendar's own address/ID, not the spreadsheet ID."
    if exc.resp.status in (401, 403):
        return "Share the calendar with the service account's client_email (Make changes to events) — see workflows/setup_google_service_account.md."
    return "See the Google Calendar API error above for details."
