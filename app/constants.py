"""Shared constants used by every user story.

Keeping status values and role names in one place means every
story uses exactly the same strings (see the consistency review).
"""

# ---- User profiles (roles) ----
USER_ADMIN = "User Admin"
INTERIOR_DESIGNER = "Interior Designer"
CUSTOMER = "Customer"
PLATFORM_MANAGER = "Platform Manager"
SALES_MANAGER = "Sales Manager"
ALL_ROLES = [USER_ADMIN, INTERIOR_DESIGNER, CUSTOMER, PLATFORM_MANAGER, SALES_MANAGER]

# ---- Status values ----
ACCOUNT_ACTIVE = "Active"
ACCOUNT_SUSPENDED = "Suspended"

PROFILE_ACTIVE = "Active"
PROFILE_INACTIVE = "Inactive"

IDP_ACTIVE = "Active"        # visible to customers
IDP_ARCHIVED = "Archived"    # hidden by the designer (#13)
IDP_HIDDEN = "Hidden"        # hidden by the Platform Manager (#38)

CATEGORY_ACTIVE = "Active"
CATEGORY_UNDER_REVIEW = "Under Review"   # flagged in #40
CATEGORY_INACTIVE = "Inactive"

REPORT_PENDING = "Pending"
REPORT_CLOSED = "Closed"

REPORT_REASONS = ["Copied photos from another designer", "Misleading cost information",
                  "Inappropriate content", "Fake project (not completed by this designer)",
                  "Spam / advertising", "Offensive description"]

DECISION_HIDE = "Hide IDP"
DECISION_WARN = "Warn"
DECISION_DISMISS = "Dismiss"

# ---- Activity log types (#7) ----
ACT_LOGIN = "Login"
ACT_LOGOUT = "Logout"
ACT_PROFILE_EDIT = "Profile Edit"
ACT_STATUS_CHANGE = "Status Change"
ACTIVITY_TYPES = [ACT_LOGIN, ACT_LOGOUT, ACT_PROFILE_EDIT, ACT_STATUS_CHANGE]

# ---- Cost estimation (#29, #47) ----
GST_RATE = 0.09
PROPERTY_TYPES = ["HDB 3-Room", "HDB 4-Room", "HDB 5-Room", "Condo", "Landed"]
MIN_FACTOR = 0.5
MAX_FACTOR = 3.0
FACTOR_PROPERTY = "PROPERTY"
FACTOR_STYLE = "STYLE"

# Starter renovation items (code, name, unit, rate in SGD) for the first rule. After that the Sales
# Manager edits the list in #47; #29 and the designer suggestions read the active rule.
RENOVATION_ITEMS = [
    ("FLOOR", "Vinyl flooring", "sqm", 45), ("TILE", "Bathroom tiling", "sqm", 85),
    ("PAINT", "Wall painting", "sqm", 8), ("CEIL", "False ceiling", "sqm", 60),
    ("HACK", "Hacking / demolition", "sqm", 30), ("KCAB", "Kitchen cabinets", "m", 900),
    ("WARD", "Built-in wardrobe", "m", 750), ("ELEC", "Electrical points", "unit", 120),
    ("PLUMB", "Plumbing points", "unit", 180), ("LIGHT", "Lighting fixtures", "unit", 95),
    ("FEAT", "Feature wall", "sqm", 150), ("GRILLE", "Window grilles", "unit", 220),
]

# ---- Sales report (#50) ----
PERIOD_TYPES = ["Daily", "Weekly", "Monthly"]

# ---- Navigation menu per role ----
# (label, Flask endpoint). A menu item only appears once its
# endpoint exists, so stories can be added one at a time.
MENU = {
    USER_ADMIN: [
        ("Create User Account", "create_user_account.displayCreateUAForm"),
        ("Accounts & Activity Log", "view_activity_log.searchAccount"),
        ("User Profiles", "manage_user_profiles.displayProfiles"),
    ],
    INTERIOR_DESIGNER: [
        ("Manage Portfolio", "manage_portfolio.displayPortfolio"),
        ("Company Information", "company_profile.displayCompanyForm"),
    ],
    CUSTOMER: [
        ("My Interests", "choose_preferences.displayPreferenceForm"),
        ("My Favourites", "compare_favourites.displayFavourites"),
        ("Cost Breakdown", "cost_breakdown.displayCostBreakdownForm"),
    ],
    PLATFORM_MANAGER: [
        ("Reported IDPs", "manage_reports.displayReportList"),
        ("Category Health", "category_health.displayCategoryHealth"),
        ("Categories", "manage_categories.displayCategoryList"),
        ("Reports", "platform_report.displayReportForm"),
    ],
    SALES_MANAGER: [
        ("Estimation Rules", "estimation_rule.displayEstimationRuleForm"),
        ("Sales Reports", "sales_report.displaySalesReportForm"),
    ],
}
