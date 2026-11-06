"""Unit tests for User Story #7 View Account Activity Log."""
from app.control.view_activity_log_controller import ViewActivityLogController
from app.control.login_controller import LoginController
from app.entity.activity_log import ActivityLog
from app.entity.user_account import UserAccount
from app.db import get_db
from tests.conftest import login


def acc(username):
    return UserAccount.findByUsername(username)


def add_log(accountID, kind, ts):
    db = get_db()
    db.execute("INSERT INTO activity_log (account_id, activity_type, description, performed_by, ip_address, timestamp) "
               "VALUES (?,?,?,?,?,?)", (accountID, kind, kind, accountID, "10.0.0.1", ts))
    db.commit()


# ---- Controller ----
def test_search_by_username_name_or_email(ctx):
    c = ViewActivityLogController()
    assert [a.username for a in c.searchUserAccount("chloe")] == ["customer"]          # name
    assert [a.username for a in c.searchUserAccount("smanager@")] == ["smanager"]     # email
    assert [a.username for a in c.searchUserAccount("design")] == ["designer"]        # username


def test_search_with_no_match_returns_empty_list(ctx):
    assert ViewActivityLogController().searchUserAccount("zzzz") == []


def test_empty_keyword_lists_all_accounts(ctx):
    assert len(ViewActivityLogController().searchUserAccount("")) == 5


def test_log_is_newest_first(ctx):
    cid = acc("customer").accountID
    add_log(cid, "Login", "2026-10-01 09:00:00")
    add_log(cid, "Logout", "2026-10-03 09:00:00")
    add_log(cid, "Profile Edit", "2026-10-02 09:00:00")
    logs = ViewActivityLogController().viewActivityLog(cid)
    assert [l.timestamp[:10] for l in logs] == ["2026-10-03", "2026-10-02", "2026-10-01"]
    assert logs[0].performedByName == "customer"


def test_account_with_no_activity_returns_empty_list(ctx):
    assert ViewActivityLogController().viewActivityLog(acc("pmanager").accountID) == []


def test_filter_by_type_and_dates(ctx):
    cid = acc("customer").accountID
    for ts in ("2026-09-30 10:00:00", "2026-10-05 10:00:00", "2026-10-10 23:30:00", "2026-10-11 00:00:01"):
        add_log(cid, "Login", ts)
    add_log(cid, "Logout", "2026-10-06 10:00:00")
    c = ViewActivityLogController()
    assert len(c.filterActivityLog(cid, "Login")) == 4
    logs = c.filterActivityLog(cid, "Login", "2026-10-01", "2026-10-10")      # inclusive range
    assert [l.timestamp for l in logs] == ["2026-10-10 23:30:00", "2026-10-05 10:00:00"]


def test_filter_rejects_reversed_dates(ctx):
    c = ViewActivityLogController()
    assert c.filterActivityLog(1, None, "2026-10-10", "2026-10-01") is None
    assert "on or before" in c.errorMsg


def test_filter_rejects_bad_date_and_type(ctx):
    c = ViewActivityLogController()
    assert c.filterActivityLog(1, None, "10/10/2026") is None
    assert c.filterActivityLog(1, "Hacking") is None


def test_export_csv(ctx):
    cid = acc("customer").accountID
    add_log(cid, "Login", "2026-10-01 09:00:00")
    c = ViewActivityLogController()
    text = c.exportActivityLog(c.viewActivityLog(cid))
    lines = text.strip().splitlines()
    assert lines[0] == "Date/Time,Activity Type,Description,Performed By,IP Address"
    assert lines[1].startswith("2026-10-01 09:00:00,Login")


def test_suspend_account_logs_status_change_and_blocks_login(ctx):
    admin, cust = acc("admin"), acc("customer")
    assert ViewActivityLogController().suspendUserAccount(cust.accountID, admin.accountID) is True
    assert acc("customer").status == "Suspended"
    log = ActivityLog.getActivityLog(cust.accountID)[0]
    assert log.activityType == "Status Change" and log.performedByName == "admin"
    account, err = LoginController().validateLogin("customer", "Password123!")
    assert account is None and "suspended" in err


def test_cannot_suspend_self_or_twice(ctx):
    admin, cust = acc("admin"), acc("customer")
    c = ViewActivityLogController()
    assert c.suspendUserAccount(admin.accountID, admin.accountID) is False
    c.suspendUserAccount(cust.accountID, admin.accountID)
    assert c.suspendUserAccount(cust.accountID, admin.accountID) is False


# ---- Page ----
def test_only_user_admin_can_open(client):
    login(client, "smanager")
    assert client.get("/admin/activity-log/").status_code == 403


def test_search_page_shows_no_accounts_found(client):
    login(client, "admin")
    assert "No accounts found." in client.get("/admin/activity-log/?keyword=zzzz").get_data(as_text=True)


def test_log_page_shows_own_login(client, app):
    login(client, "admin")
    with app.app_context():
        aid = acc("admin").accountID
    html = client.get(f"/admin/activity-log/{aid}").get_data(as_text=True)
    assert "Logged in" in html


def test_log_page_shows_no_activity_message(client, app):
    login(client, "admin")
    with app.app_context():
        pid = acc("pmanager").accountID
    assert "No activity recorded for this account." in client.get(f"/admin/activity-log/{pid}").get_data(as_text=True)


def test_export_download(client, app):
    login(client, "admin")
    with app.app_context():
        aid = acc("admin").accountID
    resp = client.get(f"/admin/activity-log/{aid}/export")
    assert resp.mimetype == "text/csv"
    assert "attachment; filename=activity_log_admin.csv" in resp.headers["Content-Disposition"]


def test_suspend_button(client, app):
    login(client, "admin")
    with app.app_context():
        cid = acc("customer").accountID
    resp = client.post(f"/admin/activity-log/{cid}/suspend", follow_redirects=True)
    assert "Account suspended." in resp.get_data(as_text=True)


def test_page_lists_current_accounts_when_opened(client):
    login(client, "admin")
    html = client.get("/admin/activity-log/").get_data(as_text=True)
    assert "5 current account(s)" in html and "smanager" in html and "customer" in html


def test_role_filter(ctx):
    names = [a.username for a in ViewActivityLogController().searchUserAccount("", "Customer")]
    assert names == ["customer"]
