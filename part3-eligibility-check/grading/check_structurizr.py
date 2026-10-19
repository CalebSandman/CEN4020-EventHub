#!/usr/bin/env python3
# Spec: check_structurizr.md (same folder)

import re
import shutil
import subprocess
import sys
from pathlib import Path

VIEW_KINDS = ("systemContext", "container", "component")
# systemContext <identifier> [key] [description] {   (key and description are quoted or bare)
VIEW = re.compile(
    r"^\s*(?P<kind>systemContext|container|component)\s+(?P<scope>[^\s{\"]+)"
    r"(?:\s+(?P<key>\"[^\"]*\"|[^\s{\"]+))?(?:\s+(?P<desc>\"[^\"]*\"))?\s*\{?\s*$"
)
BLOCK = re.compile(r"^\s*(?P<name>workspace|model|views)\b.*\{\s*$")

GREEN, RED = "\U0001f7e2", "\U0001f534"
failures = 0


def emit(ok, text):
    global failures
    if not ok:
        failures += 1
    print(f"   {GREEN if ok else RED} {text}")


def strip_comments_and_strings(text):
    # Return the DSL with strings blanked and comments removed, for brace counting.
    text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    out = []
    for line in text.splitlines():
        line = re.sub(r'"[^"]*"', '""', line)
        line = re.sub(r"(#|//).*$", "", line)
        out.append(line)
    return "\n".join(out)


def find_views(dsl_text):
    # Yield (kind, key) for each view declaration inside the views block.
    in_views, depth, views_depth = False, 0, None
    originals = dsl_text.splitlines()
    for line, raw in zip(originals, strip_comments_and_strings(dsl_text).splitlines()):
        if not in_views and re.match(r"^\s*views\s*\{", raw):
            in_views, views_depth = True, depth
        if in_views:
            m = VIEW.match(line.split("#")[0].split("//")[0])
            if m and depth == views_depth + 1:
                key = m.group("key")
                yield m.group("kind"), key.strip('"') if key else None
        depth += raw.count("{") - raw.count("}")
        if in_views and depth <= views_depth:
            in_views = False


def run_cli(dsl: Path):
    cli = shutil.which("structurizr") or shutil.which("structurizr.sh")
    if not cli:
        print(f"   ⚪ structurizr CLI not on PATH; cannot prove the file opens in Structurizr Lite")
        return
    try:
        r = subprocess.run([cli, "validate", "-workspace", str(dsl)],
                           capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as e:
        emit(False, f"structurizr validate failed to run: {e}")
        return
    emit(r.returncode == 0, "structurizr validate passes"
         + ("" if r.returncode == 0 else f": {(r.stdout + r.stderr).strip()[:300]}"))


def finish():
    print(f"\n{failures} failure(s)")
    return min(failures, 255)


def main(argv):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if len(argv) != 2:
        print("usage: check_structurizr.py <repo-path>")
        return 2
    repo = Path(argv[1]).resolve()
    if not repo.is_dir():
        print(f"{RED} not a directory: {repo}")
        return 1
    print(f"check_structurizr — {repo}\n")

    dsl = repo / "workspace.dsl"
    emit(dsl.is_file(), "workspace.dsl at the repository root")
    if not dsl.is_file():
        return finish()

    text = dsl.read_text(encoding="utf-8", errors="replace")
    bare = strip_comments_and_strings(text)
    emit(bare.count("{") == bare.count("}"),
         f"braces balance ({bare.count('{')} open, {bare.count('}')} close)")
    for name in ("workspace", "model", "views"):
        emit(re.search(rf"^\s*{name}\b[^\n]*\{{", bare, re.M) is not None, f"{name} block present")
    run_cli(dsl)

    views = list(find_views(text))
    for kind in VIEW_KINDS:
        n = sum(1 for k, _ in views if k == kind)
        emit(n >= 1, f"{n} {kind} view(s) declared")

    diagrams = repo / "diagrams"
    emit(diagrams.is_dir(), "diagrams/ exists")
    if not diagrams.is_dir():
        return finish()
    files = sorted(p for p in diagrams.iterdir() if p.suffix.lower() in (".png", ".svg"))
    emit(len(files) >= len(views),
         f"diagrams/ holds {len(files)} PNG/SVG file(s) for {len(views)} declared view(s)")
    names = [p.stem.lower() for p in files]
    for kind, key in views:
        if key is None:
            continue
        emit(any(key.lower() in s for s in names), f"export for {kind} view '{key}' in diagrams/")

    return finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
