# Seed and verify business data

**Objective:** Get the real menu, and empty-but-correctly-shaped Orders and
Customers_Leads tabs, into the Google Sheet so the agent has real data to work
with from the first call.

**When to run:** Once, after `setup_google_service_account.md`, and again any
time the sheet structure needs to be re-verified (e.g. after a header got
accidentally edited).

## Inputs

| Input | Required | Notes |
|---|---|---|
| The real menu (items, categories, prices, descriptions) | yes | Ask the business owner if not already provided. |
| Delivery zone names/keywords/fees | yes | Needed for `.env`'s `DELIVERY_ZONES_JSON`, not the sheet itself. |

## Steps

1. **Create the tabs** — `python tools/seed_menu_sheet.py` (add `--sample-data`
   only for a first smoke test; skip it once you have the real menu) and
   `python tools/seed_customers_orders_sheet.py`.

2. **Enter the real menu** — open the `Menu` tab directly in Google Sheets and
   fill in real rows. Column meanings:

   | Column | Meaning |
   |---|---|
   | `Item` | What the caller hears, e.g. "Margherita Pizza". |
   | `Category` | Free text, e.g. "Mains", "Sides" — groups the prompt-injected menu block. |
   | `Price` | Number only, no currency symbol. |
   | `Description` | Short, spoken-friendly — this gets read into the assistant's context verbatim. |
   | `Dietary Tags` | Comma list, e.g. "vegetarian, gluten-free" — lets the agent answer dietary questions without a knowledge-base lookup. |
   | `Popular Pairing` | Optional item name(s) to suggest alongside this one. |
   | `Active (Y/N)` | `N` hides an item from the agent entirely without deleting the row. |

3. **Set delivery zones** — in `.env`, fill in `DELIVERY_ZONES_JSON` as a list
   like `[{"name":"Downtown","keywords":["main st","downtown"],"fee":3.0}]`
   and `DEFAULT_DELIVERY_FEE` for unmatched addresses. Mirror the same zones
   in plain language in `knowledge_base/delivery_and_policies.md` so the agent
   can also explain coverage conversationally.

4. **Set business hours** — in `.env`, fill in `BUSINESS_HOURS_JSON` (used for
   reservation-slot math) and `BUSINESS_TIMEZONE`. Update
   `knowledge_base/hours_and_location.md` to match — these two must agree.

5. **Verify** — `python tools/verify_google_sheets_access.py`. Expect
   `ok: true` with all 3 tabs reporting `exists: true, headers_ok: true`.

6. **Push the menu into the assistant** — once `setup_vapi_assistant.md` has
   created the assistant at least once, run
   `python tools/refresh_menu_context.py` any time the Menu tab changes.

## Output

The Sheet has a real, active menu plus empty `Orders`/`Customers_Leads` tabs
with correct headers; `.env` has real `DELIVERY_ZONES_JSON`,
`DEFAULT_DELIVERY_FEE`, `BUSINESS_HOURS_JSON`, and `BUSINESS_TIMEZONE` values.

## Edge cases

- **Renamed or reordered a header column:** the agent's sheet-writing code
  keys off exact header names (see `tools/sheets_common.py`) — don't rename
  headers; add new columns to the right instead if you need more fields.
- **Item marked inactive mid-shift:** set `Active (Y/N)` to `N` rather than
  deleting the row, then re-run `tools/refresh_menu_context.py` — until that
  runs, the live assistant still has the old menu in its prompt (see the
  "menu is prompt-embedded, not live" design note in `setup_vapi_assistant.md`).
- **Delivery address doesn't match any zone:** `DEFAULT_DELIVERY_FEE` applies
  and the order is flagged `zone_unmatched` internally — if this happens
  often, add more keyword variants to `DELIVERY_ZONES_JSON` (street
  abbreviations, common misspellings, etc.).

## Notes & learnings

- _(2026-09-11) Created._
