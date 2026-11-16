# Part 7 test results

Run from `eventhub/` on the `project7` branch. The existing local `.test-deps`
directory supplied pytest, Selenium, and Ruff. `EVENTHUB_CHROMEDRIVER` pointed
to the locally cached ChromeDriver. Tests used temporary databases.

| Command | Observed result |
| --- | --- |
| `$env:PYTHONPATH='.test-deps'; $env:EVENTHUB_CHROMEDRIVER='C:/Users/cam/.cache/selenium/chromedriver/win64/156.0.8078.80/chromedriver.exe'; python -m pytest tests -q -o addopts= -p no:cacheprovider` | 250 passed in 35.21s; no failures or skips. Includes Selenium system tests. |

The first focused Part 7 run found a test-only URL error: `/admin` redirects
permanently to `/admin/`. The test now requests `/admin/`. The complete suite
result above was obtained after that correction.

## Follow-up coverage audit

| Command or check | Observed result |
| --- | --- |
| Full pytest suite with the same `PYTHONPATH` and ChromeDriver settings | 258 passed in 33.58s; no failures or skips. |
| `python -m pytest tests/test_part7_localization.py tests/test_part7_operations.py -q -o addopts= -p no:cacheprovider` | 12 passed after the final English/Spanish menu assertions. |
| `python -m ruff check eventhub tests/test_part7_localization.py tests/test_part7_operations.py manage.py scripts/drill_rollback.py` | All checks passed. |
| `python scripts/check_spec_alignment.py --strict` | `spec-alignment: ok`. |

A local rollback drill archived `main` at `4717df4`, created and verified a
backup of an isolated seeded database, and ran
`python scripts/drill_rollback.py PRIOR_RELEASE_DIR BACKUP_DB`. The prior
release served the event list and rendered the independently expected JPY
price. The drill used a temporary copy and did not modify the backup or switch
production traffic. No external webhook or live recipient was used in tests;
delivery success, failure, retry, and deduplication were verified with an
injected sender.
