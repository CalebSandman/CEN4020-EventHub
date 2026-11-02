"""Warn when code changed but the specification files did not (Call 4).

Usage: python scripts/check_spec_alignment.py [--strict] [base-ref]
Compares staged+unstaged changes (or ``base-ref...HEAD`` if given). Exit 1 only with --strict.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CODE = ("eventhub/eventhub/", "eventhub/data/")
SPEC = ("eventhub/spec/", "eventhub/docs/", "features/")


def changed(base):
    cmds = [["git", "diff", "--name-only", f"{base}...HEAD"]] if base else [
        ["git", "diff", "--name-only", "HEAD"], ["git", "diff", "--name-only", "--cached"]]
    out = set()
    for cmd in cmds:
        try:
            out.update(subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines())
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None
    return out


def main(argv):
    strict = "--strict" in argv
    refs = [a for a in argv if not a.startswith("--")]
    files = changed(refs[0] if refs else None)
    if files is None:
        print("spec-alignment: not a git checkout; skipped")
        return 0
    code = [f for f in files if f.startswith(CODE)]
    spec = [f for f in files if f.startswith(SPEC)]
    if code and not spec:
        print("WARNING: code changed but nothing under spec/ or docs/ did:")
        print("  " + "\n  ".join(sorted(code)))
        return 1 if strict else 0
    print("spec-alignment: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
