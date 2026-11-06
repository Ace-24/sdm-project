"""<<entity>> Category - an IDP category / design style (#11, #40, #47)."""
from app.db import get_db
from app.constants import CATEGORY_ACTIVE


class Category:
    def __init__(self, categoryID, categoryName, description="", status=CATEGORY_ACTIVE):
        self.categoryID = categoryID
        self.categoryName = categoryName
        self.description = description
        self.status = status

    @staticmethod
    def _fromRow(row):
        if row is None:
            return None
        return Category(row["category_id"], row["category_name"], row["description"], row["status"])

    @staticmethod
    def findById(categoryID):
        row = get_db().execute("SELECT * FROM category WHERE category_id = ?", (categoryID,)).fetchone()
        return Category._fromRow(row)

    @staticmethod
    def getAllCategories():
        rows = get_db().execute("SELECT * FROM category ORDER BY category_name").fetchall()
        return [Category._fromRow(r) for r in rows]

    @staticmethod
    def getActiveCategories():
        rows = get_db().execute("SELECT * FROM category WHERE status = ? ORDER BY category_name",
                                (CATEGORY_ACTIVE,)).fetchall()
        return [Category._fromRow(r) for r in rows]

    @staticmethod
    def existsByName(name, excludeID=None):
        row = get_db().execute("SELECT category_id FROM category WHERE category_name = ? COLLATE NOCASE",
                               ((name or "").strip(),)).fetchone()
        return row is not None and row[0] != excludeID

    @staticmethod
    def updateStatus(categoryID, status):
        """#40 A1 - e.g. flag a category 'Under Review'."""
        db = get_db()
        db.execute("UPDATE category SET status = ? WHERE category_id = ?", (status, categoryID))
        db.commit()
        return True

    @staticmethod
    def getAllWithCounts():
        """Manage Categories - every category with the number of projects using it."""
        rows = get_db().execute(
            "SELECT c.*, (SELECT COUNT(*) FROM idp_category ic WHERE ic.category_id = c.category_id) AS used "
            "FROM category c ORDER BY c.category_name").fetchall()
        out = []
        for r in rows:
            c = Category._fromRow(r)
            c.projectCount = r["used"]
            out.append(c)
        return out

    @staticmethod
    def countProjects(categoryID):
        return get_db().execute("SELECT COUNT(*) FROM idp_category WHERE category_id = ?", (categoryID,)).fetchone()[0]

    def createCategory(self):
        db = get_db()
        cur = db.execute("INSERT INTO category (category_name, description, status) VALUES (?, ?, ?)",
                         (self.categoryName, self.description, self.status))
        db.commit()
        self.categoryID = cur.lastrowid
        return self.categoryID

    def updateCategory(self, oldName=None):
        """Save changes. A renamed category keeps its style multiplier in the estimation rules (#47)."""
        db = get_db()
        db.execute("UPDATE category SET category_name = ?, description = ?, status = ? WHERE category_id = ?",
                   (self.categoryName, self.description, self.status, self.categoryID))
        if oldName and oldName != self.categoryName:
            db.execute("UPDATE rule_factor SET factor_key = ? WHERE factor_type = 'STYLE' AND factor_key = ?",
                       (self.categoryName, oldName))
        db.commit()
        return True

    @staticmethod
    def deleteCategory(categoryID):
        """Only for categories no project uses. Also removes customers' interest in it."""
        db = get_db()
        db.execute("DELETE FROM customer_preference WHERE category_id = ?", (categoryID,))
        db.execute("DELETE FROM category WHERE category_id = ?", (categoryID,))
        db.commit()
        return True
