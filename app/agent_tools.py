"""The dispatcher that executes each of the 5 custom tools Vapi calls.

Kept deliberately close to the schemas defined in
tools/create_or_update_vapi_assistant.py's CUSTOM_TOOL_DEFS — that file is the
source of truth for what Vapi is actually configured to send; this file is
what actually runs when it does. If they drift, tool calls will fail with a
missing-key error here, which is the signal to reconcile the two.
"""

from __future__ import annotations

import calendar_client
import config
import knowledge_base
import pricing
import sheets_client


def dispatch(name: str, tool_input: dict, call_ctx: dict) -> dict:
    call_id = call_ctx.get("call_id")
    caller_number = call_ctx.get("customer_number")

    if name == "search_business_info":
        results = knowledge_base.search(tool_input["query"])
        if not results:
            return {
                "results": [],
                "note": "No knowledge base content matched — tell the caller you'll confirm and follow up, don't guess.",
            }
        return {"results": results}

    if name == "calculate_order_total":
        return pricing.calculate(
            items=tool_input["items"],
            order_type=tool_input["order_type"],
            delivery_address=tool_input.get("delivery_address"),
        )

    if name == "create_order":
        items = tool_input["items"]
        order_type = tool_input["order_type"]
        delivery_address = tool_input.get("delivery_address")
        # Always recompute — never trust a total the model might state.
        totals = pricing.calculate(items=items, order_type=order_type, delivery_address=delivery_address)
        return sheets_client.append_order(
            call_id=call_id,
            customer_name=tool_input.get("customer_name"),
            phone=tool_input.get("phone") or caller_number or "",
            items=items,
            subtotal=totals["subtotal"],
            delivery_fee=totals["delivery_fee"],
            total=totals["total"],
            order_type=order_type,
            delivery_address=delivery_address,
            delivery_zone=totals["zone_matched"],
            notes=tool_input.get("notes"),
        )

    if name == "check_calendar_availability":
        return calendar_client.get_free_slots(tool_input["date"], tool_input.get("party_size"))

    if name == "book_appointment":
        date_str = tool_input["date"]
        time_str = tool_input["time"]
        duration = tool_input.get("duration_minutes") or config.RESERVATION_DEFAULT_DURATION_MINUTES

        if not calendar_client.is_slot_free(date_str, time_str, duration):
            fresh = calendar_client.get_free_slots(date_str, tool_input.get("party_size"))
            return {"booked": False, "reason": "slot_taken", "open_slots": fresh["open_slots"]}

        result = calendar_client.create_event(
            date_str=date_str,
            time_str=time_str,
            duration_minutes=duration,
            customer_name=tool_input["customer_name"],
            phone=tool_input.get("phone") or caller_number or "",
            party_size=tool_input.get("party_size"),
            notes=tool_input.get("notes"),
        )
        return {"booked": True, **result}

    if name == "save_lead":
        return sheets_client.append_lead(
            call_id=call_id,
            name=tool_input.get("name"),
            phone=tool_input.get("phone") or caller_number or "",
            email=tool_input.get("email"),
            lead_type=tool_input["type"],
            interest=tool_input["interest"],
            qualified=tool_input.get("qualified", "TBD"),
            qualification_notes=tool_input.get("qualification_notes"),
            follow_up_needed=bool(tool_input.get("follow_up_needed", False)),
        )

    return {"error": f"unknown tool: {name}"}
