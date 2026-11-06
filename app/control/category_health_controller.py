"""<<control>> CategoryHealthController - User Story #40 Category Health Report."""
from app.entity.category import Category
from app.entity.idp import IDP
from app.constants import CATEGORY_ACTIVE, CATEGORY_UNDER_REVIEW

DAYS = 30


class CategoryHealthController:
    def generateHealthReport(self):
        """Main flow steps 2-5. Returns the CategoryHealth list, highest score first."""
        categories = Category.getAllCategories()
        results = IDP.getCategoryStatistics(categories, DAYS)          # S1
        self._calculateHealthScores(results)                           # S2
        return sorted(results, key=lambda h: (-h.healthScore, h.categoryName))

    @staticmethod
    def _calculateHealthScores(results):
        max_idps = max((h.idpCount for h in results), default=0)
        max_interest = max((h.interestCount for h in results), default=0)
        max_growth = max((h.growthRate for h in results), default=0)
        for h in results:
            h.calculateScore(max_idps, max_interest, max_growth)

    def flagCategoryForReview(self, categoryID):
        """A1 - only active categories can be flagged."""
        c = Category.findById(categoryID)
        if c is None or c.status != CATEGORY_ACTIVE:
            return False
        return Category.updateStatus(categoryID, CATEGORY_UNDER_REVIEW)
