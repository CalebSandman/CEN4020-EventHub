#!/usr/bin/env python3
# Spec: check_part3.md (same folder)

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GREEN, RED = "\U0001f7e2", "\U0001f534"


def run(script, args):
    r = subprocess.run([sys.executable, str(HERE / script), *args])
    print()
    return r.returncode


def main(argv):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    if len(argv) != 2:
        print("usage: check_part3.py <repo-path>")
        return 2
    repo = Path(argv[1])
    total = run("check_sdd_features_layout.py", [str(repo)])
    files = sorted(repo.glob("features/*/requirements.md"))
    if files:
        for f in files:
            total += run("check_req_form.py", [str(f)])
            total += run("check_ears.py", [str(f)])
        total += run("check_supersedes.py", [str(f) for f in files])
    else:
        print("   ⚪ no features/<folder>/requirements.md to check\n")
    total += run("check_structurizr.py", [str(repo)])
    verdict = "ELIGIBLE for grading" if total == 0 else f"NOT eligible: {total} failure(s)"
    print(f"{GREEN if total == 0 else RED} Part 3 gate: {verdict}")
    return min(total, 255)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
