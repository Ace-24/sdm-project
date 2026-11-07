"""Unit tests for Browse Projects (public), the project page with its cost breakdown,
and saving favourites."""
import pytest
from app.control.browse_idp_controller import BrowseIDPController
from app.control.view_idp_controller import ViewIDPController
from app.control.create_estimation_rule_controller import CreateEstimationRuleController
from app.entity.estimation_rule import EstimationRule
from app.entity.unit_rate import UnitRate
from app.entity.idp import IDP
from app.entity.user_account import UserAccount
from app.entity.favourite import Favourite
from app.constants import PROPERTY_TYPES, RENOVATION_ITEMS
from tests.conftest import login
from tests.helpers import account_id, add_idp, add_category, add_cost_items, count


def set_factors(**factors):
    rule = EstimationRule(None, "Factors", account_id("smanager"))
    rule.unitRates = [UnitRate(code, name, unit, rate) for code, name, unit, rate in RENOVATION_ITEMS]
    rule.propertyFactors = {p: factors.get(p.replace(" ", "_").replace("-", "_"), 1.0) for p in PROPERTY_TYPES}
    assert CreateEstimationRuleController().createEstimationRule(rule)


# ---- Browse ----
def test_browse_shows_only_active_and_searches(ctx):
    jap = add_category("Japandi")
    add_idp(title="Zen Japandi Loft", categories=[jap])
    add_idp(title="Industrial Kitchen")
    add_idp(title="Hidden One", status="Hidden")
    c = BrowseIDPController()
    idps, total, pages = c.searchIDPs()
    assert total == 2 and "Hidden One" not in [i.title for i in idps]
    assert [i.title for i in c.searchIDPs("kitchen")[0]] == ["Industrial Kitchen"]
    assert [i.title for i in c.searchIDPs("japandi")[0]] == ["Zen Japandi Loft"]    # matches the category name
    assert [i.title for i in c.searchIDPs("", jap)[0]] == ["Zen Japandi Loft"]
    assert [i.title for i in c.searchIDPs("daniel")[0]] != []                        # designer name


def test_browse_pages(ctx):
    for n in range(30):
        add_idp(title=f"P{n}")
    idps, total, pages = BrowseIDPController().searchIDPs(page=2)
    assert (len(idps), total, pages) == (6, 30, 2)


def test_browse_is_public(client, app):
    with app.app_context():
        add_idp(title="Public Project")
    html = client.get("/projects/").get_data(as_text=True)
    assert "Public Project" in html and "Sign Up" in html


def test_visitors_land_on_browse(client):
    assert "/projects/" in client.get("/").headers["Location"]


# ---- Project page + cost breakdown ----
def test_breakdown_default_uses_designers_rates(ctx):
    iid = add_idp(ptype="HDB 4-Room")
    add_cost_items(iid, [("Vinyl flooring", "sqm", 50, 40), ("Kitchen cabinets", "m", 4, 900)])
    b = ViewIDPController().getCostBreakdown(IDP.getIDPDetails(iid))
    assert b["propertyType"] == "HDB 4-Room" and b["factor"] == 1.0
    assert (b["subtotal"], b["gst"], b["total"]) == (5600.0, 504.0, 6104.0)


def test_breakdown_adjusts_for_property_type(ctx):
    set_factors(Condo=1.2, Landed=1.5, HDB_4_Room=1.0)
    iid = add_idp(ptype="HDB 4-Room")
    add_cost_items(iid, [("Vinyl flooring", "sqm", 50, 40)])            # 2000
    c = ViewIDPController()
    idp = IDP.getIDPDetails(iid)
    assert c.getCostBreakdown(idp, "Condo")["subtotal"] == 2400.0
    assert c.getCostBreakdown(idp, "Landed")["subtotal"] == 3000.0
    assert c.getCostBreakdown(idp, "Spaceship")["propertyType"] == "HDB 4-Room"   # unknown -> project's own type


def test_breakdown_is_relative_to_projects_own_type(ctx):
    set_factors(Condo=1.2, Landed=1.5)
    iid = add_idp(ptype="Condo")                                          # rates entered for a condo
    add_cost_items(iid, [("Feature wall", "sqm", 10, 120)])               # 1200
    b = ViewIDPController().getCostBreakdown(IDP.getIDPDetails(iid), "Landed")
    assert b["factor"] == 1.25 and b["subtotal"] == 1500.0


def test_hidden_project_only_for_owner_and_platform_manager(ctx):
    iid = add_idp(status="Hidden")
    c = ViewIDPController()
    assert c.getIDPDetails(iid) is None
    assert c.getIDPDetails(iid, UserAccount.findByUsername("customer")) is None
    assert c.getIDPDetails(iid, UserAccount.findByUsername("designer")) is not None
    assert c.getIDPDetails(iid, UserAccount.findByUsername("pmanager")) is not None


def test_views_are_recorded_but_not_for_own_designer(client, app):
    with app.app_context():
        iid = add_idp()
    client.get(f"/projects/{iid}")                       # visitor
    login(client, "customer")
    client.get(f"/projects/{iid}")                       # customer
    client.get(f"/projects/{iid}?property=Condo")        # changing property type is not a new view
    client.get("/logout")
    login(client, "designer")
    client.get(f"/projects/{iid}")                       # own designer
    with app.app_context():
        assert count("SELECT COUNT(*) FROM idp_view WHERE idp_id = ?", (iid,)) == 2


def test_project_page_is_public_and_shows_breakdown(client, app):
    with app.app_context():
        iid = add_idp(title="Cosy Condo", ptype="Condo")
        add_cost_items(iid, [("Wall painting", "sqm", 100, 8)])
    html = client.get(f"/projects/{iid}?property=Landed").get_data(as_text=True)
    assert "Cosy Condo" in html and "Wall painting" in html and "Cost breakdown" in html
    assert "Sign up to save this project" in html


def test_missing_project_is_404(client):
    assert client.get("/projects/9999").status_code == 404


# ---- Favourites ----
def test_toggle_favourite(ctx):
    iid = add_idp()
    cid = account_id("customer")
    c = ViewIDPController()
    assert c.toggleFavourite(cid, IDP.getIDPDetails(iid)) is True and Favourite.isFavourite(cid, iid)
    assert c.toggleFavourite(cid, IDP.getIDPDetails(iid)) is False and not Favourite.isFavourite(cid, iid)


def test_save_favourite_from_page(client, app):
    with app.app_context():
        iid = add_idp(title="Love It")
    login(client, "customer")
    html = client.post(f"/projects/{iid}/favourite", follow_redirects=True).get_data(as_text=True)
    assert "Saved to your favourites." in html
    assert "Love It" in client.get("/customer/favourites/").get_data(as_text=True)


def test_visitor_must_log_in_to_save(client, app):
    with app.app_context():
        iid = add_idp()
    resp = client.post(f"/projects/{iid}/favourite")
    assert "/login" in resp.headers["Location"]


def test_designers_cannot_save_favourites(client, app):
    with app.app_context():
        iid = add_idp()
    login(client, "designer")
    assert client.post(f"/projects/{iid}/favourite").status_code == 403
