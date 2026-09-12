"""Google Sheets access for the always-on agent server.

Self-contained — does not import from tools/ — so app/ deploys as a standalone
service with its own dependency set. Uses a service account; see
workflows/setup_google_service_account.md for why and how.

Only Orders and Customers_Leads are written here — the Menu tab is read once
per assistant update by tools/create_or_update_vapi_assistant.py and injected
into the system prompt, not read live during a call (see the latency
reasoning in workflows/setup_vapi_assistant.md).
"""

from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from functools import lru_cache

import gspread
from google.oauth2.service_account import Credentials

import config
from retry import with_retries

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


@lru_cache(maxsize=1)
def _spreadsheet() -> gspread.Spreadsheet:
    info = json.loads(base64.b64decode(config.GOOGLE_SERVICE_ACCOUNT_JSON_B64))
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    client = gspread.authorize(creds)
    return client.open_by_key(config.GOOGLE_SHEETS_SPREADSHEET_ID)


def _last4(phone: str | None) -> str:
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    return digits[-4:] if digits else "0000"


def append_order(
    *,
    call_id: str | None,
    customer_name: str | None,
    phone: str,
    items: list[dict],
    subtotal: float,
    delivery_fee: float,
    total: float,
    order_type: str,
    delivery_address: str | None,
    delivery_zone: str | None,
    notes: str | None,
) -> dict:
    now = datetime.now(timezone.utc)
    order_id = f"ORD-{now.strftime('%Y%m%d%H%M%S')}-{_last4(phone)}"
    row = [
        order_id,
        now.isoformat(),
        call_id or "",
        customer_name or "",
        phone,
        json.dumps(items),
        subtotal,
        delivery_fee,
        total,
        order_type,
        delivery_address or "",
        delivery_zone or "",
        "Pending",
        notes or "",
    ]
    with_retries(lambda: _spreadsheet().worksheet(config.ORDERS_SHEET_NAME).append_row(row))
    return {"order_id": order_id, "total": total, "status": "Pending"}


def append_lead(
    *,
    call_id: str | None,
    name: str | None,
    phone: str,
    email: str | None,
    lead_type: str,
    interest: str,
    qualified: str,
    qualification_notes: str | None,
    follow_up_needed: bool,
) -> dict:
    now = datetime.now(timezone.utc)
    lead_id = f"LEAD-{now.strftime('%Y%m%d%H%M%S')}-{_last4(phone)}"
    row = [
        lead_id,
        now.isoformat(),
        call_id or "",
        name or "",
        phone,
        email or "",
        lead_type,
        interest,
        qualified,
        qualification_notes or "",
        "Y" if follow_up_needed else "N",
        "New",
    ]
    with_retries(lambda: _spreadsheet().worksheet(config.LEADS_SHEET_NAME).append_row(row))
    return {"lead_id": lead_id}
