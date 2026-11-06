"""Unit tests for User Story #1 Create User Account."""
import pytest
from app.control.create_user_account_controller import CreateUserAccountController
from app.entity.user_account import UserAccount
from app.entity.user_profile import UserProfile
from app.db import get_db
from tests.conftest import login


def profile_id(name):
    return next(p.profileID for p in UserProfile.getActiveProfiles() if p.profileName == name)


def new_ua(**over):
    data = dict(username="newuser", name="New User", email="new@mail.com", phoneNo="91234567",
                profileID=profile_id("Customer"))
    data.update(over)
    return UserAccount(None, data["username"], data["name"], data["email"], data["phoneNo"], data["profileID"])


# ---- Controller ----
def test_get_active_profiles_returns_all_five(ctx):
    names = [p.profileName for p in CreateUserAccountController().getActiveProfiles()]
    assert names == ["User Admin", "Interior Designer", "Customer", "Platform Manager", "Sales Manager"]


def test_valid_account_is_created_active(ctx):
    c = CreateUserAccountController()
    assert c.createUserAccount(new_ua(), "Secret123") is True
    saved = UserAccount.findByUsername("newuser")
    assert saved.status == "Active"
    assert saved.profileName == "Customer"
    assert saved.checkPassword("Secret123")          # stored as a hash, not plain text
    assert saved.passwordHash != "Secret123"


def test_username_taken_is_rejected(ctx):
    c = CreateUserAccountController()
    assert c.createUserAccount(new_ua(username="Customer"), "Secret123") is False   # demo 'customer' exists
    assert "Username already taken." in c.errorMsgs


@pytest.mark.parametrize("field,value,message", [
    ("username", "", "Username is required."),
    ("username", "ab", "Username must be 4-20 characters"),
    ("name", "", "Name is required."),
    ("email", "not-an-email", "Email is not in a valid format."),
    ("phoneNo", "1234", "Phone number must be 8 digits"),
    ("phoneNo", "", "Phone number is required."),
    ("profileID", None, "Please select a user profile."),
])
def test_invalid_fields_are_reported(ctx, field, value, message):
    c = CreateUserAccountController()
    assert c.createUserAccount(new_ua(**{field: value}), "Secret123") is False
    assert any(m.startswith(message) for m in c.errorMsgs)
    assert UserAccount.findByUsername("newuser") is None


@pytest.mark.parametrize("password", ["short1A", "alllowercase1", "ALLUPPERCASE1", "NoNumbersHere"])
def test_password_policy(ctx, password):
    c = CreateUserAccountController()
    assert c.createUserAccount(new_ua(), password) is False
    assert any("Password must be" in m for m in c.errorMsgs)


def test_inactive_profile_is_rejected(ctx):
    db = get_db()
    db.execute("UPDATE user_profile SET status = 'Inactive' WHERE profile_name = 'Sales Manager'")
    db.commit()
    c = CreateUserAccountController()
    sm_id = db.execute("SELECT profile_id FROM user_profile WHERE profile_name = 'Sales Manager'").fetchone()[0]
    assert c.createUserAccount(new_ua(profileID=sm_id), "Secret123") is False


def test_credentials_notification_only_when_ticked(ctx):
    c = CreateUserAccountController()
    c.createUserAccount(new_ua(username="withmail"), "Secret123", emailCredentials=True)
    c.createUserAccount(new_ua(username="nomail"), "Secret123", emailCredentials=False)
    rows = get_db().execute("SELECT a.username, n.message FROM notification n "
                            "JOIN user_account a ON a.account_id = n.account_id").fetchall()
    assert [r[0] for r in rows] == ["withmail"]
    assert "Username: withmail" in rows[0][1]


# ---- Page ----
def test_only_user_admin_can_open_the_page(client):
    login(client, "customer")
    assert client.get("/admin/accounts/create").status_code == 403


def test_form_lists_profiles(client):
    login(client, "admin")
    html = client.get("/admin/accounts/create").get_data(as_text=True)
    assert "Create User Account" in html
    assert "Sales Manager" in html


def test_submit_creates_account_and_new_user_can_log_in(client, app):
    login(client, "admin")
    with app.app_context():
        pid = profile_id("Interior Designer")
    resp = client.post("/admin/accounts/create", data={
        "username": "janedesign", "password": "Design2026", "name": "Jane Design",
        "email": "jane@mail.com", "phone_no": "81234567", "profile_id": str(pid)})
    assert "Account created successfully" in resp.get_data(as_text=True)
    client.get("/logout")
    login(client, "janedesign", "Design2026")
    assert "Jane Design" in client.get("/home").get_data(as_text=True)


def test_submit_with_errors_keeps_entered_values(client):
    login(client, "admin")
    html = client.post("/admin/accounts/create", data={
        "username": "admin", "password": "x", "name": "Typed Name", "email": "bad",
        "phone_no": "1", "profile_id": ""}).get_data(as_text=True)
    assert "Username already taken." in html
    assert "Typed Name" in html


def test_menu_shows_link_for_admin(client):
    login(client, "admin")
    assert "Create User Account" in client.get("/home").get_data(as_text=True)
