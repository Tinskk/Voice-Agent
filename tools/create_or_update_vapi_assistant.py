"""Create or update the Vapi assistant: system prompt (with the current menu
block rendered in), model/voice/transcriber, and the 5 custom tools +
endCall/transferCall.

Idempotent: tool IDs are cached in .tmp/vapi_tool_ids.json and matched by
name, so re-running PATCHes existing tools/assistant instead of duplicating
them. Safe to re-run any time the system prompt, tools, or menu change.

    python tools/create_or_update_vapi_assistant.py

First run prints an `assistant_id` — save it as VAPI_ASSISTANT_ID in .env so
later runs update the same assistant instead of creating a new one.
"""

from __future__ import annotations

from common import ROOT, emit, env, log, read_json, write_json
from number_words import naira_words
from sheets_common import MENU_SHEET_NAME, open_spreadsheet
from vapi_common import patch, post

PROMPT_TEMPLATE_PATH = ROOT / "tools" / "vapi_system_prompt_template.md"
TOOL_IDS_CACHE_PATH = ROOT / ".tmp" / "vapi_tool_ids.json"

AGENT_SERVER_URL = env("AGENT_SERVER_URL")  # e.g. https://your-app.onrender.com
WEBHOOK_SECRET = env("VAPI_WEBHOOK_SECRET", required=True)
BUSINESS_NAME = env("BUSINESS_NAME", default="the restaurant")
ESCALATION_NUMBER = env("ESCALATION_TRANSFER_NUMBER")

MODEL_PROVIDER = env("VAPI_MODEL_PROVIDER", default="anthropic")
MODEL_NAME = env("VAPI_MODEL_NAME", default="claude-sonnet-5")
VOICE_PROVIDER = env("VAPI_VOICE_PROVIDER", default="11labs")
VOICE_ID = env("VAPI_VOICE_ID", default="21m00Tcm4TlvDq8ikWAM")
TRANSCRIBER_PROVIDER = env("VAPI_TRANSCRIBER_PROVIDER", default="deepgram")
TRANSCRIBER_MODEL = env("VAPI_TRANSCRIBER_MODEL", default="nova-2")

CUSTOM_TOOL_DEFS = [
    {
        "name": "search_business_info",
        "description": (
            "Search business FAQs/policies (hours, location, delivery areas, "
            "catering policy, etc.) for an answer. Call this before answering "
            "anything not covered by the menu block in the system prompt."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The caller's question, e.g. 'are you open on Sunday' or 'do you deliver to Green Hills'.",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "calculate_order_total",
        "description": (
            "Calculate the subtotal, delivery fee, and total for a set of order "
            "items before committing. Always call this and read the total back "
            "to the caller before calling create_order."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "item": {"type": "string"},
                            "qty": {"type": "integer"},
                            "unit_price": {"type": "number"},
                        },
                        "required": ["item", "qty", "unit_price"],
                    },
                },
                "order_type": {"type": "string", "enum": ["delivery", "pickup"]},
                "delivery_address": {"type": "string"},
            },
            "required": ["items", "order_type"],
        },
    },
    {
        "name": "create_order",
        "description": (
            "Log a confirmed order to the Orders sheet. Only call this after "
            "reading the total back (via calculate_order_total) and getting the "
            "caller's explicit yes."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "customer_name": {"type": "string"},
                "phone": {
                    "type": "string",
                    "description": "Callback number. Optional — if the caller doesn't give one, the number they're calling from is used automatically.",
                },
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "item": {"type": "string"},
                            "qty": {"type": "integer"},
                            "unit_price": {"type": "number"},
                        },
                        "required": ["item", "qty", "unit_price"],
                    },
                },
                "order_type": {"type": "string", "enum": ["delivery", "pickup"]},
                "delivery_address": {"type": "string"},
                "notes": {"type": "string"},
            },
            "required": ["items", "order_type"],
        },
    },
    {
        "name": "check_calendar_availability",
        "description": "Check real-time reservation availability for a given date before offering times.",
        "parameters": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "YYYY-MM-DD"},
                "preferred_time": {"type": "string", "description": "HH:MM, 24h, optional"},
                "party_size": {"type": "integer"},
            },
            "required": ["date"],
        },
    },
    {
        "name": "book_appointment",
        "description": (
            "Book a reservation on the calendar. Only call this after reading "
            "the date/time/party size back to the caller and getting their yes. "
            "Re-checks availability itself — handle a conflict result by "
            "immediately offering the alternatives it returns."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "date": {"type": "string"},
                "time": {"type": "string"},
                "duration_minutes": {"type": "integer"},
                "party_size": {"type": "integer"},
                "customer_name": {"type": "string"},
                "phone": {
                    "type": "string",
                    "description": "Callback number. Optional — if the caller doesn't give one, the number they're calling from is used automatically.",
                },
                "notes": {"type": "string"},
            },
            "required": ["date", "time", "customer_name"],
        },
    },
    {
        "name": "save_lead",
        "description": (
            "Log a catering/event inquiry or other lead to the Customers_Leads "
            "sheet, with your qualification judgment."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "phone": {
                    "type": "string",
                    "description": "Callback number. Optional — if the caller doesn't give one, the number they're calling from is used automatically.",
                },
                "email": {"type": "string"},
                "type": {"type": "string", "enum": ["Order", "Lead", "Reservation"]},
                "interest": {"type": "string"},
                "qualified": {"type": "string", "enum": ["Yes", "No", "TBD"]},
                "qualification_notes": {"type": "string"},
                "follow_up_needed": {"type": "boolean"},
            },
            "required": ["interest", "type"],
        },
    },
]


def render_menu_block() -> str:
    spreadsheet = open_spreadsheet()
    worksheet = spreadsheet.worksheet(MENU_SHEET_NAME)
    rows = worksheet.get_all_records()

    active_rows = [r for r in rows if str(r.get("Active (Y/N)", "Y")).strip().upper() != "N"]
    if not active_rows:
        return "(No active menu items yet — tell the caller the menu is being updated and take a callback instead of guessing.)"

    by_category: dict[str, list[dict]] = {}
    for row in active_rows:
        by_category.setdefault(str(row.get("Category") or "Other"), []).append(row)

    lines = []
    for category, items in by_category.items():
        lines.append(f"### {category}")
        for item in items:
            name = item.get("Item", "")
            price = item.get("Price", "")
            try:
                price_words = naira_words(float(price))
            except (TypeError, ValueError):
                price_words = str(price)
            desc = str(item.get("Description") or "").strip()
            tags = str(item.get("Dietary Tags") or "").strip()
            pairing = str(item.get("Popular Pairing") or "").strip()
            # Both forms are given deliberately: the numeral is what you pass
            # as unit_price to calculate_order_total/create_order; the words
            # are exactly what you should say out loud — say "SPOKEN" verbatim,
            # never read the numeral's digits one at a time.
            line = f"- {name} — {price} (SPOKEN: \"{price_words}\")"
            if desc:
                line += f". {desc}"
            if tags:
                line += f" (dietary: {tags})"
            if pairing:
                line += f" (pairs well with: {pairing})"
            lines.append(line)
        lines.append("")
    return "\n".join(lines).strip()


def build_system_prompt(menu_block: str) -> str:
    template = PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")
    return template.replace("{{BUSINESS_NAME}}", BUSINESS_NAME).replace("{{MENU_BLOCK}}", menu_block)


def load_tool_id_cache() -> dict:
    if TOOL_IDS_CACHE_PATH.exists():
        return read_json(TOOL_IDS_CACHE_PATH)
    return {}


def ensure_custom_tools() -> list[str]:
    if not AGENT_SERVER_URL:
        log("WARNING: AGENT_SERVER_URL is not set — tools will point nowhere until it is. Set it after deploy_agent_server.md and re-run.")
    webhook_url = f"{AGENT_SERVER_URL.rstrip('/')}/vapi/tool-calls" if AGENT_SERVER_URL else "https://REPLACE_ME/vapi/tool-calls"

    cache = load_tool_id_cache()
    tool_ids: list[str] = []

    for tool_def in CUSTOM_TOOL_DEFS:
        body = {
            "type": "function",
            "function": {
                "name": tool_def["name"],
                "description": tool_def["description"],
                "parameters": tool_def["parameters"],
            },
            "server": {"url": webhook_url, "secret": WEBHOOK_SECRET},
        }
        existing_id = cache.get(tool_def["name"])
        if existing_id:
            log(f"updating tool {tool_def['name']!r} ({existing_id})")
            patch(f"/tool/{existing_id}", body)
            tool_ids.append(existing_id)
        else:
            log(f"creating tool {tool_def['name']!r}")
            created = post("/tool", body)
            tool_id = created["id"]
            cache[tool_def["name"]] = tool_id
            tool_ids.append(tool_id)

    # Native tools — no server webhook, Vapi handles these itself.
    if "endCall" not in cache:
        log("creating endCall tool")
        created = post("/tool", {"type": "endCall"})
        cache["endCall"] = created["id"]
    tool_ids.append(cache["endCall"])

    if ESCALATION_NUMBER:
        transfer_body = {"type": "transferCall", "destinations": [{"type": "number", "number": ESCALATION_NUMBER}]}
        if "transferCall" not in cache:
            log("creating transferCall tool")
            created = post("/tool", transfer_body)
            cache["transferCall"] = created["id"]
        else:
            patch(f"/tool/{cache['transferCall']}", transfer_body)
        tool_ids.append(cache["transferCall"])
    else:
        log("ESCALATION_TRANSFER_NUMBER not set — skipping transferCall tool. Callers can't be transferred until it's added.")

    write_json(TOOL_IDS_CACHE_PATH, cache)
    return tool_ids


def create_or_update_assistant(tool_ids: list[str], system_prompt: str) -> dict:
    assistant_id = env("VAPI_ASSISTANT_ID")

    body = {
        "name": f"{BUSINESS_NAME} Voice Agent",
        "firstMessage": f"Thanks for calling {BUSINESS_NAME}! How can I help you today?",
        "model": {
            "provider": MODEL_PROVIDER,
            "model": MODEL_NAME,
            "messages": [{"role": "system", "content": system_prompt}],
            "toolIds": tool_ids,
        },
        "voice": {"provider": VOICE_PROVIDER, "voiceId": VOICE_ID},
        "transcriber": {"provider": TRANSCRIBER_PROVIDER, "model": TRANSCRIBER_MODEL},
        # Loosened from Vapi's defaults after real test calls showed the
        # assistant jumping in before the caller finished a thought —
        # especially noticeable with non-US speech pacing/pauses. Higher
        # waitSeconds/onNoPunctuationSeconds means it waits longer for a real
        # pause before responding, at the cost of a bit more latency.
        "startSpeakingPlan": {
            "waitSeconds": 0.8,
            "smartEndpointingPlan": {"provider": "vapi"},
            "transcriptionEndpointingPlan": {
                "onPunctuationSeconds": 0.2,
                "onNoPunctuationSeconds": 2.5,
                "onNumberSeconds": 0.8,
            },
        },
        "stopSpeakingPlan": {
            "numWords": 2,
            "voiceSeconds": 0.3,
            "backoffSeconds": 1.0,
        },
    }

    if assistant_id:
        log(f"updating assistant {assistant_id}")
        result = patch(f"/assistant/{assistant_id}", body)
    else:
        log("creating new assistant")
        result = post("/assistant", body)

    return result


def main() -> None:
    log("rendering menu block from the Menu sheet...")
    menu_block = render_menu_block()

    log("building system prompt...")
    system_prompt = build_system_prompt(menu_block)

    log("ensuring custom tools exist / are up to date...")
    tool_ids = ensure_custom_tools()

    log("creating/updating assistant...")
    assistant = create_or_update_assistant(tool_ids, system_prompt)

    emit(
        {
            "assistant_id": assistant.get("id"),
            "tool_count": len(tool_ids),
            "note": "Save assistant_id as VAPI_ASSISTANT_ID in .env if this was the first run.",
        }
    )


if __name__ == "__main__":
    main()
