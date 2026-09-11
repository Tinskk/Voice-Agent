"""Vapi webhook verification + request/response shaping.

Vapi's tool-call contract (per https://docs.vapi.ai/tools/custom-tools and
https://docs.vapi.ai/server-url/events, current as of when this was written):

    POST <server.url>
    {
      "message": {
        "type": "tool-calls",
        "toolCallList": [{"id": "...", "name": "...", "arguments": {...}}],
        "call": {"id": "...", ...}
      }
    }

    -> response: {"results": [{"toolCallId": "...", "result": ...}]}

A request can contain multiple simultaneous tool calls (handle the whole
list, not just one). Some Vapi accounts/versions nest the call under
`function: {name, arguments}` instead of flat `name`/`arguments` — this module
handles both shapes defensively rather than assuming one. If a real payload
turns out to differ, adjust `_tool_call_name`/`_tool_call_arguments` here and
log the correction in workflows/setup_vapi_assistant.md.

Authentication: tools/create_or_update_vapi_assistant.py sets an inline
`server.secret` on each tool, which Vapi sends back as the `X-Vapi-Secret`
header verbatim (no signing) — see
https://docs.vapi.ai/server-url/server-authentication. Verified with a
constant-time comparison.
"""

from __future__ import annotations

import hmac

import config

SECRET_HEADER = "x-vapi-secret"


def verify_secret(header_value: str | None) -> bool:
    if not header_value:
        return False
    return hmac.compare_digest(header_value, config.VAPI_WEBHOOK_SECRET)


def _tool_call_name(item: dict) -> str | None:
    if "name" in item:
        return item["name"]
    return item.get("function", {}).get("name")


def _tool_call_arguments(item: dict) -> dict:
    if "arguments" in item:
        return item["arguments"] or {}
    return item.get("function", {}).get("arguments") or {}


def parse_tool_calls(payload: dict) -> list[dict]:
    """Returns a list of {id, name, arguments} dicts, empty if the payload
    isn't a tool-calls message."""
    message = payload.get("message", {})
    raw_calls = message.get("toolCallList") or []
    return [
        {
            "id": item.get("id"),
            "name": _tool_call_name(item),
            "arguments": _tool_call_arguments(item),
        }
        for item in raw_calls
        if item.get("id") and _tool_call_name(item)
    ]


def parse_call_context(payload: dict) -> dict:
    message = payload.get("message", {})
    call = message.get("call", {}) or {}
    customer = call.get("customer", {}) or {}
    return {
        "call_id": call.get("id"),
        "customer_number": customer.get("number") or call.get("customerNumber"),
    }


def build_results_response(results: list[tuple[str, dict]]) -> dict:
    return {"results": [{"toolCallId": tool_call_id, "result": result} for tool_call_id, result in results]}
