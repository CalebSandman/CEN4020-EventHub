# Part 7 configuration management requirements

Source: `CEN 4020 AI Project - Part 7.pdf`, pages 1-2 and Call 6 on pages 3-5.
These refine the existing Part 6 localization requirements without changing the
purchase arithmetic contract.

- **part7-001** (ubiquitous): EventHub shall offer English and Spanish as selectable interface languages and retain the selection during navigation and authentication.
- **part7-002** (state-driven): When Spanish is selected, EventHub shall display each available top-level menu action and the main navigation label in Spanish; when English is selected, it shall display them in English.
- **part7-003** (ubiquitous): Operators shall be able to configure the default interface language for visitors with no language selection. Unsupported defaults shall fall back to English; unsupported selections shall leave the active language unchanged.
- **part7-004** (ubiquitous): Language changes shall affect presentation only. Purchase totals, stored currency precision, exchange rates, and order history shall remain unchanged.
- **part7-005** (ubiquitous): Automated tests shall cover guest, buyer, and administrator menus in both languages, selection persistence, and the configured default, while the full system suite remains green.
- **part7-006** (state-driven): In Spanish mode, common and parameterized validation feedback shall render in Spanish without changing service-layer error codes or stored audit values.
- **part7-007** (event-driven): When a suspicious order alert exists, an operator-run scan shall send pending alerts to a configured human-facing notification endpoint and retry failed deliveries without creating duplicate alert records.
- **part7-008** (ubiquitous): Operators shall have a tested, non-destructive SQLite backup and integrity-verification command to support recovery drills.

The transcript additionally asks for regional dates and money, currency and rate
regressions, alerts, and recoverability. These were implemented or documented in
Part 6; Part 7 must preserve them. Deployment of alert paging and assignment of
a production backup owner remain operational decisions outside this codebase.
