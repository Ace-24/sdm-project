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
    rule.unitRates = [UnitRate(code, name, unit, rate) for code, name, unit, _ in RENOVATION_ITEMS]
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


def test_existing_items_keep_their_code(ctx):
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
    assert "The rate for Vinyl flooring must be a positive number." in c.errorMsgs


# ---- Editable renovation item list ----
def test_item_name_and_unit_can_be_edited(ctx):
    rule = make_rule()
    rule.unitRates[0].itemName, rule.unitRates[0].unit = "  Laminate   flooring ", "unit"
    assert CreateEstimationRuleController().createEstimationRule(rule) is True
    r = UnitRate.findByCode("FLOOR")
    assert (r.itemName, r.unit) == ("Laminate flooring", "unit")              # spaces tidied, code kept


def test_items_can_be_removed(ctx):
    rule = make_rule()
    rule.unitRates = [r for r in rule.unitRates if r.itemCode != "GRILLE"]
    assert CreateEstimationRuleController().createEstimationRule(rule) is True
    codes = [r.itemCode for r in UnitRate.getActiveRates()]
    assert len(codes) == 11 and "GRILLE" not in codes


def test_new_item_gets_a_generated_code(ctx):
    rule = make_rule()
    rule.unitRates += [UnitRate("", "Skylight window", "sqm", 150), UnitRate("", "Skylight blinds", "unit", 80)]
    assert CreateEstimationRuleController().createEstimationRule(rule) is True
    added = {r.itemName: r.itemCode for r in UnitRate.getActiveRates()[-2:]}
    assert added == {"Skylight window": "SKYLIG", "Skylight blinds": "SKYLIG2"}


def test_new_item_does_not_reuse_an_old_code(ctx):
    rule = make_rule()                                   # removing FLOOR then adding a new 'Floor' item
    rule.unitRates = [r for r in rule.unitRates if r.itemCode != "FLOOR"] + [UnitRate("", "Floor", "sqm", 40)]
    assert CreateEstimationRuleController().createEstimationRule(rule) is True
    assert UnitRate.getActiveRates()[-1].itemCode == "FLOOR2"


def test_unknown_code_is_treated_as_new_item(ctx):
    rule = make_rule()
    rule.unitRates.append(UnitRate("HACKED", "Curtains", "lot", 900))
    assert CreateEstimationRuleController().createEstimationRule(rule) is True
    assert UnitRate.getActiveRates()[-1].itemCode == "CURTAI"


def test_rule_needs_at_least_one_item(ctx):
    rule = make_rule()
    rule.unitRates = []
    c = CreateEstimationRuleController()
    assert c.createEstimationRule(rule) is False
    assert "The rule needs at least one renovation item." in c.errorMsgs


def test_item_name_rules(ctx):
    rule = make_rule()
    rule.unitRates[0].itemName = ""
    rule.unitRates[1].itemName = "x" * 41
    rule.unitRates[2].itemName = "kitchen CABINETS"                     # same as item 4, any case
    c = CreateEstimationRuleController()
    assert c.createEstimationRule(rule) is False
    assert "Item 1: please enter an item name." in c.errorMsgs
    assert "Item 2: the name must be 40 characters or fewer." in c.errorMsgs
    assert "'Kitchen cabinets' is listed more than once." in c.errorMsgs


def test_unit_must_be_from_list(ctx):
    rule = make_rule()
    rule.unitRates[0].unit = "bucket"
    c = CreateEstimationRuleController()
    assert c.createEstimationRule(rule) is False
    assert "Vinyl flooring: please choose a unit (sqm, m, unit, lot)." in c.errorMsgs


def test_cost_breakdown_and_designer_use_new_list(client, app):
    with app.app_context():
        rule = make_rule()
        rule.unitRates.append(UnitRate("", "Skylight window", "sqm", 150))
        assert CreateEstimationRuleController().createEstimationRule(rule)
    login(client, "customer")
    assert "Skylight window" in client.get("/customer/cost-breakdown/").get_data(as_text=True)
    client.get("/logout")
    login(client, "designer")
    assert "Skylight window" in client.get("/designer/portfolio/new").get_data(as_text=True)


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


def _form(items=None, **over):
    """Build the posted form. items: [(code, name, unit, rate)] - defaults to the starter list at 60."""
    items = items if items is not None else [(c, n, u, "60") for c, n, u, _ in RENOVATION_ITEMS]
    data = {"rule_name": "Web rule", "item_code": [i[0] for i in items], "item_name": [i[1] for i in items],
            "item_unit": [i[2] for i in items], "item_rate": [i[3] for i in items]}
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
    items = [(c, n, u, "-1" if c == "PAINT" else "60") for c, n, u, _ in RENOVATION_ITEMS]
    html = client.post("/sales/estimation-rules/", data=_form(items, **{"prop:Condo": "5"})).get_data(as_text=True)
    assert "The rate for Wall painting must be a positive number." in html
    assert "The multiplier for Condo must be between 0.5 and 3.0." in html
    assert 'value="Web rule"' in html


def test_page_has_add_and_remove_controls(client):
    login(client, "smanager")
    html = client.get("/sales/estimation-rules/").get_data(as_text=True)
    assert "+ Add item" in html and "remove-item" in html and 'name="item_name"' in html


def test_page_add_edit_remove_items(client, app):
    login(client, "smanager")
    items = [(c, n, u, "60") for c, n, u, _ in RENOVATION_ITEMS if c != "GRILLE"]
    items[0] = ("FLOOR", "SPC flooring", "sqm", "55")
    items += [("", "Skylight window", "sqm", "150"), ("", "", "sqm", "")]          # last row left empty: ignored
    html = client.post("/sales/estimation-rules/", data=_form(items)).get_data(as_text=True)
    assert "Estimation rule saved and activated" in html
    with app.app_context():
        rates = {r.itemCode: (r.itemName, r.rate) for r in UnitRate.getActiveRates()}
        assert rates["FLOOR"] == ("SPC flooring", 55) and rates["SKYLIG"] == ("Skylight window", 150)
        assert "GRILLE" not in rates and len(rates) == 12


def test_page_errors_keep_added_rows(client):
    login(client, "smanager")
    items = [(c, n, u, "60") for c, n, u, _ in RENOVATION_ITEMS] + [("", "Skylight window", "sqm", "0")]
    html = client.post("/sales/estimation-rules/", data=_form(items)).get_data(as_text=True)
    assert "The rate for Skylight window must be a positive number." in html
    assert 'value="Skylight window"' in html
