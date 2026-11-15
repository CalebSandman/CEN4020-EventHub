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
