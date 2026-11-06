"""<<entity>> IDPComparison - 2 to 3 favourite IDPs compared side by side (#27)."""


class IDPComparison:
    def __init__(self, customerID):
        self.customerID = customerID
        self.idps = []
        self.bestValueID = None

    def addIDPs(self, idps):
        self.idps = list(idps)

    def findBestValue(self):
        """S4 - the IDP with the lowest cost per sqm (the first one if there is a tie)."""
        best = min(self.idps, key=lambda i: i.getCostPerSqm(), default=None)
        self.bestValueID = best.idpID if best else None
        return self.bestValueID
