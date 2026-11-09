"""<<control>> CompareFavouritesController - User Story #27 Compare Favourite IDPs."""
from app.entity.favourite import Favourite
from app.entity.idp_comparison import IDPComparison

MIN_SELECT, MAX_SELECT = 2, 3


class CompareFavouritesController:
    def __init__(self):
        self.errorMsg = None

    def getFavourites(self, customerID):
        return Favourite.findByCustomer(customerID)

    def compareFavourites(self, customerID, idpIDs):
        """Returns an IDPComparison, or None (with errorMsg)."""
        idpIDs = list(dict.fromkeys(idpIDs))            # remove duplicates, keep order
        if not self._validateSelection(idpIDs):
            return None
        idps = Favourite.getSelectedIDPs(customerID, idpIDs)
        if len(idps) != len(idpIDs) or not all(i.isComparable() for i in idps):
            self.errorMsg = "Please select 2 to 3 IDPs to compare"
            return None
        comparison = IDPComparison(customerID)
        comparison.addIDPs(idps)
        comparison.findBestValue()
        return comparison

    def _validateSelection(self, idpIDs):
        self.errorMsg = None
        if not (MIN_SELECT <= len(idpIDs) <= MAX_SELECT):
            self.errorMsg = "Please select 2 to 3 IDPs to compare"
            return False
        return True
