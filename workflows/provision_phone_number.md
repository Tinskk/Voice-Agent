# Provision the phone number

**Objective:** Get a working inbound phone number that connects callers to
the Vapi assistant.

**When to run:** Once, after `setup_vapi_assistant.md` (the assistant must
exist first). This buys a real number — a real, ongoing cost — so confirm with
the business owner before running.

## Inputs

| Input | Required | Notes |
|---|---|---|
| `VAPI_ASSISTANT_ID` set in `.env` | yes | From `setup_vapi_assistant.md`. |
| Preferred area code | no | Vapi picks a number if omitted or unavailable. |
| Whether the business wants to forward its existing number here later | no | See "Output" below — this workflow gets a *new* number; keeping the old one is a separate, later step. |

## Steps

1. **Buy a number and attach it to the assistant** —
   `python tools/provision_vapi_phone_number.py --area-code <code>` (omit
   `--area-code` to let Vapi choose). This is a real purchase — confirm with
   the owner first if you haven't already.
   - Expect: `ok: true` with a `number` and `phone_number_id`.
   - **Save `phone_number_id` as `VAPI_PHONE_NUMBER_ID` in `.env`.**

2. **Call the number yourself** and confirm you hear the assistant's greeting.

3. **If the assistant was recreated later** (a new `VAPI_ASSISTANT_ID`), re-run
   the same command — since `VAPI_PHONE_NUMBER_ID` is already set, it just
   re-attaches the existing number to the current assistant instead of buying
   a second one.

## Output

A working phone number, saved as `VAPI_PHONE_NUMBER_ID` in `.env`, that
connects callers to the current Vapi assistant.

## Edge cases

- **Want to keep the business's existing number instead:** this workflow only
  covers getting a new number through Vapi (the fastest path to a working
  demo). Porting an existing number is a separate, slower process (carrier
  Letter of Authorization) — the simpler middle ground is call-forwarding the
  existing number to the new Vapi number once it's live, which is fast and
  reversible. Ask the business owner which they want before assuming.
- **Purchase fails / no numbers available for the requested area code:** retry
  without `--area-code`, or try a nearby area code.
- **Re-running accidentally buys a second number:** only happens if
  `VAPI_PHONE_NUMBER_ID` wasn't saved to `.env` after the first successful
  run — check the Vapi dashboard for duplicate numbers and delete the unused one.

## Notes & learnings

- _(2026-09-11) Created._
