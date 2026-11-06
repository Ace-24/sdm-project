"""<<control>> PlatformReportController - the Platform Manager's daily / weekly / monthly report (spec item 6)."""
from app.control import report_period
from app.entity.platform_report import PlatformReport


class PlatformReportController:
    def __init__(self):
        self.errorMsg = None

    def generateReport(self, periodType, refDate):
        """Returns the PlatformReport, or None (with errorMsg) if the period is invalid."""
        self.errorMsg = None
        day = report_period.validatePeriod(periodType, refDate)
        if day is None:
            self.errorMsg = "Please select a report period and a date that is not in the future"
            return None
        start, end = report_period.calculateDateRange(periodType, day)
        report = PlatformReport(periodType, start, end)
        report.collectSummary()
        report.collectCategoryRows()
        return report
