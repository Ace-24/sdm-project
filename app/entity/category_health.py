"""<<entity>> CategoryHealth - the health score of one category (#40)."""

AT_RISK_BELOW = 40
DOING_WELL_FROM = 70


class CategoryHealth:
    def __init__(self, categoryID, categoryName, categoryStatus, idpCount=0, interestCount=0, growthRate=0.0):
        self.categoryID = categoryID
        self.categoryName = categoryName
        self.categoryStatus = categoryStatus
        self.idpCount = idpCount              # active IDPs in the category
        self.interestCount = interestCount    # views + favourites in the last 30 days
        self.growthRate = growthRate          # % change in new IDPs vs the previous 30 days
        self.healthScore = 0.0
        self.healthStatus = "No data"

    @staticmethod
    def growthPercent(recent, previous):
        """Growth in new IDPs: last 30 days vs the 30 days before."""
        if previous == 0:
            return 100.0 if recent > 0 else 0.0
        return round((recent - previous) / previous * 100, 1)

    def calculateScore(self, maxIDPs, maxInterest, maxGrowth):
        """Scale each measure 0-100 against the highest category, then
        score = 40% IDP score + 40% interest score + 20% growth score.
        Negative growth scores 0."""
        if self.idpCount == 0:
            self.healthScore, self.healthStatus = 0.0, "No data"
            return self.healthScore
        idp_score = self.idpCount / maxIDPs * 100 if maxIDPs else 0
        interest_score = self.interestCount / maxInterest * 100 if maxInterest else 0
        growth_score = max(self.growthRate, 0) / maxGrowth * 100 if maxGrowth > 0 else 0
        self.healthScore = round(0.4 * idp_score + 0.4 * interest_score + 0.2 * growth_score, 1)
        self.healthStatus = ("At Risk" if self.healthScore < AT_RISK_BELOW
                             else "Doing Well" if self.healthScore >= DOING_WELL_FROM else "Stable")
        return self.healthScore
