"""Database access shared by all entity classes (SQLite)."""
import os
import sqlite3
from flask import current_app, g

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


def get_db():
    """Return the SQLite connection for the current request."""
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
        if current_app.config.get("TESTING"):
            # test databases are thrown away, so skip waiting for the disk
            g.db.execute("PRAGMA synchronous = OFF")
            g.db.execute("PRAGMA journal_mode = MEMORY")
    return g.db


def close_db(_e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create all tables (drops existing data)."""
    db = get_db()
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        db.executescript(f.read())
    db.commit()
