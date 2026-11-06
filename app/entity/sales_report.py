"""<<entity>> SalesReport and SalesReportRow - User Story #50 Export Sales Report."""
import csv
import io
from datetime import timedelta
from app.db import get_db

CSV_HEADER = ["Date", "Estimates", "Total Estimated Value (SGD)", "Average Estimated Value (SGD)",
              "IDP Views", "Shortlists"]


class SalesReportRow:
    def __init__(self, day, estimatesCount=0, totalEstimatedValue=0.0, idpViews=0, shortlists=0):
        self.day = day                                   # date
        self.estimatesCount = estimatesCount
        self.totalEstimatedValue = round(totalEstimatedValue, 2)
        self.averageEstimatedValue = self.calculateAverage()
        self.idpViews = idpViews
        self.shortlists = shortlists

    def calculateAverage(self):
        return round(self.totalEstimatedValue / self.estimatesCount, 2) if self.estimatesCount else 0.0

    def toCSVLine(self):
        return [self.day.isoformat(), self.estimatesCount, f"{self.totalEstimatedValue:.2f}",
                f"{self.averageEstimatedValue:.2f}", self.idpViews, self.shortlists]

    @staticmethod
    def findByDateRange(start, end):
        """S2 - one row per day from start to end (dates, inclusive). Days with no activity are zero.
        Reads saved cost breakdowns (#29), IDP views and favourites (shortlists)."""
        lo, hi = start.isoformat() + " 00:00:00", end.isoformat() + " 23:59:59"
        db = get_db()
        est = {r[0]: (r[1], r[2]) for r in db.execute(
            "SELECT substr(created_date, 1, 10), COUNT(*), SUM(total) FROM cost_breakdown "
            "WHERE created_date BETWEEN ? AND ? GROUP BY 1", (lo, hi))}
        views = dict(db.execute("SELECT substr(viewed_date, 1, 10), COUNT(*) FROM idp_view "
                                "WHERE viewed_date BETWEEN ? AND ? GROUP BY 1", (lo, hi)).fetchall())
        favs = dict(db.execute("SELECT substr(saved_date, 1, 10), COUNT(*) FROM favourite "
                               "WHERE saved_date BETWEEN ? AND ? GROUP BY 1", (lo, hi)).fetchall())
        rows, day = [], start
        while day <= end:
            key = day.isoformat()
            count, total = est.get(key, (0, 0.0))
            rows.append(SalesReportRow(day, count, total or 0.0, views.get(key, 0), favs.get(key, 0)))
            day += timedelta(days=1)
        return rows


class SalesReport:
    def __init__(self, periodType, startDate, endDate, generatedBy, rows=None):
        self.periodType = periodType
        self.startDate = startDate
        self.endDate = endDate
        self.generatedBy = generatedBy
        self.rows = rows or []
        self.totalEstimates = 0
        self.totalEstimatedValue = 0.0
        self.totalViews = 0
        self.totalShortlists = 0

    def calculateTotals(self):
        self.totalEstimates = sum(r.estimatesCount for r in self.rows)
        self.totalEstimatedValue = round(sum(r.totalEstimatedValue for r in self.rows), 2)
        self.totalViews = sum(r.idpViews for r in self.rows)
        self.totalShortlists = sum(r.shortlists for r in self.rows)

    def averageEstimatedValue(self):
        return round(self.totalEstimatedValue / self.totalEstimates, 2) if self.totalEstimates else 0.0

    def toCSV(self):
        """S3 - header, one line per day, then a totals line."""
        out = io.StringIO()
        writer = csv.writer(out, lineterminator="\n")
        writer.writerow(CSV_HEADER)
        for r in self.rows:
            writer.writerow(r.toCSVLine())
        writer.writerow(["TOTAL", self.totalEstimates, f"{self.totalEstimatedValue:.2f}",
                         f"{self.averageEstimatedValue():.2f}", self.totalViews, self.totalShortlists])
        return out.getvalue()

    def getFileName(self):
        return f"sales_report_{self.periodType.lower()}_{self.startDate.isoformat()}.csv"
