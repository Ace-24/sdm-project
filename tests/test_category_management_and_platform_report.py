"""Unit tests for Manage Categories and Platform Reports (Platform Manager)."""
from datetime import date, timedelta
from app.control.manage_categories_controller import ManageCategoriesController
from app.control.platform_report_controller import PlatformReportController
from app.control.manage_project_categories_controller import ManageProjectCategoriesController
from app.entity.category import Category
from app.entity.user_account import UserAccount
from app.db import get_db
from tests.conftest import login
from tests.helpers import account_id, add_idp, add_category, add_preference, count


# ---- Manage categories ----
def test_create_category(ctx):
    c = ManageCategoriesController()
    assert c.createCategory("Neo-Classical", "Columns and mouldings") is True
    assert Category.existsByName("neo-classical")
    assert c.createCategory("NEO-CLASSICAL", "") is False and "already exists" in c.errorMsg
    assert c.createCategory("x", "") is False and "2 to 40 characters" in c.errorMsg


def test_update_category_and_rename_keeps_style_factor(ctx):
    cid = add_category("Japandy")
    db = get_db()
    db.execute("INSERT INTO rule_factor VALUES (1, 'STYLE', 'Japandy', 1.3)")
    db.commit()
    c = ManageCategoriesController()
    assert c.updateCategory(cid, "Japandi", "Japanese + Scandi", "Under Review") is True
    saved = Category.findById(cid)
    assert (saved.categoryName, saved.status) == ("Japandi", "Under Review")
    assert count("SELECT COUNT(*) FROM rule_factor WHERE factor_key = 'Japandi'") == 1


def test_update_validation(ctx):
    a, b = add_category("Coastal"), add_category("Rustic")
    c = ManageCategoriesController()
    assert c.updateCategory(b, "coastal", "", "Active") is False and "already exists" in c.errorMsg
    assert c.updateCategory(b, "Rustic", "", "Deleted") is False
    assert c.updateCategory(b, "Rustic", "same name is fine", "Active") is True


def test_delete_only_unused_categories(ctx):
    used, unused = add_category("Used"), add_category("Unused")
    add_idp(categories=[used])
    add_preference("customer", unused)
    c = ManageCategoriesController()
    assert c.deleteCategory(used) is False and "used by 1 project" in c.errorMsg
    assert c.deleteCategory(unused) is True and Category.findById(unused) is None
    assert count("SELECT COUNT(*) FROM customer_preference WHERE category_id = ?", (unused,)) == 0


def test_category_requests_from_designers_are_listed(ctx):
    add_category("Japandi")
    ManageProjectCategoriesController().requestNewCategory(UserAccount.findByUsername("designer"),
                                                           "Neo-Classical", "Clients ask for it")
    reqs = ManageCategoriesController().getCategoryRequests(account_id("pmanager"))
    assert len(reqs) == 1 and "Neo-Classical" in reqs[0].subject


# ---- Platform report ----
def _stamp(days_ago=0):
    return (date.today() - timedelta(days=days_ago)).isoformat() + " 10:00:00"


def test_report_counts_activity_in_period(ctx):
    cat = add_category("Japandi")
    iid = add_idp(categories=[cat], created=_stamp(0))
    add_idp(categories=[cat], created=_stamp(40))                      # outside a daily report
    db = get_db()
    db.executemany("INSERT INTO idp_view (idp_id, viewed_date) VALUES (?, ?)", [(iid, _stamp(0))] * 3)
    db.execute("INSERT INTO favourite (customer_id, idp_id, saved_date) VALUES (?, ?, ?)",
               (account_id("customer"), iid, _stamp(0)))
    db.execute("INSERT INTO report (idp_id, reporter_id, reason, reported_date) VALUES (?, ?, 'Spam', ?)",
               (iid, account_id("customer"), _stamp(0)))
    db.commit()
    r = PlatformReportController().generateReport("Daily", date.today().isoformat())
    assert r.summary["New IDPs listed"] == 1 and r.summary["IDP views"] == 3
    assert r.summary["IDPs shortlisted"] == 1 and r.summary["Reports received"] == 1
    assert r.summary["New customer accounts"] >= 1                     # demo accounts are created today
    assert r.categoryRows[0] == ("Japandi", 1, 3, 1)


def test_report_periods_and_validation(ctx):
    c = PlatformReportController()
    r = c.generateReport("Monthly", "2026-02-10")
    assert (r.startDate, r.endDate) == (date(2026, 2, 1), date(2026, 2, 28))
    assert c.generateReport("Weekly", (date.today() + timedelta(days=2)).isoformat()) is None
    assert c.errorMsg == "Please select a report period and a date that is not in the future"


def test_report_csv(ctx):
    r = PlatformReportController().generateReport("Weekly", "2026-10-28")
    text = r.toCSV()
    assert text.startswith("Platform report,Weekly,2026-10-26,2026-11-01")
    assert "Measure,Value" in text and "Category,New IDPs,IDP views,Shortlisted" in text
    assert r.getFileName() == "platform_report_weekly_2026-10-26.csv"


# ---- Pages ----
def test_categories_page_create_and_delete(client, app):
    login(client, "pmanager")
    resp = client.post("/platform/categories/", data={"name": "Neo-Classical", "description": "x"}, follow_redirects=True)
    assert "Category &#39;Neo-Classical&#39; created" in resp.get_data(as_text=True)
    with app.app_context():
        cid = next(c.categoryID for c in Category.getAllCategories() if c.categoryName == "Neo-Classical")
    assert "Edit Category" in client.get(f"/platform/categories/{cid}/edit").get_data(as_text=True)
    assert "Category deleted" in client.post(f"/platform/categories/{cid}/delete", follow_redirects=True).get_data(as_text=True)


def test_platform_report_page_and_export(client):
    login(client, "pmanager")
    html = client.get(f"/platform/platform-reports/?period=Weekly&date={date.today().isoformat()}").get_data(as_text=True)
    assert "Weekly report" in html and "IDP views" in html
    resp = client.post("/platform/platform-reports/export", data={"period": "Daily", "date": date.today().isoformat()})
    assert resp.mimetype == "text/csv"


def test_only_platform_managers(client):
    login(client, "designer")
    assert client.get("/platform/categories/").status_code == 403
    assert client.get("/platform/platform-reports/").status_code == 403
