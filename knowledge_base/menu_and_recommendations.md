# Menu context & recommendations

The authoritative menu (items, prices, categories, dietary tags, pairings)
lives in the Google Sheet's **Menu** tab and is injected directly into the
assistant's system prompt — see `tools/create_or_update_vapi_assistant.py`.
Don't duplicate prices or item names here.

This file is for **narrative context that doesn't fit in a spreadsheet cell**:
longer flavor descriptions, chef's notes, seasonal specials framing, or
upsell guidance that helps the agent recommend well beyond what the
`Description`/`Popular Pairing` columns can hold. Add content here as it
comes up — it's picked up by `search_business_info` like any other knowledge
base file.

## Not yet finalized

- Any seasonal or limited-time items and how to talk about them.
- General upsell guidance beyond the per-item `Popular Pairing` column (e.g.
  "always offer a drink with a pickup order").
