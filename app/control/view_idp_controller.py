"""<<control>> ViewIDPController - a project's own page: photos, details, cost estimate and the
designer's cost breakdown, adjusted for the property type the visitor picks."""
from app.entity.idp import IDP
from app.entity.idp_view import IDPView
from app.entity.idp_cost_item import IDPCostItem
from app.entity.estimation_rule import EstimationRule
from app.entity.favourite import Favourite
from app.entity.company_profile import CompanyProfile
from app.constants import IDP_ACTIVE, PROPERTY_TYPES, GST_RATE, PLATFORM_MANAGER


class ViewIDPController:
    def getIDPDetails(self, idpID, viewer=None):
        """Active projects are public. Hidden/archived ones are only shown to their
        designer and to Platform Managers."""
        idp = IDP.getIDPDetails(idpID)
        if idp is None:
            return None
        if idp.status != IDP_ACTIVE and not (viewer and (viewer.accountID == idp.designerID
                                                         or viewer.profileName == PLATFORM_MANAGER)):
            return None
        return idp

    def recordView(self, idp, viewer=None):
        """Count the view (used by #40, #50 and the designer's interest counts).
        Designers viewing their own project are not counted."""
        if viewer is not None and viewer.accountID == idp.designerID:
            return
        IDPView.recordView(idp.idpID, viewer.accountID if viewer else None)

    def getCostBreakdown(self, idp, propertyType=None):
        """The designer's lines, scaled by the property multiplier (from #47's active rule)
        relative to the project's own property type. Returns a dict for the page."""
        selected = propertyType if propertyType in PROPERTY_TYPES else idp.propertyType
        rule = EstimationRule.findActive()
        factor = 1.0
        if rule is not None:
            base = rule.getPropertyFactor(idp.propertyType) or 1.0
            factor = round(rule.getPropertyFactor(selected) / base, 4)
        items = IDPCostItem.findByIDP(idp.idpID)
        lines = [(i, i.calculateLineTotal(factor)) for i in items]
        subtotal = IDPCostItem.subtotal(items, factor)
        gst = round(subtotal * GST_RATE, 2)
        return {"propertyType": selected, "factor": factor, "lines": lines,
                "subtotal": subtotal, "gst": gst, "total": round(subtotal + gst, 2)}

    def isFavourite(self, customerID, idpID):
        return Favourite.isFavourite(customerID, idpID)

    def toggleFavourite(self, customerID, idp):
        """Save to / remove from the favourites list. Returns True if it is now saved."""
        if Favourite.isFavourite(customerID, idp.idpID):
            Favourite.removeFavourite(customerID, idp.idpID)
            return False
        if idp.status != IDP_ACTIVE:
            return False
        Favourite.addFavourite(customerID, idp.idpID)
        return True

    def getDesignerCompany(self, idp):
        """The designer's company information for the 'About the designer' box."""
        return CompanyProfile.findByDesigner(idp.designerID)
