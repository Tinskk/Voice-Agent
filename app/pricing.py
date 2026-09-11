"""Order total calculation + delivery-zone fee lookup.

Pure, dependency-free logic — no Sheets/Calendar calls — so it's cheap to call
speculatively from calculate_order_total and safe to call again inside
create_order (which always recomputes rather than trusting a total the model
might state).

Delivery zones come from config.DELIVERY_ZONES:
    [{"name": "Downtown", "keywords": ["main st", "downtown"], "fee": 3.0}, ...]
Matched by case-insensitive substring against the delivery address; the first
matching zone wins. No match -> config.DEFAULT_DELIVERY_FEE and
zone_unmatched=True, so the assistant can flag it rather than silently
guessing a fee.
"""

from __future__ import annotations

import config


def line_total(qty: int, unit_price: float) -> float:
    return round(qty * unit_price, 2)


def subtotal(items: list[dict]) -> float:
    return round(sum(line_total(item["qty"], item["unit_price"]) for item in items), 2)


def match_delivery_zone(delivery_address: str | None) -> tuple[str | None, float, bool]:
    """Returns (zone_name_or_None, fee, zone_unmatched)."""
    if not delivery_address:
        return None, 0.0, False

    address_lower = delivery_address.lower()
    for zone in config.DELIVERY_ZONES:
        keywords = zone.get("keywords", [])
        if any(str(kw).lower() in address_lower for kw in keywords):
            return zone.get("name"), float(zone.get("fee", config.DEFAULT_DELIVERY_FEE)), False

    return None, config.DEFAULT_DELIVERY_FEE, True


def calculate(items: list[dict], order_type: str, delivery_address: str | None = None) -> dict:
    sub = subtotal(items)

    if order_type == "delivery":
        zone_name, fee, zone_unmatched = match_delivery_zone(delivery_address)
    else:
        zone_name, fee, zone_unmatched = None, 0.0, False

    total = round(sub + fee, 2)

    return {
        "subtotal": sub,
        "delivery_fee": fee,
        "total": total,
        "zone_matched": zone_name,
        "zone_unmatched": zone_unmatched,
    }
