"""<<control>> ViewActivityLogController - User Story #7 View Account Activity Log."""
import csv
import io
from datetime import datetime
from app.entity.user_account import UserAccount
from app.entity.activity_log import ActivityLog
from app.constants import ACCOUNT_SUSPENDED, ACCOUNT_ACTIVE, ACT_STATUS_CHANGE, ACTIVITY_TYPES


class ViewActivityLogController:
    def __init__(self):
        self.errorMsg = None

    def searchUserAccount(self, keyword, profileName=None):
        """Sub-flow S1 - accounts matching the keyword (username, name or email).
        With no keyword, every current account is listed so the admin can browse."""
        return UserAccount.searchUserAccounts(keyword, profileName or None)

    def viewActivityLog(self, accountID):
        """Main flow step 4 - all entries, newest first."""
        return ActivityLog.getActivityLog(accountID)

    def filterActivityLog(self, accountID, activityType=None, fromDate=None, toDate=None):
        """A1 - Filter Activity Log. Returns None (and sets errorMsg) if the filter is invalid."""
        self.errorMsg = None
        if activityType and activityType not in ACTIVITY_TYPES:
            self.errorMsg = "Unknown activity type."
            return None
        try:
            start = datetime.strptime(fromDate, "%Y-%m-%d") if fromDate else None
            end = datetime.strptime(toDate, "%Y-%m-%d") if toDate else None
        except ValueError:
            self.errorMsg = "Dates must be in the format YYYY-MM-DD."
            return None
        if start and end and start > end:
            self.errorMsg = "The 'from' date must be on or before the 'to' date."
            return None
        return ActivityLog.getFilteredLog(accountID, activityType or None, fromDate or None, toDate or None)

    def exportActivityLog(self, logs):
        """A2 - Export Activity Log: the displayed entries as CSV text."""
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["Date/Time", "Activity Type", "Description", "Performed By", "IP Address"])
        for log in logs:
            writer.writerow([log.timestamp, log.activityType, log.description, log.performedByName, log.ipAddress])
        return out.getvalue()

    def suspendUserAccount(self, accountID, adminID, ipAddress=None):
        """A3 - Suspend User Account. Returns False if it is the admin's own account
        or the account is already suspended."""
        account = UserAccount.findById(accountID)
        if account is None or account.accountID == adminID or account.status == ACCOUNT_SUSPENDED:
            return False
        old = account.status
        account.updateStatus(ACCOUNT_SUSPENDED)
        ActivityLog.record(accountID, ACT_STATUS_CHANGE, f"Status changed from {old} to {ACCOUNT_SUSPENDED}",
                           performedBy=adminID, ipAddress=ipAddress)
        return True

    def reactivateUserAccount(self, accountID, adminID, ipAddress=None):
        """A4 - Reactivate a suspended account (false flag or resolved case)."""
        account = UserAccount.findById(accountID)
        if account is None or account.status != ACCOUNT_SUSPENDED:
            return False
        account.updateStatus(ACCOUNT_ACTIVE)
        ActivityLog.record(accountID, ACT_STATUS_CHANGE, f"Status changed from {ACCOUNT_SUSPENDED} to {ACCOUNT_ACTIVE}",
                           performedBy=adminID, ipAddress=ipAddress)
        return True
