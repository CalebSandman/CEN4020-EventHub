# Part 7 operations setup

The repository supplies tested commands and a notification protocol. A working
notification destination and backup owner must be provisioned in the deployment
environment; no email account or webhook can be created by source code alone.

## Alert delivery

1. Provision an HTTPS relay that accepts a JSON POST and routes it to the
   on-call human or team. Set `EVENTHUB_ALERT_WEBHOOK_URL` in the scheduler's
   secret configuration. Do not commit its URL if it contains a token.
2. Schedule `python manage.py scan-alerts` at least every five minutes, including
   Friday and Saturday nights. Run it with the production `EVENTHUB_DB` value.
3. The payload contains `type`, stable `alert_id`, `order_id`,
   `expected_minor`, `actual_minor`, `currency`, and `reason`. The relay should
   deduplicate by `alert_id`, show a human the amounts in currency minor units,
   and link the operator to `/admin/alerts` on the deployed site.
4. A 2xx response records `notified_at`; an error leaves the alert pending for
   the next scan. Route command failures to the same on-call channel. Confirm
   that a deliberately anomalous order in staging reaches a human before
   relying on the schedule.

## Backups and rollback

1. Assign one named backup owner and a separate restore approver. Record them
   in the production operations roster, along with recovery objectives and
   off-host destination. A project role or proposed address is not a working
   mailbox or a named owner.
2. Schedule `python manage.py backup-db NEW_DATED_PATH` to separate protected
   storage. Never reuse a destination path. Protect the files and monitor
   failures; the command verifies each new snapshot before it reports success.
3. Run `python manage.py verify-backup PATH` on a retained snapshot, then run
   `python scripts/drill_rollback.py PRIOR_RELEASE_DIR PATH` against a copy.
   Record the release hash, backup timestamp, elapsed recovery time, and result.
4. Practice the actual production traffic switch with the deployment owner.
   The local drill proves only that a retained release can read a copied backup
   and render an event list and a zero-decimal JPY price.
