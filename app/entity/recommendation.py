"""<<entity>> Recommendation - an IDP shown on a customer's front page (#11)."""
from app.db import get_db
from app.constants import IDP_ACTIVE
from app.entity.base import now_str


class Recommendation:
    def __init__(self, recommendationID, customerID, idpID, addedDate):
        self.recommendationID = recommendationID
        self.customerID = customerID
        self.idpID = idpID
        self.addedDate = addedDate

    @staticmethod
    def refreshRecommendations(idpID, customerIDs):
        """The IDP is now recommended to exactly these customers."""
        db = get_db()
        db.execute("DELETE FROM recommendation WHERE idp_id = ?", (idpID,))
        stamp = now_str()
        db.executemany("INSERT INTO recommendation (customer_id, idp_id, added_date) VALUES (?, ?, ?)",
                       [(cid, idpID, stamp) for cid in customerIDs])
        db.commit()
        return True

    @staticmethod
    def getForCustomer(customerID, limit=9):
        """Home page: active IDPs recommended by #11 or in the customer's preferred
        categories (so new customers see projects straight after choosing categories)."""
        from app.entity.idp import IDP
        rows = get_db().execute(
            IDP._SELECT + "WHERE i.status = ? AND (i.idp_id IN (SELECT idp_id FROM recommendation WHERE customer_id = ?) "
            "OR i.idp_id IN (SELECT ic.idp_id FROM idp_category ic JOIN customer_preference cp "
            "ON cp.category_id = ic.category_id WHERE cp.customer_id = ?)) "
            "ORDER BY i.created_date DESC, i.idp_id DESC LIMIT ?",
            (IDP_ACTIVE, customerID, customerID, limit)).fetchall()
        return [IDP._fromRow(r) for r in rows]
