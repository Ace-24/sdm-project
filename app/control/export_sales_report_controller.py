"""<<control>> ExportSalesReportController - User Story #50 Export Sales Report."""
from app.control import report_period
from app.entity.sales_report import SalesReport, SalesReportRow


class ExportSalesReportController:
    def __init__(self):
        self.errorMsg = None
        self.report = None

    def exportSalesReport(self, salesManagerID, periodType, refDate):
        """Main flow steps 5-9. Returns the CSV text, or None (with errorMsg) if the period is invalid."""
        self.errorMsg = None
        day = self._validatePeriod(periodType, refDate)
        if day is None:
            self.errorMsg = "Please select a report period and a date that is not in the future"   # E1
            return None
        start, end = self._calculateDateRange(periodType, day)
        rows = SalesReportRow.findByDateRange(start, end)
        self.report = SalesReport(periodType, start, end, salesManagerID, rows)
        self.report.calculateTotals()
        return self.report.toCSV()

    # ---- Sub-flow S1: Validate Report Period ----
    @staticmethod
    def _validatePeriod(periodType, refDate):
        """Returns the date if valid, otherwise None."""
        return report_period.validatePeriod(periodType, refDate)

    # ---- Main flow step 6 ----
    @staticmethod
    def _calculateDateRange(periodType, day):
        return report_period.calculateDateRange(periodType, day)
