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
    python -m ruff check .
    node --test tests/browser_interactions.test.cjs
    python scripts/check_spec_alignment.py          # warns if code changed but spec/ and docs/ did not
From the repository root, install the hook with `git config core.hooksPath eventhub/scripts`.
The hook changes into the application directory before running checks. Node.js 22+ is required
for the JavaScript interaction tests. Ruff checks import style, comparison style, syntax and
selected correctness errors; it does not enforce whole-file formatting.

CI (`../.github/workflows/ci.yml`) runs these checks on pushes and pull requests.
The repository owner must configure branch protection to require the `checks` job before merging;
the workflow file alone cannot prevent a failing change from being merged.
