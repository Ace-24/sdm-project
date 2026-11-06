-- Unified schema for the Interior Design Platform.
-- One table per entity class; every user story uses these same tables.

DROP TABLE IF EXISTS company_profile;
DROP TABLE IF EXISTS idp_cost_item;
DROP TABLE IF EXISTS breakdown_item;
DROP TABLE IF EXISTS cost_breakdown;
DROP TABLE IF EXISTS rule_factor;
DROP TABLE IF EXISTS unit_rate;
DROP TABLE IF EXISTS estimation_rule;
DROP TABLE IF EXISTS report;
DROP TABLE IF EXISTS idp_view;
DROP TABLE IF EXISTS favourite;
DROP TABLE IF EXISTS recommendation;
DROP TABLE IF EXISTS customer_preference;
DROP TABLE IF EXISTS idp_category;
DROP TABLE IF EXISTS idp;
DROP TABLE IF EXISTS category;
DROP TABLE IF EXISTS notification;
DROP TABLE IF EXISTS activity_log;
DROP TABLE IF EXISTS user_account;
DROP TABLE IF EXISTS user_profile;

-- ===== Users (#1, #7, login) =====
CREATE TABLE user_profile (
    profile_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_name  TEXT NOT NULL UNIQUE,
    description   TEXT,
    status        TEXT NOT NULL DEFAULT 'Active'
);

CREATE TABLE user_account (
    account_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL,
    phone_no      TEXT,
    profile_id    INTEGER NOT NULL REFERENCES user_profile(profile_id),
    status        TEXT NOT NULL DEFAULT 'Active',
    created_date  TEXT NOT NULL
);

CREATE TABLE activity_log (
    log_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id    INTEGER NOT NULL REFERENCES user_account(account_id),
    activity_type TEXT NOT NULL,
    description   TEXT,
    performed_by  INTEGER REFERENCES user_account(account_id),
    ip_address    TEXT,
    timestamp     TEXT NOT NULL
);

-- Stands in for real email (#1 login credentials, #38 outcomes)
CREATE TABLE notification (
    notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id      INTEGER NOT NULL REFERENCES user_account(account_id),
    subject         TEXT NOT NULL,
    message         TEXT NOT NULL,
    created_date    TEXT NOT NULL
);

-- Interior designer's company information (spec item 2)
CREATE TABLE company_profile (
    designer_id   INTEGER PRIMARY KEY REFERENCES user_account(account_id),
    company_name  TEXT NOT NULL,
    uen           TEXT,
    address       TEXT,
    phone         TEXT NOT NULL,
    email         TEXT NOT NULL,
    website       TEXT,
    description   TEXT,
    updated_date  TEXT NOT NULL
);

-- ===== Categories and IDPs (#11, #13, #27, #38, #40) =====
CREATE TABLE category (
    category_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name TEXT NOT NULL UNIQUE,
    description   TEXT,
    status        TEXT NOT NULL DEFAULT 'Active'
);

CREATE TABLE idp (
    idp_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    designer_id     INTEGER NOT NULL REFERENCES user_account(account_id),
    title           TEXT NOT NULL,
    description     TEXT,
    property_type   TEXT,
    total_cost      REAL NOT NULL DEFAULT 0,
    floor_area      REAL NOT NULL DEFAULT 0,
    completion_date TEXT,
    photo_urls      TEXT,               -- comma-separated
    status          TEXT NOT NULL DEFAULT 'Active',
    created_date    TEXT NOT NULL,
    updated_date    TEXT,
    archived_date   TEXT
);

-- Cost breakdown entered by the designer for each project (#13 Edit)
CREATE TABLE idp_cost_item (
    item_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    idp_id     INTEGER NOT NULL REFERENCES idp(idp_id),
    item_name  TEXT NOT NULL,
    unit       TEXT NOT NULL,
    quantity   REAL NOT NULL,
    unit_rate  REAL NOT NULL
);

CREATE TABLE idp_category (
    idp_id      INTEGER NOT NULL REFERENCES idp(idp_id),
    category_id INTEGER NOT NULL REFERENCES category(category_id),
    linked_date TEXT NOT NULL,
    PRIMARY KEY (idp_id, category_id)
);

CREATE TABLE customer_preference (
    customer_id   INTEGER NOT NULL REFERENCES user_account(account_id),
    category_id   INTEGER NOT NULL REFERENCES category(category_id),
    selected_date TEXT NOT NULL,
    PRIMARY KEY (customer_id, category_id)
);

CREATE TABLE recommendation (
    recommendation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id       INTEGER NOT NULL REFERENCES user_account(account_id),
    idp_id            INTEGER NOT NULL REFERENCES idp(idp_id),
    added_date        TEXT NOT NULL,
    UNIQUE (customer_id, idp_id)
);

CREATE TABLE favourite (
    favourite_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id  INTEGER NOT NULL REFERENCES user_account(account_id),
    idp_id       INTEGER NOT NULL REFERENCES idp(idp_id),
    saved_date   TEXT NOT NULL,
    UNIQUE (customer_id, idp_id)
);

CREATE TABLE idp_view (
    view_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    idp_id      INTEGER NOT NULL REFERENCES idp(idp_id),
    customer_id INTEGER REFERENCES user_account(account_id),
    viewed_date TEXT NOT NULL
);

CREATE TABLE report (
    report_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    idp_id        INTEGER NOT NULL REFERENCES idp(idp_id),
    reporter_id   INTEGER NOT NULL REFERENCES user_account(account_id),
    reason        TEXT NOT NULL,
    description   TEXT,
    evidence_urls TEXT,
    status        TEXT NOT NULL DEFAULT 'Pending',
    decision      TEXT,
    closed_by     INTEGER REFERENCES user_account(account_id),
    reported_date TEXT NOT NULL,
    closed_date   TEXT
);

-- ===== Cost estimation (#47, #29, #50) =====
CREATE TABLE estimation_rule (
    rule_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_name    TEXT NOT NULL,
    created_by   INTEGER NOT NULL REFERENCES user_account(account_id),
    created_date TEXT NOT NULL,
    is_active    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE unit_rate (
    unit_rate_id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id      INTEGER NOT NULL REFERENCES estimation_rule(rule_id),
    item_code    TEXT NOT NULL,
    item_name    TEXT NOT NULL,
    unit         TEXT NOT NULL,
    rate         REAL NOT NULL,
    UNIQUE (rule_id, item_code)
);

-- EstimationRule.propertyFactors / styleFactors (factor_type = PROPERTY or STYLE)
CREATE TABLE rule_factor (
    rule_id     INTEGER NOT NULL REFERENCES estimation_rule(rule_id),
    factor_type TEXT NOT NULL,
    factor_key  TEXT NOT NULL,
    factor      REAL NOT NULL,
    PRIMARY KEY (rule_id, factor_type, factor_key)
);

CREATE TABLE cost_breakdown (
    breakdown_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id   INTEGER NOT NULL REFERENCES user_account(account_id),
    rule_id       INTEGER NOT NULL REFERENCES estimation_rule(rule_id),
    property_type TEXT NOT NULL,
    style         TEXT NOT NULL,
    subtotal      REAL NOT NULL,
    gst           REAL NOT NULL,
    total         REAL NOT NULL,
    created_date  TEXT NOT NULL
);

CREATE TABLE breakdown_item (
    item_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    breakdown_id INTEGER NOT NULL REFERENCES cost_breakdown(breakdown_id),
    item_code    TEXT NOT NULL,
    item_name    TEXT NOT NULL,
    unit         TEXT NOT NULL,
    quantity     REAL NOT NULL,
    unit_rate    REAL NOT NULL,
    line_total   REAL NOT NULL
);

-- Indexes for the date-range reports (#40, #50)
CREATE INDEX idx_view_date ON idp_view(viewed_date);
CREATE INDEX idx_fav_date ON favourite(saved_date);
CREATE INDEX idx_breakdown_date ON cost_breakdown(created_date);
