#!/usr/bin/env python3
# Spec: check_req_form.md (same folder)

import re
import sys
from pathlib import Path

ID = r"[a-z0-9]+(?:-[a-z0-9]+)*-\d{3}"
FENCE = re.compile(r"^ {0,3}(```|~~~)")
REQ = re.compile(rf"^- \*\*(?P<id>{ID})\*\* \([^)]+\): +\S.*$")
# Any line that opens with an ID-like token, split into the parts the form rules look at.
PARTS = re.compile(
    r"^(?P<indent>[ \t]*)(?P<marker>(?:[-*+]|\d+[.)])[ \t]+)?(?P<open>\*\*|__)?"
    r"(?P<token>[A-Za-z0-9_-]*\d)(?P<colon>:)?(?P<close>\*\*|__)?(?P<rest>.*)$"
)
ID_OK = re.compile(rf"^{ID}$")
REST_OK = re.compile(r"^ \([^)]+\): +\S")
LIST_ITEM = re.compile(r"^[ \t]*(?:[-*+]|\d+[.)])[ \t]")
SUPERSEDES = re.compile(rf"^[ \t]+supersedes:[ \t]*(?P<id>{ID})[ \t]*$")
SUPERSEDES_ANY = re.compile(r"^[ \t]*(?:(?:[-*+]|\d+[.)])[ \t]+)?supersedes[ \t]*:", re.I)
SUPERSEDED_BY = re.compile(rf"\bsuperseded by (?P<id>{ID})\.?\s*$")
SUPERSEDED_ANY = re.compile(r"\bsuperseded by\s+[`*(\[]*[A-Za-z0-9_-]*\d", re.I)

GREEN, RED = "\U0001f7e2", "\U0001f534"


def broken_rules(m):
    # The form rules a candidate line breaks, in the order the spec names them.
    rules = []
    if m.group("indent"):
        rules.append("the line must start at the left margin")
    if m.group("marker") != "- ":
        rules.append("the bullet must be `- `")
    if not (m.group("open") == "**" and m.group("close") == "**"):
        rules.append("the ID must be bold: `**id-nnn**`")
    elif m.group("colon"):
        rules.append("nothing but the ID goes inside the bold")
    if not ID_OK.match(m.group("token")):
        rules.append("the ID must be lowercase letters or digits joined by single hyphens and end in three digits")
    if not REST_OK.match(m.group("rest")):
        rules.append("`(<pattern>): ` and a sentence must follow the ID")
    return rules or ["the line does not have the form `- **id-nnn** (pattern): sentence`"]


class Checker:
    def __init__(self):
        self.failures = 0
        self.reqs = {}        # id -> dict(superseded, line)

    def emit(self, ok, text):
        if not ok:
            self.failures += 1
        print(f"   {GREEN if ok else RED} {text}")

    def read_file(self, md: Path, label=None):
        label = label or str(md)
        lines = md.read_bytes().decode("utf-8-sig").splitlines()
        in_fence = False
        last_id = None        # the requirement a supersedes: line may attach to
        prev = None           # what the previous line was: "req", "cont", or None
        for n, line in enumerate(lines, 1):
            where = f"{label}:{n}"
            if FENCE.match(line):
                in_fence = not in_fence
                last_id, prev = None, None
                continue
            if in_fence:
                continue
            if not line.strip():
                last_id, prev = None, None
                continue
            if SUPERSEDES_ANY.match(line):
                s = SUPERSEDES.match(line)
                if not s:
                    self.emit(False, f"{where}: malformed supersedes line, must be an indented `supersedes: <id>`")
                elif last_id is None:
                    self.emit(False, f"{where}: supersedes line has no requirement directly above it")
                else:
                    self.emit(True, f"{where}: supersedes {s.group('id')} under {last_id}")
                prev = None
                continue
            m = PARTS.match(line)
            candidate = m and (m.group("open") or m.group("rest").lstrip().startswith("("))
            if candidate:
                if REQ.match(line):
                    last_id, prev = self.requirement(where, line, REQ.match(line).group("id")), "req"
                else:
                    self.emit(False, f"{where}: malformed requirement line: " + "; ".join(broken_rules(m)))
                    last_id, prev = None, None
                continue
            if prev == "req" and not line.startswith("#") and not LIST_ITEM.match(line):
                self.emit(False, f"{where}: a requirement must be on one line ({last_id} continues here)")
                prev = "cont"
                continue
            last_id, prev = None, None
        count = len(self.reqs)
        self.emit(count > 0, f"{label} holds {count} requirement(s)")

    def requirement(self, where, line, rid):
        if rid in self.reqs:
            self.emit(False, f"{where}: duplicate ID {rid} (also at {self.reqs[rid]['line']})")
            return rid
        by = SUPERSEDED_BY.search(line)
        self.reqs[rid] = {"superseded": by is not None, "line": where}
        self.emit(True, f"{rid}: line form")
        if by is None and SUPERSEDED_ANY.search(line):
            self.emit(False, f"{rid}: the line must end with `superseded by <id>`")
        return rid

    def summary(self):
        active = sum(1 for r in self.reqs.values() if not r["superseded"])
        print(f"\n{len(self.reqs)} requirement(s), {active} active, {self.failures} failure(s)")


def main(argv):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(argv) != 2:
        print("usage: check_req_form.py <file.md>")
        return 2
    md = Path(argv[1])
    if not md.is_file():
        print(f"{RED} not a file: {md}")
        return 1
    print(f"check_req_form — {md}\n")
    checker = Checker()
    try:
        checker.read_file(md, str(md))
    except UnicodeDecodeError as e:
        print(f"   {RED} {md} is not valid UTF-8: {e.reason} at byte {e.start}")
        return 1
    checker.summary()
    return min(checker.failures, 255)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
