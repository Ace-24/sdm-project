"""<<control>> LoginController - checks credentials and records login/logout."""
from app.entity.user_account import UserAccount
from app.entity.activity_log import ActivityLog
from app.constants import ACT_LOGIN, ACT_LOGOUT


class LoginController:
    def validateLogin(self, username, password, ipAddress=None):
        """Return (UserAccount, None) on success or (None, error message)."""
        if not username or not password:
            return None, "Please enter your username and password."
        account = UserAccount.findByUsername(username.strip())
        if account is None or not account.checkPassword(password):
            return None, "Invalid username or password."
        if not account.isActive():
            return None, "This account is suspended. Please contact the User Admin."
        if account.profileStatus != "Active":
            return None, f"The {account.profileName} profile is currently suspended. Please contact the User Admin."
        ActivityLog.record(account.accountID, ACT_LOGIN, "Logged in", ipAddress=ipAddress)
        return account, None

    def logout(self, accountID, ipAddress=None):
        ActivityLog.record(accountID, ACT_LOGOUT, "Logged out", ipAddress=ipAddress)
