# app/ — the always-on voice-agent webhook server

This is the actual product: a small FastAPI service that Vapi calls live,
mid-phone-call, whenever the assistant decides to use one of its custom tools
(FAQ lookup, order pricing/creation, calendar availability/booking, lead
capture). It runs continuously once deployed — nobody invokes it on demand.
The conversation itself (speech-to-text, the LLM turn loop, text-to-speech) is
entirely Vapi's job; this server has no LLM calls in it at all.

This is deliberately **not** shaped like the `tools/`/`workflows/` layer
described in the project's `CLAUDE.md`: those are for one-off scripts a human
runs through Claude Code, while this is a conventional backend service that
must respond fast, synchronously, to a live call. See the "app/ exception"
section of `CLAUDE.md` for why.

## Files

| File | Responsibility |
|---|---|
| `main.py` | FastAPI app — `/health`, `/vapi/tool-calls` (the real endpoint), `/vapi/events` (log-only stub) |
| `config.py` | Environment variable loading, fails fast on boot if something required is missing |
| `vapi_client.py` | Webhook secret verification, tool-call payload parsing, response shaping |
| `agent_tools.py` | The dispatcher that executes each of the 5 custom tools |
| `sheets_client.py` | Google Sheets writes (Orders, Customers_Leads) via a service account |
| `calendar_client.py` | Google Calendar freebusy check + event creation via the same service account |
| `pricing.py` | Order total calculation + delivery-zone fee lookup (pure, no API calls) |
| `knowledge_base.py` | Loads and keyword-searches `knowledge_base/*.md`/`*.txt` |
| `store.py` | SQLite: tool-call dedupe (idempotency) + short-term per-call scratch state |
| `render.yaml` | Render deployment blueprint |

Modules import each other directly (`import config`, not `from . import config`)
— this isn't a Python package, it's a flat set of modules that run with `app/`
itself as the working directory / on `sys.path`, matching how Render's
`rootDir: app` + `uvicorn main:app` runs it in production.

The **menu** is not read here — it's rendered once from the Menu sheet and
baked into the assistant's system prompt by
`tools/create_or_update_vapi_assistant.py`, not fetched live per call. See
that tool's docstring and `workflows/setup_vapi_assistant.md` for why.

## Running locally

1. Fill in `.env` at the project root (copy `.env.example`) — you need a real
   Vapi API key/webhook secret and Google service account credentials. See
   `workflows/setup_google_service_account.md` and `workflows/setup_vapi_assistant.md`.
2. From the project root:
   ```
   pip install -r app/requirements.txt
   uvicorn main:app --reload --app-dir app
   ```
3. Expose it publicly for Vapi's webhook to reach during local testing, e.g.
   `ngrok http 8000`, and point a tool's `server.url` at the ngrok URL
   temporarily (or just test with hand-crafted `curl` requests shaped like
   Vapi's real tool-call payload — see `workflows/deploy_agent_server.md`).

## Deploying

See `workflows/deploy_agent_server.md`. Short version: push to GitHub, create
a Render Web Service from `app/render.yaml`, set the env vars in the Render
dashboard, then point `AGENT_SERVER_URL` (in `.env`) at the deployed URL and
re-run `tools/create_or_update_vapi_assistant.py` so the tools' webhooks point
at the real, live URL.

## Known v1 limitations

- No payment integration — orders are logged `Pending`; the owner follows up manually.
- Tool-call dedupe / call-scratch state (SQLite) doesn't survive a redeploy —
  acceptable given each call's own context also lives in Vapi for its duration.
- Knowledge base search is keyword-based, no embeddings/vector DB.
- The menu only updates when `tools/refresh_menu_context.py` is re-run after an
  edit — not truly live per call (a deliberate latency/simplicity tradeoff).
- No SMS/email confirmation after a call — out of scope for v1.
- `/vapi/events` is a log-only stub; nothing consumes call transcripts/recordings automatically yet.
