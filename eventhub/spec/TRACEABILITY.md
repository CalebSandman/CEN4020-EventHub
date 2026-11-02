# Requirement -> component -> tests
(Superseded requirements are covered by their replacements: system-001/003/004/005/006, auth-008, currency-009.)

| Requirement(s) | Component | Main tests |
|---|---|---|
| auth-001..003, 006, 008 | `identity` | `test_identity.py` |
| auth-004/005/009..013 | `identity` guards + `boundary` | `test_app_routes.py` (redirect/return-URL/no-records tests) |
| system-002 | `identity` session policy | `test_identity.py::test_session_*`, `test_app_routes.py::test_session_expires` |
| event-browsing-001..005, 008..011 | `catalog`, `boundary/catalog_routes` | `test_catalog.py`, `test_app_routes.py` |
| event-browsing-007 | `boundary/catalog_routes.quick_buy` + `static/app.js` | `test_double_click_*` |
| currency-001..006, 008..010 | `pricing`, `administration` | `test_pricing.py`, `test_administration.py` |
| student-discount-001/002 | `pricing.is_discount_eligible` | `test_pricing.py::test_discount_eligibility` |
| ticket-purchasing-001..014 | `purchasing`, `inventory` | `test_purchasing.py` (incl. concurrency + abandonment) |
| order-history-001..003, 005 | `purchasing`, `boundary/purchase_routes` | `test_purchasing.py`, `test_full_purchase_flow` |
| order-history-004 | best effort only (see open-questions) | `test_full_purchase_flow` (no-store) |
| logging-001..009 | `audit`, `purchasing`, `administration` | `test_audit.py`, `test_purchasing.py::test_every_attempt_*`, `test_admin_updates_rate_and_reviews_audit` |
| server-side-validation-001..005, 007..010, system-001 | `purchasing.validate_quantity`, `pricing`, `boundary`, `identity` | `test_purchasing.py`, `test_app_routes.py` (RBAC, CSRF) |
| admin-003 | `administration`, `boundary/admin_routes` | `test_administration.py`, `test_app_routes.py` |
| system-003/004 | HTML + responsive CSS | `test_responsive_markup` |
| system-005/006 | Flask single deployable | `run.py` |
