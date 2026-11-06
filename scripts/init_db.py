"""Create an empty database with the 5 user profiles and one demo account per role.

Usage:  python scripts/init_db.py
Every demo account's password is: Password123!
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from werkzeug.security import generate_password_hash  # noqa: E402
from app import create_app                      # noqa: E402
from app.db import init_db, get_db              # noqa: E402
from app.constants import ALL_ROLES, RENOVATION_ITEMS, PROPERTY_TYPES  # noqa: E402
from app.entity.user_account import UserAccount  # noqa: E402

DEMO_PASSWORD = "Password123!"
DEMO_ACCOUNTS = [  # (username, name, role)
    ("admin", "Alice Admin", "User Admin"),
    ("designer", "Daniel Designer", "Interior Designer"),
    ("customer", "Chloe Customer", "Customer"),
    ("pmanager", "Peter Platform", "Platform Manager"),
    ("smanager", "Sarah Sales", "Sales Manager"),
]


def create_profiles(db):
    for role in ALL_ROLES:
        db.execute("INSERT INTO user_profile (profile_name, description) VALUES (?, ?)",
                   (role, f"{role} account"))
    db.commit()


_DEMO_HASH = []


def _demo_hash():
    """Hash the shared demo password once and reuse it (hashing is deliberately slow)."""
    if not _DEMO_HASH:
        _DEMO_HASH.append(generate_password_hash(DEMO_PASSWORD))
    return _DEMO_HASH[0]


def create_demo_accounts(db):
    for username, name, role in DEMO_ACCOUNTS:
        profileID = db.execute("SELECT profile_id FROM user_profile WHERE profile_name = ?",
                               (role,)).fetchone()[0]
        acc = UserAccount(None, username, name, f"{username}@idp.example.com", "91234567", profileID)
        acc.passwordHash = _demo_hash()
        acc.saveUserAccount()


def create_starter_rule(db):
    """A first estimation rule (#47) so the cost breakdown (#29) works on an empty database."""
    sm = db.execute("SELECT account_id FROM user_account WHERE username = 'smanager'").fetchone()[0]
    cur = db.execute("INSERT INTO estimation_rule (rule_name, created_by, created_date, is_active) "
                     "VALUES ('Starter rates', ?, datetime('now', 'localtime'), 1)", (sm,))
    rid = cur.lastrowid
    for code, name, unit, rate in RENOVATION_ITEMS:
        db.execute("INSERT INTO unit_rate (rule_id, item_code, item_name, unit, rate) VALUES (?, ?, ?, ?, ?)",
                   (rid, code, name, unit, rate))
    for ptype in PROPERTY_TYPES:
        db.execute("INSERT INTO rule_factor VALUES (?, 'PROPERTY', ?, 1.0)", (rid, ptype))
    db.commit()


def main():
    app = create_app()
    with app.app_context():
        init_db()
        db = get_db()
        create_profiles(db)
        create_demo_accounts(db)
        create_starter_rule(db)
        print("Database created at", app.config["DATABASE"])
        print("Demo logins (password %s):" % DEMO_PASSWORD)
        for username, _, role in DEMO_ACCOUNTS:
            print(f"  {username:10} {role}")


if __name__ == "__main__":
    main()
