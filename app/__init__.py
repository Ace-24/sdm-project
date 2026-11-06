"""Interior Design Platform - Flask application factory."""
import os
from flask import Flask, g, render_template
from app import db
from app.constants import MENU
from app.boundary.auth import load_logged_in_user


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SDM_SECRET_KEY", "dev-secret-change-me"),
        DATABASE=os.environ.get("SDM_DB_PATH", os.path.join(app.instance_path, "sdm.db")),
        UPLOAD_FOLDER=os.path.join(app.root_path, "static", "uploads"),   # IDP photos (#13)
        MAX_CONTENT_LENGTH=30 * 1024 * 1024,
    )
    if test_config:
        app.config.update(test_config)
    os.makedirs(app.instance_path, exist_ok=True)

    app.teardown_appcontext(db.close_db)
    app.before_request(load_logged_in_user)

    # ---- Register boundary blueprints (one per user story) ----
    from app.boundary import (login_page, create_user_account_page, view_activity_log_page,
                              manage_portfolio_page, manage_project_categories_page,
                              estimation_rule_page, sales_report_page,
                              compare_favourites_page, cost_breakdown_page,
                              manage_reports_page, category_health_page,
                              sign_up_page, choose_preferences_page, browse_idp_page, view_idp_page,
                              edit_user_account_page, manage_user_profiles_page, company_profile_page,
                              manage_categories_page, platform_report_page)
    app.register_blueprint(login_page.bp)
    app.register_blueprint(sign_up_page.bp)                  # Sign up (customers)
    app.register_blueprint(choose_preferences_page.bp)       # Choose interests (customers)
    app.register_blueprint(browse_idp_page.bp)               # Browse / search projects (public)
    app.register_blueprint(view_idp_page.bp)                 # Project page + favourites (public)
    app.register_blueprint(create_user_account_page.bp)      # #1
    app.register_blueprint(view_activity_log_page.bp)        # #7
    app.register_blueprint(edit_user_account_page.bp)        # Edit account (User Admin)
    app.register_blueprint(manage_user_profiles_page.bp)     # User profiles (User Admin)
    app.register_blueprint(company_profile_page.bp)          # Company information + designer page
    app.register_blueprint(manage_categories_page.bp)        # Manage categories (Platform Manager)
    app.register_blueprint(platform_report_page.bp)          # Platform reports (Platform Manager)
    app.register_blueprint(manage_project_categories_page.bp)  # #11
    app.register_blueprint(manage_portfolio_page.bp)         # #13
    app.register_blueprint(compare_favourites_page.bp)       # #27
    app.register_blueprint(cost_breakdown_page.bp)           # #29
    app.register_blueprint(manage_reports_page.bp)           # #38
    app.register_blueprint(category_health_page.bp)          # #40
    app.register_blueprint(estimation_rule_page.bp)          # #47
    app.register_blueprint(sales_report_page.bp)             # #50

    @app.context_processor
    def inject_menu():
        """Role menu - only shows stories whose pages exist."""
        user = getattr(g, "user", None)
        items = []
        if user is not None:
            items = [(label, ep) for label, ep in MENU.get(user.profileName, []) if ep in app.view_functions]
        return {"menu_items": items}

    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("error.html", code=403,
                               message="You do not have permission to view this page."), 403

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("error.html", code=404, message="Page not found."), 404

    return app
