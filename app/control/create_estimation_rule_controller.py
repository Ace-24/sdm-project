"""<<control>> CreateEstimationRuleController - User Story #47 Create Cost Estimation Rules."""
from app.entity.estimation_rule import EstimationRule
from app.entity.unit_rate import UnitRate
from app.entity.category import Category
from app.entity.idp_cost_item import UNITS
from app.constants import PROPERTY_TYPES, MIN_FACTOR, MAX_FACTOR

MAX_ITEM_NAME = 40


class CreateEstimationRuleController:
    def __init__(self):
        self.errorMsgs = []

    def getActiveRule(self):
        """S1 - the current rule with its rates and multipliers."""
        return EstimationRule.findActive()

    def getStyles(self):
        """Styles the Sales Manager can set a multiplier for (the active categories)."""
        return [c.categoryName for c in Category.getActiveCategories()]

    def getUnits(self):
        return UNITS

    def createEstimationRule(self, rule):
        """Main flow steps 7-9. `rule` holds the name, the edited renovation item list (UnitRate:
        itemCode is blank for a new item) and the two factor maps. Returns True if saved and activated."""
        for r in rule.unitRates:                     # tidy the typed text before checking it
            r.itemName = " ".join((r.itemName or "").split())
            r.itemCode = (r.itemCode or "").strip().upper()
        if not self._validateRule(rule):
            return False
        self._assignItemCodes(rule.unitRates)        # S3 - keep codes of existing items, new code for new items
        return rule.saveRule()                       # S4 - save and activate

    # ---- Sub-flow S2: Validate Items, Rates and Multipliers ----
    def _validateRule(self, rule):
        errors = []
        if not (rule.ruleName or "").strip():
            errors.append("Please enter a rule name.")
        if not rule.unitRates:
            errors.append("The rule needs at least one renovation item.")
        seen = set()
        for n, r in enumerate(rule.unitRates, start=1):
            label = r.itemName or f"Item {n}"
            if not r.itemName:
                errors.append(f"Item {n}: please enter an item name.")
            elif len(r.itemName) > MAX_ITEM_NAME:
                errors.append(f"Item {n}: the name must be {MAX_ITEM_NAME} characters or fewer.")
            elif r.itemName.lower() in seen:
                errors.append(f"'{r.itemName}' is listed more than once.")
            seen.add((r.itemName or "").lower())
            if r.unit not in UNITS:
                errors.append(f"{label}: please choose a unit ({', '.join(UNITS)}).")
            if r.rate is None or r.rate <= 0:
                errors.append(f"The rate for {label} must be a positive number.")
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

    @staticmethod
    def _assignItemCodes(unitRates):
        """An item that was in the active rule keeps its code. A new item gets a code made from its
        name (e.g. 'Feature wall' -> FEATUR) that no rule has used before, so old breakdowns stay clear."""
        current = {r.itemCode for r in UnitRate.getActiveRates()}
        used = UnitRate.getAllCodes()
        kept = set()
        for r in unitRates:
            if r.itemCode in current and r.itemCode not in kept:
                kept.add(r.itemCode)
                continue
            base = "".join(ch for ch in r.itemName.upper() if ch.isalnum())[:6] or "ITEM"
            code, n = base, 2
            while code in used or code in kept:
                code, n = f"{base}{n}", n + 1
            r.itemCode = code
            kept.add(code)
