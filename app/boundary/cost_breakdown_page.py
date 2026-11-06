"""<<boundary>> GenerateCostBreakdownPg - User Story #29 Generate Cost Breakdown (Customer)."""
from flask import Blueprint, render_template, request, g
from app.boundary.auth import role_required
from app.constants import CUSTOMER, PROPERTY_TYPES
from app.control.generate_cost_breakdown_controller import GenerateCostBreakdownController

bp = Blueprint("cost_breakdown", __name__, url_prefix="/customer/cost-breakdown")


class GenerateCostBreakdownPg:
    def __init__(self):
        self.controller = GenerateCostBreakdownController()

    def displayCostBreakdownForm(self, form=None, error=None):
        """Main flow 1-2."""
        return self.showItemList(self.controller.getRenovationItems(), form or {}, error)

    def showItemList(self, items, form, error):
        return render_template("cost_breakdown.html", items=items, form=form, error=error,
                               property_types=PROPERTY_TYPES, styles=self.controller.getStyles())

    def clickGenerate(self, customerID, form):
        """Main flow 4. Blank quantity boxes are ignored; anything typed must be a positive number."""
        quantities = {}
        for key, value in form.items():
            if key.startswith("qty:") and value.strip() != "":
                try:
                    quantities[key[4:]] = float(value)
                except ValueError:
                    quantities[key[4:]] = None
        cb = self.controller.generateBreakdown(customerID, quantities, form.get("property_type", ""),
                                               form.get("style", ""))
        if cb is None:
            return self.displayErrorMsg(form, self.controller.errorMsg)
        return self.displayBreakdown(cb)

    def displayBreakdown(self, cb):
        return render_template("cost_breakdown_result.html", cb=cb)

    def displayErrorMsg(self, form, msg):
        return self.displayCostBreakdownForm(form, msg)


@bp.route("/", methods=["GET"])
@role_required(CUSTOMER)
def displayCostBreakdownForm():
    return GenerateCostBreakdownPg().displayCostBreakdownForm()


@bp.route("/", methods=["POST"])
@role_required(CUSTOMER)
def clickGenerate():
    return GenerateCostBreakdownPg().clickGenerate(g.user.accountID, request.form)
