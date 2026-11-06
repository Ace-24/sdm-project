"""<<entity>> ActivityLog - logins, logouts, profile edits, status changes (#7)."""
from app.db import get_db
from app.entity.base import now_str


class ActivityLog:
    def __init__(self, logID, accountID, activityType, description, performedBy, ipAddress, timestamp,
                 performedByName=None):
        self.logID = logID
        self.accountID = accountID
        self.activityType = activityType
        self.description = description
        self.performedBy = performedBy
        self.ipAddress = ipAddress
        self.timestamp = timestamp
        self.performedByName = performedByName   # joined for display

    @staticmethod
    def _fromRow(row):
        return ActivityLog(row["log_id"], row["account_id"], row["activity_type"], row["description"],
                           row["performed_by"], row["ip_address"], row["timestamp"], row["performed_by_name"])

    _SELECT = ("SELECT l.*, p.username AS performed_by_name FROM activity_log l "
               "LEFT JOIN user_account p ON p.account_id = l.performed_by ")

    @staticmethod
    def getActivityLog(accountID):
        """#7 - every entry for the account, newest first."""
        rows = get_db().execute(ActivityLog._SELECT + "WHERE l.account_id = ? ORDER BY l.timestamp DESC, l.log_id DESC",
                                (accountID,)).fetchall()
        return [ActivityLog._fromRow(r) for r in rows]

    @staticmethod
    def getFilteredLog(accountID, activityType=None, fromDate=None, toDate=None):
        """#7 A1 - entries of one type and/or within a date range (dates are YYYY-MM-DD, inclusive)."""
        sql = ActivityLog._SELECT + "WHERE l.account_id = ? "
        params = [accountID]
        if activityType:
            sql += "AND l.activity_type = ? "
            params.append(activityType)
        if fromDate:
            sql += "AND l.timestamp >= ? "
            params.append(fromDate + " 00:00:00")
        if toDate:
            sql += "AND l.timestamp <= ? "
            params.append(toDate + " 23:59:59")
        sql += "ORDER BY l.timestamp DESC, l.log_id DESC"
        return [ActivityLog._fromRow(r) for r in get_db().execute(sql, params).fetchall()]

    @staticmethod
    def record(accountID, activityType, description="", performedBy=None, ipAddress=None):
        """Add one log entry. Called by login/logout and other stories."""
        db = get_db()
        db.execute(
            "INSERT INTO activity_log (account_id, activity_type, description, performed_by, ip_address, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (accountID, activityType, description, performedBy or accountID, ipAddress, now_str()),
        )
        db.commit()
