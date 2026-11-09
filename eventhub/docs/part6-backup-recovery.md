# EventHub backup and recovery decision

EventHub persists users and password hashes, events and inventory, exchange rates,
orders, purchase audit rows, rate-change audit rows, and purchase alerts in SQLite
(`instance/eventhub.db` by default, or `EVENTHUB_DB`). The event and initial rate
JSON files are seeds only. They cannot reconstruct accounts, sales, current rates,
or audit history. There was no backup job or restore procedure in the repository
before Part 6. Part 6 has not installed a production backup service.

## Safe backup

The production operations owner should schedule an online SQLite backup using
`sqlite3.Connection.backup()` to a new dated file on separate storage. This API
produces a transactionally consistent snapshot even when EventHub uses WAL mode.
For example, after setting `EVENTHUB_DB` and choosing a protected destination:

```python
import os, sqlite3
source = sqlite3.connect(os.environ["EVENTHUB_DB"])
destination = sqlite3.connect("/secure-backups/eventhub-YYYYMMDD-HHMM.db")
try:
    source.backup(destination)
    assert destination.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
finally:
    destination.close()
    source.close()
```

Copying only a live `.db` file is unsafe when WAL files contain committed changes.
Protect backups as sensitive data, encrypt at rest and in transit, limit access,
retain multiple generations, and store a copy outside the application host. The
backup operator should record timestamps, integrity-check results, and failures.
The scheduler must notify a human when backup or integrity verification fails.

## Restore drill

1. Stop the application and prevent new writes. Preserve the failed database and
   its `-wal` and `-shm` files for investigation; do not run `reset-all`.
2. Choose a verified backup and copy it to a **new** recovery path. Run
   `PRAGMA integrity_check` against that copy.
3. Point a staging EventHub instance at the copy with `EVENTHUB_DB`. Verify
   account access, rates, inventory, order history, and audit/alert row counts.
4. Only after a change decision, switch the production database path to the
   verified copy while the application remains stopped. Restart and confirm reads
   and a controlled test purchase. Preserve the original files until signed off.

The production operations owner, recovery point objective, recovery time
objective, schedule, retention, encryption key custody, off-host storage, and
restore approver **remain unassigned decisions**. Call 6 requested that backup
ownership be assigned by Friday; the team must name a real owner by that
deadline. This document does not claim that assignment has happened.
