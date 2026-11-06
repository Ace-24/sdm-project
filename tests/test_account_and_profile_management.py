"""Unit tests for Edit User Account, Reactivate Account and Manage User Profiles (User Admin)."""
from app.control.edit_user_account_controller import EditUserAccountController
from app.control.view_activity_log_controller import ViewActivityLogController
from app.control.manage_user_profiles_controller import ManageUserProfilesController
from app.control.login_controller import LoginController
from app.entity.user_account import UserAccount
from app.entity.user_profile import UserProfile
from app.entity.activity_log import ActivityLog
from tests.conftest import login
from tests.helpers import account_id


def profile_id(name):
    return next(p.profileID for p in UserProfile.getAllProfiles() if p.profileName == name)


def edited(account="customer", **over):
    a = UserAccount.findByUsername(account)
    for k, v in over.items():
        setattr(a, k, v)
    return a


# ---- Edit account ----
def test_edit_saves_and_logs_changes(ctx):
    c = EditUserAccountController()
    assert c.editUserAccount(edited(name="Chloe Tan", phoneNo="87654321"), account_id("admin")) is True
    acc = UserAccount.findByUsername("customer")
    assert (acc.name, acc.phoneNo) == ("Chloe Tan", "87654321")
    log = ActivityLog.getActivityLog(acc.accountID)[0]
    assert log.activityType == "Profile Edit" and log.description == "Updated name, phone"
    assert log.performedByName == "admin"


def test_edit_can_reset_password(ctx):
    EditUserAccountController().editUserAccount(edited(), account_id("admin"), "NewPass2026")
    assert LoginController().validateLogin("customer", "NewPass2026")[0] is not None
    assert LoginController().validateLogin("customer", "Password123!")[0] is None


def test_blank_password_keeps_old_one(ctx):
    EditUserAccountController().editUserAccount(edited(name="X Y"), account_id("admin"), "")
    assert LoginController().validateLogin("customer", "Password123!")[0] is not None


def test_edit_validation(ctx):
    c = EditUserAccountController()
    assert c.editUserAccount(edited(username="designer", email="bad", phoneNo="12"), account_id("admin"), "weak") is False
    for msg in ["Username already taken.", "Email is not in a valid format.",
                "Phone number must be 8 digits starting with 6, 8 or 9."]:
        assert msg in c.errorMsgs
    assert any("Password must be" in m for m in c.errorMsgs)


def test_keeping_own_username_is_fine(ctx):
    assert EditUserAccountController().editUserAccount(edited(), account_id("admin")) is True


def test_admin_cannot_remove_own_admin_profile(ctx):
    c = EditUserAccountController()
    me = edited("admin", profileID=profile_id("Customer"))
    assert c.editUserAccount(me, account_id("admin")) is False
    assert "You cannot remove your own User Admin profile." in c.errorMsgs


# ---- Reactivate ----
def test_reactivate_suspended_account(ctx):
    c = ViewActivityLogController()
    cid, aid = account_id("customer"), account_id("admin")
    c.suspendUserAccount(cid, aid)
    assert c.reactivateUserAccount(cid, aid) is True
    assert UserAccount.findById(cid).status == "Active"
    assert ActivityLog.getActivityLog(cid)[0].description == "Status changed from Suspended to Active"
    assert LoginController().validateLogin("customer", "Password123!")[0] is not None
    assert c.reactivateUserAccount(cid, aid) is False             # not suspended any more


# ---- User profiles ----
def test_profiles_list_with_counts(ctx):
    profiles = {p.profileName: p.accountCount for p in ManageUserProfilesController().getProfiles()}
    assert profiles["Customer"] == 1 and len(profiles) == 5


def test_create_profile(ctx):
    c = ManageUserProfilesController()
    assert c.createProfile("Contractor", "Renovation contractors") is True
    assert c.createProfile("contractor", "dup") is False and "already exists" in c.errorMsg
    assert c.createProfile("", "") is False


def test_suspended_profile_blocks_login_and_new_accounts(ctx):
    c = ManageUserProfilesController()
    pid = profile_id("Sales Manager")
    assert c.updateProfile(pid, "Sales team", "Inactive") is True
    account, err = LoginController().validateLogin("smanager", "Password123!")
    assert account is None and "Sales Manager profile is currently suspended" in err
    assert "Sales Manager" not in [p.profileName for p in UserProfile.getActiveProfiles()]
    c.updateProfile(pid, "Sales team", "Active")
    assert LoginController().validateLogin("smanager", "Password123!")[0] is not None


def test_user_admin_profile_cannot_be_suspended(ctx):
    c = ManageUserProfilesController()
    assert c.updateProfile(profile_id("User Admin"), "", "Inactive") is False
    assert c.errorMsg == "The User Admin profile cannot be suspended."


# ---- Pages ----
def test_edit_page_flow(client, app):
    with app.app_context():
        cid = account_id("customer")
        pid = profile_id("Customer")
    login(client, "admin")
    assert "Edit User Account: customer" in client.get(f"/admin/accounts/{cid}/edit").get_data(as_text=True)
    html = client.post(f"/admin/accounts/{cid}/edit", data={
        "username": "customer", "name": "Chloe Lim", "email": "customer@idp.example.com", "phone_no": "91234567",
        "profile_id": str(pid), "new_password": ""}).get_data(as_text=True)
    assert "Account updated successfully" in html and "Changed: name" in html


def test_reactivate_button(client, app):
    with app.app_context():
        cid = account_id("customer")
        ViewActivityLogController().suspendUserAccount(cid, account_id("admin"))
    login(client, "admin")
    assert "Reactivate Account" in client.get(f"/admin/activity-log/{cid}").get_data(as_text=True)
    assert "Account reactivated." in client.post(f"/admin/activity-log/{cid}/reactivate",
                                                  follow_redirects=True).get_data(as_text=True)


def test_profiles_page_update(client, app):
    with app.app_context():
        pid = profile_id("Customer")
    login(client, "admin")
    assert "User Profiles" in client.get("/admin/profiles/").get_data(as_text=True)
    resp = client.post(f"/admin/profiles/{pid}", data={"description": "Home owners", "status": "Active"},
                       follow_redirects=True)
    assert "Profile updated" in resp.get_data(as_text=True)


def test_only_user_admin(client):
    login(client, "pmanager")
    assert client.get("/admin/profiles/").status_code == 403
    assert client.get("/admin/accounts/1/edit").status_code == 403
