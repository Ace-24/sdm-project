"""<<entity>> Report - a user's report about an inappropriate IDP (#38)."""
from app.db import get_db
from app.entity.base import now_str
from app.constants import REPORT_PENDING, REPORT_CLOSED


class Report:
    def __init__(self, reportID, idpID, reporterID, reason, description="", evidenceURLs=None,
                 status=REPORT_PENDING, decision=None, closedBy=None, reportedDate=None, closedDate=None,
                 idpTitle=None, reporterName=None):
        self.reportID = reportID
        self.idpID = idpID
        self.reporterID = reporterID
        self.reason = reason
        self.description = description
        self.evidenceURLs = evidenceURLs or []
        self.status = status
        self.decision = decision
        self.closedBy = closedBy
        self.reportedDate = reportedDate
        self.closedDate = closedDate
        self.idpTitle = idpTitle            # joined for display
        self.reporterName = reporterName

    _SELECT = ("SELECT r.*, i.title AS idp_title, a.name AS reporter_name FROM report r "
               "JOIN idp i ON i.idp_id = r.idp_id JOIN user_account a ON a.account_id = r.reporter_id ")

    @staticmethod
    def _fromRow(row):
        if row is None:
            return None
        return Report(row["report_id"], row["idp_id"], row["reporter_id"], row["reason"], row["description"],
                      [u for u in (row["evidence_urls"] or "").split(",") if u], row["status"], row["decision"],
                      row["closed_by"], row["reported_date"], row["closed_date"], row["idp_title"], row["reporter_name"])

    @staticmethod
    def getReportsByStatus(status):
        """Main flow step 2 - e.g. all pending reports, oldest first."""
        rows = get_db().execute(Report._SELECT + "WHERE r.status = ? ORDER BY r.reported_date, r.report_id",
                                (status,)).fetchall()
        return [Report._fromRow(r) for r in rows]

    @staticmethod
    def getReport(reportID):
        return Report._fromRow(get_db().execute(Report._SELECT + "WHERE r.report_id = ?", (reportID,)).fetchone())

    def closeReport(self, decision, managerID):
        """S2 - set status Closed and record the decision, manager and date."""
        self.status, self.decision, self.closedBy, self.closedDate = REPORT_CLOSED, decision, managerID, now_str()
        db = get_db()
        db.execute("UPDATE report SET status = ?, decision = ?, closed_by = ?, closed_date = ? WHERE report_id = ?",
                   (self.status, decision, managerID, self.closedDate, self.reportID))
        db.commit()
        return True
