# Set up Google service account (Sheets + Calendar)

**Objective:** Give the agent (both `app/` and the Sheet/Calendar-touching
`tools/` scripts) non-interactive access to a Google Sheet (Menu, Orders,
Customers_Leads) and a Google Calendar (reservations), via one shared
service account.

**When to run:** Once, before anything else. Re-run the "share" steps if you
ever create a new spreadsheet or switch calendars.

## Why a service account, not the OAuth flow

`app/` is an always-on server with nobody watching it to click through a
browser consent screen, so the interactive OAuth `credentials.json`/`token.json`
pattern doesn't work here. A **service account** is a non-interactive identity
Google issues you a JSON key for; you grant it access the same way you'd share
a sheet or calendar with a person — by adding its email.

## Inputs

| Input | Required | Notes |
|---|---|---|
| A Google account | yes | To create the GCP project, the Sheet, and (optionally) a dedicated Calendar. |

## Steps

1. **Create (or pick) a Google Cloud project** — [console.cloud.google.com](https://console.cloud.google.com) → project dropdown → New Project. Any name is fine, e.g. "voice-agent".

2. **Enable both APIs** — with that project selected, "APIs & Services" → "Library" → enable **Google Sheets API** and **Google Calendar API**.

3. **Create a service account** — "APIs & Services" → "Credentials" → "Create Credentials" → "Service account". Any name (e.g. `voice-agent-sa`). No special project-level roles needed — access is granted per-resource in steps 6-7.

4. **Generate a JSON key** — open the service account → "Keys" tab → "Add Key" → "Create new key" → JSON. Treat the downloaded file like a password, never commit it.

5. **Base64-encode the key and add it to `.env`** —
   - Windows PowerShell: `[Convert]::ToBase64String([IO.File]::ReadAllBytes("path\to\key.json"))`
   - macOS/Linux: `base64 -i key.json | tr -d '\n'`

   Paste the result as `GOOGLE_SERVICE_ACCOUNT_JSON_B64` in `.env`.

6. **Create the Google Sheet and share it** — create a new spreadsheet (any
   name, e.g. "Voice Agent — Orders & Leads"), copy its ID from the URL
   (`https://docs.google.com/spreadsheets/d/<THIS PART>/edit`) into
   `GOOGLE_SHEETS_SPREADSHEET_ID` in `.env`. Share it with the service
   account's `client_email` (found in the JSON key, looks like
   `...@...iam.gserviceaccount.com`) as **Editor**.

7. **Pick/create the Calendar and share it** — either use an existing Google
   Calendar for reservations or create a dedicated one (Google Calendar →
   "Other calendars" → "+" → "Create new calendar"). Find its **Calendar ID**
   in that calendar's Settings page (for a dedicated calendar, it looks like
   an email address; for "primary", it's just the Google account's email) and
   put it in `GOOGLE_CALENDAR_ID` in `.env`. Share it with the same service
   account's `client_email`, permission **"Make changes to events"**.

   > This is the step people forget, twice over — once for the sheet, once
   > for the calendar. Skipping either produces a "not found" error even
   > though the ID is correct — the service account simply hasn't been let in.

8. **Seed the sheet tabs** — `python tools/seed_menu_sheet.py --sample-data`
   then `python tools/seed_customers_orders_sheet.py`.

9. **Verify both** — `python tools/verify_google_sheets_access.py` (expect
   `ok: true`, all 3 tabs `exists: true, headers_ok: true`) and
   `python tools/verify_google_calendar_access.py` (expect `ok: true`,
   `freebusy_read: true`, `event_create_delete: true`).

## Output

`.env` has working `GOOGLE_SERVICE_ACCOUNT_JSON_B64`,
`GOOGLE_SHEETS_SPREADSHEET_ID`, and `GOOGLE_CALENDAR_ID` values. The Sheet has
`Menu`, `Orders`, and `Customers_Leads` tabs with correct headers, and the
service account can read/write the target Calendar.

## Edge cases

- **"Spreadsheet not found" / calendar 404:** almost always means the
  resource wasn't shared with the service account's `client_email`, or the
  wrong ID was copied. Re-check steps 6/7.
- **"API has not been used in project..." error:** the Sheets or Calendar API
  isn't enabled on the GCP project the service account belongs to — repeat step 2.
- **Calendar ID confusion:** the Calendar ID is not the same as the
  spreadsheet ID or the service account email — it's specifically the
  calendar's own ID from that calendar's Settings page.
- **Lost the JSON key:** you can't re-download it — delete the key in the
  Google Cloud Console and generate a new one (step 4), then re-encode and
  re-share if you created a new service account.

## Notes & learnings

- _(2026-09-11) Created._
