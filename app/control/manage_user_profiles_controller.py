"""<<control>> ManageUserProfilesController - the User Admin manages the user profiles (roles)."""
from app.entity.user_profile import UserProfile
from app.constants import ALL_ROLES, USER_ADMIN, PROFILE_ACTIVE, PROFILE_INACTIVE

STATUSES = [PROFILE_ACTIVE, PROFILE_INACTIVE]


class ManageUserProfilesController:
    def __init__(self):
        self.errorMsg = None

    def getProfiles(self):
        return UserProfile.getAllProfiles()

    def createProfile(self, name, description):
        self.errorMsg = None
        name, description = (name or "").strip(), (description or "").strip()
        if not (2 <= len(name) <= 40):
            self.errorMsg = "Profile name must be 2 to 40 characters."
        elif UserProfile.existsByName(name):
            self.errorMsg = f"The profile '{name}' already exists."
        if self.errorMsg:
            return False
        UserProfile(None, name, description).createProfile()
        return True

    def updateProfile(self, profileID, description, status):
        """Edit the description or suspend / reactivate a profile. Accounts with a suspended
        profile cannot log in, and it cannot be given to new accounts."""
        self.errorMsg = None
        p = UserProfile.findById(profileID)
        if p is None:
            self.errorMsg = "Profile not found."
        elif status not in STATUSES:
            self.errorMsg = "Please select a valid status."
        elif p.profileName == USER_ADMIN and status != PROFILE_ACTIVE:
            self.errorMsg = "The User Admin profile cannot be suspended."
        if self.errorMsg:
            return False
        p.description, p.status = (description or "").strip(), status
        return p.updateProfile()

    @staticmethod
    def isBuiltIn(profile):
        """The 5 platform roles have their own functions in the code."""
        return profile.profileName in ALL_ROLES
