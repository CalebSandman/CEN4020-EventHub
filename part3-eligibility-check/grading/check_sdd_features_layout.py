#!/usr/bin/env python3
# Spec: check_sdd_features_layout.md (same folder)

import re
import sys
from pathlib import Path

FOLDER = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ID_TOKEN = re.compile(r"^- \*\*(?P<prefix>[A-Za-z0-9-]+)-\d+\*\*")

GREEN, RED = "\U0001f7e2", "\U0001f534"
failures = 0


def emit(ok, text):
    global failures
    if not ok:
        failures += 1
    print(f"   {GREEN if ok else RED} {text}")


def check_folder(folder: Path):
    emit(bool(FOLDER.match(folder.name)), f"folder name lowercase-hyphen: features/{folder.name}/")
    md = folder / "requirements.md"
    emit(md.is_file(), f"features/{folder.name}/requirements.md exists")
    if not md.is_file():
        return
    text = md.read_bytes().decode("utf-8-sig", errors="replace")
    for n, line in enumerate(text.splitlines(), 1):
        m = ID_TOKEN.match(line)
        if m:
            emit(m.group("prefix") == folder.name,
                 f"features/{folder.name}/requirements.md:{n}: ID prefix '{m.group('prefix')}' is the folder name")


def main(argv):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(argv) != 2:
        print("usage: check_sdd_features_layout.py <repo-path>")
        return 2
    repo = Path(argv[1]).resolve()
    if not repo.is_dir():
        print(f"{RED} not a directory: {repo}")
        return 1
    print(f"check_sdd_features_layout — {repo}\n")

    features = repo / "features"
    emit(features.is_dir(), "features/ exists")
    if not features.is_dir():
        print(f"\n0 feature folder(s), {failures} failure(s)")
        return failures
    folders = sorted(p for p in features.iterdir() if p.is_dir() and not p.name.startswith("."))
    emit(bool(folders), f"features/ holds {len(folders)} feature folder(s)")
    emit((features / "system").is_dir(), "features/system/ exists")
    for folder in folders:
        check_folder(folder)

    print(f"\n{len(folders)} feature folder(s), {failures} failure(s)")
    return min(failures, 255)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
