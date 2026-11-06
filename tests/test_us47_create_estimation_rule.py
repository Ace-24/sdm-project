"""Unit tests for User Story #47 Create Cost Estimation Rules."""
import pytest
from app.control.create_estimation_rule_controller import CreateEstimationRuleController
from app.entity.estimation_rule import EstimationRule
from app.entity.unit_rate import UnitRate
from app.constants import PROPERTY_TYPES, RENOVATION_ITEMS
from tests.conftest import login
from tests.helpers import account_id, add_category, count


def make_rule(name="2027 Q1 rates", rate=50.0, prop=1.1, styles=None):
    rule = EstimationRule(None, name, account_id("smanager"))
    rule.unitRates = [UnitRate(code, None, None, rate) for code, *_ in RENOVATION_ITEMS]
    rule.propertyFactors = {p: prop for p in PROPERTY_TYPES}
    rule.styleFactors = styles or {}
    return rule


# ---- Controller ----
def test_active_rule_has_all_items_and_property_factors(ctx):
    rule = CreateEstimationRuleController().getActiveRule()
    assert rule.ruleName == "Starter rates" and rule.isActive
    assert len(rule.unitRates) == 12
    assert set(rule.propertyFactors) == set(PROPERTY_TYPES)


def test_valid_rule_is_saved_and_activated(ctx):
    add_category("Japandi")
    old = EstimationRule.findActive()
    c = CreateEstimationRuleController()
    assert c.createEstimationRule(make_rule(styles={"Japandi": 1.3})) is True
    new = EstimationRule.findActive()
    assert new.ruleName == "2027 Q1 rates" and new.ruleID != old.ruleID
    assert new.getStyleFactor("Japandi") == 1.3
    assert new.getPropertyFactor("Condo") == 1.1
    assert EstimationRule.findById(old.ruleID).isActive is False          # old rule deactivated
    assert count("SELECT COUNT(*) FROM estimation_rule WHERE is_active = 1") == 1


def test_unit_rates_copy_name_and_unit(ctx):
    CreateEstimationRuleController().createEstimationRule(make_rule(rate=99))
    r = UnitRate.findByCode("KCAB")
    assert (r.itemName, r.unit, r.rate) == ("Kitchen cabinets", "m", 99)


def test_old_rule_keeps_its_rates(ctx):
    old = EstimationRule.findActive()
    CreateEstimationRuleController().createEstimationRule(make_rule(rate=99))
    assert [r.rate for r in EstimationRule.findById(old.ruleID).unitRates][:2] == [45, 85]


def test_missing_name_is_rejected(ctx):
    c = CreateEstimationRuleController()
    assert c.createEstimationRule(make_rule(name="  ")) is False
    assert "Please enter a rule name." in c.errorMsgs
    assert EstimationRule.findActive().ruleName == "Starter rates"


@pytest.mark.parametrize("rate", [0, -5, None])
def test_rates_must_be_positive(ctx, rate):
    rule = make_rule()
    rule.unitRates[0].rate = rate
    c = CreateEstimationRuleController()
    assert c.createEstimationRule(rule) is False
    assert "The rate for FLOOR must be a positive number." in c.errorMsgs


def test_every_item_needs_a_rate(ctx):
    rule = make_rule()
    rule.unitRates = rule.unitRates[1:]
    c = CreateEstimationRuleController()
    assert c.createEstimationRule(rule) is False
    assert "Please enter a rate for every renovation item." in c.errorMsgs


@pytest.mark.parametrize("factor", [0.4, 3.1, None])
def test_factors_must_be_between_0_5_and_3(ctx, factor):
    rule = make_rule()
    rule.propertyFactors["Condo"] = factor
    c = CreateEstimationRuleController()
    assert c.createEstimationRule(rule) is False
    assert "The multiplier for Condo must be between 0.5 and 3.0." in c.errorMsgs


def test_boundary_factors_are_allowed(ctx):
    add_category("Japandi")
    add_category("Minimalist")
    rule = make_rule(styles={"Japandi": 3.0, "Minimalist": 0.5})
    assert CreateEstimationRuleController().createEstimationRule(rule) is True


def test_unknown_style_is_rejected(ctx):
    c = CreateEstimationRuleController()
    assert c.createEstimationRule(make_rule(styles={"Martian": 1.2})) is False
    assert "Unknown style: Martian" in c.errorMsgs


# ---- Page ----
def test_only_sales_manager_can_open(client):
    login(client, "customer")
    assert client.get("/sales/estimation-rules/").status_code == 403


def test_form_shows_current_rule(client):
    login(client, "smanager")
    html = client.get("/sales/estimation-rules/").get_data(as_text=True)
    assert "Starter rates" in html and "Kitchen cabinets" in html and "HDB 4-Room" in html


def _form(**over):
    data = {"rule_name": "Web rule"}
    data.update({f"rate:{code}": "60" for code, *_ in RENOVATION_ITEMS})
    data.update({f"prop:{p}": "1.0" for p in PROPERTY_TYPES})
    data.update(over)
    return data


def test_save_from_page(client, app):
    login(client, "smanager")
    html = client.post("/sales/estimation-rules/", data=_form()).get_data(as_text=True)
    assert "Estimation rule saved and activated" in html
    with app.app_context():
        assert EstimationRule.findActive().ruleName == "Web rule"


def test_page_errors_keep_entered_values(client):
    login(client, "smanager")
    html = client.post("/sales/estimation-rules/", data=_form(**{"rate:PAINT": "-1", "prop:Condo": "5"})).get_data(as_text=True)
    assert "The rate for PAINT must be a positive number." in html
    assert "The multiplier for Condo must be between 0.5 and 3.0." in html
    assert 'value="Web rule"' in html
