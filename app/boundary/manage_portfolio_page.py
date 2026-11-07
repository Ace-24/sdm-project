"""<<boundary>> ManagePortfolioPg - User Story #13 Manage Portfolio (Interior Designer)."""
from flask import Blueprint, render_template, request, g, redirect, url_for, flash, abort
from app.boundary.auth import role_required
from app.constants import INTERIOR_DESIGNER, PROPERTY_TYPES
from app.control.manage_portfolio_controller import ManagePortfolioController
from app.entity.idp import IDP
from app.entity.idp_cost_item import IDPCostItem, UNITS
from app.entity.unit_rate import UnitRate

bp = Blueprint("manage_portfolio", __name__, url_prefix="/designer/portfolio")


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _cost_items(form):
    """Read the cost breakdown rows from the form. Completely blank rows are ignored."""
    rows = zip(form.getlist("item_name"), form.getlist("unit"), form.getlist("quantity"), form.getlist("unit_rate"))
    items = []
    for name, unit, qty, rate in rows:
        if not (name.strip() or qty.strip() or rate.strip()):
            continue
        items.append(IDPCostItem(None, None, name.strip(), unit, _num(qty), _num(rate)))
    return items


def _fill(idp, form):
    idp.title = form.get("title", "").strip()
    idp.description = form.get("description", "").strip()
    idp.propertyType = form.get("property_type", "")
    idp.floorArea = _num(form.get("floor_area"))
    idp.completionDate = form.get("completion_date", "")


class ManagePortfolioPg:
    def __init__(self):
        self.controller = ManagePortfolioController()

    def displayPortfolio(self, designerID):
        return self.displayIDPList(self.controller.getPortfolio(designerID), archived=False,
                                   counts=self.controller.getInterestCounts(designerID))

    def viewArchivedIDPs(self, designerID):
        return self.displayIDPList(self.controller.getArchivedIDPs(designerID), archived=True,
                                   counts=self.controller.getInterestCounts(designerID))

    def displayIDPList(self, idps, archived, counts=None):
        return render_template("portfolio.html", idps=idps, archived=archived, counts=counts or {})

    def selectIDP(self, idpID, designerID):
        idp = self.controller.getIDP(idpID, designerID)
        if idp is None:
            abort(404)
        return self.displayEditForm(idp)

    def displayEditForm(self, idp, errors=None, items=None, new=False):
        if items is None:
            items = idp.getCostItems() if idp.idpID else []
        return render_template("idp_edit.html", idp=idp, property_types=PROPERTY_TYPES, errors=errors or [],
                               items=items, units=UNITS, item_names=[r.itemName for r in UnitRate.getActiveRates()], new=new)

    def displayAddProjectForm(self, designerID):
        return self.displayEditForm(IDP(None, designerID, ""), new=True)

    def submitNewIDP(self, designerID, form, files):
        idp = IDP(None, designerID, "")
        _fill(idp, form)
        items = _cost_items(form)
        if self.controller.createIDP(idp, items, files.getlist("photos")):
            return render_template("success.html", message="Project added",
                                   detail="Next, choose its categories so customers interested in them can find it.",
                                   back_url=url_for("manage_project_categories.displayCategoryForm", idpID=idp.idpID),
                                   back_label="Choose categories")
        return self.displayEditForm(idp, self.controller.errorMsgs, items, new=True)

    def submitIDP(self, idpID, designerID, form, files):
        idp = self.controller.getIDP(idpID, designerID)
        if idp is None:
            abort(404)
        _fill(idp, form)
        items = _cost_items(form)
        if self.controller.editIDP(idp, files.getlist("photos"), form.getlist("remove_photo"), items):
            return self.displaySuccessPg("Project updated successfully")
        return self.displayErrorMsg(idp, self.controller.errorMsgs, items)

    def displaySuccessPg(self, message):
        return render_template("success.html", message=message,
                               back_url=url_for("manage_portfolio.displayPortfolio"), back_label="Back to portfolio")

    def displayErrorMsg(self, idp, errors, items=None):
        return self.displayEditForm(idp, errors, items)

    def clickArchive(self, idpID, designerID):
        if self.controller.archiveIDP(idpID, designerID):
            flash("Project archived", "success")
        else:
            flash("This project cannot be archived.", "error")
        return redirect(url_for("manage_portfolio.displayPortfolio"))

    def clickRestore(self, idpID, designerID):
        if self.controller.restoreIDP(idpID, designerID):
            flash("Project restored and visible to customers again", "success")
        else:
            flash("This project cannot be restored.", "error")
        return redirect(url_for("manage_portfolio.viewArchivedIDPs"))

    def clickDelete(self, idpID, designerID, back):
        if self.controller.deleteIDP(idpID, designerID):
            flash("Project deleted", "success")
        else:
            flash(self.controller.errorMsgs[0], "error")
        return redirect(url_for("manage_portfolio.viewArchivedIDPs" if back == "archived"
                                else "manage_portfolio.displayPortfolio"))


@bp.route("/")
@role_required(INTERIOR_DESIGNER)
def displayPortfolio():
    return ManagePortfolioPg().displayPortfolio(g.user.accountID)


@bp.route("/archived")
@role_required(INTERIOR_DESIGNER)
def viewArchivedIDPs():
    return ManagePortfolioPg().viewArchivedIDPs(g.user.accountID)


@bp.route("/new", methods=["GET"])
@role_required(INTERIOR_DESIGNER)
def displayAddProjectForm():
    return ManagePortfolioPg().displayAddProjectForm(g.user.accountID)


@bp.route("/new", methods=["POST"])
@role_required(INTERIOR_DESIGNER)
def submitNewIDP():
    return ManagePortfolioPg().submitNewIDP(g.user.accountID, request.form, request.files)


@bp.route("/<int:idpID>/edit", methods=["GET"])
@role_required(INTERIOR_DESIGNER)
def selectIDP(idpID):
    return ManagePortfolioPg().selectIDP(idpID, g.user.accountID)


@bp.route("/<int:idpID>/edit", methods=["POST"])
@role_required(INTERIOR_DESIGNER)
def submitIDP(idpID):
    return ManagePortfolioPg().submitIDP(idpID, g.user.accountID, request.form, request.files)


@bp.route("/<int:idpID>/archive", methods=["POST"])
@role_required(INTERIOR_DESIGNER)
def clickArchive(idpID):
    return ManagePortfolioPg().clickArchive(idpID, g.user.accountID)


@bp.route("/<int:idpID>/restore", methods=["POST"])
@role_required(INTERIOR_DESIGNER)
def clickRestore(idpID):
    return ManagePortfolioPg().clickRestore(idpID, g.user.accountID)


@bp.route("/<int:idpID>/delete", methods=["POST"])
@role_required(INTERIOR_DESIGNER)
def clickDelete(idpID):
    return ManagePortfolioPg().clickDelete(idpID, g.user.accountID, request.form.get("back"))
