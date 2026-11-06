"""<<control>> ManageCompanyProfileController - an interior designer manages their company information
(spec item 2). The information is shown on their project pages and public designer page."""
import re
from app.entity.company_profile import CompanyProfile
from app.entity.user_account import UserAccount
from app.entity.idp import IDP
from app.control.create_user_account_controller import EMAIL_RE, PHONE_RE
from app.constants import IDP_ACTIVE, INTERIOR_DESIGNER

UEN_RE = re.compile(r"^[0-9]{8,9}[A-Z]$|^[TSR][0-9]{2}[A-Z]{2}[0-9]{4}[A-Z]$")
WEB_RE = re.compile(r"^https?://[^\s]+\.[^\s]+$")


class ManageCompanyProfileController:
    def __init__(self):
        self.errorMsgs = []

    def getCompanyProfile(self, designerID):
        """The saved information, or an empty profile for a designer who has not filled it in."""
        return CompanyProfile.findByDesigner(designerID) or CompanyProfile(designerID)

    def updateCompanyProfile(self, cp):
        if not self._validateCompanyProfile(cp):
            return False
        return cp.saveCompanyProfile()

    def _validateCompanyProfile(self, cp):
        errors = []
        if not (cp.companyName or "").strip():
            errors.append("Company name is required.")
        if cp.uen and not UEN_RE.match(cp.uen):
            errors.append("UEN must be a valid Singapore UEN, e.g. 201912345K.")
        if not cp.phone or not PHONE_RE.match(cp.phone):
            errors.append("Phone number must be 8 digits starting with 6, 8 or 9.")
        if not cp.email or not EMAIL_RE.match(cp.email):
            errors.append("Email is not in a valid format.")
        if cp.website and not WEB_RE.match(cp.website):
            errors.append("Website must start with http:// or https://")
        if len(cp.description or "") > 1000:
            errors.append("Description must be 1000 characters or fewer.")
        self.errorMsgs = errors
        return not errors

    def getDesignerPage(self, designerID):
        """Public designer page: (designer, company profile, active projects) or None."""
        designer = UserAccount.findById(designerID)
        if designer is None or designer.profileName != INTERIOR_DESIGNER or not designer.isActive():
            return None
        projects = IDP.getIDPsByStatus(designerID, IDP_ACTIVE)
        return designer, CompanyProfile.findByDesigner(designerID), projects
