"""Fill the database with realistic test data for the live demo.

Usage:  python scripts/generate_test_data.py [--seed 42]

The spec asks for about 100 records per data type. This script wipes the
database, then creates (roughly):
  125 accounts, 1000+ activity log entries, 30 categories, 180 IDPs,
  customer preferences + recommendations, 600+ favourites, 5000+ IDP views,
  40 reports, 3 estimation rules with unit rates and factors,
  300 cost breakdowns with 1500+ breakdown items.

Views, favourites and breakdowns are spread over the last 90 days, and some
categories are deliberately growing or shrinking, so the Category Health (#40)
and Sales Report (#50) pages have trends to show.
All accounts use the password Password123!
"""
import argparse
import os
import random
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from werkzeug.security import generate_password_hash        # noqa: E402
from app import create_app                                   # noqa: E402
from app.db import init_db, get_db                           # noqa: E402
from app import constants as C                               # noqa: E402
from scripts.init_db import create_profiles, create_demo_accounts, DEMO_PASSWORD  # noqa: E402

NOW = datetime.now().replace(microsecond=0)
FMT = "%Y-%m-%d %H:%M:%S"

FIRST = ["Wei Ling", "Jun Hao", "Siti", "Arjun", "Mei Ting", "Kai Xuan", "Nur Aisyah", "Ravi", "Hui Min",
         "Darren", "Priya", "Marcus", "Farah", "Ethan", "Shi Hui", "Hafiz", "Grace", "Vikram", "Jasmine", "Ryan",
         "Li Na", "Zhi Wei", "Aisha", "Benjamin", "Clara", "Daniel", "Elaine", "Faisal", "Germaine", "Isaac"]
LAST = ["Tan", "Lim", "Lee", "Ng", "Wong", "Goh", "Chua", "Ong", "Koh", "Teo", "Kumar", "Rahman", "Singh",
        "Yeo", "Chan", "Ho", "Abdullah", "Pillai", "Sim", "Low"]
COMPANIES = ["Studio", "Interiors", "Design Co", "Atelier", "Living", "Spaces", "Concepts", "Home Studio"]

STYLES = {  # category -> popularity trend (>1 growing, <1 shrinking)
    "Scandinavian": 1.0, "Minimalist": 1.1, "Industrial": 0.9, "Modern Luxury": 1.0, "Japandi": 1.8,
    "Contemporary": 1.0, "Mid-Century Modern": 0.9, "Bohemian": 0.8, "Coastal": 0.9, "Farmhouse": 0.7,
    "Traditional": 0.6, "Eclectic": 0.9, "Art Deco": 0.8, "Rustic": 0.7, "Tropical": 1.2,
    "Wabi-Sabi": 1.6, "Peranakan": 1.1, "Victorian": 0.4, "Hollywood Regency": 0.6, "Transitional": 1.0,
}
ROOMS = ["Kitchen", "Living Room", "Bedroom", "Bathroom", "Study", "Kids Room", "Walk-in Wardrobe",
         "Balcony", "Dining Room", "Home Office"]
INACTIVE_CATEGORIES = {"Hollywood Regency"}
UNDER_REVIEW_CATEGORIES = {"Victorian"}

AREA = {"HDB 3-Room": (60, 70), "HDB 4-Room": (85, 95), "HDB 5-Room": (105, 120),
        "Condo": (70, 150), "Landed": (180, 400)}

ITEMS = C.RENOVATION_ITEMS
PROPERTY_FACTORS = {"HDB 3-Room": 1.0, "HDB 4-Room": 1.0, "HDB 5-Room": 1.05, "Condo": 1.15, "Landed": 1.3}

REPORT_REASONS = C.REPORT_REASONS
TITLE_WORDS = ["Cosy", "Bright", "Serene", "Bold", "Warm", "Airy", "Elegant", "Calm", "Modern", "Timeless"]


def rand_dt(days_back_max, days_back_min=0, weight_recent=1.0):
    """Random datetime between days_back_max and days_back_min days ago.
    weight_recent > 1 pushes dates towards today (growing trend),
    weight_recent < 1 pushes them towards the past (shrinking trend)."""
    u = random.random() ** weight_recent
    days = days_back_min + u * (days_back_max - days_back_min)
    return (NOW - timedelta(days=days, seconds=random.randint(0, 86399))).strftime(FMT)


def fake_ip():
    return f"192.168.{random.randint(0, 20)}.{random.randint(2, 254)}"


class TestDataGenerator:
    def __init__(self, db):
        self.db = db
        self.hash = generate_password_hash(DEMO_PASSWORD)   # one hash, reused (all share the password)
        self.profile = {r["profile_name"]: r["profile_id"]
                        for r in db.execute("SELECT * FROM user_profile").fetchall()}
        self.ids = {}            # role -> [account ids]
        self.cat_ids = {}        # name -> id
        self.idps = []           # (idp_id, designer_id, status, category names)
        self.rules = []          # (rule_id, created datetime, rates, prop factors, style factors)

    def q(self, sql, params=()):
        return self.db.execute(sql, params)

    # ---------- users ----------
    def accounts(self):
        counts = {C.USER_ADMIN: 5, C.INTERIOR_DESIGNER: 30, C.CUSTOMER: 80,
                  C.PLATFORM_MANAGER: 5, C.SALES_MANAGER: 5}
        used = set(r[0].lower() for r in self.q("SELECT username FROM user_account"))
        for role, n in counts.items():
            for _ in range(n):
                first, last = random.choice(FIRST), random.choice(LAST)
                base = (first.split()[0] + last).lower()
                username, k = base, 1
                while username in used:
                    k += 1
                    username = f"{base}{k}"
                used.add(username)
                name = f"{first} {last}"
                if role == C.INTERIOR_DESIGNER:
                    name = f"{first} {last} ({last} {random.choice(COMPANIES)})"
                status = C.ACCOUNT_SUSPENDED if role == C.CUSTOMER and random.random() < 0.05 else C.ACCOUNT_ACTIVE
                self.q("INSERT INTO user_account (username, password_hash, name, email, phone_no, profile_id, "
                       "status, created_date) VALUES (?,?,?,?,?,?,?,?)",
                       (username, self.hash, name, f"{username}@mail.example.com",
                        f"{random.choice('89')}{random.randint(1000000, 9999999)}",
                        self.profile[role], status, rand_dt(365, 91)))
        for row in self.q("SELECT a.account_id, p.profile_name FROM user_account a "
                          "JOIN user_profile p ON p.profile_id = a.profile_id"):
            self.ids.setdefault(row[1], []).append(row[0])

    def company_profiles(self):
        """Company information for every designer (spec item 2)."""
        areas = ["Ubi Avenue 1", "Kaki Bukit Road", "MacPherson Road", "Toa Payoh Lorong 4", "Jurong Gateway",
                 "Paya Lebar Square", "Bukit Merah Central", "Woodlands Loop"]
        rows = []
        for acc in self.ids[C.INTERIOR_DESIGNER]:
            name, username = self.q("SELECT name, username FROM user_account WHERE account_id = ?", (acc,)).fetchone()
            company = name[name.index("(") + 1:-1] if "(" in name else f"{name} Studio"
            rows.append((acc, company, f"20{random.randint(15, 24)}{random.randint(10000, 99999)}{random.choice('ABCDEKMNZ')}",
                         f"{random.randint(1, 80)} {random.choice(areas)}, #0{random.randint(1, 9)}-{random.randint(10, 99)}, "
                         f"Singapore {random.randint(300000, 799999)}",
                         f"6{random.randint(1000000, 9999999)}", f"hello@{username}.design.example.com",
                         f"https://{username}.design.example.com",
                         f"{company} designs warm, practical homes for Singapore families. "
                         f"We handle {random.choice(['HDB', 'condo', 'landed'])} renovations from concept to handover.",
                         rand_dt(90)))
        self.db.executemany("INSERT INTO company_profile VALUES (?,?,?,?,?,?,?,?,?)", rows)

    def activity_logs(self):
        rows = []
        admins = self.ids[C.USER_ADMIN]
        for role, ids in self.ids.items():
            for acc in ids:
                for _ in range(random.randint(4, 12)):
                    t = rand_dt(90)
                    ip = fake_ip()
                    rows.append((acc, C.ACT_LOGIN, "Logged in", acc, ip, t))
                    t_out = min(datetime.strptime(t, FMT) + timedelta(minutes=random.randint(5, 120)), NOW).strftime(FMT)
                    rows.append((acc, C.ACT_LOGOUT, "Logged out", acc, ip, t_out))
                if random.random() < 0.3:
                    rows.append((acc, C.ACT_PROFILE_EDIT, "Updated phone number", random.choice(admins),
                                 fake_ip(), rand_dt(90)))
        for acc, in self.q("SELECT account_id FROM user_account WHERE status = ?", (C.ACCOUNT_SUSPENDED,)):
            rows.append((acc, C.ACT_STATUS_CHANGE, "Status changed from Active to Suspended",
                         random.choice(admins), fake_ip(), rand_dt(30)))
        self.db.executemany("INSERT INTO activity_log (account_id, activity_type, description, performed_by, "
                            "ip_address, timestamp) VALUES (?,?,?,?,?,?)", rows)

    # ---------- categories + IDPs ----------
    def categories(self):
        for name in list(STYLES) + ROOMS:
            status = C.CATEGORY_INACTIVE if name in INACTIVE_CATEGORIES else \
                C.CATEGORY_UNDER_REVIEW if name in UNDER_REVIEW_CATEGORIES else C.CATEGORY_ACTIVE
            kind = "Design style" if name in STYLES else "Room type"
            cur = self.q("INSERT INTO category (category_name, description, status) VALUES (?,?,?)",
                         (name, f"{kind}: {name}", status))
            self.cat_ids[name] = cur.lastrowid

    def idp_records(self):
        designers = self.ids[C.INTERIOR_DESIGNER]
        demo_designer = self.q("SELECT account_id FROM user_account WHERE username='designer'").fetchone()[0]
        style_names = [s for s in STYLES if s not in INACTIVE_CATEGORIES]
        for n in range(180):
            designer = demo_designer if n < 8 else random.choice(designers)
            style = random.choices(style_names, weights=[STYLES[s] for s in style_names])[0]
            room = random.choice(ROOMS)
            ptype = random.choice(C.PROPERTY_TYPES)
            area = round(random.uniform(*AREA[ptype]), 1)
            # the designer's own cost breakdown; the total cost is its subtotal
            premium = 1.4 if style in ("Modern Luxury", "Art Deco") else 1.0
            items = []
            for code, iname, unit, base in random.sample(ITEMS, random.randint(3, 6)):
                qty = round(area * random.uniform(0.3, 1.0), 1) if unit == "sqm" else \
                    random.randint(2, 8) if unit == "m" else random.randint(3, 12)
                items.append((iname, unit, qty, round(base * random.uniform(0.8, 1.4) * premium, 2)))
            cost = round(sum(q * r for _, _, q, r in items), 2)
            status = random.choices([C.IDP_ACTIVE, C.IDP_ARCHIVED, C.IDP_HIDDEN], weights=[85, 10, 5])[0]
            # growing styles get newer projects (growth in new IDPs for #40)
            created = rand_dt(180, 0, weight_recent=STYLES[style])
            completion = (datetime.strptime(created, FMT) - timedelta(days=random.randint(10, 700))).strftime("%Y-%m-%d")
            archived = rand_dt(30) if status == C.IDP_ARCHIVED else None
            title = f"{random.choice(TITLE_WORDS)} {style} {room} - {ptype}"
            desc = (f"A {style.lower()} {room.lower()} makeover for a {ptype} home in "
                    f"{random.choice(['Tampines', 'Punggol', 'Bishan', 'Jurong East', 'Sengkang', 'Toa Payoh', 'Bukit Timah', 'Clementi'])}.")
            cur = self.q("INSERT INTO idp (designer_id, title, description, property_type, total_cost, floor_area, "
                         "completion_date, photo_urls, status, created_date, updated_date, archived_date) "
                         "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                         (designer, title, desc, ptype, cost, area, completion, "", status, created,
                          created, archived))
            self.db.executemany("INSERT INTO idp_cost_item (idp_id, item_name, unit, quantity, unit_rate) "
                                "VALUES (?, ?, ?, ?, ?)", [(cur.lastrowid,) + it for it in items])
            cats = [style] + ([room] if random.random() < 0.7 else [])
            for c in cats:
                self.q("INSERT INTO idp_category (idp_id, category_id, linked_date) VALUES (?,?,?)",
                       (cur.lastrowid, self.cat_ids[c], created))
            self.idps.append((cur.lastrowid, designer, status, cats))

    def preferences_and_recommendations(self):
        active_cats = [n for n in self.cat_ids if n not in INACTIVE_CATEGORIES]
        for cust in self.ids[C.CUSTOMER]:
            prefs = random.sample(active_cats, random.randint(2, 4))
            for p in prefs:
                self.q("INSERT INTO customer_preference (customer_id, category_id, selected_date) VALUES (?,?,?)",
                       (cust, self.cat_ids[p], rand_dt(365, 91)))
            matches = [i for i in self.idps if i[2] == C.IDP_ACTIVE and set(i[3]) & set(prefs)]
            for idp in random.sample(matches, min(5, len(matches))):
                self.q("INSERT INTO recommendation (customer_id, idp_id, added_date) VALUES (?,?,?)",
                       (cust, idp[0], rand_dt(60)))

    # ---------- customer interest ----------
    def favourites_and_views(self):
        customers = self.ids[C.CUSTOMER]
        demo_customer = self.q("SELECT account_id FROM user_account WHERE username='customer'").fetchone()[0]
        active = [i for i in self.idps if i[2] == C.IDP_ACTIVE]
        popularity = {i[0]: random.uniform(0.3, 3.0) * STYLES.get(i[3][0], 1.0) for i in self.idps}
        fav_rows = set()
        for cust in customers:
            n = 6 if cust == demo_customer else random.randint(3, 12)
            picks = random.choices(active, weights=[popularity[i[0]] for i in active], k=n * 2)
            for idp in picks:
                if len([f for f in fav_rows if f[0] == cust]) >= n:
                    break
                fav_rows.add((cust, idp[0]))
        self.db.executemany(
            "INSERT INTO favourite (customer_id, idp_id, saved_date) VALUES (?,?,?)",
            [(c, i, rand_dt(90, 0, STYLES.get(self._style(i), 1.0))) for c, i in fav_rows])

        views = []
        for idp in self.idps:
            n = int(popularity[idp[0]] * random.randint(10, 30))
            trend = STYLES.get(idp[3][0], 1.0)
            for _ in range(n):
                views.append((idp[0], random.choice(customers), rand_dt(90, 0, trend)))
        self.db.executemany("INSERT INTO idp_view (idp_id, customer_id, viewed_date) VALUES (?,?,?)", views)

    def _style(self, idp_id):
        for i in self.idps:
            if i[0] == idp_id:
                return i[3][0]
        return None

    def reports(self):
        reporters = self.ids[C.CUSTOMER]
        pms = self.ids[C.PLATFORM_MANAGER]
        visible = [i for i in self.idps if i[2] != C.IDP_ARCHIVED]
        for n in range(40):
            idp = random.choice(visible)
            reported = rand_dt(60)
            closed = n >= 25
            decision = random.choice([C.DECISION_HIDE, C.DECISION_WARN, C.DECISION_DISMISS]) if closed else None
            closed_date = (datetime.strptime(reported, FMT) + timedelta(days=random.randint(1, 5))).strftime(FMT) if closed else None
            self.q("INSERT INTO report (idp_id, reporter_id, reason, description, evidence_urls, status, decision, "
                   "closed_by, reported_date, closed_date) VALUES (?,?,?,?,?,?,?,?,?,?)",
                   (idp[0], random.choice(reporters), random.choice(REPORT_REASONS),
                    "Please check this project listing.", "",
                    C.REPORT_CLOSED if closed else C.REPORT_PENDING, decision,
                    random.choice(pms) if closed else None, reported, closed_date))

    # ---------- cost estimation ----------
    def estimation_rules(self):
        sm = self.q("SELECT account_id FROM user_account WHERE username='smanager'").fetchone()[0]
        style_keys = [n for n in self.cat_ids if n not in INACTIVE_CATEGORIES]
        for k, (name, days_ago, bump) in enumerate([("2026 Q2 rates", 120, 0.95),
                                                    ("2026 Q3 rates", 60, 1.0),
                                                    ("2026 Q4 rates", 20, 1.04)]):
            created = (NOW - timedelta(days=days_ago)).strftime(FMT)
            is_active = 1 if k == 2 else 0
            cur = self.q("INSERT INTO estimation_rule (rule_name, created_by, created_date, is_active) "
                         "VALUES (?,?,?,?)", (name, sm, created, is_active))
            rid = cur.lastrowid
            rates = {}
            for code, iname, unit, base in ITEMS:
                rate = round(base * bump, 2)
                rates[code] = (iname, unit, rate)
                self.q("INSERT INTO unit_rate (rule_id, item_code, item_name, unit, rate) VALUES (?,?,?,?,?)",
                       (rid, code, iname, unit, rate))
            styles = {}
            for key in style_keys:
                f = 1.4 if key in ("Modern Luxury", "Art Deco") else 1.2 if key in ("Peranakan", "Victorian") \
                    else 0.9 if key in ("Minimalist", "Scandinavian") else 1.0
                styles[key] = f
                self.q("INSERT INTO rule_factor VALUES (?,?,?,?)", (rid, "STYLE", key, f))
            for key, f in PROPERTY_FACTORS.items():
                self.q("INSERT INTO rule_factor VALUES (?,?,?,?)", (rid, "PROPERTY", key, f))
            self.rules.append((rid, datetime.strptime(created, FMT), rates, PROPERTY_FACTORS, styles))

    def cost_breakdowns(self):
        customers = self.ids[C.CUSTOMER]
        for _ in range(300):
            created = rand_dt(90, 0, 1.3)
            cdt = datetime.strptime(created, FMT)
            rule = [r for r in self.rules if r[1] <= cdt][-1] if any(r[1] <= cdt for r in self.rules) else self.rules[0]
            rid, _, rates, pf, sf = rule
            ptype = random.choice(C.PROPERTY_TYPES)
            style = random.choice(list(sf))
            factor = pf[ptype] * sf[style]
            items = []
            for code in random.sample(list(rates), random.randint(3, 7)):
                iname, unit, rate = rates[code]
                qty = random.randint(1, 8) if unit in ("unit", "m") else random.randint(10, 90)
                line = round(qty * rate * factor, 2)       # same formula as #29
                items.append((code, iname, unit, qty, rate, line))
            subtotal = round(sum(i[5] for i in items), 2)
            gst = round(subtotal * C.GST_RATE, 2)
            cur = self.q("INSERT INTO cost_breakdown (customer_id, rule_id, property_type, style, subtotal, gst, "
                         "total, created_date) VALUES (?,?,?,?,?,?,?,?)",
                         (random.choice(customers), rid, ptype, style, subtotal, gst, round(subtotal + gst, 2), created))
            self.db.executemany("INSERT INTO breakdown_item (breakdown_id, item_code, item_name, unit, quantity, "
                                "unit_rate, line_total) VALUES (?,?,?,?,?,?,?)",
                                [(cur.lastrowid,) + i for i in items])

    def run(self):
        self.accounts()
        self.company_profiles()
        self.activity_logs()
        self.categories()
        self.idp_records()
        self.preferences_and_recommendations()
        self.favourites_and_views()
        self.reports()
        self.estimation_rules()
        self.cost_breakdowns()
        self.db.commit()


TABLES = ["user_profile", "user_account", "company_profile", "activity_log", "category", "idp", "idp_cost_item", "idp_category",
          "customer_preference", "recommendation", "favourite", "idp_view", "report",
          "estimation_rule", "unit_rate", "rule_factor", "cost_breakdown", "breakdown_item"]


def generate(db, seed=42):
    random.seed(seed)
    create_profiles(db)
    create_demo_accounts(db)
    TestDataGenerator(db).run()
    return {t: db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TABLES}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42, help="random seed (same seed = same data)")
    args = parser.parse_args()
    app = create_app()
    with app.app_context():
        init_db()
        counts = generate(get_db(), args.seed)
        print("Test data created in", app.config["DATABASE"])
        for t, n in counts.items():
            print(f"  {t:22} {n:6}")
        print("All accounts use the password", DEMO_PASSWORD)


if __name__ == "__main__":
    main()
