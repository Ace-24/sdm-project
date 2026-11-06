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
        """Main flow 1-2: show the current active rule."""
        return self.showCurrentRule(self.controller.getActiveRule())

    def showCurrentRule(self, rule, entered=None, errors=None):
        styles = self.controller.getStyles()
        return render_template("estimation_rule.html", rule=rule, property_types=PROPERTY_TYPES,
                               styles=styles, entered=entered, errors=errors or [])

    def clickSave(self, form):
        """Main flow 6: build the new rule from the form and ask the controller to save it."""
        rule = EstimationRule(None, form.get("rule_name", "").strip(), g.user.accountID)
        rule.unitRates = [UnitRate(k[5:], None, None, _num(v)) for k, v in form.items() if k.startswith("rate:")]
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
