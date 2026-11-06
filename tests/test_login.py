"""Unit tests for LoginController and the login pages."""
from app.control.login_controller import LoginController
from app.db import get_db
from app.constants import ACT_LOGIN, ACT_LOGOUT
from tests.conftest import login


def _log_types(accountID):
    rows = get_db().execute("SELECT activity_type FROM activity_log WHERE account_id = ? ORDER BY log_id",
                            (accountID,)).fetchall()
    return [r[0] for r in rows]


# ---- Controller tests ----
def test_valid_login_returns_account_and_logs_activity(ctx):
    account, error = LoginController().validateLogin("admin", "Password123!")
    assert error is None
    assert account.username == "admin"
    assert account.profileName == "User Admin"
    assert _log_types(account.accountID) == [ACT_LOGIN]


def test_wrong_password_is_rejected(ctx):
    account, error = LoginController().validateLogin("admin", "wrong")
    assert account is None
    assert error == "Invalid username or password."


def test_unknown_user_is_rejected(ctx):
    account, error = LoginController().validateLogin("nobody", "Password123!")
    assert account is None


def test_username_is_not_case_sensitive(ctx):
    account, error = LoginController().validateLogin("Customer", "Password123!")
    assert error is None
    assert account.username == "customer"


def test_username_spaces_are_ignored(ctx):
    account, error = LoginController().validateLogin("  customer ", "Password123!")
    assert error is None


def test_password_is_case_sensitive(ctx):
    account, error = LoginController().validateLogin("customer", "password123!")
    assert account is None


def test_empty_fields_are_rejected(ctx):
    account, error = LoginController().validateLogin("", "")
    assert account is None
    assert "enter your username" in error


def test_suspended_account_cannot_log_in(ctx):
    db = get_db()
    db.execute("UPDATE user_account SET status = 'Suspended' WHERE username = 'customer'")
    db.commit()
    account, error = LoginController().validateLogin("customer", "Password123!")
    assert account is None
    assert "suspended" in error


def test_logout_is_logged(ctx):
    account, _ = LoginController().validateLogin("designer", "Password123!")
    LoginController().logout(account.accountID)
    assert _log_types(account.accountID) == [ACT_LOGIN, ACT_LOGOUT]


# ---- Page (boundary) tests ----
def test_login_page_loads(client):
    resp = client.get("/login")
    assert resp.status_code == 200
    assert b"Login" in resp.data


def test_successful_login_redirects_to_home(client):
    resp = login(client, "smanager")
    assert resp.status_code == 302
    home = client.get("/home")
    assert b"Sarah Sales" in home.data
    assert b"Sales Manager" in home.data


def test_customer_can_log_in(client):
    login(client, "customer")
    home = client.get("/home")
    assert b"Chloe Customer" in home.data
    assert b"Customer" in home.data


def test_failed_login_shows_error(client):
    resp = login(client, "smanager", "bad")
    assert b"Invalid username or password." in resp.data


def test_home_requires_login(client):
    resp = client.get("/home")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_logout_clears_session(client):
    login(client, "admin")
    client.get("/logout")
    resp = client.get("/home")
    assert resp.status_code == 302
