"""Generate docs/TRACEABILITY.md - which code implements each user story.

Usage:  python scripts/traceability.py

Everything is read from the code itself (classes, methods, Flask routes,
templates, entity calls, tests), so the table always matches the code.
"""
import ast
import importlib
import inspect
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app import create_app  # noqa: E402

# (story id, story name, actor, boundary module, control module, test file)
STORIES = [
    ("-", "Login / Logout", "All users", "login_page", "login_controller", "test_login.py"),
    ("-", "Sign Up", "Visitor", "sign_up_page", "sign_up_controller", "test_sign_up_and_interests.py"),
    ("-", "Choose Interests", "Customer", "choose_preferences_page", "choose_preferences_controller",
     "test_sign_up_and_interests.py"),
    ("-", "Browse / Search Projects", "Anyone", "browse_idp_page", "browse_idp_controller",
     "test_browse_and_view_idp.py"),
    ("-", "View Project + Save to Favourites", "Anyone / Customer", "view_idp_page", "view_idp_controller",
     "test_browse_and_view_idp.py"),
    ("#1", "Create User Account", "User Admin", "create_user_account_page", "create_user_account_controller",
     "test_us01_create_user_account.py"),
    ("#7", "View Account Activity Log", "User Admin", "view_activity_log_page", "view_activity_log_controller",
     "test_us07_view_activity_log.py"),
    ("-", "Edit User Account", "User Admin", "edit_user_account_page", "edit_user_account_controller",
     "test_account_and_profile_management.py"),
    ("-", "Manage User Profiles", "User Admin", "manage_user_profiles_page", "manage_user_profiles_controller",
     "test_account_and_profile_management.py"),
    ("-", "Manage Company Information + Designer Page", "Interior Designer / Anyone", "company_profile_page",
     "manage_company_profile_controller", "test_company_profile.py"),
    ("-", "Manage Categories", "Platform Manager", "manage_categories_page", "manage_categories_controller",
     "test_category_management_and_platform_report.py"),
    ("-", "Submit Report on a Project", "Customer", "submit_report_page", "submit_report_controller",
     "test_submit_report.py"),
    ("-", "Platform Reports (daily / weekly / monthly)", "Platform Manager", "platform_report_page",
     "platform_report_controller", "test_category_management_and_platform_report.py"),
    ("#11", "Manage Project Categories", "Interior Designer", "manage_project_categories_page",
     "manage_project_categories_controller", "test_us11_manage_project_categories.py"),
    ("#13", "Manage Portfolio", "Interior Designer", "manage_portfolio_page", "manage_portfolio_controller",
     "test_us13_manage_portfolio.py"),
    ("#27", "Compare Favourite IDPs", "Customer", "compare_favourites_page", "compare_favourites_controller",
     "test_us27_compare_favourites.py"),
    ("#29", "Generate Cost Breakdown", "Customer", "cost_breakdown_page", "generate_cost_breakdown_controller",
     "test_us29_generate_cost_breakdown.py"),
    ("#38", "Manage Reports on Inappropriate IDPs", "Platform Manager", "manage_reports_page",
     "manage_reports_controller", "test_us38_manage_reports.py"),
    ("#40", "Category Health Report", "Platform Manager", "category_health_page", "category_health_controller",
     "test_us40_category_health.py"),
    ("#47", "Create Cost Estimation Rules", "Sales Manager", "estimation_rule_page",
     "create_estimation_rule_controller", "test_us47_create_estimation_rule.py"),
    ("#50", "Export Sales Report", "Sales Manager", "sales_report_page", "export_sales_report_controller",
     "test_us50_export_sales_report.py"),
]


def rel(path):
    return os.path.relpath(path, ROOT).replace(os.sep, "/")


def own_classes(module, suffix):
    """Classes ending in `suffix` defined in the module, in source order."""
    found = [obj for name, obj in inspect.getmembers(module, inspect.isclass)
             if obj.__module__ == module.__name__ and name.endswith(suffix)]
    if not found:
        raise LookupError(f"No *{suffix} class in {module.__name__}")
    return sorted(found, key=lambda c: inspect.getsourcelines(c)[1])


def own_class(module, suffix):
    return own_classes(module, suffix)[0]


def methods(cls):
    """'+ name(params)' for public, '- name(params)' for private (leading underscore)."""
    out = []
    for name, fn in cls.__dict__.items():
        if isinstance(fn, staticmethod):
            fn = fn.__func__
        if not inspect.isfunction(fn) or name.startswith("__"):
            continue
        params = [p for p in inspect.signature(fn).parameters if p != "self"]
        vis = "-" if name.startswith("_") else "+"
        out.append(f"{vis} {name.lstrip('_')}({', '.join(params)})")
    return out


def entity_classes():
    """All <<entity>> classes in app/entity: {class name: class}."""
    found = {}
    folder = os.path.join(ROOT, "app", "entity")
    for f in sorted(os.listdir(folder)):
        if f.endswith(".py") and f not in ("__init__.py", "base.py"):
            mod = importlib.import_module(f"app.entity.{f[:-3]}")
            for name, obj in inspect.getmembers(mod, inspect.isclass):
                if obj.__module__ == mod.__name__:
                    found[name] = obj
    return found


ENTITIES = entity_classes()

# Methods that exist in only one entity class, so a call like h.calculateScore()
# can be traced to CategoryHealth even when the class is not imported directly.
_OWNERS = {}
for _cname, _cls in ENTITIES.items():
    for _m in _cls.__dict__:
        if not _m.startswith("__"):
            _OWNERS.setdefault(_m, set()).add(_cname)
UNIQUE_METHODS = {m: next(iter(c)) for m, c in _OWNERS.items() if len(c) == 1}

# Entity classes created inside other entity methods (not visible from the controller)
CREATED_BY_ENTITY = {"CostBreakdown": ["BreakdownItem"], "SalesReport": [], "IDP": []}


def entity_calls(module):
    """Entity methods the module uses: Class.method(...) calls, plus obj.method(...)
    calls where the method belongs to an entity class imported by the module."""
    tree = ast.parse(inspect.getsource(module))
    imported = {a.asname or a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
                and (n.module or "").startswith("app.entity") for a in n.names}
    imported = {c for c in imported if c in ENTITIES}
    by_method = {}
    for cname in imported:
        for m in ENTITIES[cname].__dict__:
            if not m.startswith("__"):
                by_method.setdefault(m, set()).add(cname)
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            attr, value = node.func.attr, node.func.value
            if isinstance(value, ast.Name) and value.id in imported and attr in ENTITIES[value.id].__dict__:
                calls.add(f"{value.id}.{attr}()")
            elif attr in by_method:
                for cname in by_method[attr]:
                    calls.add(f"{cname}.{attr}()")
            elif attr in UNIQUE_METHODS and not attr.startswith("_"):
                calls.add(f"{UNIQUE_METHODS[attr]}.{attr}()")
                imported.add(UNIQUE_METHODS[attr])
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in imported:
            calls.add(f"new {node.func.id}()")
    return imported, calls


def templates(module):
    return sorted(set(re.findall(r'render_template\("([^"]+)"', inspect.getsource(module))))


def routes(app, bp_name):
    out = []
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
        if rule.endpoint.startswith(bp_name + "."):
            verbs = ",".join(sorted(m for m in rule.methods if m in ("GET", "POST")))
            out.append((verbs, rule.rule, rule.endpoint.split(".", 1)[1]))
    return out


def count_tests(path):
    with open(path, encoding="utf-8") as f:
        return len(re.findall(r"^def test_", f.read(), re.M))


def main():
    app = create_app({"TESTING": True})
    lines = ["# Traceability: user stories to code", "",
             "Generated by `python scripts/traceability.py` from the code itself, so it always matches the code.",
             "Each story follows the same Boundary-Control-Entity (BCE) structure as its class and sequence diagrams.",
             "", "## Summary", "",
             "| Story | Name | Actor | <<boundary>> | <<control>> | <<entity>> classes used | Tests |",
             "|---|---|---|---|---|---|---|"]
    details = []
    total_tests = 0
    counted = set()
    for sid, name, actor, bmod, cmod, tfile in STORIES:
        b = importlib.import_module(f"app.boundary.{bmod}")
        c = importlib.import_module(f"app.control.{cmod}")
        bclasses, ccls = own_classes(b, "Pg"), own_class(c, "Controller")
        bcls = bclasses[0]
        bnames = ", ".join(f"`{x.__name__}`" for x in bclasses)
        ents_c, calls_c = entity_calls(c)
        ents_b, calls_b = entity_calls(b)
        ents = set(ents_c | ents_b)
        for e in list(ents):
            ents.update(CREATED_BY_ENTITY.get(e, []))
        if any(call.startswith("IDP.getCategoryStatistics") for call in calls_c):
            ents.add("CategoryHealth")          # returned by IDP.getCategoryStatistics()
        ents = sorted(ents)
        tpath = os.path.join(ROOT, "tests", tfile)
        n = count_tests(tpath)
        if tfile not in counted:
            total_tests += n
            counted.add(tfile)
        lines.append(f"| {sid} | {name} | {actor} | {bnames} | `{ccls.__name__}` | "
                     f"{', '.join('`%s`' % e for e in ents) or '-'} | {n} |")

        d = [f"## {sid} {name}" if sid != "-" else f"## {name}", "", f"**Actor:** {actor}", "",
             "| Layer | Class | File |", "|---|---|---|",
             *[f"| <<boundary>> | `{x.__name__}` | `{rel(inspect.getsourcefile(b))}` |" for x in bclasses],
             f"| <<control>> | `{ccls.__name__}` | `{rel(inspect.getsourcefile(c))}` |"]
        for e in ents:
            d.append(f"| <<entity>> | `{e}` | `{rel(inspect.getsourcefile(ENTITIES[e]))}` |")
        for x in bclasses:
            d += ["", f"**`{x.__name__}` methods (boundary)**", ""] + [f"- `{m}`" for m in methods(x)]
        d += ["", f"**`{ccls.__name__}` methods (control)**", ""] + [f"- `{m}`" for m in methods(ccls)]
        used = sorted(calls_c | calls_b)
        d += ["", "**Entity methods used**", ""] + ([f"- `{m}`" for m in used] or ["- none"])
        d += ["", "**Pages (URL routes)**", "", "| HTTP | URL | Route function |", "|---|---|---|"]
        d += [f"| {v} | `{u}` | `{f}` |" for v, u, f in routes(app, b.bp.name)]
        tpls = templates(b)
        d += ["", "**Templates:** " + (", ".join(f"`app/templates/{t}`" for t in tpls) or "-")]
        d += ["", f"**Unit tests:** `tests/{tfile}` ({n} tests)", ""]
        details.append("\n".join(d))

    lines += ["", f"Total: **{total_tests}** test functions for these stories, plus "
              "`tests/test_generate_test_data.py` for the test data. pytest reports a higher number because "
              "parameterised tests run once per input value.", "",
              "### Naming between design and code", "",
              "- Class names use capitalised words (e.g. design `createUserAccountPg` = code `CreateUserAccountPg`).",
              "- Method names match the diagrams exactly (e.g. `displayCreateUAForm()`, `createUserAccount()`).",
              "- Private methods (`-` in the class diagram) start with `_` in Python, e.g. `_validateAccountDetails()`.",
              "- Route functions in each boundary file have the same names as the boundary methods they call.", ""]
    out = os.path.join(ROOT, "docs", "TRACEABILITY.md")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n" + "\n".join(details))
    print("Written", rel(out))


if __name__ == "__main__":
    main()
