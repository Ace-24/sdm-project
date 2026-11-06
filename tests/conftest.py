"""Shared pytest fixtures: a fresh app + database for every test."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest                                   # noqa: E402
from app import create_app                      # noqa: E402
from app.db import init_db, get_db              # noqa: E402
from scripts.init_db import create_profiles, create_demo_accounts, create_starter_rule, DEMO_PASSWORD  # noqa: E402


@pytest.fixture
def app(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.db"), "SECRET_KEY": "test"})
    with app.app_context():
        init_db()
        db = get_db()
        create_profiles(db)
        create_demo_accounts(db)
        create_starter_rule(db)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def ctx(app):
    """Run a test inside an application context (for entity/controller tests)."""
    with app.app_context():
        yield


def login(client, username, password=DEMO_PASSWORD):
    return client.post("/login", data={"username": username, "password": password})
