"""<<entity>> UnitRate - the price of one renovation item under a rule (#47, #29)."""
from app.db import get_db


class UnitRate:
    def __init__(self, itemCode, itemName, unit, rate, ruleID=None):
        self.itemCode = itemCode
        self.itemName = itemName
        self.unit = unit
        self.rate = rate
        self.ruleID = ruleID

    @staticmethod
    def _fromRow(row):
        return UnitRate(row["item_code"], row["item_name"], row["unit"], row["rate"], row["rule_id"])

    @staticmethod
    def findByCode(itemCode):
        """The item's unit rate under the active rule (or None)."""
        row = get_db().execute(
            "SELECT u.* FROM unit_rate u JOIN estimation_rule r ON r.rule_id = u.rule_id "
            "WHERE r.is_active = 1 AND u.item_code = ?", (itemCode,)).fetchone()
        return UnitRate._fromRow(row) if row else None

    @staticmethod
    def getActiveRates():
        """All unit rates of the active rule (#29 item list)."""
        rows = get_db().execute(
            "SELECT u.* FROM unit_rate u JOIN estimation_rule r ON r.rule_id = u.rule_id "
            "WHERE r.is_active = 1 ORDER BY u.unit_rate_id").fetchall()
        return [UnitRate._fromRow(r) for r in rows]

    @staticmethod
    def findByRule(ruleID):
        rows = get_db().execute("SELECT * FROM unit_rate WHERE rule_id = ? ORDER BY unit_rate_id",
                                (ruleID,)).fetchall()
        return [UnitRate._fromRow(r) for r in rows]

    @staticmethod
    def getAllCodes():
        """Every item code used by any rule (new items must not reuse one)."""
        return {r[0] for r in get_db().execute("SELECT DISTINCT item_code FROM unit_rate").fetchall()}
