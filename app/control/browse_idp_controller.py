"""<<control>> BrowseIDPController - anyone (logged in or not) can browse and search projects."""
import math
from app.entity.idp import IDP
from app.entity.category import Category

PAGE_SIZE = 24


class BrowseIDPController:
    def getCategories(self):
        return Category.getActiveCategories()

    def searchIDPs(self, keyword="", categoryID=None, page=1):
        """Returns (IDPs on this page, total matches, number of pages)."""
        page = max(1, page)
        idps, total = IDP.searchIDPs(keyword, categoryID, PAGE_SIZE, (page - 1) * PAGE_SIZE)
        return idps, total, max(1, math.ceil(total / PAGE_SIZE))
