"""<<control>> ChoosePreferencesController - a customer picks the categories they want to see."""
from app.entity.category import Category
from app.entity.customer_preference import CustomerPreference

MAX_PREFERENCES = 10


class ChoosePreferencesController:
    def __init__(self):
        self.errorMsg = None

    def getActiveCategories(self):
        return Category.getActiveCategories()

    def getPreferences(self, customerID):
        return CustomerPreference.getCategoryIDs(customerID)

    def savePreferences(self, customerID, categoryIDs):
        categoryIDs = sorted(set(categoryIDs))
        active = {c.categoryID for c in Category.getActiveCategories()}
        if not (1 <= len(categoryIDs) <= MAX_PREFERENCES) or not set(categoryIDs) <= active:
            self.errorMsg = f"Please choose 1 to {MAX_PREFERENCES} categories"
            return False
        return CustomerPreference.savePreferences(customerID, categoryIDs)
