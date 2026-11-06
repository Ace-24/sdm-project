"""<<entity>> EstimationRule - one version of the pricing rules (#47, used by #29)."""
from app.db import get_db
from app.entity.base import now_str
from app.entity.unit_rate import UnitRate
from app.constants import FACTOR_PROPERTY, FACTOR_STYLE


class EstimationRule:
    def __init__(self, ruleID, ruleName, createdBy, createdDate=None, isActive=False,
                 unitRates=None, propertyFactors=None, styleFactors=None):
        self.ruleID = ruleID
        self.ruleName = ruleName
        self.createdBy = createdBy
        self.createdDate = createdDate
        self.isActive = isActive
        self.unitRates = unitRates or []               # List<UnitRate>
        self.propertyFactors = propertyFactors or {}   # Map<String, double>
        self.styleFactors = styleFactors or {}         # Map<String, double>

    @staticmethod
    def _load(row):
        if row is None:
            return None
        rule = EstimationRule(row["rule_id"], row["rule_name"], row["created_by"], row["created_date"],
                              bool(row["is_active"]))
        rule.unitRates = UnitRate.findByRule(rule.ruleID)
        for f in get_db().execute("SELECT * FROM rule_factor WHERE rule_id = ? ORDER BY factor_key",
                                  (rule.ruleID,)).fetchall():
            target = rule.propertyFactors if f["factor_type"] == FACTOR_PROPERTY else rule.styleFactors
            target[f["factor_key"]] = f["factor"]
        return rule

    @staticmethod
    def findActive():
        """The rule currently in use (S1, and #29)."""
        row = get_db().execute("SELECT * FROM estimation_rule WHERE is_active = 1").fetchone()
        return EstimationRule._load(row)

    @staticmethod
    def findById(ruleID):
        row = get_db().execute("SELECT * FROM estimation_rule WHERE rule_id = ?", (ruleID,)).fetchone()
        return EstimationRule._load(row)

    def getPropertyFactor(self, propertyType):
        return self.propertyFactors.get(propertyType, 1.0)

    def getStyleFactor(self, style):
        return self.styleFactors.get(style, 1.0)

    def saveRule(self):
        """S3 + S4 - save the rule with its unit rates and factors as the active rule,
        and deactivate the previous one (all in one transaction)."""
        db = get_db()
        try:
            self._deactivateCurrent(db)
            self.createdDate = now_str()
            cur = db.execute("INSERT INTO estimation_rule (rule_name, created_by, created_date, is_active) "
                             "VALUES (?, ?, ?, 1)", (self.ruleName, self.createdBy, self.createdDate))
            self.ruleID = cur.lastrowid
            self.isActive = True
            for r in self.unitRates:
                r.ruleID = self.ruleID
                db.execute("INSERT INTO unit_rate (rule_id, item_code, item_name, unit, rate) VALUES (?, ?, ?, ?, ?)",
                           (self.ruleID, r.itemCode, r.itemName, r.unit, r.rate))
            for ftype, factors in ((FACTOR_PROPERTY, self.propertyFactors), (FACTOR_STYLE, self.styleFactors)):
                for key, value in factors.items():
                    db.execute("INSERT INTO rule_factor VALUES (?, ?, ?, ?)", (self.ruleID, ftype, key, value))
            db.commit()
            return True
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def _deactivateCurrent(db):
        db.execute("UPDATE estimation_rule SET is_active = 0 WHERE is_active = 1")
