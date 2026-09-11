"""Report on today's orders from the Orders sheet.

    python tools/daily_orders_report.py

Reads every row, filters to today's date in BUSINESS_TIMEZONE, and summarizes
count + total revenue so the owner can see the day's orders without opening
the sheet.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from common import emit, env, log
from sheets_common import ORDERS_SHEET_NAME, open_spreadsheet


def to_number(value: object) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


def main() -> None:
    tz_name = env("BUSINESS_TIMEZONE", default="UTC")
    tz = ZoneInfo(tz_name)
    today = datetime.now(tz).date()

    spreadsheet = open_spreadsheet()
    worksheet = spreadsheet.worksheet(ORDERS_SHEET_NAME)
    rows = worksheet.get_all_records()

    def is_today(row: dict) -> bool:
        raw = str(row.get("Timestamp", "")).strip()
        if not raw:
            return False
        try:
            ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return False
        return ts.astimezone(tz).date() == today

    todays_orders = [r for r in rows if is_today(r)]
    total = sum(to_number(r.get("Total")) for r in todays_orders)

    log(f"{len(todays_orders)} order(s) today ({today.isoformat()}, {tz_name})")

    emit(
        {
            "date": today.isoformat(),
            "timezone": tz_name,
            "count": len(todays_orders),
            "total_revenue": total,
            "orders": [
                {
                    "order_id": r.get("Order ID"),
                    "customer_name": r.get("Customer Name"),
                    "phone": r.get("Phone"),
                    "order_type": r.get("Order Type"),
                    "total": to_number(r.get("Total")),
                    "status": r.get("Status"),
                    "timestamp": r.get("Timestamp"),
                }
                for r in todays_orders
            ],
        }
    )


if __name__ == "__main__":
    main()
