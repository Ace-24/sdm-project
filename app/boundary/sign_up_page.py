"""<<boundary>> SignUpPg - visitors create their own Customer account."""
from flask import Blueprint, render_template, request, redirect, url_for, session, g
from app.control.sign_up_controller import SignUpController
from app.entity.user_account import UserAccount

bp = Blueprint("sign_up", __name__)


class SignUpPg:
    def __init__(self):
        self.controller = SignUpController()

    def displaySignUpForm(self, form=None, errors=None):
        return render_template("signup.html", form=form or {}, errors=errors or [])

    def submitSignUp(self, form):
        ua = UserAccount(None, form.get("username", "").strip(), form.get("name", "").strip(),
                         form.get("email", "").strip(), form.get("phone_no", "").strip(), None)
        if not self.controller.registerCustomer(ua, form.get("password", ""), request.remote_addr):
            return self.displayErrorMsg(form, self.controller.errorMsgs)
        session.clear()
        session["account_id"] = ua.accountID          # logged in straight away
        return redirect(url_for("choose_preferences.displayPreferenceForm", welcome=1))

    def displayErrorMsg(self, form, errors):
        return self.displaySignUpForm(form, errors)


@bp.route("/signup", methods=["GET", "POST"])
def displaySignUpForm():
    if g.user:
        return redirect(url_for("login.displayHome"))
    page = SignUpPg()
    if request.method == "POST":
        return page.submitSignUp(request.form)
    return page.displaySignUpForm()
