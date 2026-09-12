# Deploy the agent server

**Objective:** Get `app/` running continuously on Render so it can answer
Vapi's tool-call webhook 24/7 during live calls.

**When to run:** Once for the first deploy, then any time `app/` changes and
needs to go live (Render auto-redeploys on push once connected, so this is
mostly a first-time setup). Do this **before** `setup_vapi_assistant.md`,
since the assistant's tools need a real, deployed URL to point at.

## Inputs

| Input | Required | Notes |
|---|---|---|
| GitHub repo with this project pushed | yes | Render deploys from a connected repo. |
| A Render account | yes | Free to create; the service itself needs the Starter plan (~$7/mo). |
| All `.env` values filled in except Vapi-assistant-specific ones | yes | You'll re-enter them as Render env vars — see `.env.example`. `VAPI_ASSISTANT_ID`/`VAPI_PHONE_NUMBER_ID` aren't needed by `app/` itself. |

## Steps

1. **Push to GitHub** — commit `app/`, `tools/`, `workflows/`,
   `knowledge_base/`, and the rest of the project (everything except what's
   gitignored — `.env` and `app/data/*.db` never get committed) to the repo.

2. **Create a Render Web Service from the blueprint** — in the Render
   dashboard, "New" → "Blueprint" → connect the repo → set **Blueprint Path**
   to `app/render.yaml` explicitly (it defaults to looking at the repo root)
   → confirm.

   (Manual alternative: "New" → "Web Service" → connect repo → Root
   Directory: `app` → Build Command: `pip install -r requirements.txt` →
   Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT` → Plan:
   **Starter**, not Free — the free tier spins down after 15 min idle, which
   is too slow for a webhook Vapi expects a fast ack from mid-call.)

3. **Set the environment variables** — in the service's "Environment" tab, add
   `VAPI_WEBHOOK_SECRET`, `GOOGLE_SERVICE_ACCOUNT_JSON_B64`,
   `GOOGLE_SHEETS_SPREADSHEET_ID`, `GOOGLE_CALENDAR_ID`, `BUSINESS_NAME`,
   `BUSINESS_TIMEZONE`, `BUSINESS_HOURS_JSON`, `DELIVERY_ZONES_JSON`,
   `DEFAULT_DELIVERY_FEE`, `RESERVATION_SLOT_MINUTES`,
   `RESERVATION_DEFAULT_DURATION_MINUTES`, `ESCALATION_TRANSFER_NUMBER`.
   Never commit these — they only live in `.env` locally and in Render's
   dashboard.

4. **Deploy and confirm health** — once the build finishes,
   `curl https://<your-app>.onrender.com/health` should return
   `{"status":"ok"}`.

5. **Set `AGENT_SERVER_URL`** in the local `.env` to
   `https://<your-app>.onrender.com`, so the next workflow
   (`setup_vapi_assistant.md`) points the tools' webhooks at the real URL.

6. **Smoke-test the tool-call endpoint before any real call exists** — send a
   hand-crafted request shaped like Vapi's contract:
   ```
   curl -X POST https://<your-app>.onrender.com/vapi/tool-calls \
     -H "Content-Type: application/json" \
     -H "x-vapi-secret: <your VAPI_WEBHOOK_SECRET>" \
     -d '{"message":{"type":"tool-calls","toolCallList":[{"id":"test-1","name":"search_business_info","arguments":{"query":"opening hours"}}],"call":{"id":"test-call"}}}'
   ```
   Expect a `200` with `{"results":[{"toolCallId":"test-1","result":{...}}]}`.
   Repeat with a bad/missing `x-vapi-secret` header and confirm you get `401`.

## Output

A live URL (`https://<your-app>.onrender.com`) running `app/`, responding
correctly to hand-crafted tool-call requests, ready for `setup_vapi_assistant.md`
to point real Vapi tools at.

## Edge cases

- **Build fails on missing env var:** `config.py` fails fast at boot with the
  exact variable name that's missing — check the Render logs, add it, redeploy.
- **`/health` times out or 502s right after deploy:** cold start on the first
  request after a build — wait ~30s and retry before assuming something's wrong.
- **Blueprint deploy fails immediately, "render.yaml not found":** set
  **Blueprint Path** to `app/render.yaml` explicitly when creating the Blueprint.
- **First deploy after Blueprint creation fails:** expected if you haven't
  filled in the `sync: false` env vars yet — Render creates the service from
  the blueprint before you've had a chance to add secrets. Go to the
  service's Environment tab, add the missing values, save, and it auto-redeploys.
- **Redeploy resets tool-call dedupe/session state:** expected —
  `app/store.py`'s SQLite file lives on Render's ephemeral disk. Known v1
  limitation, not a bug (see `app/README.md`).
- **Tool-call smoke test returns 401 even with the right secret:** double-check
  there's no trailing whitespace/newline in the Render env var value, and that
  it matches `.env` exactly.

## Notes & learnings

- _(2026-09-11) Created._
- _(2026-09-12) An order placed live didn't land in the Orders sheet with no
  visible cause — turned out the code had zero retry logic around Sheets/
  Calendar writes, so any single transient error (rate limit from rapid
  back-to-back test calls, a brief network blip) failed the whole tool call
  outright. Added `app/retry.py` (`with_retries`, 3 attempts with backoff)
  around every Sheets/Calendar API call in `sheets_client.py` and
  `calendar_client.py`. Separately found `app/calendar_client.py` uses
  `ZoneInfo(BUSINESS_TIMEZONE)` for all reservation-availability math, which
  throws `ZoneInfoNotFoundError` on any Python environment without the OS's
  IANA timezone database — confirmed locally on Windows, and plausible on a
  minimal Render Python image too. Added `tzdata` to both `requirements.txt`
  and `app/requirements.txt` as a pure-Python fallback so this can't depend on
  what the underlying OS happens to ship. If reservation availability checks
  ever start failing outright, check for this exact error first.
