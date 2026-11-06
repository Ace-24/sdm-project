"""<<boundary>> LoginPg - login form, logout and the role home page."""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, g
from app.control.login_controller import LoginController
from app.boundary.auth import login_required
from app.constants import CUSTOMER
from app.entity.recommendation import Recommendation
from app.entity.customer_preference import CustomerPreference
from app.entity.category import Category

bp = Blueprint("login", __name__)


class LoginPg:
    def __init__(self):
        self.controller = LoginController()

    def displayLoginForm(self, error=None):
        return render_template("login.html", error=error)

    def submitLogin(self, username, password):
        account, error = self.controller.validateLogin(username, password, request.remote_addr)
        if error:
            return self.displayLoginForm(error)
        session.clear()
        session["account_id"] = account.accountID
        return redirect(url_for("login.displayHome"))

    def clickLogout(self):
        if g.user is not None:
            self.controller.logout(g.user.accountID, request.remote_addr)
        session.clear()
        flash("You have been logged out.", "success")
        return redirect(url_for("login.displayLoginForm"))


@bp.route("/", methods=["GET"])
def index():
    return redirect(url_for("login.displayHome") if g.user else url_for("browse_idp.displayBrowsePage"))


@bp.route("/login", methods=["GET", "POST"])
def displayLoginForm():
    page = LoginPg()
    if request.method == "POST":
        return page.submitLogin(request.form.get("username", ""), request.form.get("password", ""))
    if g.user:
        return redirect(url_for("login.displayHome"))
    return page.displayLoginForm()


@bp.route("/logout")
def clickLogout():
    return LoginPg().clickLogout()


@bp.route("/home")
@login_required
def displayHome():
    recommendations, interests = [], []
    if g.user.profileName == CUSTOMER:
        recommendations = Recommendation.getForCustomer(g.user.accountID)   # preferred categories + #11
        prefs = set(CustomerPreference.getCategoryIDs(g.user.accountID))
        interests = [c.categoryName for c in Category.getActiveCategories() if c.categoryID in prefs]
    return render_template("home.html", recommendations=recommendations, interests=interests)
