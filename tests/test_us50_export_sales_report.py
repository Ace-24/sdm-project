"""Unit tests for User Story #50 Export Sales Report."""
from datetime import date, timedelta
import pytest
from app.control.export_sales_report_controller import ExportSalesReportController
from app.entity.sales_report import SalesReportRow
from app.db import get_db
from tests.conftest import login
from tests.helpers import account_id, add_idp


def add_breakdown(ts, total):
    db = get_db()
    db.execute("INSERT INTO cost_breakdown (customer_id, rule_id, property_type, style, subtotal, gst, total, created_date) "
               "VALUES (?, 1, 'Condo', 'Japandi', ?, 0, ?, ?)", (account_id("customer"), total, total, ts))
    db.commit()


def add_view(iid, ts):
    get_db().execute("INSERT INTO idp_view (idp_id, customer_id, viewed_date) VALUES (?, ?, ?)",
                     (iid, account_id("customer"), ts))
    get_db().commit()


def add_fav(iid, ts):
    get_db().execute("INSERT INTO favourite (customer_id, idp_id, saved_date) VALUES (?, ?, ?)",
                     (account_id("customer"), iid, ts))
    get_db().commit()


R = ExportSalesReportController._calculateDateRange


# ---- Date ranges ----
def test_daily_range():
    assert R("Daily", date(2026, 10, 28)) == (date(2026, 10, 28), date(2026, 10, 28))


def test_weekly_range_is_monday_to_sunday():
    assert R("Weekly", date(2026, 10, 28)) == (date(2026, 10, 26), date(2026, 11, 1))     # Wednesday
    assert R("Weekly", date(2026, 10, 26)) == (date(2026, 10, 26), date(2026, 11, 1))     # Monday
    assert R("Weekly", date(2026, 11, 1)) == (date(2026, 10, 26), date(2026, 11, 1))      # Sunday


def test_monthly_range_handles_month_lengths():
    assert R("Monthly", date(2026, 10, 15)) == (date(2026, 10, 1), date(2026, 10, 31))
    assert R("Monthly", date(2026, 2, 10)) == (date(2026, 2, 1), date(2026, 2, 28))
    assert R("Monthly", date(2028, 2, 10)) == (date(2028, 2, 1), date(2028, 2, 29))       # leap year


# ---- Validation ----
@pytest.mark.parametrize("period,ref", [("", "2026-10-01"), ("Yearly", "2026-10-01"), ("Daily", ""),
                                        ("Daily", "01/10/2026"),
                                        ("Daily", (date.today() + timedelta(days=1)).isoformat())])
def test_invalid_period_or_date(ctx, period, ref):
    c = ExportSalesReportController()
    assert c.exportSalesReport(1, period, ref) is None
    assert c.errorMsg == "Please select a report period and a date that is not in the future"


def test_today_is_allowed(ctx):
    assert ExportSalesReportController().exportSalesReport(1, "Daily", date.today().isoformat()) is not None


# ---- Data ----
def test_rows_count_activity_per_day(ctx):
    iid = add_idp()
    add_breakdown("2026-10-26 09:00:00", 1000)
    add_breakdown("2026-10-26 18:00:00", 3000)
    add_breakdown("2026-10-27 10:00:00", 500)
    add_breakdown("2026-11-02 10:00:00", 9999)          # next week - excluded
    add_view(iid, "2026-10-26 12:00:00")
    add_view(iid, "2026-10-26 23:59:59")
    add_fav(iid, "2026-10-28 08:00:00")
    rows = SalesReportRow.findByDateRange(date(2026, 10, 26), date(2026, 11, 1))
    assert len(rows) == 7
    mon, tue, wed = rows[0], rows[1], rows[2]
    assert (mon.estimatesCount, mon.totalEstimatedValue, mon.averageEstimatedValue, mon.idpViews) == (2, 4000, 2000, 2)
    assert (tue.estimatesCount, tue.averageEstimatedValue) == (1, 500)
    assert (wed.estimatesCount, wed.averageEstimatedValue, wed.shortlists) == (0, 0.0, 1)


def test_csv_has_header_rows_and_totals(ctx):
    add_breakdown("2026-10-26 09:00:00", 1000)
    add_breakdown("2026-10-27 09:00:00", 2000)
    c = ExportSalesReportController()
    lines = c.exportSalesReport(1, "Weekly", "2026-10-28").strip().splitlines()
    assert lines[0] == "Date,Estimates,Total Estimated Value (SGD),Average Estimated Value (SGD),IDP Views,Shortlists"
    assert lines[1] == "2026-10-26,1,1000.00,1000.00,0,0"
    assert len(lines) == 1 + 7 + 1
    assert lines[-1] == "TOTAL,2,3000.00,1500.00,0,0"
    assert c.report.getFileName() == "sales_report_weekly_2026-10-26.csv"


def test_monthly_report_has_one_row_per_day(ctx):
    lines = ExportSalesReportController().exportSalesReport(1, "Monthly", "2026-09-15").strip().splitlines()
    assert len(lines) == 1 + 30 + 1
    assert lines[-1] == "TOTAL,0,0.00,0.00,0,0"


# ---- Page ----
def test_only_sales_manager_can_open(client):
    login(client, "designer")
    assert client.get("/sales/reports/").status_code == 403


def test_download(client):
    login(client, "smanager")
    resp = client.post("/sales/reports/export", data={"period_type": "Monthly", "ref_date": "2026-10-05"})
    assert resp.mimetype == "text/csv"
    assert "filename=sales_report_monthly_2026-10-01.csv" in resp.headers["Content-Disposition"]


def test_error_shown_on_page(client):
    login(client, "smanager")
    future = (date.today() + timedelta(days=3)).isoformat()
    html = client.post("/sales/reports/export", data={"period_type": "Daily", "ref_date": future}).get_data(as_text=True)
    assert "Please select a report period and a date that is not in the future" in html
