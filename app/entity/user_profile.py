"""<<entity>> UserProfile - a role such as Customer or Sales Manager."""
from app.db import get_db
from app.constants import PROFILE_ACTIVE


class UserProfile:
    def __init__(self, profileID, profileName, description="", status=PROFILE_ACTIVE):
        self.profileID = profileID
        self.profileName = profileName
        self.description = description
        self.status = status

    @staticmethod
    def _fromRow(row):
        if row is None:
            return None
        return UserProfile(row["profile_id"], row["profile_name"], row["description"], row["status"])

    @staticmethod
    def findById(profileID):
        row = get_db().execute("SELECT * FROM user_profile WHERE profile_id = ?", (profileID,)).fetchone()
        return UserProfile._fromRow(row)

    @staticmethod
    def getActiveProfiles():
        """Used by #1 to fill the profile drop-down."""
        rows = get_db().execute(
            "SELECT * FROM user_profile WHERE status = ? ORDER BY profile_id", (PROFILE_ACTIVE,)
        ).fetchall()
        return [UserProfile._fromRow(r) for r in rows]

    @staticmethod
    def getAllProfiles():
        """Manage User Profiles - every profile with its number of accounts."""
        rows = get_db().execute(
            "SELECT p.*, (SELECT COUNT(*) FROM user_account a WHERE a.profile_id = p.profile_id) AS accounts "
            "FROM user_profile p ORDER BY p.profile_id").fetchall()
        out = []
        for r in rows:
            p = UserProfile._fromRow(r)
            p.accountCount = r["accounts"]
            out.append(p)
        return out

    @staticmethod
    def existsByName(name):
        return get_db().execute("SELECT 1 FROM user_profile WHERE profile_name = ? COLLATE NOCASE",
                                ((name or "").strip(),)).fetchone() is not None

    def createProfile(self):
        db = get_db()
        cur = db.execute("INSERT INTO user_profile (profile_name, description, status) VALUES (?, ?, ?)",
                         (self.profileName, self.description, self.status))
        db.commit()
        self.profileID = cur.lastrowid
        return self.profileID

    def updateProfile(self):
        db = get_db()
        db.execute("UPDATE user_profile SET description = ?, status = ? WHERE profile_id = ?",
                   (self.description, self.status, self.profileID))
        db.commit()
        return True
