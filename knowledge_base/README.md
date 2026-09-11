# Knowledge base

Drop `.md` or `.txt` files in this folder to give the voice agent more to draw
on when answering questions via the `search_business_info` tool (hours,
location, delivery areas, catering policy, cancellation policy, etc.). No code
changes are needed — `app/knowledge_base.py` picks up new files automatically
the next time it searches (it checks file modification times, so you don't
even need to redeploy).

This is separate from the **menu**, which lives in the Google Sheet and is
injected directly into the assistant's system prompt (see
`tools/create_or_update_vapi_assistant.py` and
`workflows/setup_vapi_assistant.md`) — don't duplicate prices/items here.

## Format tips

- One topic per file usually works best (`hours_and_location.md`,
  `delivery_and_policies.md`).
- Use `##` headings inside a file to mark distinct sub-topics — the loader
  splits on headings when present, which gives the agent more focused chunks
  to search.
- Keep it in plain, spoken-friendly language — the agent reads this content
  out loud to a caller, it doesn't need to be written for machines.

## How it's used

When a caller asks something that isn't answered by the menu (e.g. "are you
open on Sunday?" or "do you deliver to Green Hills?"), the agent searches this
folder for the most relevant chunks before answering. If nothing relevant is
found, it says it will confirm and follow up rather than guessing — so a thin
knowledge base means more "let me get back to you" replies, not wrong answers.
