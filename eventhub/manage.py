"""Management CLI (stop the web server before using reset commands).

    python manage.py init-db
    python manage.py create-admin "Ada Admin" ada@example.com    # prompts for password
    python manage.py list-events                                  # ids, tickets left / capacity
    python manage.py set-tickets EVENT_ID AVAILABLE [CAPACITY]    # change one event's tickets
    python manage.py reset-sales [--yes]    # delete orders+audit log, restore all tickets; keeps users/rates
    python manage.py reset-all   [--yes]    # delete the whole database and rebuild from data files
"""
from __future__ import annotations

import getpass
import os
import sys

from eventhub import database, identity, maintenance

# The CLI never serves requests, so it does not need a real session key.
os.environ.setdefault("EVENTHUB_SECRET_KEY", "cli-only-not-used-for-sessions")
from eventhub.app import ROOT, create_app

USAGE = __doc__


def _confirm(argv, prompt) -> bool:
    if "--yes" in argv:
        return True
    return input(f"{prompt} Type 'yes' to continue: ").strip().lower() == "yes"


def main(argv) -> int:
    args = [a for a in argv[1:] if a != "--yes"]
    if not args:
        print(USAGE)
        return 2
    cmd = args[0]

    if cmd == "reset-all":
        path = os.environ.get("EVENTHUB_DB", str(ROOT / "instance" / "eventhub.db"))
        if not _confirm(argv, f"This DELETES {path} (all users, orders, audit log, rates)."):
            print("Cancelled.")
            return 1
        for suffix in ("", "-wal", "-shm"):
            if os.path.exists(path + suffix):
                os.remove(path + suffix)
        app = create_app()  # rebuilds schema, rates and events from the data files
        print("Database rebuilt from data files:", app.config["DATABASE_PATH"])
        print("Create an administrator again with: python manage.py create-admin")
        return 0

    app = create_app()  # creates schema + seeds as a side effect
    conn = database.connect(app.config["DATABASE_PATH"])
    try:
        if cmd == "init-db":
            print("Database ready:", app.config["DATABASE_PATH"])
        elif cmd == "list-events":
            for e in maintenance.list_events(conn):
                print(f"{e['id']:>3}  {e['tickets_available']:>4} / {e['capacity']:<4}  {e['name']}")
        elif cmd == "set-tickets" and len(args) in (3, 4):
            maintenance.set_tickets(conn, int(args[1]), int(args[2]),
                                    int(args[3]) if len(args) == 4 else None)
            print("Updated.")
        elif cmd == "reset-sales":
            if not _confirm(argv, "This deletes ALL orders and audit records and restores all tickets."):
                print("Cancelled.")
                return 1
            print(maintenance.reset_sales(conn))
        elif cmd == "create-admin" and len(args) == 3:
            user = identity.create_admin_user(conn, args[1], args[2], getpass.getpass("Password: "))
            print(f"Created administrator {user.email}")
        else:
            print(USAGE)
            return 2
    except (identity.IdentityError, maintenance.MaintenanceError) as exc:
        print("Error:", getattr(exc, "message", None) or exc)
        return 1
    except ValueError:
        print("Error: ids and ticket counts must be whole numbers.")
        return 1
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
