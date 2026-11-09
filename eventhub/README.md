# EventHub

Ticketing web app (Python 3.10+ / Flask / SQLite), a single deployable modular monolith that follows
the C4 component model in `docs/architecture/workspace.dsl`.

## Run
    python -m venv .venv && . .venv/bin/activate
    pip install -r requirements-dev.txt
    export EVENTHUB_SECRET_KEY="$(python -c 'import secrets;print(secrets.token_hex(32))')"
    python manage.py create-admin "Ada Admin" ada@example.com    # optional, prompts for password
    python run.py                                                # http://127.0.0.1:5000
    python -m pytest                                             # all tests

## Miminum needed to run
    pip install -r requirements-dev.txt
    python manage.py create-admin "Ada Admin" ada@example.com
    # optional, prompts for password
    python run.py
    # http://127.0.0.1:5000

## Maintenance (stop the server before reset commands)
    python manage.py list-events                      # id, tickets left / capacity
    python manage.py set-tickets [EVENT_ID] [QUANTITY] [CAPACITY]      # set tickets left (and optionally capacity)
    python manage.py reset-sales                      # delete orders + audit log, restore all tickets (keeps users, rates)
    python manage.py reset-all                        # delete the whole database, rebuild from data files
    python manage.py scan-alerts                     # reconcile stored purchases; exit 1 if alerts need review

Administrators can review suspicious totals at `/admin/alerts`. Run `scan-alerts`
periodically with an external scheduler and route its nonzero exit status to the
operations team. The scan uses each order's stored rate, discount, quantity,
currency precision, and base price; it does not contact a payment service.
Buyers can choose English or Spanish in the header. Locale changes affect display
only and persist in the session through login.

Backup and restore guidance is in `docs/part6-backup-recovery.md`. No production
backup schedule or owner is configured in this repository.

## Unit tests
    Located in `tests` folder

## Project 5 automated tests

Install `requirements-dev.txt`, then run the complete suite from this `eventhub/` directory:

    python -m pytest tests/ -v --junitxml=project5-results.xml

The pytest command includes Selenium browser system tests, the existing Node.js interaction
tests, isolated HTTP integration tests, component tests, and a 200-round two-buyer final-ticket
race. Chrome or Chromium and Node.js must be
installed; Selenium Manager obtains a matching ChromeDriver on first use. To use a local
driver, set `EVENTHUB_CHROMEDRIVER` to its path. Set
`EVENTHUB_CONCURRENCY_ROUNDS=5` for a quicker development run. Each test starts its own
temporary database; the normal `instance/eventhub.db` is never reset. The JUnit XML file
contains test counts, durations, and failure details. Requirement mapping and unresolved
decisions are in `spec/PROJECT5_TRACEABILITY.md` and `docs/open-questions.md`.

`EVENTHUB_SECRET_KEY` signs the session cookies. Keep it secret and constant; if unset, a random key is used and
everyone is logged out on each restart.

Set `EVENTHUB_COOKIE_SECURE=1` when serving over HTTPS. The database is created at `instance/eventhub.db`
(override with `EVENTHUB_DB`). Events load from `data/events.json`; initial rates from `data/exchange_rates.json`.

## C4 component -> module
| C4 component | Module | Needs Flask? |
|---|---|---|
| HTTP Boundary | `eventhub/boundary/` (+ `app.py` wiring) | yes |
| Identity & Authorization | `eventhub/identity.py` | only the route-guard decorators |
| Event Catalog | `eventhub/catalog.py` | no |
| Purchasing & Orders | `eventhub/purchasing.py` | no |
| Pricing | `eventhub/pricing.py` | no |
| Inventory Repository | `eventhub/inventory.py` | no |
| Audit Trail | `eventhub/audit.py` | no |
| Administration | `eventhub/administration.py` (service) + `boundary/admin_routes.py` (adapter) | service: no |
| EventHub Database | `eventhub/database.py` | no |
| Event Setup Data | `data/events.json` | - |

Every non-boundary module takes a `sqlite3.Connection`, so each has its own test file in `tests/`
and runs against a temporary database. Dependencies follow the C4 arrows (e.g. `purchasing` ->
`catalog`, `pricing`, `inventory`, `audit`; `pricing` never imports `purchasing`).

## Read before relying on it
See `docs/open-questions.md`: the discount %, per-order limit, session length and exchange rates are
**placeholders**, and the "no screenshots" requirement cannot be enforced by a website.
