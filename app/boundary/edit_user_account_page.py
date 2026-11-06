"""<<boundary>> EditUserAccountPg - the User Admin edits an account's details."""
from flask import Blueprint, render_template, request, g, url_for, abort
from app.boundary.auth import role_required
from app.constants import USER_ADMIN
from app.control.edit_user_account_controller import EditUserAccountController
from app.entity.user_account import UserAccount

bp = Blueprint("edit_user_account", __name__, url_prefix="/admin/accounts")


class EditUserAccountPg:
    def __init__(self):
        self.controller = EditUserAccountController()

    def displayEditForm(self, accountID, ua=None, errors=None):
        account = self.controller.getAccount(accountID)
        if account is None:
            abort(404)
        return render_template("edit_user_account.html", account=ua or account, original=account,
                               profiles=self.controller.getActiveProfiles(), errors=errors or [])

    def submitEdit(self, accountID, form):
        if self.controller.getAccount(accountID) is None:
            abort(404)
        try:
            profileID = int(form.get("profile_id", ""))
        except ValueError:
            profileID = None
        ua = UserAccount(accountID, form.get("username", "").strip(), form.get("name", "").strip(),
                         form.get("email", "").strip(), form.get("phone_no", "").strip(), profileID)
        if self.controller.editUserAccount(ua, g.user.accountID, form.get("new_password", ""), request.remote_addr):
            return self.displaySuccessPg(accountID, self.controller.changed)
        return self.displayEditForm(accountID, ua, self.controller.errorMsgs)

    def displaySuccessPg(self, accountID, changed):
        return render_template("success.html", message="Account updated successfully",
                               detail=("Changed: " + ", ".join(changed)) if changed else "No changes were made.",
                               back_url=url_for("view_activity_log.displayActivityLog", accountID=accountID),
                               back_label="Back to account")


@bp.route("/<int:accountID>/edit", methods=["GET"])
@role_required(USER_ADMIN)
def displayEditForm(accountID):
    return EditUserAccountPg().displayEditForm(accountID)


@bp.route("/<int:accountID>/edit", methods=["POST"])
@role_required(USER_ADMIN)
def submitEdit(accountID):
    return EditUserAccountPg().submitEdit(accountID, request.form)
