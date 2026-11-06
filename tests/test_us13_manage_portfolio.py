"""Unit tests for User Story #13 Manage Portfolio."""
import io
from datetime import date, timedelta
from werkzeug.datastructures import FileStorage
from app.control.manage_portfolio_controller import ManagePortfolioController
from app.entity.idp import IDP
from tests.conftest import login
from tests.helpers import account_id, add_idp, add_category, count


def photo(name, size=1000):
    return FileStorage(stream=io.BytesIO(b"x" * size), filename=name)


# ---- Controller ----
def test_portfolio_shows_active_and_hidden_newest_first(ctx):
    add_idp(title="Old", completion="2025-01-01")
    add_idp(title="New", completion="2026-05-01")
    add_idp(title="Archived one", status="Archived")
    add_idp(title="Hidden one", status="Hidden", completion="2024-01-01")
    add_idp(designer="customer", title="Someone else's")   # not this designer's
    titles = [i.title for i in ManagePortfolioController().getPortfolio(account_id("designer"))]
    assert titles == ["New", "Old", "Hidden one"]


def test_archived_list(ctx):
    add_idp(title="Active one")
    add_idp(title="Archived one", status="Archived")
    assert [i.title for i in ManagePortfolioController().getArchivedIDPs(account_id("designer"))] == ["Archived one"]


def test_cannot_open_another_designers_idp(ctx):
    other = add_idp(designer="customer")
    assert ManagePortfolioController().getIDP(other, account_id("designer")) is None


def test_edit_saves_details(ctx, app):
    iid = add_idp()
    c = ManagePortfolioController()
    idp = c.getIDP(iid, account_id("designer"))
    idp.title, idp.totalCost = "Renamed", 45000
    assert c.editIDP(idp) is True
    saved = IDP.getIDPDetails(iid)
    assert saved.title == "Renamed" and saved.totalCost == 45000 and saved.updatedDate


def test_edit_validation_errors(ctx):
    iid = add_idp()
    c = ManagePortfolioController()
    idp = c.getIDP(iid, account_id("designer"))
    idp.title, idp.description, idp.totalCost, idp.floorArea = "", "", -1, 0
    idp.completionDate = (date.today() + timedelta(days=5)).isoformat()
    assert c.editIDP(idp) is False
    for msg in ["Title is required.", "Description is required.", "Total cost must be a positive number.",
                "Floor area must be a positive number.", "Completion date cannot be in the future."]:
        assert msg in c.errorMsgs
    assert IDP.getIDPDetails(iid).title == "Test IDP"     # nothing saved


def test_photo_rules(ctx, app, tmp_path):
    app.config["UPLOAD_FOLDER"] = str(tmp_path)
    iid = add_idp()
    c = ManagePortfolioController()
    idp = c.getIDP(iid, account_id("designer"))
    assert c.editIDP(idp, [photo("plan.pdf")]) is False
    assert "plan.pdf: photos must be JPG or PNG files." in c.errorMsgs
    assert c.editIDP(idp, [photo("big.jpg", 5 * 1024 * 1024)]) is False
    assert "big.jpg: photos must be under 5 MB." in c.errorMsgs
    assert c.editIDP(idp, [photo("room.png"), photo("kitchen.JPG")]) is True
    saved = IDP.getIDPDetails(iid)
    assert len(saved.photoURLs) == 2
    assert all((tmp_path / p).exists() for p in saved.photoURLs)
    assert c.editIDP(saved, removePhotos=[saved.photoURLs[0]]) is True
    assert len(IDP.getIDPDetails(iid).photoURLs) == 1


def test_archive_and_restore(ctx):
    iid = add_idp()
    me = account_id("designer")
    c = ManagePortfolioController()
    assert c.archiveIDP(iid, me) is True
    idp = IDP.getIDPDetails(iid)
    assert idp.status == "Archived" and idp.archivedDate
    assert c.archiveIDP(iid, me) is False             # already archived
    assert c.restoreIDP(iid, me) is True
    idp = IDP.getIDPDetails(iid)
    assert idp.status == "Active" and idp.archivedDate is None


def test_archive_removes_recommendations(ctx):
    iid = add_idp()
    from app.entity.recommendation import Recommendation
    Recommendation.refreshRecommendations(iid, [account_id("customer")])
    ManagePortfolioController().archiveIDP(iid, account_id("designer"))
    assert count("SELECT COUNT(*) FROM recommendation WHERE idp_id = ?", (iid,)) == 0


def test_cannot_archive_hidden_or_others(ctx):
    me = account_id("designer")
    c = ManagePortfolioController()
    assert c.archiveIDP(add_idp(status="Hidden"), me) is False
    assert c.archiveIDP(add_idp(designer="customer"), me) is False


def test_delete_removes_idp_and_links(ctx):
    cat = add_category("Japandi")
    iid = add_idp(categories=[cat])
    from app.db import get_db
    get_db().execute("INSERT INTO favourite (customer_id, idp_id, saved_date) VALUES (?, ?, '2026-10-01')",
                     (account_id("customer"), iid))
    get_db().commit()
    assert ManagePortfolioController().deleteIDP(iid, account_id("designer")) is True
    assert IDP.getIDPDetails(iid) is None
    assert count("SELECT COUNT(*) FROM idp_category WHERE idp_id = ?", (iid,)) == 0
    assert count("SELECT COUNT(*) FROM favourite WHERE idp_id = ?", (iid,)) == 0


def test_cannot_delete_reported_idp(ctx):
    iid = add_idp()
    from app.db import get_db
    get_db().execute("INSERT INTO report (idp_id, reporter_id, reason, reported_date) VALUES (?, ?, 'Spam', '2026-10-01')",
                     (iid, account_id("customer")))
    get_db().commit()
    c = ManagePortfolioController()
    assert c.deleteIDP(iid, account_id("designer")) is False
    assert "cannot be deleted" in c.errorMsgs[0]


# ---- Page ----
def test_only_designers_can_open(client):
    login(client, "customer")
    assert client.get("/designer/portfolio/").status_code == 403


def test_portfolio_page_and_edit(client, app):
    with app.app_context():
        iid = add_idp(title="Cosy Kitchen")
    login(client, "designer")
    assert "Cosy Kitchen" in client.get("/designer/portfolio/").get_data(as_text=True)
    html = client.post(f"/designer/portfolio/{iid}/edit", data={
        "title": "Cosy Kitchen v2", "description": "Updated", "property_type": "Condo",
        "floor_area": "100", "completion_date": "2026-02-01",
        "item_name": ["Kitchen cabinets", ""], "unit": ["m", "sqm"], "quantity": ["5", ""],
        "unit_rate": ["900", ""]}).get_data(as_text=True)
    assert "Project updated successfully" in html


def test_edit_page_of_other_designer_is_404(client, app):
    with app.app_context():
        iid = add_idp(designer="customer")
    login(client, "designer")
    assert client.get(f"/designer/portfolio/{iid}/edit").status_code == 404


def test_archive_button_flow(client, app):
    with app.app_context():
        iid = add_idp(title="To archive")
    login(client, "designer")
    html = client.post(f"/designer/portfolio/{iid}/archive", follow_redirects=True).get_data(as_text=True)
    assert "Project archived" in html and "To archive" not in html
    assert "To archive" in client.get("/designer/portfolio/archived").get_data(as_text=True)


# ---- Cost breakdown, Add Project, interest counts ----
from app.entity.idp_cost_item import IDPCostItem  # noqa: E402


def item(name="Vinyl flooring", unit="sqm", qty=50.0, rate=40.0):
    return IDPCostItem(None, None, name, unit, qty, rate)


def test_edit_cost_breakdown_recalculates_total(ctx):
    iid = add_idp(total=1)
    c = ManagePortfolioController()
    idp = c.getIDP(iid, account_id("designer"))
    assert c.editIDP(idp, costItems=[item(), item("Kitchen cabinets", "m", 4, 900)]) is True
    saved = IDP.getIDPDetails(iid)
    assert saved.totalCost == 5600.0
    assert [i.itemName for i in saved.getCostItems()] == ["Vinyl flooring", "Kitchen cabinets"]


def test_cost_item_validation(ctx):
    iid = add_idp()
    c = ManagePortfolioController()
    idp = c.getIDP(iid, account_id("designer"))
    assert c.editIDP(idp, costItems=[]) is False
    assert "Please add at least one cost breakdown item." in c.errorMsgs
    assert c.editIDP(idp, costItems=[item(name=""), item(unit="km"), item(qty=0), item(rate=-1)]) is False
    for msg in ["Cost item 1: please enter an item name.", "Cost item 2: please select a unit.",
                "Cost item 3: quantity must be a positive number.", "Cost item 4: unit rate must be a positive number."]:
        assert msg in c.errorMsgs


def test_add_project(ctx):
    me = account_id("designer")
    idp = IDP(None, me, "Brand New Loft", description="Fresh project", propertyType="Condo", floorArea=95,
              completionDate="2026-03-01")
    new_id = ManagePortfolioController().createIDP(idp, [item(qty=95, rate=45)])
    saved = IDP.getIDPDetails(new_id)
    assert saved.status == "Active" and saved.totalCost == 4275.0 and saved.designerID == me


def test_add_project_needs_breakdown_and_details(ctx):
    c = ManagePortfolioController()
    assert c.createIDP(IDP(None, account_id("designer"), ""), []) is None
    assert "Title is required." in c.errorMsgs and "Please add at least one cost breakdown item." in c.errorMsgs


def test_interest_counts(ctx):
    iid = add_idp()
    from app.db import get_db
    db = get_db()
    db.executemany("INSERT INTO idp_view (idp_id, viewed_date) VALUES (?, '2026-10-01')", [(iid,)] * 3)
    db.execute("INSERT INTO favourite (customer_id, idp_id, saved_date) VALUES (?, ?, '2026-10-01')",
               (account_id("customer"), iid))
    db.commit()
    assert ManagePortfolioController().getInterestCounts(account_id("designer"))[iid] == (3, 1)


def test_add_project_page(client):
    login(client, "designer")
    assert "Add Project" in client.get("/designer/portfolio/new").get_data(as_text=True)
    html = client.post("/designer/portfolio/new", data={
        "title": "Web Loft", "description": "From the page", "property_type": "HDB 5-Room", "floor_area": "110",
        "completion_date": "2026-01-10", "item_name": ["Wall painting"], "unit": ["sqm"], "quantity": ["120"],
        "unit_rate": ["8"]}).get_data(as_text=True)
    assert "Project added" in html and "Choose categories" in html
