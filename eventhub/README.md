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

## Maintenance (stop the server first for the reset commands)
    python manage.py list-events                      # id, tickets left / capacity
    python manage.py set-tickets [EVENT_ID] [QUANTITY] [CAPACITY]      # set tickets left (and optionally capacity)
    python manage.py reset-sales                      # delete orders + audit log, restore all tickets (keeps users, rates)
    python manage.py reset-all                        # delete the whole database, rebuild from data files

## Unit tests
    Located in `tests` folder

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
