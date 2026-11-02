#!/usr/bin/env python3
# Spec: check_ears.md (same folder)

import re
import sys
from pathlib import Path

PATTERNS = {"ubiquitous", "event-driven", "state-driven", "unwanted", "optional", "complex"}
SIMPLE = {"event-driven": "when", "state-driven": "while", "unwanted": "if", "optional": "where"}
ORDER = {"where": 0, "while": 1, "when": 2, "if": 2}

FENCE = re.compile(r"^ {0,3}(```|~~~)")
REQ = re.compile(r"^- \*\*(?P<id>[^*\s]+)\*\* \((?P<pattern>[^)]*)\):\s+(?P<text>.+?)\s*$")
SUPERSEDED_BY = re.compile(r"\bsuperseded by [A-Za-z0-9_-]+\.?\s*$")
CODE = re.compile(r"`[^`]*`")
QUOTED = re.compile(r"\"[^\"]*\"|“[^”]*”")
EMPHASIS = re.compile(r"(?<!\w)[*_]+|[*_]+(?!\w)")
SHALL = re.compile(r"\bshall\b", re.I)
NAME = re.compile(r"\{[^{}]*\}")
KEYWORD = re.compile(r"\b(when|while|if)\b|(?:^|,)\s*\b(where)\b", re.I)
OPENER = re.compile(r"^(when|while|if|where)\b", re.I)
NAME_FIRST = re.compile(r"^(the\s+)?\{[^{}]*\}", re.I)
NAME_LAST = re.compile(r"\{[^{}]*\}\s*$")
AFTER_CLAUSE = re.compile(r"(,|\bthen\b)\s*(the\s+)?\{[^{}]*\}\s*$", re.I)
IF_THEN = re.compile(r"\bif\b.*\bthen\b", re.I)

GREEN, RED = "\U0001f7e2", "\U0001f534"


def prepare(text):
    # The sentence as the wording checks see it (spec 015 and 020).
    text = SUPERSEDED_BY.sub("", text)
    text = CODE.sub(" ", text)
    text = QUOTED.sub(" ", text)
    text = EMPHASIS.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def keywords(pre):
    # The keyword clauses before "shall", in order of appearance.
    return [(m.group(1) or m.group(2)).lower() for m in KEYWORD.finditer(pre)]


class Checker:
    def __init__(self):
        self.failures = 0
        self.reqs = {}        # id -> dict(prefix, pattern, text, line)

    def emit(self, ok, text):
        if not ok:
            self.failures += 1
        print(f"   {GREEN if ok else RED} {text}")

    def read_file(self, md: Path, label=None):
        label = label or str(md)
        lines = md.read_bytes().decode("utf-8-sig").splitlines()
        in_fence = False
        for n, line in enumerate(lines, 1):
            if FENCE.match(line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            m = REQ.match(line)
            if not m:
                continue
            rid, pattern = m.group("id"), m.group("pattern")
            prefix = rid.rsplit("-", 1)[0] if "-" in rid else rid
            text = prepare(m.group("text"))
            self.reqs[rid] = {"prefix": prefix, "pattern": pattern, "text": text, "line": f"{label}:{n}"}
            if pattern not in PATTERNS:
                self.emit(False, f"{rid}: pattern '{pattern}' is not one of {sorted(PATTERNS)}")
                continue
            self.emit(True, f"{rid}: pattern {pattern}")
            self.check_wording(rid, pattern, text)

    def check_wording(self, rid, pattern, text):
        shall = SHALL.search(text)
        self.emit(shall is not None, f"{rid}: contains 'shall'")
        if shall is None:
            return
        pre = text[:shall.start()]
        names = NAME.findall(text)
        self.emit(len(names) == 1, f"{rid}: exactly one system name in braces, found {len(names)}")
        if len(names) != 1:
            return
        self.emit(NAME_LAST.search(pre) is not None, f"{rid}: 'shall' directly after the {{system name}}")
        found = keywords(pre)
        if pattern == "ubiquitous":
            self.emit(NAME_FIRST.match(pre) is not None,
                      f"{rid}: ubiquitous, the {{system name}} comes first (only 'The' may precede it)")
            return
        if pattern in SIMPLE:
            own = SIMPLE[pattern]
            self.emit(OPENER.match(pre) is not None and OPENER.match(pre).group(1).lower() == own,
                      f"{rid}: {pattern} opens with '{own.capitalize()}'")
            others = sorted(set(found) - {own})
            self.emit(not others, f"{rid}: {pattern}, no keyword other than '{own}' before 'shall'"
                      + (f" (found {', '.join(others)})" if others else ""))
        else:
            self.emit(OPENER.match(pre) is not None, f"{rid}: complex opens with a keyword")
            distinct = sorted(set(found))
            self.emit(len(distinct) >= 2, f"{rid}: complex, {len(distinct)} different keyword(s) before 'shall' (needs 2)")
            ranks = [ORDER[k] for k in found]
            self.emit(ranks == sorted(ranks), f"{rid}: complex, clauses in EARS order (Where, While, When/If)")
        if "if" in found:
            self.emit(IF_THEN.search(pre) is not None, f"{rid}: 'then' after 'If' and before 'shall'")
        if pattern != "unwanted":
            self.emit("," in pre, f"{rid}: {pattern}, comma before 'shall'")
        self.emit(AFTER_CLAUSE.search(pre) is not None,
                  f"{rid}: the {{system name}} directly after the last clause (after the comma or 'then')")

    def summary(self):
        print(f"\n{len(self.reqs)} requirement(s), {self.failures} failure(s)")


def main(argv):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(argv) != 2:
        print("usage: check_ears.py <file.md>")
        return 2
    md = Path(argv[1])
    if not md.is_file():
        print(f"{RED} not a file: {md}")
        return 1
    print(f"check_ears — {md}\n")
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
