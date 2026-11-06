"""<<control>> SignUpController - a visitor creates their own Customer account."""
from app.control.create_user_account_controller import CreateUserAccountController
from app.entity.user_profile import UserProfile
from app.entity.activity_log import ActivityLog
from app.constants import CUSTOMER, ACT_LOGIN


class SignUpController:
    def __init__(self):
        self.errorMsgs = []

    def registerCustomer(self, ua, password, ipAddress=None):
        """Same checks as #1 Create User Account, but the profile is always Customer.
        Returns True if the account was created (the user is then logged in)."""
        customer = next((p for p in UserProfile.getActiveProfiles() if p.profileName == CUSTOMER), None)
        ua.profileID = customer.profileID if customer else None
        create = CreateUserAccountController()
        if not create.createUserAccount(ua, password):
            self.errorMsgs = create.errorMsgs
            return False
        ActivityLog.record(ua.accountID, ACT_LOGIN, "Signed up and logged in", ipAddress=ipAddress)
        return True
