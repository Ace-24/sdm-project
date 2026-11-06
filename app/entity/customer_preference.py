"""<<entity>> CustomerPreference - categories a customer is interested in (#11)."""
from app.db import get_db
from app.constants import ACCOUNT_ACTIVE


class CustomerPreference:
    def __init__(self, customerID, categoryID, selectedDate):
        self.customerID = customerID
        self.categoryID = categoryID
        self.selectedDate = selectedDate

    @staticmethod
    def findCustomersByCategories(categoryIDs):
        """Active customers who picked at least one of the categories."""
        if not categoryIDs:
            return []
        marks = ",".join("?" * len(categoryIDs))
        rows = get_db().execute(
            f"SELECT DISTINCT cp.customer_id FROM customer_preference cp "
            f"JOIN user_account a ON a.account_id = cp.customer_id "
            f"WHERE cp.category_id IN ({marks}) AND a.status = ? ORDER BY cp.customer_id",
            list(categoryIDs) + [ACCOUNT_ACTIVE]).fetchall()
        return [r[0] for r in rows]

    @staticmethod
    def getCategoryIDs(customerID):
        rows = get_db().execute("SELECT category_id FROM customer_preference WHERE customer_id = ? "
                                "ORDER BY category_id", (customerID,)).fetchall()
        return [r[0] for r in rows]

    @staticmethod
    def savePreferences(customerID, categoryIDs):
        """Replace the customer's preferred categories."""
        from app.entity.base import now_str
        db = get_db()
        db.execute("DELETE FROM customer_preference WHERE customer_id = ?", (customerID,))
        stamp = now_str()
        db.executemany("INSERT INTO customer_preference (customer_id, category_id, selected_date) VALUES (?, ?, ?)",
                       [(customerID, cid, stamp) for cid in categoryIDs])
        db.commit()
        return True
