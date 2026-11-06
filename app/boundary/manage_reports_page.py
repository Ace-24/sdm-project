"""<<boundary>> ManageReportsPg - User Story #38 Manage Reports on Inappropriate IDPs (Platform Manager)."""
from flask import Blueprint, render_template, request, g, url_for, abort
from app.boundary.auth import role_required
from app.constants import PLATFORM_MANAGER
from app.control.manage_reports_controller import ManageReportsController, DECISIONS

bp = Blueprint("manage_reports", __name__, url_prefix="/platform/reports")


class ManageReportsPg:
    def __init__(self):
        self.controller = ManageReportsController()

    def displayReportList(self):
        return self.showReportList(self.controller.getPendingReports())

    def showReportList(self, reports):
        return render_template("reports.html", reports=reports)

    def selectReport(self, reportID, error=None):
        report, idp = self.controller.getReportDetails(reportID)
        if report is None:
            abort(404)
        return self.displayReportDetails(report, idp, error)

    def displayReportDetails(self, r, idp, error=None):
        return render_template("report_details.html", report=r, idp=idp, decisions=DECISIONS, error=error)

    def submitDecision(self, reportID, decision):
        if self.controller.processDecision(reportID, decision, g.user.accountID):
            return self.displaySuccessPg()
        return self.displayErrorMsg(reportID, self.controller.errorMsg)

    def displaySuccessPg(self):
        return render_template("success.html", message="Report closed",
                               detail="The decision was applied and the people involved have been notified.",
                               back_url=url_for("manage_reports.displayReportList"), back_label="Back to reports")

    def displayErrorMsg(self, reportID, msg):
        return self.selectReport(reportID, msg)


@bp.route("/")
@role_required(PLATFORM_MANAGER)
def displayReportList():
    return ManageReportsPg().displayReportList()


@bp.route("/<int:reportID>", methods=["GET"])
@role_required(PLATFORM_MANAGER)
def selectReport(reportID):
    return ManageReportsPg().selectReport(reportID)


@bp.route("/<int:reportID>", methods=["POST"])
@role_required(PLATFORM_MANAGER)
def submitDecision(reportID):
    return ManageReportsPg().submitDecision(reportID, request.form.get("decision", ""))
