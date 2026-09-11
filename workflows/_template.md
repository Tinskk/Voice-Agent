# <Workflow Name>

**Objective:** One sentence. What this produces and for whom.

**When to run:** The trigger — a request phrasing, a schedule, another workflow finishing.

## Inputs

| Input | Required | Notes |
|---|---|---|
| `topic` | yes | Ask if not provided. |
| `date_range` | no | Defaults to the last 7 days. |

Ask for anything required and missing before starting. Don't guess inputs that
change what gets produced.

## Steps

1. **<Step name>** — `python tools/<tool>.py --arg value`
   - Expect: what a good result looks like.
   - If empty/zero results: what to do instead.

2. **<Step name>** — `python tools/<tool>.py --input .tmp/<file>.json`
   - Expect: ...

3. **Deliver** — push the final output to <Google Sheet / Slides / doc> and return
   the link. Nothing in `.tmp/` counts as delivered.

## Output

What the user gets: a link, a summary, a count. Be specific — this is the
definition of done.

## Edge cases

- **No results found:** report it and stop; don't fabricate filler.
- **Auth expired:** delete `token.json`, re-run, complete the browser prompt.
- **Rate limited:** wait and retry once; if it persists, report it and note the
  limit in this section.
- **Partial failure:** deliver what succeeded, state clearly what didn't.

## Notes & learnings

Append what each run teaches — quirks, limits, better methods. Date the entries.

- _(2026-09-11) Created._
