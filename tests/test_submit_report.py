"""Unit tests for Submit Report (customers report an IDP; this is the input for #38)."""
import io
import pytest
from werkzeug.datastructures import FileStorage
from app.control.submit_report_controller import SubmitReportController
from app.entity.user_account import UserAccount
from app.entity.idp import IDP
from app.entity.report import Report
from tests.conftest import login
from tests.helpers import account_id, add_idp, add_report, count

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100


@pytest.fixture(autouse=True)
def uploads(app, tmp_path):
    app.config["UPLOAD_FOLDER"] = str(tmp_path / "uploads")      # keep test files out of app/static
    return tmp_path / "uploads"


def photo(name="proof.png", data=PNG):
    return FileStorage(stream=io.BytesIO(data), filename=name)


def submit(idpID, username="customer", reason="Spam / advertising", description="Looks like an advert", evidence=None):
    c = SubmitReportController()
    report = c.submitReport(UserAccount.findByUsername(username), IDP.getIDPDetails(idpID), reason, description, evidence)
    return report, c.errorMsgs


# ---- Controller ----
def test_valid_report_is_saved_as_pending(ctx):
    iid = add_idp()
    report, errors = submit(iid)
    assert errors == [] and report.reportID
    saved = Report.getReport(report.reportID)
    assert (saved.idpID, saved.reporterID, saved.status) == (iid, account_id("customer"), "Pending")
    assert saved.reason == "Spam / advertising" and saved.description == "Looks like an advert" and saved.reportedDate


def test_platform_managers_are_notified(ctx):
    iid = add_idp(title="Odd Project")
    submit(iid)
    assert count("SELECT COUNT(*) FROM notification WHERE account_id = ? AND subject = ?",
                 (account_id("pmanager"), "New report about 'Odd Project'")) == 1


def test_description_is_optional(ctx):
    report, errors = submit(add_idp(), description="")
    assert report is not None and errors == []


def test_second_pending_report_is_rejected(ctx):
    iid = add_idp()
    submit(iid)
    report, errors = submit(iid)
    assert report is None and "already reported" in errors[0]
    assert count("SELECT COUNT(*) FROM report") == 1


def test_can_report_again_after_review_closed(ctx):
    iid = add_idp()
    add_report(iid, status="Closed")
    report, _ = submit(iid)
    assert report is not None


def test_reason_must_be_from_list(ctx):
    report, errors = submit(add_idp(), reason="I just don't like it")
    assert report is None and errors == ["Please select a reason."]


def test_description_length_limit(ctx):
    assert submit(add_idp(), description="x" * 1000)[0] is not None
    report, errors = submit(add_idp(title="Other"), description="x" * 1001)
    assert report is None and "1000 characters" in errors[0]


def test_hidden_project_cannot_be_reported(ctx):
    report, errors = submit(add_idp(status="Hidden"))
    assert report is None and errors == ["This project can no longer be reported."]


def test_only_customers_can_report(ctx):
    report, errors = submit(add_idp(), username="designer")
    assert report is None and "Only customers can report projects." in errors


def test_evidence_photo_is_saved(ctx, uploads):
    report, _ = submit(add_idp(), evidence=photo())
    name = Report.getReport(report.reportID).evidenceURLs[0]
    assert name.startswith("report_") and name.endswith(".png") and (uploads / name).exists()


def test_evidence_must_be_an_image(ctx):
    report, errors = submit(add_idp(), evidence=photo("notes.pdf"))
    assert report is None and errors == ["Evidence must be a JPG or PNG image."]


def test_evidence_size_limit(ctx):
    report, errors = submit(add_idp(), evidence=photo("big.jpg", b"0" * (5 * 1024 * 1024)))
    assert report is None and errors == ["Evidence must be under 5 MB."]


# ---- Boundary ----
def test_visitor_is_sent_to_login(client, ctx):
    iid = add_idp()
    resp = client.get(f"/projects/{iid}/report")
    assert resp.status_code == 302 and "/login" in resp.headers["Location"]


def test_designer_gets_403(client, ctx):
    iid = add_idp()
    login(client, "designer")
    assert client.get(f"/projects/{iid}/report").status_code == 403


def test_missing_or_hidden_project_404(client, ctx):
    login(client, "customer")
    assert client.get("/projects/9999/report").status_code == 404
    assert client.get(f"/projects/{add_idp(status='Hidden')}/report").status_code == 404


def test_project_page_shows_report_button_to_customer(client, ctx):
    iid = add_idp()
    login(client, "customer")
    assert b"Report this project" in client.get(f"/projects/{iid}").data


def test_full_flow_report_reaches_platform_manager(client, ctx):
    iid = add_idp(title="Reported Through Page")
    login(client, "customer")
    page = client.get(f"/projects/{iid}/report")
    assert page.status_code == 200 and b"Spam / advertising" in page.data
    resp = client.post(f"/projects/{iid}/report", data={
        "reason": "Spam / advertising", "description": "Advert",
        "evidence": (io.BytesIO(PNG), "proof.png")}, content_type="multipart/form-data")
    assert b"Report submitted" in resp.data
    rid = get_report_id()
    client.get("/logout")
    login(client, "pmanager")
    assert b"Reported Through Page" in client.get("/platform/reports/").data
    details = client.get(f"/platform/reports/{rid}").data
    assert b'class="evidence"' in details


def test_error_message_shown_on_page(client, ctx):
    iid = add_idp()
    login(client, "customer")
    resp = client.post(f"/projects/{iid}/report", data={"reason": ""})
    assert resp.status_code == 200 and b"Please select a reason." in resp.data


def get_report_id():
    from app.db import get_db
    return get_db().execute("SELECT MAX(report_id) FROM report").fetchone()[0]
