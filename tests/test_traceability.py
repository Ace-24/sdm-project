"""Keeps docs/TRACEABILITY.md honest: every story in the matrix must have its
boundary class, control class, routes and test file."""
import importlib
import os
import pytest
from scripts import traceability as t


@pytest.mark.parametrize("story", t.STORIES, ids=[s[0] + " " + s[1] for s in t.STORIES])
def test_story_has_bce_classes_routes_and_tests(app, story):
    sid, name, actor, bmod, cmod, tfile = story
    b = importlib.import_module(f"app.boundary.{bmod}")
    c = importlib.import_module(f"app.control.{cmod}")
    assert t.own_class(b, "Pg") and t.own_class(c, "Controller")
    assert t.routes(app, b.bp.name), f"{name} has no pages"
    assert os.path.exists(os.path.join(t.ROOT, "tests", tfile))


@pytest.mark.parametrize("story", t.STORIES, ids=[s[0] + " " + s[1] for s in t.STORIES])
def test_walkthrough_can_trace_every_page(app, story):
    """docs/CODE_WALKTHROUGH.md: every page of every story has a traceable flow and an explanation."""
    from scripts import walkthrough as w
    sid, name, actor, bmod, cmod, tfile = story
    b = importlib.import_module(f"app.boundary.{bmod}")
    c = importlib.import_module(f"app.control.{cmod}")
    flows = w.route_flows(app, b, t.own_class(c, "Controller"), c)
    assert flows and all("<<boundary>>" in f or "helper" in f or "directly" in f for f in flows)
    assert w.NOTES.get(name), f"No explanation written for {name}"
