"""<<control>> EditUserAccountController - the User Admin corrects an account's details."""
from app.control.create_user_account_controller import (CreateUserAccountController, EMAIL_RE, PHONE_RE,
                                                         USERNAME_RE)
from app.entity.user_account import UserAccount
from app.entity.user_profile import UserProfile
from app.entity.activity_log import ActivityLog
from app.constants import ACT_PROFILE_EDIT, USER_ADMIN


class EditUserAccountController:
    def __init__(self):
        self.errorMsgs = []

    def getAccount(self, accountID):
        return UserAccount.findById(accountID)

    def getActiveProfiles(self):
        return UserProfile.getActiveProfiles()

    def editUserAccount(self, ua, adminID, newPassword="", ipAddress=None):
        """Validate and save. A blank newPassword keeps the current password.
        The change is recorded in the account's activity log (#7)."""
        before = UserAccount.findById(ua.accountID)
        if before is None:
            self.errorMsgs = ["Account not found."]
            return False
        if not self._validateAccountDetails(ua, before, adminID, newPassword):
            return False
        changed = [label for label, a, b in (("username", before.username, ua.username), ("name", before.name, ua.name),
                                             ("email", before.email, ua.email), ("phone", before.phoneNo, ua.phoneNo),
                                             ("profile", before.profileID, ua.profileID)) if a != b]
        ua.passwordHash = before.passwordHash
        if newPassword:
            ua.setPassword(newPassword)
            changed.append("password")
        ua.updateUserAccount()
        if changed:
            ActivityLog.record(ua.accountID, ACT_PROFILE_EDIT, "Updated " + ", ".join(changed),
                               performedBy=adminID, ipAddress=ipAddress)
        self.changed = changed
        return True

    def _validateAccountDetails(self, ua, before, adminID, newPassword):
        errors = []
        if not ua.username or not USERNAME_RE.match(ua.username):
            errors.append("Username must be 4-20 characters (letters, numbers, . or _).")
        elif UserAccount.checkUsernameExists(ua.username, excludeID=ua.accountID):
            errors.append("Username already taken.")
        if not ua.name:
            errors.append("Name is required.")
        if not ua.email or not EMAIL_RE.match(ua.email):
            errors.append("Email is not in a valid format.")
        if not ua.phoneNo or not PHONE_RE.match(ua.phoneNo):
            errors.append("Phone number must be 8 digits starting with 6, 8 or 9.")
        active = {p.profileID: p.profileName for p in UserProfile.getActiveProfiles()}
        if ua.profileID not in active:
            errors.append("Please select a user profile.")
        elif ua.accountID == adminID and active[ua.profileID] != USER_ADMIN:
            errors.append("You cannot remove your own User Admin profile.")
        if newPassword and not CreateUserAccountController.checkPasswordPolicy(newPassword):
            errors.append("Password must be at least 8 characters with an uppercase letter, "
                          "a lowercase letter and a number.")
        self.errorMsgs = errors
        return not errors
