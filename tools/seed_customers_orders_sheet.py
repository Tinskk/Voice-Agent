"""Create/verify the Orders and Customers_Leads tabs in the Google Sheet.

Idempotent: only creates a tab or writes its header row when missing — never
touches existing data.

    python tools/seed_customers_orders_sheet.py
"""

from __future__ import annotations

import gspread

from common import emit, log
from sheets_common import (
    LEADS_HEADERS,
    LEADS_SHEET_NAME,
    ORDERS_HEADERS,
    ORDERS_SHEET_NAME,
    open_spreadsheet,
)


def ensure_tab(spreadsheet: gspread.Spreadsheet, name: str, headers: list[str]) -> str:
    try:
        worksheet = spreadsheet.worksheet(name)
        log(f"tab {name!r} already exists")
    except gspread.exceptions.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=name, rows=500, cols=len(headers))
        worksheet.append_row(headers)
        log(f"created tab {name!r} with headers")
        return "created"

    if not worksheet.row_values(1):
        worksheet.append_row(headers)
        log(f"wrote missing header row to {name!r}")
        return "headers_added"

    return "unchanged"


def main() -> None:
    spreadsheet = open_spreadsheet()

    orders_status = ensure_tab(spreadsheet, ORDERS_SHEET_NAME, ORDERS_HEADERS)
    leads_status = ensure_tab(spreadsheet, LEADS_SHEET_NAME, LEADS_HEADERS)

    emit(
        {
            "spreadsheet_title": spreadsheet.title,
            "orders_tab": orders_status,
            "leads_tab": leads_status,
        }
    )


if __name__ == "__main__":
    main()
