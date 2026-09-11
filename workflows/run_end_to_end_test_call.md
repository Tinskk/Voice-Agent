# Run an end-to-end test call

**Objective:** Prove the whole system works with a real phone call, not just
individually-tested pieces — confirm an order, a reservation, and a lead all
land correctly where the owner will actually look for them.

**When to run:** Once after `provision_phone_number.md`, and again after any
material change to the system prompt, tools, or `app/` before trusting it with
real customers.

## Inputs

| Input | Required | Notes |
|---|---|---|
| The provisioned phone number | yes | From `provision_phone_number.md`. |
| Access to the Google Sheet and Calendar | yes | To verify results directly. |

## Steps

1. **Call and ask an FAQ** — e.g. "are you open on Sundays?" Expect a specific
   answer sourced from `knowledge_base/`, or an honest "I'll confirm and
   follow up" if that content isn't filled in yet — not a guessed answer.

2. **Ask for a recommendation** — e.g. "what do you recommend?" or "what's
   vegetarian?" Expect an answer using only items actually in the Menu sheet.

3. **Place a delivery order** — multiple items, a delivery address inside one
   of your configured zones. Confirm the assistant reads back a subtotal,
   delivery fee, and total before confirming, and reads back an order ID at
   the end.
   - **Verify:** open the `Orders` tab (or `python tools/daily_orders_report.py`)
     and confirm the row has the right items, subtotal, fee, total, and status `Pending`.

4. **Book a reservation** — a date/time/party size. Confirm the assistant
   reads the date/time/party size back before booking.
   - **Verify:** open the target Google Calendar and confirm the event exists
     at the right time with the right details in its description.

5. **Try booking a slot you know is already taken** (call again, ask for the
   exact same time as step 4) — confirm the assistant offers fresh
   alternatives instead of double-booking or just failing silently.

6. **Trigger a catering/event lead** — e.g. "I want to book catering for a
   40-person office event next month." Confirm the assistant collects name,
   phone, and event details, and states it'll follow up rather than quoting a price.
   - **Verify:** open `Customers_Leads` (or
     `python tools/leads_followup_report.py`) and confirm the row has sensible
     `Interest`, `Qualified`, and `Follow Up Needed` values.

7. **Trigger an escalation** (if `ESCALATION_TRANSFER_NUMBER` is set) — ask
   for a manager, or simulate a complaint about a past order. Confirm the
   assistant says it's transferring before doing so, and that the transfer
   number actually rings.

## Output

A completed call log matching every verification point above — order in the
Sheet, event on the Calendar, lead in the Sheet, transfer working — confirmed
by looking directly at the Sheet/Calendar, not by trusting the call "sounded right."

## Edge cases

- **Assistant guesses instead of calling a tool:** note the exact question
  that triggered it and tighten the relevant system-prompt section
  (`tools/vapi_system_prompt_template.md`) — this is exactly the kind of
  thing to fix from a real transcript, not guess about in advance.
- **Delivery address doesn't match the zone you expected:** check
  `DELIVERY_ZONES_JSON` keywords include the phrasing the caller actually
  used (street abbreviations, "near X" phrasing, etc.).
- **Reservation booked at the wrong time:** almost always a timezone mismatch
  — confirm `BUSINESS_TIMEZONE` matches the business's actual timezone.
- **A step fails partway through:** don't patch it live mid-call-testing;
  finish the test call, then fix and re-test steps 3 onward cleanly (state
  from a broken order/booking can otherwise confuse the next test).

## Notes & learnings

- _(2026-09-11) Created._
