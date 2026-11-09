"""<<control>> ManageProjectCategoriesController - User Story #11 Manage Project Categories."""
from app.entity.category import Category
from app.entity.idp_category import IDPCategory
from app.entity.customer_preference import CustomerPreference
from app.entity.recommendation import Recommendation
from app.entity.notification import Notification
from app.entity.user_account import UserAccount
from app.constants import CATEGORY_ACTIVE, IDP_ACTIVE, PLATFORM_MANAGER

MIN_CATEGORIES = 1
MAX_CATEGORIES = 5


class ManageProjectCategoriesController:
    def __init__(self):
        self.errorMsg = None

    def getIDPCategories(self, idpID):
        return IDPCategory.getCategoryIDs(idpID)

    def getActiveCategories(self):
        return Category.getActiveCategories()

    def updateIDPCategories(self, idp, categoryIDs):
        """Returns True if saved."""
        categoryIDs = sorted(set(categoryIDs))
        if not self._validateCategories(categoryIDs):
            return False
        IDPCategory.replaceLinks(idp.idpID, categoryIDs)
        # only active projects are recommended
        customers = CustomerPreference.findCustomersByCategories(categoryIDs) if idp.status == IDP_ACTIVE else []
        Recommendation.refreshRecommendations(idp.idpID, customers)
        self.matchedCustomers = len(customers)
        return True

    def _validateCategories(self, categoryIDs):
        self.errorMsg = None
        active = {c.categoryID for c in Category.getActiveCategories()}
        if not (MIN_CATEGORIES <= len(categoryIDs) <= MAX_CATEGORIES) or not set(categoryIDs) <= active:
            self.errorMsg = "Please select 1 to 5 active categories"
            return False
        return True

    def requestNewCategory(self, designer, categoryName, reason):
        self.errorMsg = None
        categoryName, reason = (categoryName or "").strip(), (reason or "").strip()
        if not categoryName or not reason:
            self.errorMsg = "Please enter a category name and a reason."
            return False
        if Category.existsByName(categoryName):
            self.errorMsg = f"The category '{categoryName}' already exists."
            return False
        for pm in UserAccount.findIDsByProfile(PLATFORM_MANAGER):
            Notification.send(pm, f"New category request: {categoryName}",
                              f"{designer.name} ({designer.username}) requested the category "
                              f"'{categoryName}'. Reason: {reason}")
        return True
