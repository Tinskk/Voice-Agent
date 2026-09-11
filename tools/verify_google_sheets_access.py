"""Sanity-check Google Sheets access before relying on it elsewhere.

Confirms the service account can open the spreadsheet and that the Menu,
Orders, and Customers_Leads tabs exist with the expected header row.

    python tools/verify_google_sheets_access.py
"""

from __future__ import annotations

import gspread

from common import emit, fail, log
from sheets_common import (
    LEADS_HEADERS,
    LEADS_SHEET_NAME,
    MENU_HEADERS,
    MENU_SHEET_NAME,
    ORDERS_HEADERS,
    ORDERS_SHEET_NAME,
    open_spreadsheet,
)


def check_tab(spreadsheet: gspread.Spreadsheet, name: str, expected_headers: list[str]) -> dict:
    try:
        worksheet = spreadsheet.worksheet(name)
    except gspread.exceptions.WorksheetNotFound:
        return {"tab": name, "exists": False, "headers_ok": False, "data_rows": 0}

    all_values = worksheet.get_all_values()
    headers = all_values[0] if all_values else []
    return {
        "tab": name,
        "exists": True,
        "headers_ok": headers == expected_headers,
        "headers_found": headers,
        "data_rows": max(len(all_values) - 1, 0),
    }


def main() -> None:
    log("opening spreadsheet...")
    spreadsheet = open_spreadsheet()
    log(f"opened {spreadsheet.title!r}")

    results = [
        check_tab(spreadsheet, MENU_SHEET_NAME, MENU_HEADERS),
        check_tab(spreadsheet, ORDERS_SHEET_NAME, ORDERS_HEADERS),
        check_tab(spreadsheet, LEADS_SHEET_NAME, LEADS_HEADERS),
    ]

    missing = [r["tab"] for r in results if not r["exists"]]
    bad_headers = [r["tab"] for r in results if r["exists"] and not r["headers_ok"]]

    if missing:
        fail(
            f"Missing tab(s): {', '.join(missing)}",
            hint="Run `python tools/seed_menu_sheet.py` and/or `python tools/seed_customers_orders_sheet.py` to create them.",
        )
    if bad_headers:
        fail(
            f"Header row doesn't match the expected columns on: {', '.join(bad_headers)}",
            hint="Fix the header row manually to match sheets_common.py, or clear it and re-run the seed script.",
        )

    emit({"spreadsheet_title": spreadsheet.title, "tabs": results})


if __name__ == "__main__":
    main()
