"""<<boundary>> CompareFavouritesPg - User Story #27 Compare Favourite IDPs (Customer)."""
from flask import Blueprint, render_template, request, g
from app.boundary.auth import role_required
from app.constants import CUSTOMER
from app.control.compare_favourites_controller import CompareFavouritesController

bp = Blueprint("compare_favourites", __name__, url_prefix="/customer/favourites")


class CompareFavouritesPg:
    def __init__(self):
        self.controller = CompareFavouritesController()

    def displayFavourites(self, customerID, error=None, selected=None):
        return self.displayFavouriteList(self.controller.getFavourites(customerID), error, selected or [])

    def displayFavouriteList(self, favourites, error, selected):
        return render_template("favourites.html", favourites=favourites, error=error, selected=set(selected))

    def clickCompare(self, customerID, idpIDs):
        comparison = self.controller.compareFavourites(customerID, idpIDs)
        if comparison is None:
            return self.displayErrorMsg(customerID, self.controller.errorMsg, idpIDs)
        return self.displayComparison(comparison)

    def displayComparison(self, c):
        return render_template("compare.html", comparison=c)

    def displayErrorMsg(self, customerID, msg, idpIDs):
        return self.displayFavourites(customerID, msg, idpIDs)


def _ids(values):
    return [int(v) for v in values if str(v).isdigit()]


@bp.route("/")
@role_required(CUSTOMER)
def displayFavourites():
    return CompareFavouritesPg().displayFavourites(g.user.accountID)


@bp.route("/compare", methods=["POST"])
@role_required(CUSTOMER)
def clickCompare():
    return CompareFavouritesPg().clickCompare(g.user.accountID, _ids(request.form.getlist("idp_id")))
