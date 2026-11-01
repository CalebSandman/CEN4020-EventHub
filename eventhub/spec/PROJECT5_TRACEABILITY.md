# Project 5 requirement-to-test mapping

IDs are from `features/*/requirements.md`. Browser tests use Selenium and a real local HTTP server. Other tests use isolated SQLite databases.

| Requirement IDs | Tests with relevant assertions |
|---|---|
| user-accounts-and-authentication-001, -002, -003, -006, -008 | `test_identity.py`, `test_system_selenium.py::test_complete_purchase_journey_and_persistence`, `test_project5_integration.py::test_home_currency_hash_and_email_eligibility` |
| user-accounts-and-authentication-004, -005, -009, -010, -011, -012, -013 | `test_app_routes.py::test_protected_pages_redirect_to_login_with_return_url`, `test_login_returns_to_requested_page`, `test_unauthenticated_sees_no_protected_data_and_no_records_created`, `test_system_selenium.py::test_browser_auth_search_and_access_control` |
| event-browsing-and-searching-001, -002, -003, -004, -005 | `test_app_routes.py::test_event_list_and_detail`, `test_search_by_artist_and_venue`, `test_system_selenium.py::test_complete_purchase_journey_and_persistence`, `test_browser_auth_search_and_access_control` |
| event-browsing-and-searching-006, -007, -008 | `test_system_selenium.py::test_complete_purchase_journey_and_persistence`, `test_app_routes.py::test_double_click_buys_one_ticket`, `test_catalog.py` seed tests, `browser_interactions.test.cjs` |
| event-browsing-and-searching-009, -010, -011 | `test_app_routes.py::test_no_match_message_then_full_list`, `test_search_text_is_escaped`, `test_system_selenium.py::test_browser_auth_search_and_access_control` |
| currency-support-001, -002, -003, -008, -010 | `test_pricing.py`, `test_app_routes.py::test_currency_selection_changes_displayed_prices`, `test_system_selenium.py::test_complete_purchase_journey_and_persistence` |
| currency-support-004, -009 | `test_pricing.py` seed tests, `test_administration.py` rate-update tests, `test_purchasing.py::test_order_keeps_rate_after_admin_changes_it` |
| currency-support-005, -006 | `test_app_routes.py::test_unsupported_currency_selection_rejected`, `test_project5_integration.py::test_direct_invalid_purchase_preserves_state` |
| student-discount-001, -002 | `test_pricing.py::test_discount_eligibility`, `test_app_routes.py::test_student_discount_end_to_end`, `test_project5_integration.py::test_home_currency_hash_and_email_eligibility` |
| ticket-purchasing-001, -002, -003, -004, -005, -006 | `test_system_selenium.py::test_complete_purchase_journey_and_persistence`, `test_purchasing.py::test_successful_purchase` |
| ticket-purchasing-007, -008, -009, -010, -011, -012, -013 | `test_purchasing.py::test_cannot_exceed_availability`, `test_concurrent_buyers_never_oversell`, `test_project5_integration.py::test_two_buyers_final_ticket_repeated`, `test_direct_invalid_purchase_preserves_state` |
| ticket-purchasing-014 | `test_purchasing.py::test_abandoned_checkout_leaves_data_untouched`, `test_app_routes.py::test_abandoned_checkout_changes_nothing` |
| order-history-and-confirmations-001, -002, -003, -005 | `test_app_routes.py::test_full_purchase_flow`, `test_cannot_open_another_users_order`, `test_system_selenium.py::test_complete_purchase_journey_and_persistence` |
| order-history-and-confirmations-004 | Unverifiable as written: a website cannot prevent OS screenshots. `test_app_routes.py::test_full_purchase_flow` checks `Cache-Control: no-store` only. |
| logging-and-auditing-001, -002, -003, -004, -006, -007 | `test_audit.py`, `test_purchasing.py::test_every_attempt_is_audited_with_its_reason`, `test_project5_integration.py::test_two_buyers_final_ticket_repeated`, `test_direct_invalid_purchase_preserves_state`, `test_system_selenium.py::test_browser_invalid_quantity_is_audited` |
| logging-and-auditing-005, -008, -009 | `test_app_routes.py::test_admin_updates_rate_and_reviews_audit`, `test_buyer_denied_admin_pages` |
| administration-and-architecture-documentation-003 | `test_administration.py`, `test_app_routes.py::test_admin_updates_rate_and_reviews_audit` |
| server-side-validation-and-security-001, -002, -003, -004, -005 | `test_boundary_validation.py`, `test_project5_integration.py::test_direct_invalid_purchase_preserves_state`, `test_system_selenium.py::test_browser_invalid_quantity_is_audited` |
| server-side-validation-and-security-007, -008, -009, -010 | `test_app_routes.py::test_buyer_denied_admin_pages`, `test_admin_updates_rate_and_reviews_audit`, `test_buyer_cannot_become_admin_by_registering_with_role_field` |
| system-001, -002 | `test_boundary_validation.py`, `test_app_routes.py::test_session_expires`, `test_server_rejects_bad_inputs_with_distinct_messages` |
| system-003, -004 | `test_app_routes.py::test_responsive_markup`, `test_system_selenium.py` browser rendering; mobile usability still needs device evaluation |
| system-005, -006 | Flask startup in `test_app_routes.py`; `run.py` is inspected as a deployment artifact |

Superseded IDs: currency-support-007, responsive-web-interface-001/-002, administration-and-architecture-documentation-001/-002, server-side-validation-and-security-006, and user-accounts-and-authentication-007 are covered by their replacements.

Call 5 topics without EARS IDs: `test_project5_integration.py::test_duplicate_submission_current_behavior`, `test_bounded_excessive_invalid_requests`, and `test_home_currency_hash_and_email_eligibility` characterize current behavior. Policy decisions and the missing performance target are in `docs/open-questions.md`.
