"""<<boundary>> CreateEstimationRulePg - User Story #47 Create Cost Estimation Rules (Sales Manager)."""
from flask import Blueprint, render_template, request, g, url_for
from app.boundary.auth import role_required
from app.constants import SALES_MANAGER, PROPERTY_TYPES
from app.control.create_estimation_rule_controller import CreateEstimationRuleController
from app.entity.estimation_rule import EstimationRule
from app.entity.unit_rate import UnitRate

bp = Blueprint("estimation_rule", __name__, url_prefix="/sales/estimation-rules")


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class CreateEstimationRulePg:
    def __init__(self):
        self.controller = CreateEstimationRuleController()

    def displayEstimationRuleForm(self):
        return self.showCurrentRule(self.controller.getActiveRule())

    def showCurrentRule(self, rule, entered=None, errors=None):
        styles = self.controller.getStyles()
        current = {r.itemCode: r for r in rule.unitRates} if rule else {}
        if entered is not None:
            items = [{"code": c, "name": n, "unit": u, "rate": v, "current": current.get(c)}
                     for c, n, u, v in self._itemRows(entered)]
        else:
            items = [{"code": r.itemCode, "name": r.itemName, "unit": r.unit, "rate": r.rate, "current": r}
                     for r in (rule.unitRates if rule else [])]
        return render_template("estimation_rule.html", rule=rule, property_types=PROPERTY_TYPES,
                               styles=styles, items=items, units=self.controller.getUnits(),
                               entered=entered, errors=errors or [])

    @staticmethod
    def _itemRows(form):
        """The item table is sent as parallel lists: item_code, item_name, item_unit, item_rate."""
        cols = [form.getlist(k) for k in ("item_code", "item_name", "item_unit", "item_rate")]
        rows = list(zip(*[c + [""] * (max(map(len, cols)) - len(c)) for c in cols])) if any(cols) else []
        return [r for r in rows if r[1].strip() or r[3].strip()]       # skip new rows left empty (no name, no rate)

    def clickSave(self, form):
        """Build the new rule from the form and ask the controller to save it."""
        rule = EstimationRule(None, form.get("rule_name", "").strip(), g.user.accountID)
        rule.unitRates = [UnitRate(code, name, unit, _num(rate)) for code, name, unit, rate in self._itemRows(form)]
        rule.propertyFactors = {k[5:]: _num(v) for k, v in form.items() if k.startswith("prop:")}
        rule.styleFactors = {k[6:]: _num(v) for k, v in form.items() if k.startswith("style:") and v != ""}
        if self.controller.createEstimationRule(rule):
            return self.displaySuccessPg(rule)
        return self.displayErrorMsg(form, self.controller.errorMsgs)

    def displaySuccessPg(self, rule):
        return render_template("success.html", message="Estimation rule saved and activated",
                               detail=f"'{rule.ruleName}' is now used for all customer cost breakdowns.",
                               back_url=url_for("estimation_rule.displayEstimationRuleForm"),
                               back_label="Back to estimation rules")

    def displayErrorMsg(self, form, errors):
        return self.showCurrentRule(self.controller.getActiveRule(), entered=form, errors=errors)


@bp.route("/", methods=["GET"])
@role_required(SALES_MANAGER)
def displayEstimationRuleForm():
    return CreateEstimationRulePg().displayEstimationRuleForm()


@bp.route("/", methods=["POST"])
@role_required(SALES_MANAGER)
def clickSave():
    return CreateEstimationRulePg().clickSave(request.form)
