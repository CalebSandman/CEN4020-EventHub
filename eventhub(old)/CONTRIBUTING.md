# Contributing

* Small changes, each reviewed by a human before merge. AI-generated code is read line by line.
* Money is computed only in `eventhub/pricing.py` (see `docs/decisions/0001-money-representation.md`).
* Audit rows are written only through `eventhub/audit.py`; routes never log purchases themselves.
* Components must not import Flask (except `identity` guards and `boundary/`) and must take a
  database connection as an argument so they can be unit tested alone.
* **Definition of done:** (1) reviewed by someone else, (2) tests written and passing,
  (3) `spec/` updated to match, (4) every automatic check passes.

## Checks
    pip install -r requirements-dev.txt
    python -m pytest
    python scripts/check_spec_alignment.py          # warns if code changed but spec/ and docs/ did not
    cp scripts/pre-commit .git/hooks/pre-commit     # run tests + alignment before each commit
CI (`.github/workflows/ci.yml`) re-runs everything on each push and has the final say.
