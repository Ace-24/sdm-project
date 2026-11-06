"""Unit tests for User Story #29 Generate Cost Breakdown (uses #47's active rule)."""
from app.control.generate_cost_breakdown_controller import GenerateCostBreakdownController
from app.control.create_estimation_rule_controller import CreateEstimationRuleController
from app.entity.cost_breakdown import CostBreakdown, BreakdownItem
from app.entity.estimation_rule import EstimationRule
from app.entity.unit_rate import UnitRate
from app.constants import PROPERTY_TYPES, RENOVATION_ITEMS
from tests.conftest import login
from tests.helpers import account_id, add_category, count


def set_rule(condo=1.2, japandi=1.5):
    """Make an active #47 rule with known multipliers."""
    add_category("Japandi")
    rule = EstimationRule(None, "Test rule", account_id("smanager"))
    rule.unitRates = [UnitRate(code, None, None, rate) for code, _, _, rate in RENOVATION_ITEMS]
    rule.propertyFactors = {p: (condo if p == "Condo" else 1.0) for p in PROPERTY_TYPES}
    rule.styleFactors = {"Japandi": japandi}
    assert CreateEstimationRuleController().createEstimationRule(rule)


# ---- Entities ----
def test_line_total():
    assert BreakdownItem("PAINT", "Wall painting", "sqm", 50, 8, 1.0).lineTotal == 400.0
    assert BreakdownItem("PAINT", "Wall painting", "sqm", 50, 8, 1.5).lineTotal == 600.0


def test_subtotal_gst_total():
    cb = CostBreakdown(None, 1, 1, "Condo", "Standard")
    cb.items = [BreakdownItem("A", "a", "sqm", 10, 45, 1.0), BreakdownItem("B", "b", "unit", 2, 120, 1.0)]
    assert cb.calculateTotal() == 752.1          # 450 + 240 = 690, GST 9% = 62.10
    assert (cb.subtotal, cb.gst) == (690.0, 62.1)


# ---- Controller ----
def test_items_come_from_active_rule(ctx):
    items = GenerateCostBreakdownController().getRenovationItems()
    assert len(items) == 12 and items[0].itemName == "Vinyl flooring"


def test_breakdown_without_style_uses_property_factor_only(ctx):
    set_rule(condo=1.2)
    c = GenerateCostBreakdownController()
    cb = c.generateBreakdown(account_id("customer"), {"FLOOR": 10, "ELEC": 2}, "Condo", "")
    # FLOOR 10 x 45 x 1.2 = 540 ; ELEC 2 x 120 x 1.2 = 288 ; subtotal 828 ; GST 74.52
    assert [i.lineTotal for i in cb.items] == [540.0, 288.0]
    assert (cb.subtotal, cb.gst, cb.total) == (828.0, 74.52, 902.52)
    assert cb.style == "Standard"


def test_breakdown_applies_style_multiplier(ctx):
    set_rule(condo=1.2, japandi=1.5)
    cb = GenerateCostBreakdownController().generateBreakdown(account_id("customer"), {"FLOOR": 10}, "Condo", "Japandi")
    assert cb.items[0].lineTotal == 810.0            # 10 x 45 x 1.2 x 1.5


def test_breakdown_is_saved_for_sales_report(ctx):
    set_rule()
    cb = GenerateCostBreakdownController().generateBreakdown(account_id("customer"), {"PAINT": 50}, "HDB 4-Room", "")
    rule = EstimationRule.findActive()
    assert count("SELECT COUNT(*) FROM cost_breakdown WHERE breakdown_id = ? AND rule_id = ? AND customer_id = ?",
                 (cb.breakdownID, rule.ruleID, account_id("customer"))) == 1
    assert count("SELECT COUNT(*) FROM breakdown_item WHERE breakdown_id = ?", (cb.breakdownID,)) == 1


def test_invalid_quantities(ctx):
    c = GenerateCostBreakdownController()
    cust = account_id("customer")
    for q in ({}, {"FLOOR": 0}, {"FLOOR": -3}, {"FLOOR": None}, {"NOPE": 5}):
        assert c.generateBreakdown(cust, q, "Condo", "") is None
        assert c.errorMsg == "Please enter a positive quantity for at least one item"
    assert count("SELECT COUNT(*) FROM cost_breakdown") == 0


def test_property_type_and_style_must_be_valid(ctx):
    c = GenerateCostBreakdownController()
    assert c.generateBreakdown(account_id("customer"), {"FLOOR": 5}, "", "") is None
    assert c.generateBreakdown(account_id("customer"), {"FLOOR": 5}, "Condo", "Martian") is None
    assert c.errorMsg == "Please select a property type and a style."


def test_new_rule_changes_prices(ctx):
    c = GenerateCostBreakdownController()
    before = c.generateBreakdown(account_id("customer"), {"FLOOR": 10}, "Condo", "").items[0].lineTotal
    set_rule(condo=2.0)
    after = c.generateBreakdown(account_id("customer"), {"FLOOR": 10}, "Condo", "").items[0].lineTotal
    assert (before, after) == (450.0, 900.0)


# ---- Page ----
def test_only_customers(client):
    login(client, "smanager")
    assert client.get("/customer/cost-breakdown/").status_code == 403


def test_form_and_generate(client):
    login(client, "customer")
    assert "Vinyl flooring" in client.get("/customer/cost-breakdown/").get_data(as_text=True)
    html = client.post("/customer/cost-breakdown/", data={"property_type": "HDB 4-Room", "style": "",
                                                          "qty:PAINT": "50", "qty:FLOOR": ""}).get_data(as_text=True)
    assert "Your Cost Breakdown" in html and "436.00" in html          # 400 + 36 GST


def test_page_error_keeps_values(client):
    login(client, "customer")
    html = client.post("/customer/cost-breakdown/", data={"property_type": "Condo", "qty:PAINT": "abc"}).get_data(as_text=True)
    assert "Please enter a positive quantity for at least one item" in html
