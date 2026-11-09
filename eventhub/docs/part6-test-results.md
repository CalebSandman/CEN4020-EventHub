# Part 6 test results

Working directory: `eventhub/` on branch `project6`. The repository already
contains local `.test-deps`, so commands set `PYTHONPATH` to use its pytest and
Selenium packages. Tests use temporary databases, not `instance/eventhub.db`.

| Command | Actual result |
| --- | --- |
| `$env:PYTHONPATH='.test-deps'; python -m pytest tests/test_part6_maintenance.py -q -o addopts=` | 20 passed in 1.89s |
| `$env:PYTHONPATH='.test-deps'; python -m pytest tests/test_system_selenium.py -q -o addopts=` (outside restricted sandbox) | 3 passed in 12.72s |
| `$env:PYTHONPATH='.test-deps'; python -m pytest tests -q -o addopts=` (outside restricted sandbox) | 246 passed, 0 failed, 0 skipped in 30.03s |
| `$env:PYTHONPATH='.test-deps'; python -m ruff check eventhub tests/test_part6_maintenance.py manage.py` | All checks passed |
| `$env:PYTHONPATH='.test-deps'; $env:EVENTHUB_CHROMEDRIVER='C:/Users/cam/.cache/selenium/chromedriver/win64/156.0.8078.80/chromedriver.exe'; python -m pytest tests -q -o addopts=` (after PDF audit) | 246 passed, 0 failed, 0 skipped in 31.51s |
| `python scripts/check_spec_alignment.py --strict` (after PDF audit) | spec-alignment: ok |

Representative final output:

```text
........................................................................ [ 29%]
........................................................................ [ 58%]
.................................................. [ 87%]
..............................                                           [100%]
246 passed in 30.03s
```

The first full run in the restricted sandbox ended with 241 passed and 3 setup
errors because Selenium Manager could not access its ChromeDriver download URL.
After an outside-sandbox run made ChromeDriver available, one browser assertion
identified the expected symbol-format change; the assertion was updated to
check `$89.00 USD` and `€163.76 EUR`. The subsequent browser and full runs above
both passed. No test result was changed solely to hide a calculation failure.
