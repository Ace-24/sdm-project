"""<<control>> ManageCategoriesController - the Platform Manager manages the IDP categories (spec item 6)."""
from app.entity.category import Category
from app.entity.notification import Notification
from app.constants import CATEGORY_ACTIVE, CATEGORY_UNDER_REVIEW, CATEGORY_INACTIVE

STATUSES = [CATEGORY_ACTIVE, CATEGORY_UNDER_REVIEW, CATEGORY_INACTIVE]


class ManageCategoriesController:
    def __init__(self):
        self.errorMsg = None

    def getCategories(self):
        return Category.getAllWithCounts()

    def getCategory(self, categoryID):
        return Category.findById(categoryID)

    def getCategoryRequests(self, managerID):
        """New category requests sent by designers from #11."""
        return Notification.findForAccount(managerID, "New category request")

    def createCategory(self, name, description):
        c = Category(None, (name or "").strip(), (description or "").strip(), CATEGORY_ACTIVE)
        if not self._validateCategory(c):
            return False
        c.createCategory()
        return True

    def updateCategory(self, categoryID, name, description, status):
        old = Category.findById(categoryID)
        if old is None:
            self.errorMsg = "Category not found."
            return False
        c = Category(categoryID, (name or "").strip(), (description or "").strip(), status)
        if not self._validateCategory(c):
            return False
        return c.updateCategory(oldName=old.categoryName)

    def deleteCategory(self, categoryID):
        self.errorMsg = None
        if Category.findById(categoryID) is None:
            self.errorMsg = "Category not found."
            return False
        used = Category.countProjects(categoryID)
        if used:
            self.errorMsg = (f"This category is used by {used} project(s), so it cannot be deleted. "
                             "Set it to Inactive instead.")
            return False
        return Category.deleteCategory(categoryID)

    def _validateCategory(self, c):
        self.errorMsg = None
        if not (2 <= len(c.categoryName) <= 40):
            self.errorMsg = "Category name must be 2 to 40 characters."
        elif Category.existsByName(c.categoryName, excludeID=c.categoryID):
            self.errorMsg = f"The category '{c.categoryName}' already exists."
        elif c.status not in STATUSES:
            self.errorMsg = "Please select a valid status."
        return self.errorMsg is None
