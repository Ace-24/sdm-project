"""<<boundary>> ChoosePreferencesPg - a customer chooses the categories shown on their home page."""
from flask import Blueprint, render_template, request, g, redirect, url_for, flash
from app.boundary.auth import role_required
from app.constants import CUSTOMER
from app.control.choose_preferences_controller import ChoosePreferencesController, MAX_PREFERENCES

bp = Blueprint("choose_preferences", __name__, url_prefix="/customer/interests")


class ChoosePreferencesPg:
    def __init__(self):
        self.controller = ChoosePreferencesController()

    def displayPreferenceForm(self, customerID, welcome=False, selected=None, error=None):
        if selected is None:
            selected = self.controller.getPreferences(customerID)
        return render_template("preferences.html", categories=self.controller.getActiveCategories(),
                               selected=set(selected), welcome=welcome, error=error, maximum=MAX_PREFERENCES)

    def submitPreferences(self, customerID, categoryIDs, welcome):
        if self.controller.savePreferences(customerID, categoryIDs):
            flash("Your interests are saved. Here are projects from the categories you chose.", "success")
            return redirect(url_for("login.displayHome"))
        return self.displayPreferenceForm(customerID, welcome, categoryIDs, self.controller.errorMsg)


@bp.route("/", methods=["GET"])
@role_required(CUSTOMER)
def displayPreferenceForm():
    return ChoosePreferencesPg().displayPreferenceForm(g.user.accountID, request.args.get("welcome") == "1")


@bp.route("/", methods=["POST"])
@role_required(CUSTOMER)
def submitPreferences():
    ids = [int(v) for v in request.form.getlist("category_id") if v.isdigit()]
    return ChoosePreferencesPg().submitPreferences(g.user.accountID, ids, request.form.get("welcome") == "1")
