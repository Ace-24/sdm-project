"""<<boundary>> ViewActivityLogPg - User Story #7 View Account Activity Log (User Admin)."""
from flask import Blueprint, render_template, request, Response, g, redirect, url_for, flash, abort
from app.boundary.auth import role_required
from app.constants import USER_ADMIN, ACTIVITY_TYPES, ALL_ROLES
from app.control.view_activity_log_controller import ViewActivityLogController
from app.entity.user_account import UserAccount

bp = Blueprint("view_activity_log", __name__, url_prefix="/admin/activity-log")


class ViewActivityLogPg:
    def __init__(self):
        self.controller = ViewActivityLogController()

    def searchAccount(self, keyword, profileName=""):
        """Lists every current account when the page opens; the keyword and role narrow it down."""
        accounts = self.controller.searchUserAccount(keyword or "", profileName)
        if accounts:
            return self.displayAccountList(keyword or "", profileName or "", accounts)
        return self.displayErrorMsg("No accounts found.", keyword=keyword or "", profileName=profileName or "")

    def displayAccountList(self, keyword, profileName, accounts, error=None):
        return render_template("activity_search.html", keyword=keyword, role=profileName, roles=ALL_ROLES,
                               accounts=accounts, error=error)

    def displayActivityLog(self, accountID, args):
        account = UserAccount.findById(accountID)
        if account is None:
            abort(404)
        filters = {k: args.get(k, "") for k in ("type", "from", "to")}
        if any(filters.values()):
            logs = self.filterLog(accountID, filters["type"], filters["from"], filters["to"])
        else:
            logs = self.controller.viewActivityLog(accountID)
        if logs:
            return self.displayLogList(account, logs, filters)
        msg = self.controller.errorMsg or ("No activity matches this filter." if any(filters.values())
                                           else "No activity recorded for this account.")
        return self.displayErrorMsg(msg, account=account, filters=filters)

    def filterLog(self, accountID, activityType, fromDate, toDate):
        return self.controller.filterActivityLog(accountID, activityType, fromDate, toDate)

    def displayLogList(self, account, logs, filters, error=None):
        return render_template("activity_log.html", account=account, logs=logs, filters=filters,
                               types=ACTIVITY_TYPES, error=error)

    def displayErrorMsg(self, msg, account=None, filters=None, keyword="", profileName=""):
        """Show the message on the account search page, or on the account's log page."""
        if account is None:
            return self.displayAccountList(keyword, profileName, [], msg)
        return self.displayLogList(account, [], filters or {}, msg)

    def clickExport(self, accountID, args):
        account = UserAccount.findById(accountID)
        if account is None:
            abort(404)
        logs = self.controller.filterActivityLog(accountID, args.get("type"), args.get("from"), args.get("to")) or []
        csv_text = self.controller.exportActivityLog(logs)
        return Response(csv_text, mimetype="text/csv", headers={
            "Content-Disposition": f"attachment; filename=activity_log_{account.username}.csv"})

    def clickSuspend(self, accountID):
        if self.controller.suspendUserAccount(accountID, g.user.accountID, request.remote_addr):
            flash("Account suspended.", "success")
        else:
            flash("This account cannot be suspended.", "error")
        return redirect(url_for("view_activity_log.displayActivityLog", accountID=accountID))


@bp.route("/")
@role_required(USER_ADMIN)
def searchAccount():
    return ViewActivityLogPg().searchAccount(request.args.get("keyword"), request.args.get("role", ""))


@bp.route("/<int:accountID>")
@role_required(USER_ADMIN)
def displayActivityLog(accountID):
    return ViewActivityLogPg().displayActivityLog(accountID, request.args)


@bp.route("/<int:accountID>/export")
@role_required(USER_ADMIN)
def clickExport(accountID):
    return ViewActivityLogPg().clickExport(accountID, request.args)


@bp.route("/<int:accountID>/suspend", methods=["POST"])
@role_required(USER_ADMIN)
def clickSuspend(accountID):
    return ViewActivityLogPg().clickSuspend(accountID)


def _reactivate(page, accountID):
    if page.controller.reactivateUserAccount(accountID, g.user.accountID, request.remote_addr):
        flash("Account reactivated.", "success")
    else:
        flash("This account is not suspended.", "error")
    return redirect(url_for("view_activity_log.displayActivityLog", accountID=accountID))


@bp.route("/<int:accountID>/reactivate", methods=["POST"])
@role_required(USER_ADMIN)
def clickReactivate(accountID):
    """Reactivate a suspended account."""
    return _reactivate(ViewActivityLogPg(), accountID)
