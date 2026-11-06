"""<<boundary>> ManageUserProfilesPg - the User Admin manages user profiles."""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.boundary.auth import role_required
from app.constants import USER_ADMIN
from app.control.manage_user_profiles_controller import ManageUserProfilesController, STATUSES

bp = Blueprint("manage_user_profiles", __name__, url_prefix="/admin/profiles")


class ManageUserProfilesPg:
    def __init__(self):
        self.controller = ManageUserProfilesController()

    def displayProfiles(self, error=None, form=None):
        return render_template("user_profiles.html", profiles=self.controller.getProfiles(), statuses=STATUSES,
                               error=error, form=form or {}, is_built_in=self.controller.isBuiltIn)

    def submitNewProfile(self, form):
        if self.controller.createProfile(form.get("name"), form.get("description")):
            flash("Profile created", "success")
            return redirect(url_for("manage_user_profiles.displayProfiles"))
        return self.displayProfiles(self.controller.errorMsg, form)

    def submitProfileUpdate(self, profileID, form):
        if self.controller.updateProfile(profileID, form.get("description"), form.get("status")):
            flash("Profile updated", "success")
        else:
            flash(self.controller.errorMsg, "error")
        return redirect(url_for("manage_user_profiles.displayProfiles"))


@bp.route("/", methods=["GET"])
@role_required(USER_ADMIN)
def displayProfiles():
    return ManageUserProfilesPg().displayProfiles()


@bp.route("/", methods=["POST"])
@role_required(USER_ADMIN)
def submitNewProfile():
    return ManageUserProfilesPg().submitNewProfile(request.form)


@bp.route("/<int:profileID>", methods=["POST"])
@role_required(USER_ADMIN)
def submitProfileUpdate(profileID):
    return ManageUserProfilesPg().submitProfileUpdate(profileID, request.form)
