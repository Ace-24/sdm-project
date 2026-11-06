"""<<entity>> PlatformReport - the Platform Manager's daily / weekly / monthly report (spec item 6)."""
import csv
import io
from app.db import get_db
from app.constants import CUSTOMER, INTERIOR_DESIGNER


class PlatformReport:
    def __init__(self, periodType, startDate, endDate):
        self.periodType = periodType
        self.startDate = startDate
        self.endDate = endDate
        self.summary = {}          # label -> number
        self.categoryRows = []     # (category, new IDPs, views, shortlists)

    def _range(self):
        return self.startDate.isoformat() + " 00:00:00", self.endDate.isoformat() + " 23:59:59"

    def collectSummary(self):
        lo, hi = self._range()
        db = get_db()
        one = lambda sql, *p: db.execute(sql, p).fetchone()[0]
        accounts = ("SELECT COUNT(*) FROM user_account a JOIN user_profile p ON p.profile_id = a.profile_id "
                    "WHERE p.profile_name = ? AND a.created_date BETWEEN ? AND ?")
        self.summary = {
            "New IDPs listed": one("SELECT COUNT(*) FROM idp WHERE created_date BETWEEN ? AND ?", lo, hi),
            "New customer accounts": one(accounts, CUSTOMER, lo, hi),
            "New designer accounts": one(accounts, INTERIOR_DESIGNER, lo, hi),
            "IDP views": one("SELECT COUNT(*) FROM idp_view WHERE viewed_date BETWEEN ? AND ?", lo, hi),
            "IDPs shortlisted": one("SELECT COUNT(*) FROM favourite WHERE saved_date BETWEEN ? AND ?", lo, hi),
            "Reports received": one("SELECT COUNT(*) FROM report WHERE reported_date BETWEEN ? AND ?", lo, hi),
            "Reports closed": one("SELECT COUNT(*) FROM report WHERE closed_date BETWEEN ? AND ?", lo, hi),
        }
        return self.summary

    def collectCategoryRows(self):
        """Per active category: new IDPs, views and shortlists in the period, most viewed first."""
        lo, hi = self._range()
        rows = get_db().execute(
            "SELECT c.category_name, "
            "(SELECT COUNT(*) FROM idp i JOIN idp_category ic ON ic.idp_id = i.idp_id "
            " WHERE ic.category_id = c.category_id AND i.created_date BETWEEN ? AND ?), "
            "(SELECT COUNT(*) FROM idp_view v JOIN idp_category ic ON ic.idp_id = v.idp_id "
            " WHERE ic.category_id = c.category_id AND v.viewed_date BETWEEN ? AND ?), "
            "(SELECT COUNT(*) FROM favourite f JOIN idp_category ic ON ic.idp_id = f.idp_id "
            " WHERE ic.category_id = c.category_id AND f.saved_date BETWEEN ? AND ?) "
            "FROM category c WHERE c.status = 'Active'", (lo, hi, lo, hi, lo, hi)).fetchall()
        self.categoryRows = sorted([tuple(r) for r in rows], key=lambda r: (-r[2], r[0]))
        return self.categoryRows

    def toCSV(self):
        out = io.StringIO()
        w = csv.writer(out, lineterminator="\n")
        w.writerow(["Platform report", self.periodType, self.startDate.isoformat(), self.endDate.isoformat()])
        w.writerow([])
        w.writerow(["Measure", "Value"])
        for k, v in self.summary.items():
            w.writerow([k, v])
        w.writerow([])
        w.writerow(["Category", "New IDPs", "IDP views", "Shortlisted"])
        for r in self.categoryRows:
            w.writerow(r)
        return out.getvalue()

    def getFileName(self):
        return f"platform_report_{self.periodType.lower()}_{self.startDate.isoformat()}.csv"
