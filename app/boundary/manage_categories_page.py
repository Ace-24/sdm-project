"""<<boundary>> ManageCategoriesPg - the Platform Manager manages IDP categories."""
from flask import Blueprint, render_template, request, g, redirect, url_for, flash, abort
from app.boundary.auth import role_required
from app.constants import PLATFORM_MANAGER
from app.control.manage_categories_controller import ManageCategoriesController, STATUSES

bp = Blueprint("manage_categories", __name__, url_prefix="/platform/categories")


class ManageCategoriesPg:
    def __init__(self):
        self.controller = ManageCategoriesController()

    def displayCategoryList(self, error=None, form=None):
        return render_template("categories.html", categories=self.controller.getCategories(),
                               requests=self.controller.getCategoryRequests(g.user.accountID),
                               error=error, form=form or {})

    def submitNewCategory(self, form):
        if self.controller.createCategory(form.get("name"), form.get("description")):
            flash(f"Category '{form.get('name', '').strip()}' created", "success")
            return redirect(url_for("manage_categories.displayCategoryList"))
        return self.displayCategoryList(self.controller.errorMsg, form)

    def displayEditForm(self, categoryID, category=None, error=None):
        original = self.controller.getCategory(categoryID)
        if original is None:
            abort(404)
        return render_template("category_edit.html", category=category or original, statuses=STATUSES, error=error)

    def submitCategoryUpdate(self, categoryID, form):
        if self.controller.updateCategory(categoryID, form.get("name"), form.get("description"), form.get("status")):
            flash("Category updated", "success")
            return redirect(url_for("manage_categories.displayCategoryList"))
        from app.entity.category import Category
        typed = Category(categoryID, form.get("name", ""), form.get("description", ""), form.get("status", ""))
        return self.displayEditForm(categoryID, typed, self.controller.errorMsg)

    def clickDelete(self, categoryID):
        if self.controller.deleteCategory(categoryID):
            flash("Category deleted", "success")
        else:
            flash(self.controller.errorMsg, "error")
        return redirect(url_for("manage_categories.displayCategoryList"))


@bp.route("/", methods=["GET"])
@role_required(PLATFORM_MANAGER)
def displayCategoryList():
    return ManageCategoriesPg().displayCategoryList()


@bp.route("/", methods=["POST"])
@role_required(PLATFORM_MANAGER)
def submitNewCategory():
    return ManageCategoriesPg().submitNewCategory(request.form)


@bp.route("/<int:categoryID>/edit", methods=["GET"])
@role_required(PLATFORM_MANAGER)
def displayEditForm(categoryID):
    return ManageCategoriesPg().displayEditForm(categoryID)


@bp.route("/<int:categoryID>/edit", methods=["POST"])
@role_required(PLATFORM_MANAGER)
def submitCategoryUpdate(categoryID):
    return ManageCategoriesPg().submitCategoryUpdate(categoryID, request.form)


@bp.route("/<int:categoryID>/delete", methods=["POST"])
@role_required(PLATFORM_MANAGER)
def clickDelete(categoryID):
    return ManageCategoriesPg().clickDelete(categoryID)
