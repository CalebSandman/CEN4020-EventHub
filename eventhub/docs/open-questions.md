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
| Q8 | **Repeated confirmation requests**: Should a second rapid submission be rejected or deduplicated? | Two valid requests currently create two orders if inventory allows. Characterization test: `test_duplicate_submission_current_behavior`. Recommend an idempotency token tied to the checkout action, enforced by a unique database constraint. | `boundary/purchase_routes.py`, `purchasing.py` |
| Q9 | **Rate protection**: What requests per user/IP and time window are permitted? | No rate limiter exists. A bounded 200-request isolated test verifies invalid requests do not create orders and are individually audited. Recommend configurable rate limits and operational monitoring once a policy is approved. | `boundary/purchase_routes.py` |
| Q10 | **Email change and discount**: What eligibility rule applies after a registered email changes? | No email-edit route exists. Eligibility is recomputed from the current database email on each purchase; an isolated test verifies the discount stops after a database email edit. | `identity.py`, `pricing.py` |
| Q11 | **Performance acceptance**: What measured latency/throughput target and environment apply? | No quantitative target exists; test runtime and JUnit durations are observations only. | `project5-results.xml` |

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

Anonymous attempts that reach these routes are logged with `NOT_AUTHENTICATED`, a null user,
and the requested event, quantity and currency before redirecting to login. Requests rejected
by CSRF protection are not treated as valid purchase actions.

## Browser interaction policy

Card navigation waits 600 ms to allow a slower double-click to buy one ticket. Browsers do not
expose the operating system double-click interval, so this cannot support every configured
interval. A visible instant-buy button provides a direct keyboard/touch alternative. Modified
link clicks and keyboard activation retain native navigation. Automated JavaScript tests execute
the handlers with a simulated DOM and clock; real browser layout and touch testing remain needed.
