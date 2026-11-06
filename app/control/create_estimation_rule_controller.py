"""<<control>> CreateEstimationRuleController - User Story #47 Create Cost Estimation Rules."""
from app.entity.estimation_rule import EstimationRule
from app.entity.unit_rate import UnitRate
from app.entity.category import Category
from app.constants import PROPERTY_TYPES, MIN_FACTOR, MAX_FACTOR


class CreateEstimationRuleController:
    def __init__(self):
        self.errorMsgs = []

    def getActiveRule(self):
        """S1 - the current rule with its rates and multipliers."""
        return EstimationRule.findActive()

    def getStyles(self):
        """Styles the Sales Manager can set a multiplier for (the active categories)."""
        return [c.categoryName for c in Category.getActiveCategories()]

    def createEstimationRule(self, rule):
        """Main flow steps 7-9. `rule` holds the name, the entered rates (UnitRate with
        only itemCode + rate) and the two factor maps. Returns True if saved and activated."""
        if not self._validateRule(rule):
            return False
        # S3 - create the unit rates: copy each item's name and unit from the current rate
        rule.unitRates = [UnitRate(r.itemCode, base.itemName, base.unit, r.rate)
                          for r, base in ((r, UnitRate.findByCode(r.itemCode)) for r in rule.unitRates)]
        return rule.saveRule()                       # S4 - save and activate

    # ---- Sub-flow S2: Validate Rates and Multipliers ----
    def _validateRule(self, rule):
        errors = []
        if not (rule.ruleName or "").strip():
            errors.append("Please enter a rule name.")
        current = {r.itemCode for r in UnitRate.getActiveRates()}
        entered = {r.itemCode: r.rate for r in rule.unitRates}
        if set(entered) != current:
            errors.append("Please enter a rate for every renovation item.")
        for code, rate in entered.items():
            if rate is None or rate <= 0:
                errors.append(f"The rate for {code} must be a positive number.")
        if set(rule.propertyFactors) != set(PROPERTY_TYPES):
            errors.append("Please enter a multiplier for every property type.")
        unknown = set(rule.styleFactors) - set(self.getStyles())
        if unknown:
            errors.append("Unknown style: " + ", ".join(sorted(unknown)))
        for key, f in list(rule.propertyFactors.items()) + list(rule.styleFactors.items()):
            if f is None or not (MIN_FACTOR <= f <= MAX_FACTOR):
                errors.append(f"The multiplier for {key} must be between {MIN_FACTOR} and {MAX_FACTOR}.")
        self.errorMsgs = errors
        return not errors
