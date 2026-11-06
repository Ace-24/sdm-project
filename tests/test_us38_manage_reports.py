"""Unit tests for User Story #38 Manage Reports on Inappropriate IDPs."""
import pytest
from app.control.manage_reports_controller import ManageReportsController
from app.entity.report import Report
from app.entity.idp import IDP
from tests.conftest import login
from tests.helpers import account_id, add_idp, add_report, count


def notes(username):
    return count("SELECT COUNT(*) FROM notification WHERE account_id = ?", (account_id(username),))


# ---- Controller ----
def test_pending_reports_oldest_first(ctx):
    iid = add_idp(title="Reported IDP")
    add_report(iid, reported="2026-10-22 10:00:00")
    add_report(iid, reported="2026-10-20 10:00:00")
    add_report(iid, status="Closed")
    reports = ManageReportsController().getPendingReports()
    assert [r.reportedDate[:10] for r in reports] == ["2026-10-20", "2026-10-22"]
    assert reports[0].idpTitle == "Reported IDP" and reports[0].reporterName == "Chloe Customer"


def test_report_details_include_idp(ctx):
    iid = add_idp(title="Reported IDP")
    rid = add_report(iid)
    report, idp = ManageReportsController().getReportDetails(rid)
    assert report.reason == "Spam / advertising" and idp.title == "Reported IDP"


def test_hide_decision_hides_idp_and_closes_report(ctx):
    iid = add_idp()
    rid = add_report(iid)
    assert ManageReportsController().processDecision(rid, "Hide IDP", account_id("pmanager")) is True
    assert IDP.getIDPDetails(iid).status == "Hidden"
    r = Report.getReport(rid)
    assert (r.status, r.decision, r.closedBy) == ("Closed", "Hide IDP", account_id("pmanager")) and r.closedDate
    assert notes("customer") == 1 and notes("designer") == 1          # outcome to reporter and designer


def test_warn_decision_warns_designer_and_keeps_idp(ctx):
    iid = add_idp()
    rid = add_report(iid)
    assert ManageReportsController().processDecision(rid, "Warn", account_id("pmanager")) is True
    assert IDP.getIDPDetails(iid).status == "Active"
    assert count("SELECT COUNT(*) FROM notification WHERE account_id = ? AND subject LIKE 'Warning%'",
                 (account_id("designer"),)) == 1
    assert notes("customer") == 1


def test_dismiss_changes_nothing_but_closes(ctx):
    iid = add_idp()
    rid = add_report(iid)
    assert ManageReportsController().processDecision(rid, "Dismiss", account_id("pmanager")) is True
    assert IDP.getIDPDetails(iid).status == "Active"
    assert Report.getReport(rid).status == "Closed"


def test_cannot_decide_twice(ctx):
    rid = add_report(add_idp())
    c = ManageReportsController()
    c.processDecision(rid, "Dismiss", account_id("pmanager"))
    assert c.processDecision(rid, "Hide IDP", account_id("pmanager")) is False
    assert c.errorMsg == "This report has already been closed."


@pytest.mark.parametrize("decision", ["", "Delete", None])
def test_invalid_decision(ctx, decision):
    rid = add_report(add_idp())
    c = ManageReportsController()
    assert c.processDecision(rid, decision, account_id("pmanager")) is False
    assert Report.getReport(rid).status == "Pending"


# ---- Page ----
def test_only_platform_managers(client):
    login(client, "customer")
    assert client.get("/platform/reports/").status_code == 403


def test_no_pending_reports_message(client):
    login(client, "pmanager")
    assert "No pending reports" in client.get("/platform/reports/").get_data(as_text=True)


def test_review_and_decide(client, app):
    with app.app_context():
        rid = add_report(add_idp(title="Suspicious Loft"))
    login(client, "pmanager")
    assert "Suspicious Loft" in client.get(f"/platform/reports/{rid}").get_data(as_text=True)
    assert "Report closed" in client.post(f"/platform/reports/{rid}", data={"decision": "Hide IDP"}).get_data(as_text=True)
    assert "No pending reports" in client.get("/platform/reports/").get_data(as_text=True)


def test_page_shows_error_for_missing_decision(client, app):
    with app.app_context():
        rid = add_report(add_idp())
    login(client, "pmanager")
    html = client.post(f"/platform/reports/{rid}", data={"decision": ""}).get_data(as_text=True)
    assert "Please select a decision" in html


def test_hidden_idp_disappears_from_customer_recommendations(client, app):
    from app.entity.recommendation import Recommendation
    with app.app_context():
        iid = add_idp(title="Soon hidden")
        Recommendation.refreshRecommendations(iid, [account_id("customer")])
        rid = add_report(iid)
        ManageReportsController().processDecision(rid, "Hide IDP", account_id("pmanager"))
    login(client, "customer")
    assert "Soon hidden" not in client.get("/home").get_data(as_text=True)
