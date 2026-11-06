"""<<boundary>> ViewIDPPg - a project's own page (public)."""
from flask import Blueprint, render_template, request, g, abort, redirect, url_for, flash
from app.constants import CUSTOMER, PROPERTY_TYPES
from app.control.view_idp_controller import ViewIDPController

bp = Blueprint("view_idp", __name__, url_prefix="/projects")


class ViewIDPPg:
    def __init__(self):
        self.controller = ViewIDPController()

    def displayIDPPage(self, idpID, propertyType=None):
        idp = self.controller.getIDPDetails(idpID, g.user)
        if idp is None:
            abort(404)
        if propertyType is None:                        # don't count a property-type change as a new view
            self.controller.recordView(idp, g.user)
        breakdown = self.controller.getCostBreakdown(idp, propertyType)
        is_customer = g.user is not None and g.user.profileName == CUSTOMER
        saved = is_customer and self.controller.isFavourite(g.user.accountID, idp.idpID)
        return render_template("idp_detail.html", idp=idp, b=breakdown, property_types=PROPERTY_TYPES,
                               is_customer=is_customer, saved=saved,
                               company=self.controller.getDesignerCompany(idp))

    def clickFavourite(self, idpID):
        if g.user is None:
            flash("Please log in or sign up to save projects to your favourites.", "error")
            return redirect(url_for("login.displayLoginForm"))
        if g.user.profileName != CUSTOMER:
            abort(403)
        idp = self.controller.getIDPDetails(idpID, g.user)
        if idp is None:
            abort(404)
        now_saved = self.controller.toggleFavourite(g.user.accountID, idp)
        flash("Saved to your favourites." if now_saved else "Removed from your favourites.", "success")
        return redirect(url_for("view_idp.displayIDPPage", idpID=idpID, property=request.form.get("property") or None))


@bp.route("/<int:idpID>")
def displayIDPPage(idpID):
    return ViewIDPPg().displayIDPPage(idpID, request.args.get("property"))


@bp.route("/<int:idpID>/favourite", methods=["POST"])
def clickFavourite(idpID):
    return ViewIDPPg().clickFavourite(idpID)
