"""<<boundary>> CategoryHealthPg - User Story #40 Category Health Report (Platform Manager)."""
from flask import Blueprint, render_template, url_for, flash, redirect
from app.boundary.auth import role_required
from app.constants import PLATFORM_MANAGER
from app.control.category_health_controller import CategoryHealthController, DAYS

bp = Blueprint("category_health", __name__, url_prefix="/platform/category-health")


class CategoryHealthPg:
    def __init__(self):
        self.controller = CategoryHealthController()

    def displayCategoryHealth(self):
        return self.displayHealthReport(self.controller.generateHealthReport())

    def displayHealthReport(self, results):
        return render_template("category_health.html", results=results, days=DAYS)

    def flagCategory(self, categoryID):
        if self.controller.flagCategoryForReview(categoryID):
            return self.displaySuccessPg()
        flash("Only active categories can be flagged for review.", "error")
        return redirect(url_for("category_health.displayCategoryHealth"))

    def displaySuccessPg(self):
        return render_template("success.html", message="Category flagged for review",
                               back_url=url_for("category_health.displayCategoryHealth"),
                               back_label="Back to category health")


@bp.route("/")
@role_required(PLATFORM_MANAGER)
def displayCategoryHealth():
    return CategoryHealthPg().displayCategoryHealth()


@bp.route("/<int:categoryID>/flag", methods=["POST"])
@role_required(PLATFORM_MANAGER)
def flagCategory(categoryID):
    return CategoryHealthPg().flagCategory(categoryID)
