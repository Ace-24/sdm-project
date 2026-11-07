"""<<boundary>> SubmitReportPg - a customer reports a project from its page."""
from flask import Blueprint, render_template, request, g, abort, redirect, url_for, flash
from app.constants import CUSTOMER
from app.control.submit_report_controller import SubmitReportController

bp = Blueprint("submit_report", __name__, url_prefix="/projects")


class SubmitReportPg:
    def __init__(self):
        self.controller = SubmitReportController()

    def _checkAccess(self, idpID):
        if g.user is None:
            flash("Please log in as a customer to report a project.", "error")
            return None, redirect(url_for("login.displayLoginForm"))
        if g.user.profileName != CUSTOMER:
            abort(403)
        idp = self.controller.getReportableIDP(idpID)
        if idp is None:
            abort(404)
        return idp, None

    def displayReportForm(self, idpID, form=None, errors=None):
        idp, stop = self._checkAccess(idpID)
        if stop:
            return stop
        return render_template("report_form.html", idp=idp, reasons=self.controller.getReasons(),
                               form=form or {}, errors=errors or [])

    def submitReport(self, idpID, form, files):
        idp, stop = self._checkAccess(idpID)
        if stop:
            return stop
        report = self.controller.submitReport(g.user, idp, form.get("reason", ""), form.get("description", ""),
                                              files.get("evidence"))
        if report is None:
            return self.displayErrorMsg(idpID, form, self.controller.errorMsgs)
        return self.displaySuccessPg(idp)

    def displaySuccessPg(self, idp):
        return render_template("success.html", message="Report submitted",
                               detail="Thank you. The Platform Manager will review it and you will be notified of the outcome.",
                               back_url=url_for("view_idp.displayIDPPage", idpID=idp.idpID), back_label="Back to the project")

    def displayErrorMsg(self, idpID, form, errors):
        return self.displayReportForm(idpID, form, errors)


@bp.route("/<int:idpID>/report", methods=["GET"])
def displayReportForm(idpID):
    return SubmitReportPg().displayReportForm(idpID)


@bp.route("/<int:idpID>/report", methods=["POST"])
def submitReport(idpID):
    return SubmitReportPg().submitReport(idpID, request.form, request.files)
