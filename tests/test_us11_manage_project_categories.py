"""Unit tests for User Story #11 Manage Project Categories."""
from app.control.manage_project_categories_controller import ManageProjectCategoriesController
from app.entity.idp import IDP
from app.entity.idp_category import IDPCategory
from app.entity.recommendation import Recommendation
from app.entity.user_account import UserAccount
from tests.conftest import login
from tests.helpers import account_id, add_idp, add_category, add_preference, count


def setup_cats():
    return {n: add_category(n) for n in ["Japandi", "Minimalist", "Kitchen", "Industrial", "Coastal", "Rustic"]}


# ---- Controller ----
def test_current_and_active_categories(ctx):
    cats = setup_cats()
    add_category("Old Style", status="Inactive")
    iid = add_idp(categories=[cats["Japandi"]])
    c = ManageProjectCategoriesController()
    assert c.getIDPCategories(iid) == [cats["Japandi"]]
    assert "Old Style" not in [x.categoryName for x in c.getActiveCategories()]


def test_update_replaces_links(ctx):
    cats = setup_cats()
    iid = add_idp(categories=[cats["Japandi"], cats["Kitchen"]])
    c = ManageProjectCategoriesController()
    assert c.updateIDPCategories(IDP.getIDPDetails(iid), [cats["Kitchen"], cats["Minimalist"]]) is True
    assert sorted(IDPCategory.getCategoryIDs(iid)) == sorted([cats["Kitchen"], cats["Minimalist"]])


def test_must_select_1_to_5_active_categories(ctx):
    cats = setup_cats()
    inactive = add_category("Old Style", status="Inactive")
    iid = add_idp(categories=[cats["Japandi"]])
    c = ManageProjectCategoriesController()
    idp = IDP.getIDPDetails(iid)
    assert c.updateIDPCategories(idp, []) is False
    assert c.errorMsg == "Please select 1 to 5 active categories"
    assert c.updateIDPCategories(idp, list(cats.values())) is False      # 6 categories
    assert c.updateIDPCategories(idp, [inactive]) is False
    assert IDPCategory.getCategoryIDs(iid) == [cats["Japandi"]]           # unchanged


def test_recommendations_go_to_matching_customers_only(ctx, app):
    cats = setup_cats()
    from app.db import get_db
    db = get_db()
    pid = db.execute("SELECT profile_id FROM user_profile WHERE profile_name='Customer'").fetchone()[0]
    for u in ("cust2", "cust3"):
        a = UserAccount(None, u, u, f"{u}@x.com", "91234567", pid)
        a.setPassword("Password123!")
        a.saveUserAccount()
    add_preference("customer", cats["Japandi"])
    add_preference("cust2", cats["Kitchen"])
    add_preference("cust3", cats["Coastal"])            # no match
    iid = add_idp()
    c = ManageProjectCategoriesController()
    assert c.updateIDPCategories(IDP.getIDPDetails(iid), [cats["Japandi"], cats["Kitchen"]]) is True
    assert c.matchedCustomers == 2
    assert [i.idpID for i in Recommendation.getForCustomer(account_id("customer"))] == [iid]
    assert Recommendation.getForCustomer(account_id("cust3")) == []
    # changing categories re-targets the recommendations
    c.updateIDPCategories(IDP.getIDPDetails(iid), [cats["Coastal"]])
    assert Recommendation.getForCustomer(account_id("customer")) == []
    assert [i.idpID for i in Recommendation.getForCustomer(account_id("cust3"))] == [iid]


def test_archived_idp_is_not_recommended(ctx):
    cats = setup_cats()
    add_preference("customer", cats["Japandi"])
    iid = add_idp(status="Archived")
    c = ManageProjectCategoriesController()
    assert c.updateIDPCategories(IDP.getIDPDetails(iid), [cats["Japandi"]]) is True
    assert c.matchedCustomers == 0


def test_request_new_category_notifies_platform_managers(ctx):
    setup_cats()
    c = ManageProjectCategoriesController()
    designer = UserAccount.findByUsername("designer")
    assert c.requestNewCategory(designer, "Neo-Classical", "Many clients ask for it") is True
    msg = count("SELECT COUNT(*) FROM notification WHERE account_id = ? AND subject LIKE '%Neo-Classical%'",
                (account_id("pmanager"),))
    assert msg == 1


def test_request_existing_or_empty_category_is_rejected(ctx):
    setup_cats()
    c = ManageProjectCategoriesController()
    designer = UserAccount.findByUsername("designer")
    assert c.requestNewCategory(designer, "japandi", "dup") is False
    assert "already exists" in c.errorMsg
    assert c.requestNewCategory(designer, "", "") is False


# ---- Page ----
def test_category_form_shows_ticked_categories(client, app):
    with app.app_context():
        cats = setup_cats()
        iid = add_idp(categories=[cats["Japandi"]])
    login(client, "designer")
    html = client.get(f"/designer/portfolio/{iid}/categories").get_data(as_text=True)
    assert f'value="{cats["Japandi"]}"\n      checked' in html or f'value="{cats["Japandi"]}" checked' in html.replace("\n      ", " ")


def test_submit_categories_success_and_error(client, app):
    with app.app_context():
        cats = setup_cats()
        iid = add_idp(categories=[cats["Japandi"]])
    login(client, "designer")
    ok = client.post(f"/designer/portfolio/{iid}/categories", data={"category_id": [str(cats["Kitchen"])]})
    assert "Project categories updated" in ok.get_data(as_text=True)
    bad = client.post(f"/designer/portfolio/{iid}/categories", data={})
    assert "Please select 1 to 5 active categories" in bad.get_data(as_text=True)


def test_customer_home_shows_recommendations(client, app):
    with app.app_context():
        cats = setup_cats()
        add_preference("customer", cats["Japandi"])
        iid = add_idp(title="Zen Japandi Loft")
        ManageProjectCategoriesController().updateIDPCategories(IDP.getIDPDetails(iid), [cats["Japandi"]])
    login(client, "customer")
    html = client.get("/home").get_data(as_text=True)
    assert "Projects you might like" in html and "Zen Japandi Loft" in html


def test_other_designers_idp_is_404(client, app):
    with app.app_context():
        iid = add_idp(designer="customer")
    login(client, "designer")
    assert client.get(f"/designer/portfolio/{iid}/categories").status_code == 404
