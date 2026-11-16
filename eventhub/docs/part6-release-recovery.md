# Release recovery procedure for Call 6

Call 6 kept release 1.2 live after the 1.3 yen incident. This repository has no
deployment pipeline or production switch, so this is an operational procedure,
not a claim that a rollback has been automated or rehearsed here.

1. Keep each release artifact, its dependency lock or environment, migration
   notes, and configuration reference available after a newer release ships.
2. Before rollout, back up the SQLite database using the online method in
   `part6-backup-recovery.md` and test that the previous artifact can start
   against a compatible copy. Schema compatibility must be checked because
   reverting code alone may not reverse a database migration.
3. On a pricing incident, stop new purchases, switch traffic to the known-good
   compatible release, and verify the purchase quote and mock charge in affected
   currencies before restoring traffic. Preserve logs and the suspect database.
4. Investigate and test a correction in a separate environment. Run all currency,
   rate-edit, alert, and full system tests before considering redeployment.
5. Record incident timing, decision maker, version identifiers, affected orders,
   and follow-up actions. Arrange an on-call human and practice the switch.

Release-artifact storage, traffic switching, on-call ownership, and rehearsed
rollback are deployment responsibilities still outside this local project.
Use `python manage.py backup-db PATH` before a local rollback drill and
`python manage.py verify-backup PATH` after copying the snapshot to staging.
Run `python scripts/drill_rollback.py PRIOR_RELEASE_DIR BACKUP_DB` to boot a
retained release against a temporary copy of the verified backup and check the
event list and JPY price. Record the release hash, backup timestamp, result,
and elapsed time. A local drill does not prove the production traffic switch
works.
