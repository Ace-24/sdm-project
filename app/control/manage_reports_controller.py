"""<<control>> ManageReportsController - User Story #38 Manage Reports on Inappropriate IDPs."""
from app.entity.report import Report
from app.entity.idp import IDP
from app.entity.notification import Notification
from app.constants import (REPORT_PENDING, IDP_HIDDEN, DECISION_HIDE, DECISION_WARN, DECISION_DISMISS)

DECISIONS = [DECISION_HIDE, DECISION_WARN, DECISION_DISMISS]


class ManageReportsController:
    def __init__(self):
        self.errorMsg = None

    def getPendingReports(self):
        return Report.getReportsByStatus(REPORT_PENDING)

    def getReportDetails(self, reportID):
        """The report and the reported IDP."""
        report = Report.getReport(reportID)
        return (report, IDP.getIDPDetails(report.idpID)) if report else (None, None)

    def processDecision(self, reportID, decision, managerID):
        """Returns True if the report was closed."""
        self.errorMsg = None
        report = Report.getReport(reportID)
        if report is None or report.status != REPORT_PENDING:
            self.errorMsg = "This report has already been closed."
            return False
        if decision not in DECISIONS:
            self.errorMsg = "Please select a decision: Hide IDP, Warn or Dismiss."
            return False
        idp = IDP.getIDPDetails(report.idpID)
        if decision == DECISION_HIDE:
            IDP.updateStatus(idp.idpID, IDP_HIDDEN)
        elif decision == DECISION_WARN:
            self._sendWarning(idp.designerID, idp, report)
        report.closeReport(decision, managerID)
        self._notifyOutcome(report, idp)
        return True

    @staticmethod
    def _sendWarning(designerID, idp, report):
        Notification.send(designerID, f"Warning about your project '{idp.title}'",
                          f"Your project was reported for: {report.reason}. Please review it and make sure it "
                          "follows the platform rules. Further reports may lead to the project being hidden.")

    @staticmethod
    def _notifyOutcome(report, idp):
        outcome = {DECISION_HIDE: "the project has been hidden from customers",
                   DECISION_WARN: "the designer has been warned",
                   DECISION_DISMISS: "no rule violation was found"}[report.decision]
        Notification.send(report.reporterID, f"Your report #{report.reportID} has been reviewed",
                          f"Thank you for your report about '{idp.title}'. Outcome: {outcome}.")
        if report.decision != DECISION_WARN:
            Notification.send(idp.designerID, f"Report about '{idp.title}' closed",
                              f"A report about your project was reviewed. Outcome: {outcome}.")
