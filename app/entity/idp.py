"""<<entity>> IDP - an Interior Design Project in a designer's portfolio.

This single class combines the IDP attributes used in #13, #27, #38 and #40.
"""
from app.db import get_db
from app.constants import IDP_ACTIVE, IDP_ARCHIVED
from app.entity.base import now_str


class IDP:
    def __init__(self, idpID, designerID, title, description="", propertyType="", totalCost=0.0,
                 floorArea=0.0, completionDate=None, photoURLs=None, status=IDP_ACTIVE,
                 createdDate=None, updatedDate=None, archivedDate=None, designerName=None, style=None):
        self.idpID = idpID
        self.designerID = designerID
        self.title = title
        self.description = description
        self.propertyType = propertyType
        self.totalCost = totalCost
        self.floorArea = floorArea
        self.completionDate = completionDate
        self.photoURLs = photoURLs or []
        self.status = status
        self.createdDate = createdDate
        self.updatedDate = updatedDate
        self.archivedDate = archivedDate
        self.designerName = designerName   # joined for display
        self.style = style                 # category names joined for display

    @staticmethod
    def _fromRow(row):
        if row is None:
            return None
        keys = row.keys()
        photos = [p for p in (row["photo_urls"] or "").split(",") if p]
        return IDP(row["idp_id"], row["designer_id"], row["title"], row["description"], row["property_type"],
                   row["total_cost"], row["floor_area"], row["completion_date"], photos, row["status"],
                   row["created_date"], row["updated_date"], row["archived_date"],
                   row["designer_name"] if "designer_name" in keys else None,
                   row["style"] if "style" in keys else None)

    _SELECT = ("SELECT i.*, a.name AS designer_name, "
               "(SELECT GROUP_CONCAT(c.category_name, ', ') FROM idp_category ic "
               " JOIN category c ON c.category_id = ic.category_id WHERE ic.idp_id = i.idp_id) AS style "
               "FROM idp i JOIN user_account a ON a.account_id = i.designer_id ")

    @staticmethod
    def getIDPDetails(idpID):
        row = get_db().execute(IDP._SELECT + "WHERE i.idp_id = ?", (idpID,)).fetchone()
        return IDP._fromRow(row)

    def isComparable(self):
        """#27 S2 - still active and has a floor area."""
        return self.status == IDP_ACTIVE and bool(self.floorArea) and self.floorArea > 0

    def getCostPerSqm(self):
        """Used by #27. Returns 0 when the floor area is missing."""
        if not self.floorArea:
            return 0.0
        return round(self.totalCost / self.floorArea, 2)

    # ---------- #13 Manage Portfolio ----------
    @staticmethod
    def getIDPsByStatus(designerID, status):
        """A designer's IDPs with the given status (or list of statuses),
        newest completion date first."""
        statuses = [status] if isinstance(status, str) else list(status)
        marks = ",".join("?" * len(statuses))
        rows = get_db().execute(
            IDP._SELECT + f"WHERE i.designer_id = ? AND i.status IN ({marks}) "
            "ORDER BY i.completion_date DESC, i.idp_id DESC", [designerID] + statuses).fetchall()
        return [IDP._fromRow(r) for r in rows]

    def updateIDP(self, costItems=None):
        """Save edited details (main flow step 8). If costItems are given they replace the
        breakdown and the total cost becomes their subtotal."""
        from app.entity.idp_cost_item import IDPCostItem
        self.updatedDate = now_str()
        if costItems is not None:
            self.totalCost = IDPCostItem.subtotal(costItems)
        db = get_db()
        db.execute("UPDATE idp SET title = ?, description = ?, property_type = ?, total_cost = ?, floor_area = ?, "
                   "completion_date = ?, photo_urls = ?, updated_date = ? WHERE idp_id = ?",
                   (self.title, self.description, self.propertyType, self.totalCost, self.floorArea,
                    self.completionDate, ",".join(self.photoURLs), self.updatedDate, self.idpID))
        if costItems is not None:
            IDPCostItem.replaceItems(self.idpID, costItems)
        db.commit()
        return True

    def createIDP(self, costItems):
        """Add a new project listing with its cost breakdown (Add Project)."""
        from app.entity.idp_cost_item import IDPCostItem
        self.createdDate = self.updatedDate = now_str()
        self.totalCost = IDPCostItem.subtotal(costItems)
        db = get_db()
        cur = db.execute("INSERT INTO idp (designer_id, title, description, property_type, total_cost, floor_area, "
                         "completion_date, photo_urls, status, created_date, updated_date) "
                         "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                         (self.designerID, self.title, self.description, self.propertyType, self.totalCost,
                          self.floorArea, self.completionDate, ",".join(self.photoURLs), IDP_ACTIVE,
                          self.createdDate, self.updatedDate))
        self.idpID = cur.lastrowid
        IDPCostItem.replaceItems(self.idpID, costItems)
        db.commit()
        return self.idpID

    def getCostItems(self):
        from app.entity.idp_cost_item import IDPCostItem
        return IDPCostItem.findByIDP(self.idpID)

    @staticmethod
    def searchIDPs(keyword="", categoryID=None, limit=24, offset=0):
        """Browse / search active projects by keyword (title, description, designer, category)
        and optional category. Returns (IDPs, total matches)."""
        where = ["i.status = ?"]
        params = [IDP_ACTIVE]
        if keyword:
            like = f"%{keyword.strip()}%"
            where.append("(i.title LIKE ? OR i.description LIKE ? OR a.name LIKE ? OR EXISTS ("
                         "SELECT 1 FROM idp_category ic JOIN category c ON c.category_id = ic.category_id "
                         "WHERE ic.idp_id = i.idp_id AND c.category_name LIKE ?))")
            params += [like, like, like, like]
        if categoryID:
            where.append("EXISTS (SELECT 1 FROM idp_category ic WHERE ic.idp_id = i.idp_id AND ic.category_id = ?)")
            params.append(categoryID)
        cond = "WHERE " + " AND ".join(where) + " "
        db = get_db()
        total = db.execute("SELECT COUNT(*) FROM idp i JOIN user_account a ON a.account_id = i.designer_id " + cond,
                           params).fetchone()[0]
        rows = db.execute(IDP._SELECT + cond + "ORDER BY i.created_date DESC, i.idp_id DESC LIMIT ? OFFSET ?",
                          params + [limit, offset]).fetchall()
        return [IDP._fromRow(r) for r in rows], total

    @staticmethod
    def getInterestCounts(designerID):
        """Spec item 5 - {idpID: (views, times shortlisted)} for a designer's projects."""
        rows = get_db().execute(
            "SELECT i.idp_id, (SELECT COUNT(*) FROM idp_view v WHERE v.idp_id = i.idp_id), "
            "(SELECT COUNT(*) FROM favourite f WHERE f.idp_id = i.idp_id) FROM idp i WHERE i.designer_id = ?",
            (designerID,)).fetchall()
        return {r[0]: (r[1], r[2]) for r in rows}

    @staticmethod
    def updateStatus(idpID, status):
        """Archive / restore (#13) or hide (#38). Records the archive date."""
        db = get_db()
        archived = now_str() if status == IDP_ARCHIVED else None
        db.execute("UPDATE idp SET status = ?, archived_date = ?, updated_date = ? WHERE idp_id = ?",
                   (status, archived, now_str(), idpID))
        if status != IDP_ACTIVE:
            # hidden or archived projects are no longer recommended to customers
            db.execute("DELETE FROM recommendation WHERE idp_id = ?", (idpID,))
        db.commit()
        return True

    @staticmethod
    def hasReports(idpID):
        return get_db().execute("SELECT 1 FROM report WHERE idp_id = ?", (idpID,)).fetchone() is not None

    @staticmethod
    def deleteIDP(idpID):
        """A5 - permanently remove the IDP and the records that point to it."""
        db = get_db()
        for table in ("idp_category", "recommendation", "favourite", "idp_view", "idp_cost_item"):
            db.execute(f"DELETE FROM {table} WHERE idp_id = ?", (idpID,))
        db.execute("DELETE FROM idp WHERE idp_id = ?", (idpID,))
        db.commit()
        return True

    # ---------- #40 Category Health ----------
    @staticmethod
    def getCategoryStatistics(categories, days=30):
        """S1 - for each category: active IDPs, interest (views + favourites of those IDPs in
        the last `days` days) and growth in new IDPs vs the previous `days` days."""
        from app.entity.category_health import CategoryHealth
        db = get_db()
        recent = f"-{days} days"
        previous = f"-{2 * days} days"
        stats = []
        for c in categories:
            cid = c.categoryID
            active = ("FROM idp i JOIN idp_category ic ON ic.idp_id = i.idp_id "
                      "WHERE ic.category_id = ? AND i.status = 'Active'")
            idp_count = db.execute("SELECT COUNT(*) " + active, (cid,)).fetchone()[0]
            views = db.execute("SELECT COUNT(*) FROM idp_view v WHERE v.idp_id IN (SELECT i.idp_id " + active + ") "
                               "AND v.viewed_date >= datetime('now', 'localtime', ?)", (cid, recent)).fetchone()[0]
            favs = db.execute("SELECT COUNT(*) FROM favourite f WHERE f.idp_id IN (SELECT i.idp_id " + active + ") "
                              "AND f.saved_date >= datetime('now', 'localtime', ?)", (cid, recent)).fetchone()[0]
            new_recent = db.execute("SELECT COUNT(*) " + active + " AND i.created_date >= datetime('now', 'localtime', ?)",
                                    (cid, recent)).fetchone()[0]
            new_prev = db.execute("SELECT COUNT(*) " + active + " AND i.created_date >= datetime('now', 'localtime', ?) "
                                  "AND i.created_date < datetime('now', 'localtime', ?)",
                                  (cid, previous, recent)).fetchone()[0]
            stats.append(CategoryHealth(cid, c.categoryName, c.status, idp_count, views + favs,
                                        CategoryHealth.growthPercent(new_recent, new_prev)))
        return stats
