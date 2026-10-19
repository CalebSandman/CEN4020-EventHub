#!/usr/bin/env python3
# Spec: check_supersedes.md (same folder)

import re
import sys
from pathlib import Path

ID = r"[a-z0-9]+(?:-[a-z0-9]+)*-\d{3}"
REQ = re.compile(rf"^- \*\*(?P<id>{ID})\*\* \([a-z-]+\): (?P<text>.+?)\s*$")
SUPERSEDES = re.compile(rf"^\s+supersedes:\s*(?P<id>{ID})\s*$")
SUPERSEDED_BY = re.compile(rf"\bsuperseded by (?P<id>{ID})\.?\s*$")

GREEN, RED = "\U0001f7e2", "\U0001f534"
failures = 0


def emit(ok, text):
    global failures
    if not ok:
        failures += 1
    print(f"   {GREEN if ok else RED} {text}")


def read_file(md: Path, reqs):
    # Add the file's requirements to reqs: id -> dict(line, superseded_by, supersedes).
    if not md.is_file():
        emit(False, f"{md} is not a file")
        return
    try:
        lines = md.read_bytes().decode("utf-8-sig").splitlines()
    except UnicodeDecodeError as e:
        emit(False, f"{md} is not valid UTF-8: {e.reason} at byte {e.start}")
        return
    last_id = None
    for n, line in enumerate(lines, 1):
        sup = SUPERSEDES.match(line)
        if sup:
            if last_id is not None:
                reqs[last_id]["supersedes"].append(sup.group("id"))
            continue
        m = REQ.match(line)
        if not m:
            last_id = None
            continue
        rid = m.group("id")
        by = SUPERSEDED_BY.search(m.group("text"))
        reqs.setdefault(rid, {"line": f"{md}:{n}", "superseded_by": by.group("id") if by else None,
                              "supersedes": []})
        last_id = rid


def check_links(reqs):
    links = 0
    for rid, r in reqs.items():
        for old in r["supersedes"]:
            links += 1
            if old not in reqs:
                emit(False, f"{rid} supersedes {old}, which is in none of the files given")
                continue
            emit(reqs[old]["superseded_by"] == rid,
                 f"{rid} supersedes {old}; {old} ends with 'superseded by {rid}'")
        if r["superseded_by"]:
            links += 1
            new = r["superseded_by"]
            if new not in reqs:
                emit(False, f"{rid} superseded by {new}, which is in none of the files given")
                continue
            emit(rid in reqs[new]["supersedes"], f"{rid} superseded by {new}; {new} has 'supersedes: {rid}'")
    return links


def main(argv):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(argv) < 2:
        print("usage: check_supersedes.py <file.md> [<file.md> ...]")
        return 2
    print("check_supersedes\n")
    reqs = {}
    for arg in argv[1:]:
        read_file(Path(arg), reqs)
    links = check_links(reqs)
    print(f"\n{len(reqs)} requirement(s), {links} link end(s) checked, {failures} failure(s)")
    return min(failures, 255)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
