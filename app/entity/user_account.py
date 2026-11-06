"""<<entity>> UserAccount - one login account on the platform."""
from werkzeug.security import generate_password_hash, check_password_hash
from app.db import get_db
from app.constants import ACCOUNT_ACTIVE
from app.entity.base import now_str


class UserAccount:
    def __init__(self, accountID, username, name, email, phoneNo, profileID,
                 status=ACCOUNT_ACTIVE, createdDate=None, passwordHash=None, profileName=None, profileStatus=None):
        self.accountID = accountID
        self.username = username
        self.name = name
        self.email = email
        self.phoneNo = phoneNo
        self.profileID = profileID
        self.status = status
        self.createdDate = createdDate
        self.passwordHash = passwordHash
        self.profileName = profileName   # joined from user_profile for display
        self.profileStatus = profileStatus

    @staticmethod
    def _fromRow(row):
        if row is None:
            return None
        keys = row.keys()
        return UserAccount(
            row["account_id"], row["username"], row["name"], row["email"], row["phone_no"],
            row["profile_id"], row["status"], row["created_date"], row["password_hash"],
            row["profile_name"] if "profile_name" in keys else None,
            row["profile_status"] if "profile_status" in keys else None,
        )

    _SELECT = ("SELECT a.*, p.profile_name, p.status AS profile_status FROM user_account a "
               "JOIN user_profile p ON p.profile_id = a.profile_id ")

    @staticmethod
    def findById(accountID):
        row = get_db().execute(UserAccount._SELECT + "WHERE a.account_id = ?", (accountID,)).fetchone()
        return UserAccount._fromRow(row)

    @staticmethod
    def findByUsername(username):
        """Usernames are not case-sensitive ("Customer" finds "customer")."""
        row = get_db().execute(UserAccount._SELECT + "WHERE a.username = ? COLLATE NOCASE",
                               ((username or "").strip(),)).fetchone()
        return UserAccount._fromRow(row)

    @staticmethod
    def checkUsernameExists(username, excludeID=None):
        """#1 - True if the username is already used (not case-sensitive) by another account."""
        row = get_db().execute("SELECT account_id FROM user_account WHERE username = ? COLLATE NOCASE",
                               ((username or "").strip(),)).fetchone()
        return row is not None and row[0] != excludeID

    def updateUserAccount(self):
        """Edit User Account - save name, username, email, phone, profile (and password hash)."""
        db = get_db()
        db.execute("UPDATE user_account SET username = ?, name = ?, email = ?, phone_no = ?, profile_id = ?, "
                   "password_hash = ? WHERE account_id = ?",
                   (self.username, self.name, self.email, self.phoneNo, self.profileID, self.passwordHash,
                    self.accountID))
        db.commit()
        return True

    @staticmethod
    def searchUserAccounts(keyword, profileName=None):
        """#7 - accounts whose username, name or email contains the keyword, optionally
        only one profile. An empty keyword returns every account."""
        like = f"%{(keyword or '').strip()}%"
        sql = UserAccount._SELECT + "WHERE (a.username LIKE ? OR a.name LIKE ? OR a.email LIKE ?) "
        params = [like, like, like]
        if profileName:
            sql += "AND p.profile_name = ? "
            params.append(profileName)
        rows = get_db().execute(sql + "ORDER BY p.profile_id, a.username", params).fetchall()
        return [UserAccount._fromRow(r) for r in rows]

    @staticmethod
    def findIDsByProfile(profileName):
        """IDs of active accounts with a profile, e.g. every Platform Manager."""
        rows = get_db().execute("SELECT a.account_id FROM user_account a JOIN user_profile p "
                                "ON p.profile_id = a.profile_id WHERE p.profile_name = ? AND a.status = 'Active'",
                                (profileName,)).fetchall()
        return [r[0] for r in rows]

    def updateStatus(self, status):
        """#7 A3 - e.g. suspend the account."""
        db = get_db()
        db.execute("UPDATE user_account SET status = ? WHERE account_id = ?", (status, self.accountID))
        db.commit()
        self.status = status

    def checkPassword(self, password):
        return self.passwordHash is not None and check_password_hash(self.passwordHash, password)

    def setPassword(self, password):
        self.passwordHash = generate_password_hash(password)

    def isActive(self):
        return self.status == ACCOUNT_ACTIVE

    def saveUserAccount(self):
        """Insert a new account and return its new ID (used by #1 and test data)."""
        db = get_db()
        cur = db.execute(
            "INSERT INTO user_account (username, password_hash, name, email, phone_no, profile_id, status, created_date) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (self.username, self.passwordHash, self.name, self.email, self.phoneNo,
             self.profileID, self.status, self.createdDate or now_str()),
        )
        db.commit()
        self.accountID = cur.lastrowid
        return self.accountID
