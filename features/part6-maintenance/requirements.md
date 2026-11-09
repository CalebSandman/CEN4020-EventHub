# Part 6 maintenance requirements from Call 6

These requirements capture the production incident and first post-launch
feature request in `CEN 4020 AI Project - Part 6.pdf`. They supplement, rather
than replace, the earlier EventHub requirements.

- **part6-001** (ubiquitous): EventHub shall calculate purchase totals with each supported currency's decimal precision and shall never scale JPY by 1/100.
- **part6-002** (ubiquitous): EventHub shall display currency amounts using the selected locale's symbols and separators without changing stored or charged amounts.
- **part6-003** (event-driven): When an exchange rate changes after checkout preview, EventHub shall require the buyer to review the new total before completing that purchase.
- **part6-004** (ubiquitous): Automated regression tests shall purchase in every supported currency and assert exact totals, including ¥4,500 rather than ¥45 for JPY.
- **part6-005** (event-driven): When an administrator updates a rate, EventHub shall store the new rate and an actor/old/new audit record, while existing orders retain historical values.
- **part6-006** (ubiquitous): Automated integration tests shall exercise authorized and unauthorized rate edits, invalid inputs, and later purchases.
- **part6-007** (event-driven): When an order total is significantly outside the amount expected from its historical event price, quantity, discount, rate, and precision, EventHub shall persist an alert and surface it to an administrator.
- **part6-008** (ubiquitous): EventHub shall support Spanish user-interface text with English fallback and a language selector, while allowing future translation resources.
- **part6-009** (ubiquitous): EventHub shall display dates by selected locale without changing stored dates or timezone meaning.
- **part6-010** (ubiquitous): The team shall identify a production backup owner and document safe backup, restore, and verification procedures.
- **part6-011** (ubiquitous): The operations team shall retain a runnable prior release and a rehearsed rollback procedure.

Operational requirements 010 and 011 require assignment and infrastructure
outside this repository; their local documentation is not proof of deployment.
