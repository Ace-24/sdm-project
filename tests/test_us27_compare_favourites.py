"""Unit tests for User Story #27 Compare Favourite IDPs."""
from app.control.compare_favourites_controller import CompareFavouritesController
from app.entity.idp_comparison import IDPComparison
from app.entity.idp import IDP
from tests.conftest import login
from tests.helpers import account_id, add_idp, add_favourite


def three_favourites():
    a = add_idp(title="A", total=40000, area=100)      # 400 / sqm
    b = add_idp(title="B", total=30000, area=100)      # 300 / sqm  <- best
    c = add_idp(title="C", total=70000, area=200)      # 350 / sqm
    for i in (a, b, c):
        add_favourite("customer", i)
    return a, b, c


# ---- Entities ----
def test_cost_per_sqm():
    assert IDP(1, 1, "x", totalCost=45000, floorArea=90).getCostPerSqm() == 500.0
    assert IDP(1, 1, "x", totalCost=45000, floorArea=0).getCostPerSqm() == 0.0


def test_find_best_value_is_lowest_cost_per_sqm():
    c = IDPComparison(1)
    c.addIDPs([IDP(1, 1, "a", totalCost=40000, floorArea=100), IDP(2, 1, "b", totalCost=30000, floorArea=100)])
    assert c.findBestValue() == 2


def test_is_comparable():
    assert IDP(1, 1, "a", floorArea=80, status="Active").isComparable()
    assert not IDP(1, 1, "a", floorArea=0, status="Active").isComparable()
    assert not IDP(1, 1, "a", floorArea=80, status="Hidden").isComparable()


# ---- Controller ----
def test_favourites_list_has_idp_details(ctx):
    three_favourites()
    favs = CompareFavouritesController().getFavourites(account_id("customer"))
    assert len(favs) == 3 and favs[0].idp.designerName == "Daniel Designer"


def test_compare_two_and_three(ctx):
    a, b, c = three_favourites()
    ctl = CompareFavouritesController()
    two = ctl.compareFavourites(account_id("customer"), [a, c])
    assert [i.title for i in two.idps] == ["A", "C"] and two.bestValueID == c
    three = ctl.compareFavourites(account_id("customer"), [a, b, c])
    assert three.bestValueID == b


def test_selection_must_be_2_to_3(ctx):
    a, b, c = three_favourites()
    d = add_idp(title="D")
    add_favourite("customer", d)
    ctl = CompareFavouritesController()
    assert ctl.compareFavourites(account_id("customer"), [a]) is None
    assert ctl.errorMsg == "Please select 2 to 3 IDPs to compare"
    assert ctl.compareFavourites(account_id("customer"), [a, b, c, d]) is None
    assert ctl.compareFavourites(account_id("customer"), [a, a]) is None        # duplicate counts once


def test_cannot_compare_idps_not_in_own_favourites(ctx):
    a, b, c = three_favourites()
    other = add_idp(title="Not saved")
    assert CompareFavouritesController().compareFavourites(account_id("customer"), [a, other]) is None


def test_unavailable_idp_is_rejected(ctx):
    a, b, c = three_favourites()
    IDP.updateStatus(b, "Hidden")
    ctl = CompareFavouritesController()
    assert ctl.compareFavourites(account_id("customer"), [a, b]) is None
    assert ctl.errorMsg == "Please select 2 to 3 IDPs to compare"


# ---- Page ----
def test_only_customers(client):
    login(client, "designer")
    assert client.get("/customer/favourites/").status_code == 403


def test_list_and_compare_page(client, app):
    with app.app_context():
        a, b, c = three_favourites()
    login(client, "customer")
    assert "Compare" in client.get("/customer/favourites/").get_data(as_text=True)
    html = client.post("/customer/favourites/compare", data={"idp_id": [str(a), str(b)]}).get_data(as_text=True)
    assert "Best value" in html and "S$300.00" in html and "S$400.00" in html


def test_compare_error_on_page(client, app):
    with app.app_context():
        a, b, c = three_favourites()
    login(client, "customer")
    html = client.post("/customer/favourites/compare", data={"idp_id": [str(a)]}).get_data(as_text=True)
    assert "Please select 2 to 3 IDPs to compare" in html
