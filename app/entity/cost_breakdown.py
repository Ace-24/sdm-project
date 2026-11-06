"""<<entity>> CostBreakdown and BreakdownItem - a customer's itemised estimate (#29, #50)."""
from app.db import get_db
from app.entity.base import now_str
from app.constants import GST_RATE


class BreakdownItem:
    def __init__(self, itemCode, itemName, unit, quantity, unitRate, factor=1.0):
        self.itemCode = itemCode
        self.itemName = itemName
        self.unit = unit
        self.quantity = quantity
        self.unitRate = unitRate
        self.factor = factor           # property type x style multiplier from #47
        self.lineTotal = self.calculateLineTotal()

    def calculateLineTotal(self):
        """S3 - quantity x unit rate x multiplier."""
        return round(self.quantity * self.unitRate * self.factor, 2)


class CostBreakdown:
    GST_RATE = GST_RATE

    def __init__(self, breakdownID, customerID, ruleID, propertyType, style,
                 items=None, subtotal=0.0, gst=0.0, total=0.0, createdDate=None):
        self.breakdownID = breakdownID
        self.customerID = customerID
        self.ruleID = ruleID
        self.propertyType = propertyType
        self.style = style
        self.items = items or []
        self.subtotal = subtotal
        self.gst = gst
        self.total = total
        self.createdDate = createdDate

    def addItems(self, quantities, unitRates, factor):
        """Create one BreakdownItem per item with a quantity. unitRates maps code -> UnitRate."""
        for code, qty in quantities.items():
            r = unitRates[code]
            self.items.append(BreakdownItem(code, r.itemName, r.unit, qty, r.rate, factor))

    def calculateSubtotal(self):
        self.subtotal = round(sum(i.lineTotal for i in self.items), 2)
        return self.subtotal

    def calculateGst(self):
        self.gst = round(self.subtotal * self.GST_RATE, 2)
        return self.gst

    def calculateTotal(self):
        """S4 - subtotal, 9% GST and total."""
        self.calculateSubtotal()
        self.calculateGst()
        self.total = round(self.subtotal + self.gst, 2)
        return self.total

    def saveBreakdown(self):
        """Main flow step 8 - saved with the customer, rule and date (used by #50)."""
        db = get_db()
        self.createdDate = now_str()
        cur = db.execute("INSERT INTO cost_breakdown (customer_id, rule_id, property_type, style, subtotal, gst, "
                         "total, created_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                         (self.customerID, self.ruleID, self.propertyType, self.style, self.subtotal, self.gst,
                          self.total, self.createdDate))
        self.breakdownID = cur.lastrowid
        db.executemany("INSERT INTO breakdown_item (breakdown_id, item_code, item_name, unit, quantity, unit_rate, "
                       "line_total) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       [(self.breakdownID, i.itemCode, i.itemName, i.unit, i.quantity, i.unitRate, i.lineTotal)
                        for i in self.items])
        db.commit()
        return True
