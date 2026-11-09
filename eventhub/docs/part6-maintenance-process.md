# Part 6 maintenance process report

## A. Overview

Call 6 describes a release 1.3 incident in which a two-decimal assumption turned
¥4,500 into ¥45 for three purchases. The team rolled back to 1.2 in about eleven
minutes. This repository did not contain that defective release: its existing
`pricing.calculate_price` already honors JPY's zero decimal places. Part 6
strengthened the implementation and tests against recurrence and added
localization, monitoring, and operational guidance. No production service was
changed.

## B. Problems found during repository review

The application uses Python 3.10+, Flask, SQLite, pytest, Selenium, and Node
interaction tests. Seeds define seven currencies: USD, EUR, GBP, CAD, MXN, JPY,
KWD. Existing code preserved historical order totals and rates, used integer
minor units with `Decimal`, and had purchase audit rows and administrator rate
editing. Its test suite had some JPY calculation coverage, but no all-currency
purchase matrix or explicit ¥4,500 versus ¥45 charge regression. The original
date filter used one English-oriented pattern; money display lacked currency
symbols and locale-specific separators. Most user-facing text lived directly in
templates. Purchase audit rows were manually viewable, but no comparison against
expected totals or alert queue existed. Rate changes recorded `updated_by` on
the current rate but no immutable before/after record. SQLite backup ownership
and a restore runbook were absent.

## C. Call 6 changes

**Currency:** `pricing.py` remains authoritative for base price, quantity,
student discount, exchange rate, and final half-up rounding. A separate
`localization.py` formatter scales the integer by its currency's *own* precision.
It displays symbols and separators for English (US) and Spanish (Spain). Checkout,
confirmation, history, and event cards use it. Neither session locale nor
formatting changes order or mock payment totals.
The checkout route keeps the displayed quote in the signed session. Purchase
rechecks the rate under a SQLite write lock and rejects a changed total with
`PRICE_CHANGED`, returning the buyer to a fresh checkout quote.

**Regression tests:** `tests/test_part6_maintenance.py` buys a ticket in every
seeded currency and checks quote, payment argument, stored total, audit row, and
rendered amount. It checks the student discount for every currency and an exact
¥4,500 incident case. Existing pricing tests retain half-up and KWD precision
checks.

**Exchange-rate administration:** Rate updates now write a `rate_audit` row with
actor, old rate, new rate, currency, and time in the same transaction. An HTTP
workflow test logs in as buyer and administrator, rejects buyer changes and a
NaN rate, updates EUR, checks the audit row, and proves that only subsequent
purchases use the new rate. The prior order retains its total and rate.

**Suspicious totals:** `alerts.scan_orders` reconstructs an expected amount from
the historical order data and records a unique alert if the ratio is outside
configurable 50%–150% bounds. The discount, rate, quantity, and precision are all
included before comparison. The admin dashboard and `/admin/alerts` scan and
surface records; a new alert also emits an operator warning in the application
log. `python manage.py scan-alerts` is a scheduler integration point:
it prints counts and returns exit code 1 while alerts remain open. Tests inject
a ¥45 stored total for a ¥4,500 order, prove one alert is created and deduplicated,
and prove a legitimate student discount does not alert. No real notification is
sent. Operations must arrange a schedule and route nonzero exits to a human.

**Localization:** The header language selector stores `en_US` or `es_ES` in the
session, retaining the choice through login. English remains the default.
Central resource lookup in `localization.py` supplies Spanish text from
`locales/es_ES.json` and `es_ES_errors.json`, with English fallback. Templates
use translation lookups rather than duplicated pages. Dates display month/day
in English (US) and day/month in Spanish (Spain), preserving the underlying ISO
timestamp and timezone. User-created event names, artists, and venues remain as
entered. Tests cover English and Spanish rendering, fallback, date and money
formats, and preservation of the JPY order total after switching language.

**Backups:** `part6-backup-recovery.md` identifies the protected SQLite data,
safe online backup API, integrity checks, staging restore drill, and off-host
protection. No backup job was installed. A production owner, schedule, and
recovery objectives remain to be assigned by the team by Friday.

**Release recovery:** `part6-release-recovery.md` records the rollback-first
procedure and the need to keep runnable prior releases. This repository does
not contain a production traffic switch or a rehearsed rollback.

**Requirements and modeling:** `features/part6-maintenance/requirements.md`
records Call 6 requirements; `spec/requirements_part6-maintenance.md` maps
them to design components and tests. The C4 component source was updated.
These files were completed during this review after initial implementation, so
the preferred requirements-first sequence cannot be claimed as the actual
chronology of this work.

## D. Maintainability improvements

The former presentation path mixed a fixed date filter and a generic money
string with route logic. `localization.py` now owns regional presentation rules,
while `pricing.py` remains arithmetic only. This avoids repeating scale and
separator logic in templates. `locales/` holds translation resources, so adding
a language mainly means registering a locale and supplying messages. `alerts.py`
isolates reconciliation from purchase coordination and HTTP authorization. The
database schema explicitly owns persistent alert and rate-audit tables. The
order base price snapshot removes dependence on a mutable event price for new
historical reconciliations. Existing checkout, inventory, identity, audit, and
purchase entry points remain intact.

## E. Implementation and challenges

The existing money representation was inspected before changes; no float or
two-decimal arithmetic was introduced. The first alert deduplication test found
that SQLite's `INSERT OR IGNORE` was reported as a new alert even when it ignored
a duplicate; the function now checks `rowcount`. A browser system test initially
failed because it expected the old symbol-free display. Its assertions were
updated to explicitly verify the new `$` and `€` symbols, while retaining its
exact stored-order assertion. The restricted test environment initially blocked
Selenium Manager's ChromeDriver lookup; the browser tests and full suite were
then run outside that restriction with approval. Existing untracked PDF and ZIP
files in the working tree were left untouched. The Part 6 work was committed on
`project6` and merged into `main` in both the CalebSandman and class `nerds`
repositories.

## F. Testing and verification

The final full pytest command, run from `eventhub/`, was
`$env:PYTHONPATH='.test-deps'; python -m pytest tests -q -o addopts=`.
It completed with **246 passed, 0 failed, 0 skipped** in 30.03 seconds.
`python -m ruff check eventhub tests/test_part6_maintenance.py manage.py`
reported “All checks passed!” before the final test run. The focused Part 6
file completed with **20 passed** before the final full run. Details and the
earlier environment-related failed attempts are in `part6-test-results.md`.
After the PDF requirements audit added formal traceability and an alert warning,
the full suite was rerun with the cached ChromeDriver: **246 passed, 0 failed,
0 skipped** in 31.51 seconds. Ruff and the strict spec-alignment check passed.
After merging Part 6 into `main`, the complete suite was run again with the
cached ChromeDriver: **246 passed, 0 failed, 0 skipped** in 32.24 seconds.

## G. Remaining limitations

Payment is simulated, so the stored total and mock payment argument can be
compared but an external processor cannot be independently reconciled. Alerts
are persistent and visible to administrators, but no email, paging integration,
or production scheduler is configured. The default ratio bounds are broad and
should be tuned with operations data. Historical orders created before this
migration have base prices backfilled from the current event record; if that
price had changed, their expected amount is approximate. New orders snapshot
their base price. The Spanish catalog covers the principal interface and common
messages; uncommon dynamically composed validation strings fall back to English.
The placeholder student discount and exchange-rate seeds remain customer open
questions. Backup ownership and infrastructure remain operational decisions.

## H. Conclusion

The maintained checkout keeps exact currency-specific arithmetic, adds an
explicit JPY regression across display and stored purchase values, records rate
changes, and provides a local path for humans to see suspicious totals. Locale
support is isolated from money and purchase logic. The full existing and new
test suite passed after these changes.
