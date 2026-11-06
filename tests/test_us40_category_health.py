"""Unit tests for User Story #40 Category Health Report."""
from datetime import datetime, timedelta
from app.control.category_health_controller import CategoryHealthController
from app.entity.category_health import CategoryHealth
from app.entity.category import Category
from app.db import get_db
from tests.conftest import login
from tests.helpers import account_id, add_idp, add_category, add_favourite


def days_ago(n):
    return (datetime.now() - timedelta(days=n)).strftime("%Y-%m-%d %H:%M:%S")


def add_views(iid, n, ago=1):
    db = get_db()
    db.executemany("INSERT INTO idp_view (idp_id, customer_id, viewed_date) VALUES (?, ?, ?)",
                   [(iid, account_id("customer"), days_ago(ago))] * n)
    db.commit()


# ---- Entity ----
def test_growth_percent():
    assert CategoryHealth.growthPercent(6, 3) == 100.0
    assert CategoryHealth.growthPercent(1, 4) == -75.0
    assert CategoryHealth.growthPercent(2, 0) == 100.0
    assert CategoryHealth.growthPercent(0, 0) == 0.0


def test_score_formula_and_labels():
    top = CategoryHealth(1, "A", "Active", idpCount=10, interestCount=200, growthRate=50)
    assert top.calculateScore(10, 200, 50) == 100.0 and top.healthStatus == "Doing Well"
    mid = CategoryHealth(2, "B", "Active", idpCount=5, interestCount=100, growthRate=-20)
    assert mid.calculateScore(10, 200, 50) == 40.0 and mid.healthStatus == "Stable"     # 20 + 20 + 0
    low = CategoryHealth(3, "C", "Active", idpCount=2, interestCount=20, growthRate=0)
    assert low.calculateScore(10, 200, 50) == 12.0 and low.healthStatus == "At Risk"


def test_category_without_idps_scores_zero():
    h = CategoryHealth(1, "Empty", "Active")
    assert h.calculateScore(10, 100, 50) == 0.0 and h.healthStatus == "No data"


# ---- Controller ----
def test_statistics_use_last_30_days_and_active_idps(ctx):
    cat = add_category("Japandi")
    a = add_idp(categories=[cat], created=days_ago(5))
    add_idp(categories=[cat], created=days_ago(40))
    add_idp(categories=[cat], status="Hidden", created=days_ago(5))    # not counted
    add_views(a, 4, ago=2)
    add_views(a, 9, ago=45)                                            # too old
    add_favourite("customer", a, days_ago(3))
    h = next(r for r in CategoryHealthController().generateHealthReport() if r.categoryName == "Japandi")
    assert (h.idpCount, h.interestCount, h.growthRate) == (2, 5, 0.0)   # 1 new in last 30 vs 1 in previous 30


def test_report_sorted_by_score(ctx):
    strong, weak, empty = add_category("Strong"), add_category("Weak"), add_category("Empty")
    for _ in range(3):
        add_views(add_idp(categories=[strong], created=days_ago(3)), 10)
    add_idp(categories=[weak], created=days_ago(50))
    report = CategoryHealthController().generateHealthReport()
    assert [h.categoryName for h in report] == ["Strong", "Weak", "Empty"]
    assert report[0].healthScore == 100.0 and report[-1].healthStatus == "No data"


def test_flag_for_review(ctx):
    cid = add_category("Victorian")
    c = CategoryHealthController()
    assert c.flagCategoryForReview(cid) is True
    assert Category.findById(cid).status == "Under Review"
    assert c.flagCategoryForReview(cid) is False          # already flagged


# ---- Page ----
def test_only_platform_managers(client):
    login(client, "smanager")
    assert client.get("/platform/category-health/").status_code == 403


def test_page_and_flag(client, app):
    with app.app_context():
        cid = add_category("Japandi")
        add_idp(categories=[cid])
    login(client, "pmanager")
    html = client.get("/platform/category-health/").get_data(as_text=True)
    assert "Japandi" in html and "Health score" in html
    assert "Category flagged for review" in client.post(f"/platform/category-health/{cid}/flag").get_data(as_text=True)
