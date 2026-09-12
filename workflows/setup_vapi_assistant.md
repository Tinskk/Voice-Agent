# Set up the Vapi assistant

**Objective:** Create (or update) the Vapi assistant with the right system
prompt, model/voice/transcriber, and the 5 custom tools + `endCall`/
`transferCall`, wired to the deployed `app/` webhook.

**When to run:** Once for the first setup, after `deploy_agent_server.md` (the
tools need a real webhook URL to point at). Re-run
`tools/refresh_menu_context.py` (not this whole workflow) for routine menu
updates; re-run this workflow's steps 3-4 if you change the system prompt
template, tool schemas, or model/voice/transcriber choice.

## Design note: why the menu isn't a live tool call

A restaurant's menu is small and changes rarely, but every extra tool
round-trip mid-call adds real, audible latency. So the menu is rendered from
the `Menu` sheet and baked directly into the assistant's system prompt by
`tools/create_or_update_vapi_assistant.py`, instead of being a `get_menu` tool
the assistant calls live. The tradeoff: a menu edit needs
`python tools/refresh_menu_context.py` to actually reach the live assistant —
it is not instantly reflected. Acceptable for a menu that changes daily at
most, not for same-shift 86'd items (flag that limitation to the owner).

## Inputs

| Input | Required | Notes |
|---|---|---|
| A Vapi account | yes | [dashboard.vapi.ai](https://dashboard.vapi.ai) — sign up, create an API key under Settings → API Keys. |
| `app/` already deployed | yes | See `deploy_agent_server.md`; `AGENT_SERVER_URL` must be set in `.env`. |
| A voice provider choice | no | Defaults to ElevenLabs (`11labs`) with a placeholder `VAPI_VOICE_ID` — pick a real voice from the Vapi dashboard's voice library and set `VAPI_VOICE_ID` in `.env`. |
| Escalation transfer number | no | Set `ESCALATION_TRANSFER_NUMBER` in `.env` for live `transferCall` — without it, the tool is skipped and escalation only happens via `save_lead` notes. |

## Steps

1. **Get a Vapi API key** — Vapi dashboard → Settings → API Keys → create one
   → put it in `VAPI_API_KEY` in `.env`.

2. **Invent a webhook secret** — any long random string (a UUID works) → put
   it in `VAPI_WEBHOOK_SECRET` in `.env`. This is set as each tool's inline
   `server.secret`, which Vapi echoes back on every request as the
   `X-Vapi-Secret` header — `app/vapi_client.py` verifies it before touching
   the request body.

3. **Create/update the assistant** —
   `python tools/create_or_update_vapi_assistant.py`. This renders the current
   menu, builds the system prompt from
   `tools/vapi_system_prompt_template.md`, creates the 5 custom tools (each
   pointed at `<AGENT_SERVER_URL>/vapi/tool-calls`) plus `endCall` and (if
   `ESCALATION_TRANSFER_NUMBER` is set) `transferCall`, and creates the
   assistant.
   - Expect: `ok: true` with an `assistant_id`.
   - **Save that `assistant_id` as `VAPI_ASSISTANT_ID` in `.env`** — re-running
     the script without it creates a second assistant instead of updating the
     first one.

4. **Verify in the dashboard** — open the assistant in Vapi's dashboard,
   confirm all 5 custom tools plus `endCall`/`transferCall` are attached, the
   system prompt includes the real menu, and the model/voice/transcriber look
   right.

5. **Test with Vapi's own web test-call feature** (if available in the
   dashboard) before spending on a real phone number — confirm a tool call
   actually reaches `app/` (check Render logs for a `/vapi/tool-calls` hit).

## Output

A Vapi assistant, referenced by `VAPI_ASSISTANT_ID` in `.env`, with the real
menu in its system prompt and all 5 custom tools + `endCall`/`transferCall`
correctly wired to the deployed `app/` webhook.

## Edge cases

- **Vapi API rejects the request body with a validation error:** Vapi's API
  surface moves fast and field names can drift from what's assumed in
  `tools/create_or_update_vapi_assistant.py` / `tools/vapi_common.py`. Read
  the error message, check https://docs.vapi.ai/api-reference, adjust the
  script, and log the fix below — this is expected occasional maintenance,
  not a sign of a fundamentally broken approach.
- **Ran the script without saving `VAPI_ASSISTANT_ID` first:** you now have two
  assistants. Delete the extra one in the dashboard, keep the `assistant_id`
  you want, save it to `.env`, and re-run.
- **Tool calls never reach `app/`:** confirm `AGENT_SERVER_URL` was set
  *before* running this script (tools bake the URL in at creation time) — if
  you deployed after already creating tools, re-run this script to update
  their `server.url`.
- **`X-Vapi-Secret` header verification always fails in `app/` logs:** confirm
  `VAPI_WEBHOOK_SECRET` in Render's environment matches the value used when
  the tools were created — if you changed it in `.env` after creating tools,
  re-run this script so the tools' `server.secret` gets updated too.
- **Escalation calls never transfer:** `ESCALATION_TRANSFER_NUMBER` was empty
  when this script last ran — set it and re-run.
- **Voice sounds rushed/wrong accent, or the assistant talks over the caller /
  responds before they've finished a thought:** these are three separate,
  fixable knobs, not something to just live with — see the 2026-09-12 note
  below for the exact fields and values that fixed this on the first real
  test call.

## Notes & learnings

- _(2026-09-12) First real test call surfaced three issues, all fixed without
  needing to touch app/'s code — only the assistant's config:_
  - _Voice was the ElevenLabs default ("Rachel"), too fast and no accent match
    for the caller. Switched to Azure's `en-NG-EzinneNeural` (a real Nigerian
    English neural voice — `en-NG-AbeoNeural` is the male equivalent) via
    `VAPI_VOICE_PROVIDER=azure` / `VAPI_VOICE_ID=en-NG-EzinneNeural` in `.env`._
  - _Transcription was mangling accented speech. Deepgram's default `nova-2`
    model is tuned for clean/studio audio; switched to `nova-2-phonecall`
    (`VAPI_TRANSCRIBER_MODEL=nova-2-phonecall`), which is specifically tuned
    for phone-line audio quality._
  - _Assistant was cutting the caller off mid-sentence. Added `startSpeakingPlan`
    (`waitSeconds: 0.8`, `smartEndpointingPlan.provider: "vapi"`,
    `transcriptionEndpointingPlan.onNoPunctuationSeconds: 2.5`) and
    `stopSpeakingPlan` (`numWords: 2`, `voiceSeconds: 0.3`,
    `backoffSeconds: 1.0`) to the assistant body in
    `create_or_update_vapi_assistant.py` — these are top-level assistant
    fields, not nested under `model`/`voice`. Vapi accepted all of this on the
    first try with no validation errors, so these field names/shapes are
    confirmed correct as of this date. Also reinforced calm pacing and
    "ask to repeat rather than guess" in the system prompt template itself —
    belt and suspenders with the endpointing config._
  - _If a future test call still shows premature interruption, the next dial
    to turn is `onNoPunctuationSeconds` (raise it further) before assuming
    something else is wrong._
- _(2026-09-12) Second issue from the same test call: caller reported prices
  being read out digit-by-digit ("one, five, zero, zero") instead of in
  words, and orders failing with an apology instead of actually placing.
  Root causes and fixes:_
  - _Prices: nothing wrong server-side — this is purely how the LLM chose to
    verbalize a plain number. Fixed by adding an explicit "Speaking prices
    and numbers" section to `vapi_system_prompt_template.md` telling it to
    always say amounts in words with "naira", never digit-by-digit, never
    read a currency symbol._
  - _Orders failing: `create_order`/`book_appointment`/`save_lead` all
    declared `phone` as a **required** tool-schema field, even though
    `app/agent_tools.py`'s dispatch already falls back to the caller's own
    number (`call.customer.number`) when `phone` is omitted. If the caller
    never explicitly stated a phone number (reasonably assuming caller ID
    would just work), the model had no value to satisfy a field marked
    required and could get stuck apologizing instead of asking again or just
    proceeding. Confirmed the backend itself was fine by calling
    `create_order` directly against the live server with realistic data —
    it worked and produced a correct order/total on the first try. Fixed by
    dropping `phone` from each tool's `required` list (kept as an optional
    property with a description explaining the fallback) and updating the
    system prompt's order-taking flow to say the caller's number is used
    automatically rather than instructing the assistant to collect it._
  - _Lesson: any optional argument that the dispatcher falls back on
    server-side must also be optional in the tool's JSON schema — marking it
    required forces the model to have a value in hand, silently defeating
    the fallback. Worth double-checking any new tool argument for this same
    mismatch before assuming a live-call failure is a deeper bug._

- _(2026-09-11) Created._
