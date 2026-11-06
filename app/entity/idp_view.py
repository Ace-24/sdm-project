"""<<entity>> IDPView - one view of an IDP's page (#40, #50, designer interest counts)."""
from app.db import get_db
from app.entity.base import now_str


class IDPView:
    def __init__(self, viewID, idpID, customerID, viewedDate):
        self.viewID = viewID
        self.idpID = idpID
        self.customerID = customerID
        self.viewedDate = viewedDate

    @staticmethod
    def recordView(idpID, customerID=None):
        """customerID is None for visitors who are not logged in."""
        db = get_db()
        db.execute("INSERT INTO idp_view (idp_id, customer_id, viewed_date) VALUES (?, ?, ?)",
                   (idpID, customerID, now_str()))
        db.commit()
