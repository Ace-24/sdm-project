"""<<control>> CreateUserAccountController - User Story #1 Create User Account."""
import re
from app.entity.user_account import UserAccount
from app.entity.user_profile import UserProfile
from app.entity.notification import Notification

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^[689]\d{7}$")               # Singapore: 8 digits starting with 6, 8 or 9
USERNAME_RE = re.compile(r"^[A-Za-z0-9._]{4,20}$")


class CreateUserAccountController:
    def __init__(self):
        self.errorMsgs = []

    def getActiveProfiles(self):
        return UserProfile.getActiveProfiles()

    def createUserAccount(self, ua, password, emailCredentials=False):
        """Returns True if the account was saved.
        On failure, self.errorMsgs lists what is wrong."""
        if not self._validateAccountDetails(ua, password):
            return False
        ua.setPassword(password)
        ua.saveUserAccount()
        if emailCredentials:
            self._sendLoginCredentials(ua, password)
        return True

    def _validateAccountDetails(self, ua, password):
        errors = []
        if not ua.username:
            errors.append("Username is required.")
        elif not USERNAME_RE.match(ua.username):
            errors.append("Username must be 4-20 characters (letters, numbers, . or _).")
        if not password:
            errors.append("Password is required.")
        elif not self.checkPasswordPolicy(password):
            errors.append("Password must be at least 8 characters with an uppercase letter, "
                          "a lowercase letter and a number.")
        if not ua.name:
            errors.append("Name is required.")
        if not ua.email:
            errors.append("Email is required.")
        elif not EMAIL_RE.match(ua.email):
            errors.append("Email is not in a valid format.")
        if not ua.phoneNo:
            errors.append("Phone number is required.")
        elif not PHONE_RE.match(ua.phoneNo):
            errors.append("Phone number must be 8 digits starting with 6, 8 or 9.")
        active_ids = [p.profileID for p in UserProfile.getActiveProfiles()]
        if ua.profileID not in active_ids:
            errors.append("Please select a user profile.")
        if ua.username and USERNAME_RE.match(ua.username) and UserAccount.checkUsernameExists(ua.username):
            errors.append("Username already taken.")
        self.errorMsgs = errors
        return not errors

    @staticmethod
    def checkPasswordPolicy(password):
        return (len(password) >= 8 and re.search(r"[A-Z]", password) is not None
                and re.search(r"[a-z]", password) is not None and re.search(r"\d", password) is not None)

    def _sendLoginCredentials(self, ua, password):
        Notification.send(
            ua.accountID, "Your Interior Design Platform account",
            f"Hello {ua.name}, an account has been created for you. "
            f"Username: {ua.username}. Temporary password: {password}. "
            "Please keep it safe and do not share it.")
