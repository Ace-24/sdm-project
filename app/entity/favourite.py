"""<<entity>> Favourite - an IDP saved by a customer (#27, #40, #50)."""
from app.db import get_db


class Favourite:
    def __init__(self, favouriteID, customerID, idpID, savedDate, idp=None):
        self.favouriteID = favouriteID
        self.customerID = customerID
        self.idpID = idpID
        self.savedDate = savedDate
        self.idp = idp          # the IDP this favourite refers to

    @staticmethod
    def findByCustomer(customerID):
        """The customer's favourites list with each IDP's details, newest first."""
        from app.entity.idp import IDP
        rows = get_db().execute(
            "SELECT f.favourite_id, f.customer_id, f.idp_id AS fav_idp, f.saved_date, sub.* FROM favourite f "
            "JOIN (" + IDP._SELECT + ") sub ON sub.idp_id = f.idp_id "
            "WHERE f.customer_id = ? ORDER BY f.saved_date DESC", (customerID,)).fetchall()
        return [Favourite(r["favourite_id"], r["customer_id"], r["fav_idp"], r["saved_date"], IDP._fromRow(r))
                for r in rows]

    @staticmethod
    def getSelectedIDPs(customerID, idpIDs):
        """The selected IDPs, only if they are in this customer's favourites."""
        wanted = set(idpIDs)
        return [f.idp for f in Favourite.findByCustomer(customerID) if f.idpID in wanted]

    @staticmethod
    def isFavourite(customerID, idpID):
        return get_db().execute("SELECT 1 FROM favourite WHERE customer_id = ? AND idp_id = ?",
                                (customerID, idpID)).fetchone() is not None

    @staticmethod
    def addFavourite(customerID, idpID):
        """Save an IDP to the favourites (shortlist). Saving twice has no effect."""
        from app.entity.base import now_str
        db = get_db()
        db.execute("INSERT OR IGNORE INTO favourite (customer_id, idp_id, saved_date) VALUES (?, ?, ?)",
                   (customerID, idpID, now_str()))
        db.commit()
        return True

    @staticmethod
    def removeFavourite(customerID, idpID):
        db = get_db()
        db.execute("DELETE FROM favourite WHERE customer_id = ? AND idp_id = ?", (customerID, idpID))
        db.commit()
        return True
