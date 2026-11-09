# Part 6 design changes report

## Existing design and incident cause

The repository is a Flask modular monolith with SQLite persistence. Before Part 6,
`eventhub/pricing.py` already used `Decimal`, integer minor units, and a
currency-specific `decimals` column. USD/EUR/GBP/CAD/MXN have two places, JPY
zero, and KWD three. It calculated JPY correctly. The Call 6 production incident
is a scenario: the broken release 1.3 formatting change is not present in this
checkout. The actual design gap was that pricing and rendering had no locale
boundary, so a future display change could confuse major and minor units.
`eventhub/boundary/__init__.py` formatted dates with one fixed pattern, and
`pricing.format_money` printed a code without regional conventions.

## Revised components and data flow

`pricing.calculate_price` remains the sole authoritative conversion and rounding
function. Its `PriceQuote.total_minor` goes unchanged to mock payment and the
order row; the purchase audit links to that order. `localization.format_money` receives the integer minor
amount and the currency's stored precision and scales only for display. The
checkout, confirmation, order history, and event catalog now use the same
presentation function. JPY uses a scale of one, so ¥4,500 remains 4,500 minor
units. Spanish selection changes session locale, labels, date order, grouping,
and symbol position; it never touches the amount or timezone. English text is the
translation key, Spanish resources live under `eventhub/locales`, and missing
keys fall back to English. A future locale needs resource and pattern registration
in `localization.py`, plus translations.
Checkout keeps its displayed quote in the signed session. Final purchase
recalculates the rate under the SQLite write lock and sends the buyer to a new
checkout quote if an administrator changed the total meanwhile. Direct purchase
and quick-buy still use the final server quote.

`eventhub/alerts.py` independently recomputes the expected order total from the
order's base USD cents, quantity, rate, discount, and currency precision. The
order now snapshots base USD cents; old databases receive a nullable migrated
column, populated from the current event price where possible. This is the one
historical approximation for pre-migration orders. Ratios outside configurable
0.50–1.50 bounds create one persistent `purchase_alerts` row per order. The
administrator dashboard and `/admin/alerts` run reconciliation and surface
alerts; new alerts also emit operator warnings. `manage.py scan-alerts` can be scheduled and exits nonzero while alerts
are open. This is a local human-facing integration point, with no email secrets.
It detects ¥45 stored against a ¥4,500 historical expectation, while allowing
legitimate quantity, rate, and student discount changes. The scan also runs in
the purchase transaction for immediate quote-versus-paid comparison.

`administration.update_rate` writes the rate and a `rate_audit` before/after row
in one SQLite transaction. Existing orders keep their rate, discount, precision,
and total. The C4 component source at `docs/architecture/workspace.dsl` now
includes Localization and Purchase Alerts. The generated PNG diagrams were not
regenerated.

## Why this design

The changes preserve the existing service boundaries and avoid another payment
or notification dependency. Integer minor amounts and `Decimal` remain the
arithmetic contract; regional rules exist only at rendering. Persistent alerts
can be inspected after a restart, and the separate rate audit provides change
accountability. The detector checks stored totals; it cannot prove that an
external payment provider charged the same amount because this project still
uses mock payment. See `part6-backup-recovery.md` for the separate operational
ownership decision.
