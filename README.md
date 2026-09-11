# Voice Agent — Restaurant phone assistant

A Vapi-powered voice agent that answers a restaurant's phone line: FAQ/customer
support, business hours, menu recommendations, order taking with pricing and
delivery, fully-automated reservation booking against Google Calendar, and
catering/event lead qualification — all logged to a Google Sheet the owner can
see and edit directly.

## How it's built

Two independent halves, sharing only `.env`-style config, a Google Sheet, and
a Google Calendar:

- **[`app/`](app/README.md)** — the actual product. A small always-on FastAPI
  service, deployed to Render, that Vapi calls live during a phone call
  whenever the assistant needs a tool (FAQ lookup, order pricing/creation,
  calendar check/booking, lead capture). Runs continuously, independent of any
  Claude Code session. Vapi itself owns the phone number, speech-to-text, the
  conversational LLM, and text-to-speech.
- **`tools/` + `workflows/`** — the WAT (Workflows/Agents/Tools) layer this
  project's `CLAUDE.md` describes, for one-off/manual jobs a human runs
  through Claude Code: seeding the Sheet, creating/updating the Vapi
  assistant, provisioning the phone number, pulling an orders/leads report.
  See `workflows/README.md`.

See `app/README.md` for why `app/` doesn't follow the WAT shape — a webhook
Vapi calls mid-conversation can't be an on-demand script.

## First-time setup

1. `workflows/setup_google_service_account.md` — Google service account with
   Sheets + Calendar access.
2. Copy `.env.example` to `.env` and fill in the Google values from step 1,
   plus `BUSINESS_NAME`, `BUSINESS_TIMEZONE`, `BUSINESS_HOURS_JSON`,
   `DELIVERY_ZONES_JSON`, `DEFAULT_DELIVERY_FEE`.
3. `pip install -r requirements.txt` (for `tools/`) and
   `pip install -r app/requirements.txt` (for `app/`).
4. `workflows/seed_and_verify_business_data.md` — create the Menu, Orders, and
   Customers_Leads tabs; add the real menu.
5. `workflows/deploy_agent_server.md` — deploy `app/` to Render; set
   `AGENT_SERVER_URL` in `.env` to the deployed URL.
6. `workflows/setup_vapi_assistant.md` — create the Vapi assistant, tools, and
   system prompt, wired to the deployed URL.
7. `workflows/provision_phone_number.md` — get a working inbound number.
8. `workflows/run_end_to_end_test_call.md` — place a real test call and verify
   the results land correctly in the Sheet and Calendar.

## Day-to-day operation

- **Update the menu:** edit the Menu tab, then run
  `python tools/refresh_menu_context.py` to push it to the live assistant.
- **Check today's orders:** `python tools/daily_orders_report.py`.
- **Check leads needing follow-up:** `python tools/leads_followup_report.py`.
- **Add knowledge base content:** drop `.md`/`.txt` files into
  `knowledge_base/` — see `knowledge_base/README.md`. No redeploy needed.
- **Change the system prompt / tools:** edit
  `tools/vapi_system_prompt_template.md` or the tool defs in
  `tools/create_or_update_vapi_assistant.py`, then re-run that script.

## Known v1 scope limits

- No payment integration — orders are logged `Pending`; the owner follows up manually.
- The menu is prompt-embedded and refreshed on demand, not read live per call.
- Tool-call dedupe / call-scratch state doesn't survive a Render redeploy.
- No SMS/email confirmation after a call.
- Knowledge base search is keyword-based, not embeddings-based.

See `app/README.md` for the full list and rationale.
