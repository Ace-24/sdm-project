"""Checks that the test data generator meets the spec (about 100 records per
data type) and that the data is consistent for the user stories."""
import pytest
from app import create_app
from app.db import get_db, init_db
from scripts.generate_test_data import generate


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    """Generate the data once and share it with every test in this file."""
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path_factory.mktemp("gen") / "gen.db")})
    with app.app_context():
        init_db()
        result = generate(get_db(), seed=42)
    return app, result


@pytest.fixture
def counts(generated):
    app, result = generated
    with app.app_context():
        yield result


def q(sql):
    return get_db().execute(sql).fetchall()


@pytest.mark.parametrize("table", ["user_account", "activity_log", "idp", "idp_cost_item", "idp_category", "customer_preference",
                                   "recommendation", "favourite", "idp_view", "cost_breakdown", "breakdown_item",
                                   "rule_factor"])
def test_at_least_100_records(counts, table):
    assert counts[table] >= 100


def test_fixed_size_tables(counts):
    assert counts["user_profile"] == 5
    assert counts["category"] == 30
    assert counts["report"] == 40
    assert counts["estimation_rule"] == 3


def test_exactly_one_active_estimation_rule(counts):
    assert q("SELECT COUNT(*) FROM estimation_rule WHERE is_active = 1")[0][0] == 1


def test_every_rule_has_a_rate_for_every_item(counts):
    rows = q("SELECT rule_id, COUNT(*) FROM unit_rate GROUP BY rule_id")
    assert [r[1] for r in rows] == [12, 12, 12]


def test_favourites_only_on_active_idps(counts):
    assert q("SELECT COUNT(*) FROM favourite f JOIN idp i ON i.idp_id = f.idp_id WHERE i.status != 'Active'")[0][0] == 0


def test_breakdown_totals_add_up(counts):
    bad = q("SELECT COUNT(*) FROM cost_breakdown b WHERE "
            "ABS(b.subtotal - (SELECT SUM(line_total) FROM breakdown_item WHERE breakdown_id = b.breakdown_id)) > 0.01 "
            "OR ABS(b.total - (b.subtotal + b.gst)) > 0.01")
    assert bad[0][0] == 0


def test_demo_accounts_have_data_to_demo(counts):
    assert q("SELECT COUNT(*) FROM favourite f JOIN user_account a ON a.account_id = f.customer_id "
             "WHERE a.username = 'customer'")[0][0] >= 2           # #27 needs 2+ favourites
    assert q("SELECT COUNT(*) FROM idp i JOIN user_account a ON a.account_id = i.designer_id "
             "WHERE a.username = 'designer'")[0][0] >= 1            # #11, #13 need IDPs
    assert q("SELECT COUNT(*) FROM report WHERE status = 'Pending'")[0][0] >= 1   # #38


def test_activity_dates_cover_last_90_days(counts):
    lo, hi = q("SELECT MIN(viewed_date), MAX(viewed_date) FROM idp_view")[0]
    assert lo < hi
    assert q("SELECT COUNT(*) FROM idp_view WHERE viewed_date > datetime('now', 'localtime')")[0][0] == 0


def test_idp_total_cost_matches_its_breakdown(counts):
    bad = q("SELECT COUNT(*) FROM idp i WHERE ABS(i.total_cost - (SELECT SUM(quantity * unit_rate) "
            "FROM idp_cost_item WHERE idp_id = i.idp_id)) > 0.05")
    assert bad[0][0] == 0


def test_no_activity_in_the_future(counts):
    assert q("SELECT COUNT(*) FROM activity_log WHERE timestamp > datetime('now', 'localtime', '+1 minute')")[0][0] == 0


def test_same_seed_gives_same_data(ctx):
    init_db()
    first = generate(get_db(), seed=7)
    init_db()
    second = generate(get_db(), seed=7)
    assert first == second


def test_every_designer_has_company_information(counts):
    missing = q("SELECT COUNT(*) FROM user_account a JOIN user_profile p ON p.profile_id = a.profile_id "
                "WHERE p.profile_name = 'Interior Designer' AND a.account_id NOT IN (SELECT designer_id FROM company_profile)")
    assert missing[0][0] == 0
