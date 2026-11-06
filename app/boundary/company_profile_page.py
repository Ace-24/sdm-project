"""<<boundary>> ManageCompanyProfilePg - designers manage their company information;
DesignerPg - the public page of a designer with their company and projects."""
from flask import Blueprint, render_template, request, g, abort, url_for
from app.boundary.auth import role_required
from app.constants import INTERIOR_DESIGNER
from app.control.manage_company_profile_controller import ManageCompanyProfileController
from app.entity.company_profile import CompanyProfile

bp = Blueprint("company_profile", __name__)


class ManageCompanyProfilePg:
    def __init__(self):
        self.controller = ManageCompanyProfileController()

    def displayCompanyForm(self, designerID, cp=None, errors=None):
        return render_template("company_profile.html", cp=cp or self.controller.getCompanyProfile(designerID),
                               errors=errors or [])

    def submitCompanyProfile(self, designerID, form):
        cp = CompanyProfile(designerID, *(form.get(k, "").strip() for k in
                                          ("company_name", "uen", "address", "phone", "email", "website",
                                           "description")))
        cp.uen = cp.uen.upper()
        if self.controller.updateCompanyProfile(cp):
            return render_template("success.html", message="Company information saved",
                                   detail="Customers see it on your project pages and your designer page.",
                                   back_url=url_for("company_profile.displayDesignerPage", designerID=designerID),
                                   back_label="View my designer page")
        return self.displayCompanyForm(designerID, cp, self.controller.errorMsgs)


class DesignerPg:
    def __init__(self):
        self.controller = ManageCompanyProfileController()

    def displayDesignerPage(self, designerID):
        data = self.controller.getDesignerPage(designerID)
        if data is None:
            abort(404)
        designer, cp, projects = data
        return render_template("designer_page.html", designer=designer, cp=cp, idps=projects)


@bp.route("/designer/company", methods=["GET"])
@role_required(INTERIOR_DESIGNER)
def displayCompanyForm():
    return ManageCompanyProfilePg().displayCompanyForm(g.user.accountID)


@bp.route("/designer/company", methods=["POST"])
@role_required(INTERIOR_DESIGNER)
def submitCompanyProfile():
    return ManageCompanyProfilePg().submitCompanyProfile(g.user.accountID, request.form)


@bp.route("/designers/<int:designerID>")
def displayDesignerPage(designerID):
    return DesignerPg().displayDesignerPage(designerID)
