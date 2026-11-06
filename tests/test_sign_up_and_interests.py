"""Unit tests for Sign Up (customers) and Choose Interests."""
from app.control.sign_up_controller import SignUpController
from app.control.choose_preferences_controller import ChoosePreferencesController
from app.entity.user_account import UserAccount
from app.entity.customer_preference import CustomerPreference
from tests.conftest import login
from tests.helpers import add_category, add_idp, count

FORM = {"username": "newbie", "password": "Welcome2026", "name": "New Bie",
        "email": "newbie@mail.com", "phone_no": "81234567"}


def new_ua(username="newbie"):
    return UserAccount(None, username, "New Bie", "newbie@mail.com", "81234567", None)


# ---- Controllers ----
def test_sign_up_creates_active_customer(ctx):
    assert SignUpController().registerCustomer(new_ua(), "Welcome2026") is True
    acc = UserAccount.findByUsername("newbie")
    assert acc.profileName == "Customer" and acc.status == "Active" and acc.checkPassword("Welcome2026")


def test_sign_up_uses_account_checks(ctx):
    c = SignUpController()
    assert c.registerCustomer(new_ua("customer"), "weak") is False
    assert "Username already taken." in c.errorMsgs
    assert any("Password must be" in m for m in c.errorMsgs)


def test_save_preferences(ctx):
    a, b = add_category("Japandi"), add_category("Kitchen")
    cid = UserAccount.findByUsername("customer").accountID
    c = ChoosePreferencesController()
    assert c.savePreferences(cid, [a, b, a]) is True
    assert CustomerPreference.getCategoryIDs(cid) == sorted([a, b])
    assert c.savePreferences(cid, [b]) is True                     # replaces old choices
    assert CustomerPreference.getCategoryIDs(cid) == [b]


def test_preferences_must_be_1_to_10_active(ctx):
    inactive = add_category("Old", status="Inactive")
    cats = [add_category(f"C{i}") for i in range(11)]
    cid = UserAccount.findByUsername("customer").accountID
    c = ChoosePreferencesController()
    assert c.savePreferences(cid, []) is False and c.errorMsg == "Please choose 1 to 10 categories"
    assert c.savePreferences(cid, cats) is False
    assert c.savePreferences(cid, [inactive]) is False


# ---- Pages ----
def test_signup_logs_in_and_asks_for_interests(client):
    resp = client.post("/signup", data=FORM)
    assert resp.status_code == 302 and "/customer/interests/?welcome=1" in resp.headers["Location"]
    html = client.get("/customer/interests/?welcome=1").get_data(as_text=True)
    assert "Welcome, New Bie!" in html


def test_signup_errors_keep_values(client):
    html = client.post("/signup", data=dict(FORM, username="admin", email="bad")).get_data(as_text=True)
    assert "Username already taken." in html and 'value="New Bie"' in html


def test_home_shows_chosen_categories_right_after_sign_up(client, app):
    with app.app_context():
        jap = add_category("Japandi")
        add_idp(title="Zen Japandi Loft", categories=[jap])
        add_idp(title="Unrelated Project")
    client.post("/signup", data=FORM)
    resp = client.post("/customer/interests/", data={"category_id": [str(jap)], "welcome": "1"}, follow_redirects=True)
    html = resp.get_data(as_text=True)
    assert "Your interests are saved" in html and "Zen Japandi Loft" in html and "Unrelated Project" not in html
    assert "From your interests: Japandi" in html


def test_logged_in_users_are_sent_home_from_signup(client):
    login(client, "customer")
    assert client.get("/signup").status_code == 302


def test_interests_page_is_for_customers(client):
    login(client, "designer")
    assert client.get("/customer/interests/").status_code == 403
