"""Generate docs/CODE_WALKTHROUGH.md - where each feature lives in the code (file + line numbers)
and how a request flows through the Boundary -> Control -> Entity layers.

Usage:  python scripts/walkthrough.py

The call flows and line numbers are read from the code itself, so re-run this after changing code.
"""
import ast
import importlib
import inspect
import os
import sys
import textwrap

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app import create_app                    # noqa: E402
from scripts import traceability as T         # noqa: E402

DOC_DIR = os.path.join(ROOT, "docs")

# ---- Plain-English explanation of each feature (keyed by story name in traceability.STORIES) ----
NOTES = {
    "Login / Logout": "The login form posts the username and password. `LoginController.validateLogin()` finds the "
        "account (usernames are not case-sensitive), checks the password hash, and refuses suspended accounts or "
        "accounts whose profile is inactive. On success the account ID is stored in the session and a Login entry "
        "is written to the activity log. Every request loads the logged-in user (`load_logged_in_user`), and "
        "`role_required` blocks pages that belong to other roles (error 403). The customer home page also shows "
        "projects from the customer's interests.",
    "Sign Up": "A visitor fills in the sign-up form. `SignUpController` reuses the #1 validation "
        "(`CreateUserAccountController`) but always gives the Customer profile. The new user is logged in straight "
        "away and sent to the Choose Interests page.",
    "Choose Interests": "The customer ticks 1-10 active categories. `ChoosePreferencesController.savePreferences()` "
        "checks the choice and replaces the rows in `customer_preference`. The home page then shows active "
        "projects in those categories (`Recommendation.getForCustomer()`).",
    "Browse / Search Projects": "Public page. `BrowseIDPController.searchIDPs()` asks `IDP.searchIDPs()` for active "
        "projects matching the keyword (title, description, designer name or category name) and the optional "
        "category, 24 per page.",
    "View Project + Save to Favourites": "Public page for one project. Only active projects are shown to the public "
        "(the designer and Platform Managers can also see hidden/archived ones). Opening the page records an "
        "`idp_view` row (not for the project's own designer, and not when only the property type is changed). "
        "The cost breakdown is the designer's lines (`IDPCostItem`) multiplied by "
        "property factor(selected type) / property factor(project's own type) from #47's active rule, plus 9% GST. "
        "Customers can save or remove the project from their favourites.",
    "Edit User Account": "The User Admin edits username, name, email, phone, profile and optionally a new password. "
        "Validation reuses #1's rules; the username must be unique among other accounts, and an admin cannot remove "
        "their own User Admin profile. Changed fields are written to the account's activity log.",
    "Manage User Profiles": "Lists the profiles with their number of accounts. New profiles can be created and "
        "existing ones edited or set Inactive. An inactive profile cannot be given to new accounts (#1 only lists "
        "active profiles) and its accounts cannot log in. The User Admin profile cannot be suspended.",
    "Manage Company Information + Designer Page": "The designer fills in company details (name required; UEN, phone, "
        "email and website format-checked). `CompanyProfile.saveCompanyProfile()` inserts or updates one row per "
        "designer. The details appear on the public designer page (with all active projects) and in the "
        "'About the designer' box on each project page.",
    "Manage Categories": "The Platform Manager creates categories (unique name, 2-40 characters), edits name, "
        "description and status, and deletes categories that no project uses. Renaming also renames the category's "
        "style multiplier in the estimation rules (#47). Designers' new-category requests (#11) are listed from the "
        "notification table.",
    "Platform Reports (daily / weekly / monthly)": "The period and date are validated and turned into a date range by "
        "`report_period` (shared with #50). `PlatformReport` counts new IDPs, new accounts, views, shortlists and "
        "reports in that range, plus a per-category table, and can export everything as CSV.",
    "Create User Account": "#1. The form lists the active profiles. `createUserAccount()` validates every field "
        "(required fields, username format and uniqueness, email, Singapore phone number, password policy, active "
        "profile) and lists all errors at once. The password is stored as a hash. If 'Email login credentials' is "
        "ticked, a notification is saved instead of sending a real email.",
    "View Account Activity Log": "#7. All current accounts are listed when the page opens; the keyword and role narrow "
        "the list. Selecting an account shows its log newest first. The log can be filtered by type and date range "
        "(dates are validated), exported as CSV, and the account suspended or reactivated (both are logged as "
        "Status Change). When there are no accounts or no log entries, `displayErrorMsg()` shows the message.",
    "Manage Project Categories": "#11. The designer ticks 1-5 active categories for one of their projects. "
        "`IDPCategory.replaceLinks()` saves them, then customers whose interests match are found "
        "(`CustomerPreference.findCustomersByCategories()`) and the project's recommendations are refreshed. "
        "Archived/hidden projects are not recommended. 'Request new category' notifies every Platform Manager.",
    "Manage Portfolio": "#13. Lists the designer's active (and hidden) projects with views and shortlist counts. Add "
        "Project and Edit validate the details, photos (JPG/PNG under 5 MB) and the cost breakdown lines; the total "
        "cost is the sum of the lines. Archive/Restore change the status (archived projects lose their "
        "recommendations). Delete removes the project and its links, but is blocked if users have reported it.",
    "Compare Favourite IDPs": "#27. The customer ticks 2-3 favourites. The controller checks the count, that they are in "
        "this customer's favourites and still comparable (active, floor area > 0). `IDPComparison.findBestValue()` "
        "marks the lowest cost per sqm (`IDP.getCostPerSqm()`).",
    "Generate Cost Breakdown": "#29. Uses #47's active rule. Each line = quantity x unit rate x property factor x style "
        "factor (`BreakdownItem.calculateLineTotal()`); subtotal, 9% GST and total are calculated by "
        "`CostBreakdown.calculateTotal()`. The breakdown is saved so #50 can count it.",
    "Manage Reports on Inappropriate IDPs": "#38. Pending reports are listed oldest first. The decision is validated "
        "(report still pending, decision is Hide IDP / Warn / Dismiss). Hide sets the IDP to Hidden (removing its "
        "recommendations), Warn sends the designer a warning; then the report is closed and the reporter and "
        "designer are notified.",
    "Category Health Report": "#40. For every category, `IDP.getCategoryStatistics()` counts active IDPs, interest "
        "(views + favourites in the last 30 days) and growth in new IDPs vs the previous 30 days. "
        "`CategoryHealth.calculateScore()` scales each measure against the highest category: "
        "40% IDPs + 40% interest + 20% growth, labelled Doing Well / Stable / At Risk / No data. Active categories "
        "can be flagged Under Review.",
    "Submit Report on a Project": "Input for #38. A logged-in customer clicks 'Report this project' on an active "
        "project. `SubmitReportController._validateReport()` checks the reason is from the list, the description "
        "is 1000 characters or fewer, the optional evidence is a JPG/PNG under 5 MB, and the customer has no "
        "pending report on the same project. `Report.createReport()` saves it as Pending and every Platform "
        "Manager gets a notification; the report then appears in #38 Reported IDPs.",
    "Create Cost Estimation Rules": "#47. The form starts from the active rule. The Sales Manager can edit each "
        "renovation item's name, unit and rate, remove items, or add new ones ('+ Add item'). Validation: rule "
        "name, at least one item, unique item names of 40 characters or fewer, a unit from the list, a positive "
        "rate, multipliers between 0.5 and 3.0, known styles. `_assignItemCodes()` keeps the code of existing "
        "items and makes a new, never-used code for new ones. `EstimationRule.saveRule()` saves everything and "
        "makes it the only active rule in one transaction. Old rules (and past breakdowns) keep their items.",
    "Export Sales Report": "#50. The period and date are validated; `report_period.calculateDateRange()` gives "
        "Monday-Sunday for weekly and the whole month for monthly. `SalesReportRow.findByDateRange()` builds one row "
        "per day from saved cost breakdowns, IDP views and favourites; `SalesReport` adds the totals and writes "
        "the CSV.",
}

SHARED = [  # (title, module, function/class names)
    ("Application setup (registers every page, role menus, error pages)", "app", ["create_app"]),
    ("Database connection and schema", "app.db", ["get_db", "close_db", "init_db"]),
    ("Login session and access control", "app.boundary.auth", ["load_logged_in_user", "login_required", "role_required"]),
    ("Shared report periods (#50 and Platform Reports)", "app.control.report_period", ["validatePeriod", "calculateDateRange"]),
]


def link(obj):
    """Markdown link to an object's source lines, relative to docs/."""
    obj = inspect.unwrap(obj)
    path = inspect.getsourcefile(obj)
    lines, start = inspect.getsourcelines(obj)
    end = start + len(lines) - 1
    rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
    return f"[`{rel}` L{start}-{end}](../{rel}#L{start}-L{end})"


def calls_in_order(fn):
    """Call nodes in a function body in the order they run: a call's arguments run before
    the call itself, so sort by where each call ends."""
    tree = ast.parse(textwrap.dedent(inspect.getsource(inspect.unwrap(fn))))
    nodes = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
    return sorted(nodes, key=lambda n: (n.end_lineno, n.end_col_offset))


def method_of(cls, name):
    fn = cls.__dict__.get(name)
    if isinstance(fn, staticmethod):
        fn = fn.__func__
    return fn if inspect.isfunction(fn) else None


def entity_method(module, attr, value):
    """Resolve an entity method call made inside `module`."""
    imported, _ = T.entity_calls(module)
    if isinstance(value, ast.Name) and value.id in T.ENTITIES and attr in T.ENTITIES[value.id].__dict__:
        return value.id, method_of(T.ENTITIES[value.id], attr)
    owners = [c for c in imported if attr in T.ENTITIES[c].__dict__]
    if len(owners) == 1:
        return owners[0], method_of(T.ENTITIES[owners[0]], attr)
    if attr in T.UNIQUE_METHODS:
        c = T.UNIQUE_METHODS[attr]
        return c, method_of(T.ENTITIES[c], attr)
    return None, None


def control_tree(ccls, cmod, name, depth, seen):
    fn = method_of(ccls, name)
    if fn is None or (ccls, name) in seen:
        return []
    seen = seen | {(ccls, name)}
    out = [f"{'  ' * depth}- <<control>> `{ccls.__name__}.{name}()` - {link(fn)}"]
    for call in calls_in_order(fn):
        f = call.func
        if not isinstance(f, ast.Attribute):
            continue
        if isinstance(f.value, ast.Name) and f.value.id == "self":
            out += control_tree(ccls, cmod, f.attr, depth + 1, seen)
            continue
        cname, efn = entity_method(cmod, f.attr, f.value)
        if efn is not None:
            out.append(f"{'  ' * (depth + 1)}- <<entity>> `{cname}.{f.attr}()` - {link(efn)}")
    return out


def boundary_tree(bcls, ccls, cmod, name, depth, seen):
    fn = method_of(bcls, name)
    if fn is None or (bcls, name) in seen:
        return []
    seen = seen | {(bcls, name)}
    out = [f"{'  ' * depth}- <<boundary>> `{bcls.__name__}.{name}()` - {link(fn)}"]
    for call in calls_in_order(fn):
        f = call.func
        if isinstance(f, ast.Name) and f.id == "render_template" and call.args and isinstance(call.args[0], ast.Constant):
            out.append(f"{'  ' * (depth + 1)}- page: `app/templates/{call.args[0].value}`")
        elif isinstance(f, ast.Attribute):
            v = f.value
            if isinstance(v, ast.Attribute) and v.attr == "controller":
                out += control_tree(ccls, cmod, f.attr, depth + 1, set())
            elif isinstance(v, ast.Name) and v.id == "self":
                out += boundary_tree(bcls, ccls, cmod, f.attr, depth + 1, seen)
    return out


def route_flows(app, bmod, ccls, cmod):
    bclasses = T.own_classes(bmod, "Pg")
    flows = []
    for verbs, url, endpoint in T.routes(app, bmod.bp.name):
        view = app.view_functions[f"{bmod.bp.name}.{endpoint}"]
        lines = [f"**{verbs} `{url}`** - route `{endpoint}()` {link(view)}", ""]
        for call in calls_in_order(view):
            f = call.func
            if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Call) and isinstance(f.value.func, ast.Name):
                cls = next((c for c in bclasses if c.__name__ == f.value.func.id), None)
                if cls:
                    lines += boundary_tree(cls, ccls, cmod, f.attr, 0, set())
            elif isinstance(f, ast.Name) and hasattr(bmod, f.id) and inspect.isfunction(getattr(bmod, f.id)) \
                    and f.id.startswith("_") and f.id not in ("_ids", "_num", "_fill", "_cost_items"):
                helper = getattr(bmod, f.id)
                lines.append(f"- helper `{f.id}()` - {link(helper)}")
                for c2 in calls_in_order(helper):
                    if isinstance(c2.func, ast.Attribute) and isinstance(c2.func.value, ast.Attribute) \
                            and c2.func.value.attr == "controller":
                        lines += control_tree(ccls, cmod, c2.func.attr, 1, set())
        if len(lines) == 2:
            lines.append("- (renders or redirects directly)")
        flows.append("\n".join(lines))
    return flows


def test_links(tfile):
    mod = importlib.import_module(f"tests.{tfile[:-3]}")
    rows = []
    for name, fn in inspect.getmembers(mod, inspect.isfunction):
        if name.startswith("test_") and fn.__module__ == mod.__name__:
            _, start = inspect.getsourcelines(fn)
            rows.append((start, name, fn))
    return [f"`{n}` ({link(fn).split('](')[0][1:].split('` ')[1]})" for _, n, fn in sorted(rows)]


def main():
    app = create_app({"TESTING": True})
    out = ["# Code walkthrough: where each feature lives and how it flows", "",
           "Generated by `python scripts/walkthrough.py`. Line numbers come from the code itself, so re-run the script "
           "after changing code. Click a link to open the file at those lines (works on GitHub and in VS Code).", "",
           "## How every request flows", "",
           "1. The browser requests a URL. Flask finds the **route function** in the story's file in `app/boundary/`.",
           "2. The route checks the user's role (`role_required`) and calls the story's **boundary** class "
           "(`...Pg`), which reads the form.",
           "3. The boundary calls the **control** class (`...Controller`) in `app/control/`, which validates the input "
           "and applies the business rules.",
           "4. The controller calls **entity** classes in `app/entity/`, which read and write the SQLite database "
           "(tables in `app/schema.sql`).",
           "5. The result goes back to the boundary, which renders an HTML **page** from `app/templates/` "
           "(or a success/error message, or a CSV download).", "",
           "In the flows below, each line is one method call, indented under the method that calls it, in the order "
           "the calls run. Where a step can succeed or fail (e.g. `displaySuccessPg()` / `displayErrorMsg()`), both "
           "paths are listed - only one runs, depending on the controller's result.", "",
           "## Shared code", ""]
    for title, modname, names in SHARED:
        mod = importlib.import_module(modname)
        out.append(f"- **{title}:** " + "; ".join(f"`{n}()` {link(getattr(mod, n))}" for n in names))
    out += ["- **Roles, status values, renovation items and menus:** `app/constants.py`",
            "- **Database tables:** `app/schema.sql`", "- **Test data:** `scripts/generate_test_data.py`", ""]
    out += ["## Contents", ""] + [f"- [{(s[0] + ' ') if s[0] != '-' else ''}{s[1]}]"
                                   f"(#{(s[0].strip('#') + '-') if s[0] != '-' else ''}"
                                   f"{s[1].lower().replace(' ', '-').replace('/', '').replace('+', '').replace('(', '').replace(')', '').replace(',', '')})"
                                   for s in T.STORIES] + [""]
    for sid, name, actor, bm, cm, tfile in T.STORIES:
        b = importlib.import_module(f"app.boundary.{bm}")
        c = importlib.import_module(f"app.control.{cm}")
        ccls = T.own_class(c, "Controller")
        title = f"{sid.strip('#')} {name}" if sid != "-" else name
        out += [f"## {title}", "", f"**Actor:** {actor}", "", NOTES.get(name, ""), "",
                "**Classes**", ""]
        out += [f"- <<boundary>> `{x.__name__}` - {link(x)}" for x in T.own_classes(b, "Pg")]
        out += [f"- <<control>> `{ccls.__name__}` - {link(ccls)}"]
        ents, _ = T.entity_calls(c)
        out += [f"- <<entity>> `{e}` - {link(T.ENTITIES[e])}" for e in sorted(ents)]
        out += ["", "**Flow of each page (in call order)**", ""]
        for flow in route_flows(app, b, ccls, c):
            out += [flow, ""]
        out += [f"**Unit tests:** `tests/{tfile}`", ""]
        out += [f"- {t}" for t in test_links(tfile)] + [""]
    with open(os.path.join(DOC_DIR, "CODE_WALKTHROUGH.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print("Written docs/CODE_WALKTHROUGH.md")


if __name__ == "__main__":
    main()
