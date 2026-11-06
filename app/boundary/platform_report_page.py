"""<<boundary>> PlatformReportPg - the Platform Manager's daily / weekly / monthly report."""
from datetime import date
from flask import Blueprint, render_template, request, Response
from app.boundary.auth import role_required
from app.constants import PLATFORM_MANAGER, PERIOD_TYPES
from app.control.platform_report_controller import PlatformReportController

bp = Blueprint("platform_report", __name__, url_prefix="/platform/platform-reports")


class PlatformReportPg:
    def __init__(self):
        self.controller = PlatformReportController()

    def displayReportForm(self, periodType=None, refDate=None):
        report, error = None, None
        if periodType:                                     # the form was submitted
            report = self.controller.generateReport(periodType, refDate)
            error = self.controller.errorMsg
        return self.displayReport(report, periodType or "Weekly", refDate or date.today().isoformat(), error)

    def displayReport(self, report, periodType, refDate, error):
        return render_template("platform_report.html", report=report, period_types=PERIOD_TYPES, period=periodType,
                               ref_date=refDate, today=date.today().isoformat(), error=error)

    def clickExport(self, periodType, refDate):
        report = self.controller.generateReport(periodType, refDate)
        if report is None:
            return self.displayReport(None, periodType, refDate, self.controller.errorMsg)
        return Response(report.toCSV(), mimetype="text/csv",
                        headers={"Content-Disposition": f"attachment; filename={report.getFileName()}"})


@bp.route("/", methods=["GET"])
@role_required(PLATFORM_MANAGER)
def displayReportForm():
    return PlatformReportPg().displayReportForm(request.args.get("period"), request.args.get("date"))


@bp.route("/export", methods=["POST"])
@role_required(PLATFORM_MANAGER)
def clickExport():
    return PlatformReportPg().clickExport(request.form.get("period", ""), request.form.get("date", ""))
