# Delivery & policies

## Delivery zones and fees

The actual zone keywords/fees used to calculate an order's delivery fee live
in `.env` as `DELIVERY_ZONES_JSON` (read by `app/pricing.py`). This file
mirrors those in plain language so the agent can also *explain* delivery
coverage conversationally, e.g. when a caller asks "do you deliver to my
area?" before getting to the point of placing an order. Generic Lagos
defaults — replace with the business's real coverage area:

- **Lekki & Ajah** (including VGC, Chevron) — ₦1,500
- **Victoria Island & Ikoyi** — ₦1,200
- **Ikeja & GRA** (including Opebi, Allen) — ₦2,000
- **Yaba & Surulere** (including Onipanu) — ₦1,800
- **Lagos Island** (including Marina, CMS, Obalende) — ₦1,500
- Anywhere else in Lagos — a flat ₦2,500 delivery fee applies

If a caller's address doesn't clearly match one of the zones above, say the
₦2,500 default fee applies and confirm it with them rather than guessing
which zone they meant.

## Cancellation / refund policy

Not yet finalized — confirm the real policy with the business owner. Until
then, the agent is instructed to say it will confirm rather than state one.

## Payment on delivery/pickup

Not yet finalized — confirm accepted payment methods.
