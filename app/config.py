"""App-wide configuration. Fails fast at import time if something required is
missing — better to crash on boot with a clear message than fail mysteriously
on the first webhook.

Local dev reads from .env (via python-dotenv); in production (Render) these
are just process environment variables set in the dashboard.

Self-contained — does not import from tools/ — so app/ deploys as a standalone
service with its own dependency set (see app/README.md).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

APP_DIR = Path(__file__).resolve().parent
ROOT = APP_DIR.parent

load_dotenv(ROOT / ".env")


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        sys.exit(f"Missing required environment variable: {name} (set it in .env or the host's env vars)")
    return value


def _json_env(name: str, default: str) -> object:
    raw = os.getenv(name, default)
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        sys.exit(f"Environment variable {name} is not valid JSON: {raw!r}")


# --- Vapi ---
VAPI_WEBHOOK_SECRET = _require("VAPI_WEBHOOK_SECRET")

# --- Google (service account, shared by Sheets + Calendar) ---
GOOGLE_SERVICE_ACCOUNT_JSON_B64 = _require("GOOGLE_SERVICE_ACCOUNT_JSON_B64")
GOOGLE_SHEETS_SPREADSHEET_ID = _require("GOOGLE_SHEETS_SPREADSHEET_ID")
GOOGLE_CALENDAR_ID = _require("GOOGLE_CALENDAR_ID")

MENU_SHEET_NAME = "Menu"
ORDERS_SHEET_NAME = "Orders"
LEADS_SHEET_NAME = "Customers_Leads"

# --- Business config ---
BUSINESS_NAME = os.getenv("BUSINESS_NAME", "the restaurant")
BUSINESS_TIMEZONE = os.getenv("BUSINESS_TIMEZONE", "UTC")
BUSINESS_HOURS = _json_env("BUSINESS_HOURS_JSON", "{}")
DELIVERY_ZONES = _json_env("DELIVERY_ZONES_JSON", "[]")
DEFAULT_DELIVERY_FEE = float(os.getenv("DEFAULT_DELIVERY_FEE", "0"))
RESERVATION_SLOT_MINUTES = int(os.getenv("RESERVATION_SLOT_MINUTES", "30"))
RESERVATION_DEFAULT_DURATION_MINUTES = int(os.getenv("RESERVATION_DEFAULT_DURATION_MINUTES", "90"))
ESCALATION_TRANSFER_NUMBER = os.getenv("ESCALATION_TRANSFER_NUMBER")

# --- App ---
KNOWLEDGE_BASE_DIR = ROOT / "knowledge_base"

# Anchored to app/ by default so it's correct regardless of the process's cwd
# (Render's rootDir, local `cd app && uvicorn ...`, etc.). Override with an
# absolute path via AGENT_DB_PATH if you ever need to.
AGENT_DB_PATH = os.getenv("AGENT_DB_PATH") or str(APP_DIR / "data" / "agent.db")
