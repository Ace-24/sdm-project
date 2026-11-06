"""<<boundary>> BrowseIDPPg - public page to browse and search projects (no login needed)."""
from flask import Blueprint, render_template, request
from app.control.browse_idp_controller import BrowseIDPController

bp = Blueprint("browse_idp", __name__, url_prefix="/projects")


class BrowseIDPPg:
    def __init__(self):
        self.controller = BrowseIDPController()

    def displayBrowsePage(self, keyword, categoryID, page):
        idps, total, pages = self.controller.searchIDPs(keyword, categoryID, page)
        return render_template("browse.html", idps=idps, total=total, pages=pages, page=page, keyword=keyword,
                               category_id=categoryID, categories=self.controller.getCategories())


@bp.route("/")
def displayBrowsePage():
    cat = request.args.get("category", "")
    page = request.args.get("page", "1")
    return BrowseIDPPg().displayBrowsePage(request.args.get("q", "").strip(), int(cat) if cat.isdigit() else None,
                                           int(page) if page.isdigit() else 1)
