"""<<boundary>> ManageProjectCategoriesPg - User Story #11 Manage Project Categories (Interior Designer)."""
from flask import Blueprint, render_template, request, g, url_for, abort, flash, redirect
from app.boundary.auth import role_required
from app.constants import INTERIOR_DESIGNER
from app.control.manage_project_categories_controller import ManageProjectCategoriesController
from app.control.manage_portfolio_controller import ManagePortfolioController

bp = Blueprint("manage_project_categories", __name__, url_prefix="/designer/portfolio")


class ManageProjectCategoriesPg:
    def __init__(self):
        self.controller = ManageProjectCategoriesController()

    def _ownIDP(self, idpID):
        idp = ManagePortfolioController().getIDP(idpID, g.user.accountID)
        if idp is None:
            abort(404)
        return idp

    def displayCategoryForm(self, idpID, error=None, selectedIDs=None):
        """Main flow steps 1-2."""
        idp = self._ownIDP(idpID)
        categories = self.controller.getActiveCategories()
        if selectedIDs is None:
            selectedIDs = self.controller.getIDPCategories(idpID)
        return self.showCategoryForm(idp, categories, selectedIDs, error)

    def showCategoryForm(self, idp, categories, selectedIDs, error):
        return render_template("idp_categories.html", idp=idp, categories=categories,
                               selected=set(selectedIDs), error=error)

    def submitCategories(self, idpID, categoryIDs):
        """Main flow step 4."""
        idp = self._ownIDP(idpID)
        if self.controller.updateIDPCategories(idp, categoryIDs):
            return self.displaySuccessPg(self.controller.matchedCustomers)
        return self.displayErrorMsg(idpID, self.controller.errorMsg, categoryIDs)

    def displaySuccessPg(self, matched):
        return render_template("success.html", message="Project categories updated",
                               detail=f"This project is now recommended to {matched} customer(s) with matching interests.",
                               back_url=url_for("manage_portfolio.displayPortfolio"), back_label="Back to portfolio")

    def displayErrorMsg(self, idpID, msg, categoryIDs):
        return self.displayCategoryForm(idpID, msg, categoryIDs)

    def clickRequestCategory(self, idpID, name, reason):
        """A2 - Request New Category."""
        self._ownIDP(idpID)
        if self.controller.requestNewCategory(g.user, name, reason):
            flash(f"Your request for '{name.strip()}' was sent to the Platform Manager.", "success")
        else:
            flash(self.controller.errorMsg, "error")
        return redirect(url_for("manage_project_categories.displayCategoryForm", idpID=idpID))


def _ids(values):
    out = []
    for v in values:
        try:
            out.append(int(v))
        except ValueError:
            pass
    return out


@bp.route("/<int:idpID>/categories", methods=["GET"])
@role_required(INTERIOR_DESIGNER)
def displayCategoryForm(idpID):
    return ManageProjectCategoriesPg().displayCategoryForm(idpID)


@bp.route("/<int:idpID>/categories", methods=["POST"])
@role_required(INTERIOR_DESIGNER)
def submitCategories(idpID):
    return ManageProjectCategoriesPg().submitCategories(idpID, _ids(request.form.getlist("category_id")))


@bp.route("/<int:idpID>/categories/request", methods=["POST"])
@role_required(INTERIOR_DESIGNER)
def clickRequestCategory(idpID):
    return ManageProjectCategoriesPg().clickRequestCategory(idpID, request.form.get("name"), request.form.get("reason"))
