# Part 7 configuration management specification

Source requirements: `../../features/part7-configuration-management/requirements.md`.
The Part 6 localization implementation predates Part 7; this specification
records its current design and the additional configuration and menu checks.

| Requirement | Design and acceptance rule | Verification |
| --- | --- | --- |
| part7-001 | `/locale` accepts only registered locale codes, stores the choice in the signed session, and redirects to a local URL. Login and registration preserve the choice. | `test_part7_localization.py` selection and authentication tests |
| part7-002 | All visible header actions, including conditional buyer/admin links, use the shared `tr` translator. The main navigation's accessible name is translated too. | `test_part7_localization.py` guest, buyer, admin menu checks |
| part7-003 | `EVENTHUB_DEFAULT_LOCALE` seeds the app default for sessions without a selected locale. Unknown defaults normalize to English; rejected selections retain the active language. A valid per-session choice takes priority. | `test_part7_localization.py` default and fallback checks |
| part7-004 | Localization is limited to templates, date, and money rendering. The pricing and purchase services use integer minor units and stored currency precision. | Part 6 currency/yen, rate-update, and locale-preservation tests |
| part7-005 | Focused menu checks and the existing HTTP, browser, and currency regression suite pass. | `docs/part7-test-results.md` |

Trace path: PDF request -> these requirements -> `eventhub/app.py`,
`eventhub/boundary/context.py`, `eventhub/boundary/catalog_routes.py`,
`eventhub/boundary/auth_routes.py`, `eventhub/boundary/__init__.py`,
`eventhub/templates/base.html`, `eventhub/localization.py`, and
`eventhub/locales/es_ES.json` -> focused and full-suite tests.
