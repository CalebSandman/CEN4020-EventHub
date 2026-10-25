# Open questions and placeholders

Nothing below is a confirmed business rule. Each has ONE place to change it.

| # | Question | Placeholder in code | Where |
|---|----------|--------------------|-------|
| Q1 | **Student discount percentage** (never written down) | 10 % | `pricing.STUDENT_DISCOUNT_PERCENT` (loud comment) |
| Q2 | **Max tickets per order** ("excessively large", limit not stated) | 10 | `purchasing.MAX_TICKETS_PER_ORDER` |
| Q3 | **Audit retention** and who may read it | Admin-only reading; nothing auto-deleted | `audit.py` docstring |
| Q4 | **Session duration** (system-002: "after some time") | 30 min inactivity | `app.py` `SESSION_LIFETIME_MINUTES`, `identity.SESSION_LIFETIME` |
| Q5 | **Discount email edge cases** | `+tag@usf.edu` eligible; `@mail.usf.edu` not; case-insensitive | `pricing.is_discount_eligible` |
| Q6 | **Ticket hold during checkout** ("settled" in Call 4 but answer not in the written spec) | No hold. Availability is re-checked atomically at confirmation; if gone, the buyer gets the insufficient-availability error (ticket-purchasing-008) | `purchasing.purchase` |
| Q7 | **Exchange-rate values** | Illustrative development rates | `data/exchange_rates.json` |

## Requirement that cannot be met as written
**order-history-and-confirmations-004** ("shall not allow the order confirmation page to be
screenshotted"): a website cannot prevent OS-level screenshots. Implemented best-effort only:
`Cache-Control: no-store` on order pages and printing disabled via CSS. Recommend the
requirement be reworded or dropped.

## Behaviour to confirm
**event-browsing-007** (double-click = instant purchase) is implemented as specified, using the
buyer's selected currency and requiring login. It is irreversible without a confirm step; consider
adding one.

## Decision: what counts as a "purchase attempt" (logging-001)
Pressing **Checkout** (preview) or **Confirm purchase**, or double-clicking a card, is an attempt. Any of them being
*refused* is audited once, with the reason code. A checkout preview that succeeds is not logged (the later confirm is).
