"""Google Sheets access shared by tools/ scripts.

Uses a service account rather than an interactive OAuth flow — these scripts
should run unattended, and this way they authenticate with the exact same
non-interactive credential app/ uses in production. See
workflows/setup_google_service_account.md for how to create one and share the
sheet with it.

Reads GOOGLE_SERVICE_ACCOUNT_JSON_B64 and GOOGLE_SHEETS_SPREADSHEET_ID from .env.
"""

from __future__ import annotations

import base64
import json

import gspread
from google.oauth2.service_account import Credentials

from common import env, fail

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

MENU_SHEET_NAME = "Menu"
ORDERS_SHEET_NAME = "Orders"
LEADS_SHEET_NAME = "Customers_Leads"

MENU_HEADERS = [
    "Item",
    "Category",
    "Price",
    "Description",
    "Dietary Tags",
    "Popular Pairing",
    "Active (Y/N)",
]

ORDERS_HEADERS = [
    "Order ID",
    "Timestamp",
    "Call ID",
    "Customer Name",
    "Phone",
    "Items JSON",
    "Subtotal",
    "Delivery Fee",
    "Total",
    "Order Type",
    "Delivery Address",
    "Delivery Zone",
    "Status",
    "Notes",
]

LEADS_HEADERS = [
    "Lead ID",
    "Timestamp",
    "Call ID",
    "Name",
    "Phone",
    "Email",
    "Type",
    "Interest",
    "Qualified",
    "Qualification Notes",
    "Follow Up Needed",
    "Status",
]


def get_gspread_client() -> gspread.Client:
    encoded = env("GOOGLE_SERVICE_ACCOUNT_JSON_B64", required=True)
    try:
        info = json.loads(base64.b64decode(encoded))
    except Exception:
        fail(
            "GOOGLE_SERVICE_ACCOUNT_JSON_B64 is not valid base64-encoded JSON",
            hint="Re-encode the service account key file — see workflows/setup_google_service_account.md",
        )
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)


def open_spreadsheet() -> gspread.Spreadsheet:
    spreadsheet_id = env("GOOGLE_SHEETS_SPREADSHEET_ID", required=True)
    client = get_gspread_client()
    try:
        return client.open_by_key(spreadsheet_id)
    except gspread.exceptions.SpreadsheetNotFound:
        fail(
            f"Spreadsheet {spreadsheet_id!r} not found or not shared with the service account",
            hint="Share the sheet with the service account's client_email as Editor — see workflows/setup_google_service_account.md",
        )
    except gspread.exceptions.APIError as exc:
        fail(
            f"Google Sheets API error: {exc}",
            hint="Check the service account has access and the Sheets API is enabled on the GCP project.",
        )
