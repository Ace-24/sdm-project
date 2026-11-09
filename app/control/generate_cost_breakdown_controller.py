"""<<control>> GenerateCostBreakdownController - User Story #29 Generate Cost Breakdown.
Uses the active estimation rule from #47 (unit rates + property/style multipliers)."""
from app.entity.unit_rate import UnitRate
from app.entity.estimation_rule import EstimationRule
from app.entity.cost_breakdown import CostBreakdown
from app.constants import PROPERTY_TYPES


class GenerateCostBreakdownController:
    def __init__(self):
        self.errorMsg = None

    def getRenovationItems(self):
        """Items of the active rule with their unit and unit rate."""
        return UnitRate.getActiveRates()

    def getStyles(self):
        rule = EstimationRule.findActive()
        return sorted(rule.styleFactors) if rule else []

    def generateBreakdown(self, customerID, quantities, propertyType, style):
        """quantities maps item code -> number (blank items left out).
        Returns the saved CostBreakdown, or None (with errorMsg)."""
        rule = EstimationRule.findActive()
        if rule is None:
            self.errorMsg = "Cost estimation is not available yet. Please try again later."
            return None
        if not self._validateQuantities(quantities, rule):
            return None
        if propertyType not in PROPERTY_TYPES or (style and style not in rule.styleFactors):
            self.errorMsg = "Please select a property type and a style."
            return None
        factor = rule.getPropertyFactor(propertyType) * (rule.getStyleFactor(style) if style else 1.0)
        cb = CostBreakdown(None, customerID, rule.ruleID, propertyType, style or "Standard")
        cb.addItems(quantities, {r.itemCode: r for r in rule.unitRates}, factor)
        cb.calculateTotal()
        cb.saveBreakdown()
        cb.factor = factor
        return cb

    def _validateQuantities(self, quantities, rule):
        self.errorMsg = None
        codes = {r.itemCode for r in rule.unitRates}
        if not quantities or any(code not in codes for code in quantities) \
                or any(q is None or q <= 0 for q in quantities.values()):
            self.errorMsg = "Please enter a positive quantity for at least one item"
            return False
        return True
