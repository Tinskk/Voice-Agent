# Tools — the execution layer

Deterministic Python. One job per script, no judgment calls, no branching on
"what the caller probably meant." If a decision needs reasoning, it belongs in
the agent layer (or, for live-call decisions, the Vapi assistant's system
prompt), not here.

## Contract

Every tool is a CLI invoked from the project root:

```
python tools/<name>.py --arg value
```

| Channel | Carries |
|---|---|
| stdout | exactly one JSON object: `{"ok": true, "data": ...}` or `{"ok": false, "error": ..., "hint": ...}` |
| stderr | progress logs, tracebacks, warnings |
| exit code | `0` success · `1` handled failure · `2` bad arguments |

Nothing but the result object goes to stdout — that's what makes a tool call
parseable instead of something to eyeball.

## Writing one

1. Copy `_template.py` and rename it `verb_noun.py` (`seed_menu_sheet.py`,
   `daily_orders_report.py`).
2. Import from `common.py`: `emit`, `fail`, `log`, `env`, `tmp_path`, `write_json`.
3. Read secrets with `env("KEY", required=True)` — never hardcode, never accept
   a key as a command-line argument.
4. Write intermediates to `.tmp/` via `tmp_path()`. Deliverables go to cloud
   services, not to disk.
5. Docstring at the top: what it does, plus a copy-pasteable example invocation.

## Rules that keep this reliable

- **Idempotent where possible.** Re-running should not double-charge, double-post,
  or double-write.
- **Fail loudly with a hint.** `fail(msg, hint=...)` — the hint tells the agent what
  to fix. Silent partial success is worse than a clean error.
- **One tool, one responsibility.** Fetching, transforming, and uploading are three
  tools, so a failure in one doesn't force redoing the others.
- **Paid API calls:** note the cost in the docstring (`provision_vapi_phone_number.py`
  buys a real number). Check with the owner before running a paid call again.
- **Rate limits and quirks you discover** get written into the calling workflow, not
  just fixed in the code.

## Files

| File | Purpose |
|---|---|
| `common.py` | Shared helpers: output contract, env loading, `.tmp/` paths |
| `_template.py` | Skeleton for a new tool |
| `sheets_common.py` | Service-account Google Sheets auth + tab/header constants (Menu, Orders, Customers_Leads) |
| `calendar_common.py` | Service-account Google Calendar auth, shared by calendar tools |
| `vapi_common.py` | Vapi REST API request helper (auth header, error handling) |
| `verify_google_sheets_access.py` | Confirms the service account can reach the sheet and all 3 tabs/headers are correct |
| `verify_google_calendar_access.py` | Confirms freebusy read + event create/delete both work on the target calendar |
| `seed_menu_sheet.py` | Creates the Menu tab (and optionally sample rows) — idempotent |
| `seed_customers_orders_sheet.py` | Creates the Orders and Customers_Leads tabs — idempotent |
| `vapi_system_prompt_template.md` | The assistant's system prompt, with `{{BUSINESS_NAME}}`/`{{MENU_BLOCK}}` placeholders |
| `create_or_update_vapi_assistant.py` | Renders the menu + system prompt, creates/updates the 5 custom tools + endCall/transferCall, creates/updates the assistant — idempotent |
| `provision_vapi_phone_number.py` | Buys a Vapi phone number and attaches it to the assistant (real cost — see docstring) |
| `refresh_menu_context.py` | Convenience wrapper: re-runs the assistant update after a menu edit |
| `daily_orders_report.py` | Summarizes today's orders from the Orders sheet |
| `leads_followup_report.py` | Lists leads with `Follow Up Needed = Y`, oldest first |

Note: these scripts use a **service account** for Google Sheets/Calendar
access, not an interactive OAuth `credentials.json`/`token.json` flow — see
`workflows/setup_google_service_account.md` for why and how to set one up.
`app/` (the always-on voice-agent server) uses the same service-account
credential independently; it does not import from this directory.
