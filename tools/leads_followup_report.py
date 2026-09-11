"""Report on leads that need follow-up from the Customers_Leads sheet.

    python tools/leads_followup_report.py

Filters to Follow Up Needed == Y, sorted oldest-first, so the owner can work
through the backlog in order.
"""

from __future__ import annotations

from common import emit, log
from sheets_common import LEADS_SHEET_NAME, open_spreadsheet


def main() -> None:
    spreadsheet = open_spreadsheet()
    worksheet = spreadsheet.worksheet(LEADS_SHEET_NAME)
    rows = worksheet.get_all_records()

    pending = [r for r in rows if str(r.get("Follow Up Needed", "")).strip().upper() == "Y"]
    pending.sort(key=lambda r: str(r.get("Timestamp", "")))

    log(f"{len(pending)} lead(s) need follow-up out of {len(rows)} total")

    emit(
        {
            "count": len(pending),
            "leads": [
                {
                    "lead_id": r.get("Lead ID"),
                    "name": r.get("Name"),
                    "phone": r.get("Phone"),
                    "type": r.get("Type"),
                    "interest": r.get("Interest"),
                    "qualified": r.get("Qualified"),
                    "qualification_notes": r.get("Qualification Notes"),
                    "status": r.get("Status"),
                    "timestamp": r.get("Timestamp"),
                }
                for r in pending
            ],
        }
    )


if __name__ == "__main__":
    main()
