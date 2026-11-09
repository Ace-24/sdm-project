"""<<entity>> IDPCategory - links an IDP to one or more categories (#11, #40)."""
from app.db import get_db
from app.entity.base import now_str


class IDPCategory:
    def __init__(self, idpID, categoryID, linkedDate):
        self.idpID = idpID
        self.categoryID = categoryID
        self.linkedDate = linkedDate

    @staticmethod
    def getCategoryIDs(idpID):
        rows = get_db().execute("SELECT category_id FROM idp_category WHERE idp_id = ? ORDER BY category_id",
                                (idpID,)).fetchall()
        return [r[0] for r in rows]

    @staticmethod
    def replaceLinks(idpID, categoryIDs):
        """Keep existing link dates, add new links, remove unticked ones."""
        db = get_db()
        current = set(IDPCategory.getCategoryIDs(idpID))
        wanted = set(categoryIDs)
        for cid in current - wanted:
            db.execute("DELETE FROM idp_category WHERE idp_id = ? AND category_id = ?", (idpID, cid))
        for cid in wanted - current:
            db.execute("INSERT INTO idp_category (idp_id, category_id, linked_date) VALUES (?, ?, ?)",
                       (idpID, cid, now_str()))
        db.commit()
        return True
