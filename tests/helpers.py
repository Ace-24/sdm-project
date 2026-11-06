"""Small helpers to create test records directly in the database."""
from app.db import get_db
from app.entity.user_account import UserAccount


def account_id(username):
    return UserAccount.findByUsername(username).accountID


def add_category(name, status="Active"):
    db = get_db()
    cur = db.execute("INSERT INTO category (category_name, description, status) VALUES (?, ?, ?)", (name, name, status))
    db.commit()
    return cur.lastrowid


def add_idp(designer="designer", title="Test IDP", status="Active", completion="2026-01-15",
            total=30000.0, area=90.0, ptype="HDB 4-Room", categories=(), created="2026-10-01 10:00:00"):
    db = get_db()
    cur = db.execute(
        "INSERT INTO idp (designer_id, title, description, property_type, total_cost, floor_area, completion_date, "
        "photo_urls, status, created_date) VALUES (?, ?, ?, ?, ?, ?, ?, '', ?, ?)",
        (account_id(designer), title, "A description", ptype, total, area, completion, status, created))
    for cid in categories:
        db.execute("INSERT INTO idp_category VALUES (?, ?, '2026-10-01 10:00:00')", (cur.lastrowid, cid))
    db.commit()
    return cur.lastrowid


def add_preference(username, categoryID):
    db = get_db()
    db.execute("INSERT INTO customer_preference VALUES (?, ?, '2026-01-01 00:00:00')", (account_id(username), categoryID))
    db.commit()


def count(sql, params=()):
    return get_db().execute(sql, params).fetchone()[0]


def add_favourite(username, idpID, saved="2026-10-01 10:00:00"):
    db = get_db()
    db.execute("INSERT INTO favourite (customer_id, idp_id, saved_date) VALUES (?, ?, ?)",
               (account_id(username), idpID, saved))
    db.commit()


def add_report(idpID, reporter="customer", reason="Spam / advertising", status="Pending", reported="2026-10-20 10:00:00"):
    db = get_db()
    cur = db.execute("INSERT INTO report (idp_id, reporter_id, reason, description, status, reported_date) "
                     "VALUES (?, ?, ?, 'Please check', ?, ?)", (idpID, account_id(reporter), reason, status, reported))
    db.commit()
    return cur.lastrowid


def add_cost_items(idpID, items):
    """items: [(name, unit, qty, rate)]"""
    db = get_db()
    db.executemany("INSERT INTO idp_cost_item (idp_id, item_name, unit, quantity, unit_rate) VALUES (?, ?, ?, ?, ?)",
                   [(idpID,) + tuple(i) for i in items])
    db.commit()
