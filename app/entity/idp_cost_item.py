"""<<entity>> IDPCostItem - one line of a project's cost breakdown, entered by the designer.
Customers see it on the project page, adjusted for the property type they pick."""
from app.db import get_db

UNITS = ["sqm", "m", "unit", "lot"]


class IDPCostItem:
    def __init__(self, itemID, idpID, itemName, unit, quantity, unitRate):
        self.itemID = itemID
        self.idpID = idpID
        self.itemName = itemName
        self.unit = unit
        self.quantity = quantity
        self.unitRate = unitRate

    def calculateLineTotal(self, factor=1.0):
        """quantity x unit rate x property multiplier."""
        return round(self.quantity * self.unitRate * factor, 2)

    @staticmethod
    def findByIDP(idpID):
        rows = get_db().execute("SELECT * FROM idp_cost_item WHERE idp_id = ? ORDER BY item_id", (idpID,)).fetchall()
        return [IDPCostItem(r["item_id"], r["idp_id"], r["item_name"], r["unit"], r["quantity"], r["unit_rate"])
                for r in rows]

    @staticmethod
    def replaceItems(idpID, items):
        """Save the designer's breakdown (replaces the old lines). Does not commit."""
        db = get_db()
        db.execute("DELETE FROM idp_cost_item WHERE idp_id = ?", (idpID,))
        db.executemany("INSERT INTO idp_cost_item (idp_id, item_name, unit, quantity, unit_rate) VALUES (?, ?, ?, ?, ?)",
                       [(idpID, i.itemName, i.unit, i.quantity, i.unitRate) for i in items])

    @staticmethod
    def subtotal(items, factor=1.0):
        return round(sum(i.calculateLineTotal(factor) for i in items), 2)
