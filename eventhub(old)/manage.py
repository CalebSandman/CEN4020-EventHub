"""Management CLI.

    python manage.py create-admin "Ada Admin" ada@example.com   # prompts for password
    python manage.py init-db
"""
from __future__ import annotations

import getpass
import sys

from eventhub.app import create_app
from eventhub import database, identity


def main(argv) -> int:
    if len(argv) < 2 or argv[1] not in ("create-admin", "init-db"):
        print(__doc__)
        return 2
    app = create_app()  # creates schema + seeds as a side effect
    if argv[1] == "init-db":
        print("Database ready:", app.config["DATABASE_PATH"])
        return 0
    if len(argv) != 4:
        print(__doc__)
        return 2
    password = getpass.getpass("Password: ")
    conn = database.connect(app.config["DATABASE_PATH"])
    try:
        user = identity.create_admin_user(conn, argv[2], argv[3], password)
    except identity.IdentityError as exc:
        print("Error:", exc.message)
        return 1
    finally:
        conn.close()
    print(f"Created administrator {user.email}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
