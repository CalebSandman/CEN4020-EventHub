"""Smoke-test a retained release against a COPY of a verified backup.

Usage: python scripts/drill_rollback.py PRIOR_RELEASE_DIR BACKUP_DB
The prior release directory must contain eventhub/run.py and eventhub/eventhub/.
This never switches traffic or writes to the supplied backup.
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eventhub import recovery

SMOKE = """
from decimal import Decimal, ROUND_HALF_UP
from eventhub.app import create_app
from eventhub import database
app = create_app({'TESTING': True, 'CSRF_ENABLED': False})
client = app.test_client()
assert client.get('/events').status_code == 200
conn = database.connect(app.config['DATABASE_PATH'])
event = conn.execute('SELECT base_price_cents FROM events ORDER BY id LIMIT 1').fetchone()
yen = conn.execute("SELECT rate, decimals FROM exchange_rates WHERE currency='JPY'").fetchone()
assert event is not None and yen is not None and yen['decimals'] == 0
expected = int((Decimal(event['base_price_cents']) / 100 * Decimal(yen['rate'])).quantize(
    Decimal(1), rounding=ROUND_HALF_UP))
conn.close()
with client.session_transaction() as session:
    session['currency'] = 'JPY'
    session['locale'] = 'en_US'
page = client.get('/events')
assert page.status_code == 200
assert f'¥{expected:,} JPY' in page.data.decode('utf-8')
print('Prior release event list and JPY price: OK')
"""


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 2
    release = Path(argv[1]).resolve()
    if not (release / "run.py").is_file():
        release = release / "eventhub"
    if not (release / "eventhub" / "app.py").is_file():
        print("Prior release directory does not contain the EventHub application.")
        return 2
    backup = Path(argv[2]).resolve()
    try:
        counts = recovery.verify_backup(backup)
    except (ValueError, OSError, sqlite3.DatabaseError) as exc:
        print("Backup verification failed:", exc)
        return 1
    with tempfile.TemporaryDirectory(prefix="eventhub-rollback-") as scratch:
        database_copy = Path(scratch) / "drill.db"
        shutil.copy2(backup, database_copy)
        env = dict(os.environ, EVENTHUB_DB=str(database_copy),
                   EVENTHUB_SECRET_KEY="rollback-drill-only")
        current_pythonpath = env.get("PYTHONPATH", "")
        if current_pythonpath:
            env["PYTHONPATH"] = os.pathsep.join(
                str(Path(entry).resolve()) for entry in current_pythonpath.split(os.pathsep) if entry
            )
        try:
            run = subprocess.run([sys.executable, "-c", SMOKE], cwd=release,
                                 env=env, capture_output=True, text=True, timeout=30)
        except subprocess.TimeoutExpired:
            print("Prior release smoke test timed out.")
            return 1
        if run.returncode:
            print(run.stderr or run.stdout)
            return 1
        print(run.stdout.strip())
        print("Backup table counts:", counts)
        print("The supplied backup was not modified.")
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
