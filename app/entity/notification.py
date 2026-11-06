"""<<entity>> Notification - stands in for real email (#1, #38)."""
from app.db import get_db
from app.entity.base import now_str


class Notification:
    def __init__(self, notificationID, accountID, subject, message, createdDate):
        self.notificationID = notificationID
        self.accountID = accountID
        self.subject = subject
        self.message = message
        self.createdDate = createdDate

    @staticmethod
    def send(accountID, subject, message):
        db = get_db()
        db.execute("INSERT INTO notification (account_id, subject, message, created_date) VALUES (?, ?, ?, ?)",
                   (accountID, subject, message, now_str()))
        db.commit()

    @staticmethod
    def findForAccount(accountID, subjectPrefix=""):
        rows = get_db().execute("SELECT * FROM notification WHERE account_id = ? AND subject LIKE ? "
                                "ORDER BY created_date DESC, notification_id DESC",
                                (accountID, subjectPrefix + "%")).fetchall()
        return [Notification(r["notification_id"], r["account_id"], r["subject"], r["message"], r["created_date"])
                for r in rows]
