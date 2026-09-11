"""Buy a new Vapi phone number and attach it to the assistant for inbound calls.

Idempotent-ish: if VAPI_PHONE_NUMBER_ID is already set in .env, re-running
just re-attaches it to the current VAPI_ASSISTANT_ID (useful after recreating
the assistant) instead of buying a second number.

    python tools/provision_vapi_phone_number.py --area-code 415

This calls Vapi's number-purchase endpoint, which may incur a real cost —
confirm with the business owner before running if you're unsure about billing.
"""

from __future__ import annotations

import argparse

from common import emit, env, fail, log
from vapi_common import patch, post

ASSISTANT_ID = env("VAPI_ASSISTANT_ID", required=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Provision a Vapi phone number and attach it to the assistant.")
    parser.add_argument("--area-code", help="Preferred US area code, e.g. 415. Vapi picks a number if omitted/unavailable.")
    args = parser.parse_args()

    existing_number_id = env("VAPI_PHONE_NUMBER_ID")
    if existing_number_id:
        log(f"VAPI_PHONE_NUMBER_ID already set ({existing_number_id}) — re-attaching to current assistant instead of buying a new number")
        result = patch(f"/phone-number/{existing_number_id}", {"assistantId": ASSISTANT_ID})
        emit({"phone_number_id": result.get("id"), "number": result.get("number"), "assistant_id": ASSISTANT_ID, "action": "reattached"})
        return

    body: dict = {"provider": "vapi", "assistantId": ASSISTANT_ID}
    if args.area_code:
        body["numberDesiredAreaCode"] = args.area_code

    log("purchasing a new Vapi phone number...")
    result = post("/phone-number", body)

    number = result.get("number")
    if not number:
        fail("Vapi did not return a phone number in the response", hint="Check the response shape against https://docs.vapi.ai/api-reference and adjust this script.")

    emit(
        {
            "phone_number_id": result.get("id"),
            "number": number,
            "assistant_id": ASSISTANT_ID,
            "action": "created",
            "note": "Save phone_number_id as VAPI_PHONE_NUMBER_ID in .env.",
        }
    )


if __name__ == "__main__":
    main()
