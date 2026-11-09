# Part 6 specification and traceability

Source requirements: `../../features/part6-maintenance/requirements.md`. This
specification records the revised design and test mapping. It was documented
during the Part 6 review after the initial implementation; the PDF's preferred
requirements-first chronology cannot be claimed retroactively.

| Requirement | Design / acceptance rule | Evidence |
| --- | --- | --- |
| part6-001, 002 | `pricing.calculate_price` uses integer minor units and `Decimal`; `localization.format_money` uses the stored currency precision only at display. | `test_part6_maintenance.py::test_every_currency_purchase_matches_quote_audit_and_display`, `test_yen_4500_incident_never_becomes_45` |
| part6-003 | Signed-session checkout quote is compared with the final rate read under SQLite write lock; changed totals return `PRICE_CHANGED` before payment or order creation. | `test_rate_change_after_checkout_requires_new_confirmation` |
| part6-004 | Purchase matrix covers USD, EUR, GBP, CAD, MXN, JPY, KWD, exact charge argument, order amount, display, discount, audit link. | `test_every_currency_purchase_matches_quote_audit_and_display`, `test_every_currency_student_discount_is_applied_before_rounding` |
| part6-005, 006 | Admin route and service enforce role; rate edit and `rate_audit` write share a transaction; order rate/total snapshots remain historical. | `test_admin_rate_workflow_and_historical_order`, `test_administration.py` |
| part6-007 | Alert scan independently recomputes expected minor total from order snapshot; ratio outside 0.50–1.50 stores a unique row; admin page and CLI surface it. | `test_alert_scan_detects_one_percent_total_without_discount_false_positive`, `test_admin_alert_page_surfaces_bad_historical_total` |
| part6-008, 009 | Session locale selects translation resources, date pattern, and money layout; missing keys use English; underlying order values are unchanged. | `test_locale_selection_rendering_fallback_and_value_preservation` |
| part6-010 | SQLite online backup and staging restore procedure documented. | `docs/part6-backup-recovery.md`; owner remains unassigned |
| part6-011 | Rollback-first and release preservation procedure documented. | `docs/part6-release-recovery.md`; production rehearsal remains external |

Architecture: `docs/architecture/workspace.dsl` and
`docs/part6-design-changes.md`. Test outcomes: `docs/part6-test-results.md`.
