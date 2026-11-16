# Part 7 configuration management report

## Assignment and transcript analysis

The Part 7 assignment asks for an English or Spanish configuration and requires
the top-level menu to appear in Spanish when Spanish is selected. Its three
deliverables are a change report (20%), a report explaining GenAI-assisted code
tracing (60%), and updated code with system-test evidence (20%).

Call 6 gives the reason for this work. After an incident in which yen prices
were scaled by 1/100, the team chose rollback-first recovery, exact purchase
tests for every currency, an admin rate-edit test, order-total alerts, and a
backup owner. The customer's first new feature request is localization:
Spanish text, regional dates, and currency formatting, with room for other
languages. The lead developer requires requirements, specification, code, and
tests in that order. The codebase already implemented most of these items for
Part 6; this Part 7 work preserves and verifies them. The repository does not
establish a production alert recipient or backup owner.

## How GenAI was used to trace the feature

The GenAI assistant read the five-page assignment, including the Call 6
transcript, and inspected the repository. It used file discovery and targeted
text searches for `locale`, `language`, `Spanish`, `format_date`,
`format_money`, and `nav`, then read the matching routes, session helper,
templates, translation resource, and tests. This is the actual tracing path:

| Requested behavior | Code located with GenAI assistance | Finding and action |
| --- | --- | --- |
| Choose English or Spanish | `eventhub/boundary/catalog_routes.py::set_locale`, `eventhub/templates/base.html` | Existing POST selector validates registered locales, stores a session choice, and returns to a safe local URL. Kept. |
| Keep choice through login | `eventhub/boundary/auth_routes.py::_rotate_session` | Existing session rotation saves and restores the locale. Kept and tested. |
| Translate top-level menu | `eventhub/templates/base.html`, `eventhub/boundary/__init__.py::_template_globals`, `eventhub/localization.py::translate`, `eventhub/locales/es_ES.json` | Visible menu actions already used `tr`. The `aria-label="Main"` did not; it now uses `tr('Main')` and the resource includes `Principal`. |
| Configure initial language | `eventhub/boundary/context.py::session_locale`, `eventhub/app.py::create_app` | Existing fallback was fixed at `en_US`. Added `EVENTHUB_DEFAULT_LOCALE`, with per-session selection taking priority and unsupported values normalizing to English. |
| Regional dates and money | `eventhub/localization.py`, template `dt` and `money` filters | Already implemented in Part 6. Localization scales display using each currency's precision, including zero-decimal JPY; it does not change stored values. |
| Incident regression and rate updates | `eventhub/tests/test_part6_maintenance.py`, `eventhub/pricing.py`, `eventhub/purchasing.py`, `eventhub/boundary/admin_routes.py` | Existing tests cover exact totals in all seven currencies, a ¥4,500 yen purchase, admin rate edits, and subsequent purchases. Preserved in the full suite. |

The assistant identified these modules as candidates; it did not assume every
match needed editing. Reading the code and tests showed that the visible menu
and most localization behavior were already present. The resulting change was
limited to the missing configuration and accessible menu text, plus focused
verification. This distinction matters: describing all Part 6 work as newly
implemented for Part 7 would misrepresent the project history.

## Changes made for Part 7

Requirements are in `features/part7-configuration-management/requirements.md`;
the design and acceptance mapping are in
`spec/requirements_part7-configuration-management.md`. The application reads
`EVENTHUB_DEFAULT_LOCALE` (default `en_US`) for a visitor with no saved choice.
Users can switch languages from the existing header selector at any time.
Unknown locale codes do not become active. The main navigation's accessible
name now follows the selected language. `tests/test_part7_localization.py`
checks the guest, buyer, and admin menus, navigation and authentication
persistence, switching back to English, and configured/default fallback.

The remaining translation catalog uses English source strings as keys and
falls back to English when a translation is absent. This is an incremental
localization system, so some longer or dynamic messages can still appear in
English. The Part 7 top-level menu requirement is fully covered. Event names,
artist names, and venue names are user/content data and are not translated.

## Follow-up corrections after the coverage audit

The coverage audit found parameterized registration, purchase, and rate-edit
errors that were still rendered in English, plus a fixed English welcome flash.
The translator now recognizes bounded numeric message patterns at presentation
time and includes the welcome message in the Spanish resource. Service error
codes, audit records, and English behavior remain unchanged.

Call 6 also requested a human-facing alert and recoverable backups. The alert
scan now sends pending alert JSON to an operator-configured HTTPS webhook. A
successful delivery records `notified_at`; a failure remains pending for retry.
The alert ID is stable so the receiving service can deduplicate at-least-once
delivery. `backup-db` creates a new online SQLite copy and checks its integrity
and key table counts; `verify-backup` repeats that check without modifying the
copy. The CLI refuses to overwrite an existing backup. Both paths have focused
tests, including migration of existing alert tables.

The repository cannot create a working email address, select a real backup
owner, install a production scheduler, or switch production traffic without
deployment access. The webhook URL and backup storage must be supplied by the
operator. The rollback runbook now names a local compatibility drill, but a
production rollback rehearsal still requires the deployed environment.
Deployment steps and ownership fields are listed in
`docs/part7-operations-setup.md`.

## Verification

See `docs/part7-test-results.md` for the command and observed full-suite result.
The suite includes HTTP and browser system tests as well as the Part 6 currency,
rate-update, and localization regressions. Tests use isolated temporary SQLite
databases, so the normal instance database is not reset.
