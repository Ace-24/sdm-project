"""<<boundary>> ExportSalesReportPg - User Story #50 Export Sales Report (Sales Manager)."""
from datetime import date
from flask import Blueprint, render_template, request, g, Response
from app.boundary.auth import role_required
from app.constants import SALES_MANAGER, PERIOD_TYPES
from app.control.export_sales_report_controller import ExportSalesReportController

bp = Blueprint("sales_report", __name__, url_prefix="/sales/reports")


class ExportSalesReportPg:
    def __init__(self):
        self.controller = ExportSalesReportController()

    def displaySalesReportForm(self, periodType="Weekly", refDate=None, error=None):
        return render_template("sales_report.html", period_types=PERIOD_TYPES, period=periodType,
                               ref_date=refDate or date.today().isoformat(), today=date.today().isoformat(),
                               error=error)

    def clickExport(self, periodType, refDate):
        csv_text = self.controller.exportSalesReport(g.user.accountID, periodType, refDate)
        if csv_text is None:
            return self.displayErrorMsg(periodType, refDate, self.controller.errorMsg)
        return self.downloadFile(csv_text, self.controller.report.getFileName())

    def downloadFile(self, csvContent, fileName):
        return Response(csvContent, mimetype="text/csv",
                        headers={"Content-Disposition": f"attachment; filename={fileName}"})

    def displayErrorMsg(self, periodType, refDate, msg):
        return self.displaySalesReportForm(periodType, refDate, msg)


@bp.route("/", methods=["GET"])
@role_required(SALES_MANAGER)
def displaySalesReportForm():
    return ExportSalesReportPg().displaySalesReportForm()


@bp.route("/export", methods=["POST"])
@role_required(SALES_MANAGER)
def clickExport():
    return ExportSalesReportPg().clickExport(request.form.get("period_type", ""), request.form.get("ref_date", ""))
