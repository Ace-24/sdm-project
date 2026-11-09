"""<<boundary>> CreateUserAccountPg - User Story #1 Create User Account (User Admin)."""
from flask import Blueprint, render_template, request
from app.boundary.auth import role_required
from app.constants import USER_ADMIN
from app.control.create_user_account_controller import CreateUserAccountController
from app.entity.user_account import UserAccount

bp = Blueprint("create_user_account", __name__, url_prefix="/admin/accounts")


class CreateUserAccountPg:
    def __init__(self):
        self.controller = CreateUserAccountController()

    def displayCreateUAForm(self, form=None, errors=None):
        profiles = self.controller.getActiveProfiles()
        return self.showProfileList(profiles, form or {}, errors or [])

    def showProfileList(self, profiles, form, errors):
        return render_template("create_user_account.html", profiles=profiles, form=form, errors=errors)

    def submitUAForm(self, form):
        try:
            profileID = int(form.get("profile_id", ""))
        except ValueError:
            profileID = None
        ua = UserAccount(None, form.get("username", "").strip(), form.get("name", "").strip(),
                         form.get("email", "").strip(), form.get("phone_no", "").strip(), profileID)
        ok = self.controller.createUserAccount(ua, form.get("password", ""),
                                               emailCredentials=form.get("email_credentials") == "on")
        if ok:
            return self.displaySuccessPg(ua, form.get("email_credentials") == "on")
        return self.displayErrorMsg(form, self.controller.errorMsgs)

    def displaySuccessPg(self, ua, emailed):
        return render_template("create_user_account_success.html", account=ua, emailed=emailed)

    def displayErrorMsg(self, form, errors):
        return self.displayCreateUAForm(form, errors)


@bp.route("/create", methods=["GET"])
@role_required(USER_ADMIN)
def displayCreateUAForm():
    return CreateUserAccountPg().displayCreateUAForm()


@bp.route("/create", methods=["POST"])
@role_required(USER_ADMIN)
def submitUAForm():
    return CreateUserAccountPg().submitUAForm(request.form)
