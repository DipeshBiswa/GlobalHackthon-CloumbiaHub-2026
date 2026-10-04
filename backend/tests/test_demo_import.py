"""Bundled demo startup works without regenerating feedback or replacing owner data."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import socket
import sqlite3
from threading import Barrier

import pytest


DATA = Path(__file__).resolve().parents[1] / "data" / "synthetic"
MARKER = "noor_demo_seed_v1"


@pytest.fixture
def demo_store(tmp_path, monkeypatch):
    import store

    monkeypatch.setattr(store, "DB_PATH", tmp_path / "demo.db")
    store.initialize()
    with store.connect() as db:
        db.executemany(
            "INSERT INTO users(id,username,password_hash,display_name,pin_hash) VALUES(?,?,?,?,?)",
            [
                ("local-owner", "noor", "password-hash", "Noor", "pin-hash"),
                ("other-owner", "another-farm", "password-hash", "Another farm", "pin-hash"),
            ],
        )
    return store


def stored_rows(store, table):
    with store.connect() as db:
        return [dict(row) for row in db.execute(f"SELECT * FROM {table} ORDER BY id")]


def marker(store):
    with store.connect() as db:
        row = db.execute("SELECT value FROM app_metadata WHERE key=?", (MARKER,)).fetchone()
    return row[0] if row else None


def test_bundled_demo_preserves_processed_records_without_models_or_network(demo_store, monkeypatch):
    import review_pipeline
    from demo_data import seed_bundled_demo

    def forbidden(*args, **kwargs):
        raise AssertionError("Bundled reviews must be imported without models or network access")

    monkeypatch.setattr(review_pipeline, "process_review", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    assert seed_bundled_demo("local-owner") is True

    expected_reviews = json.loads((DATA / "noor_reviews.json").read_text(encoding="utf-8"))
    expected_plans = json.loads((DATA / "noor_plans.json").read_text(encoding="utf-8"))
    review_rows = stored_rows(demo_store, "reviews")
    plan_rows = stored_rows(demo_store, "plans")
    assert len(review_rows) == 225
    assert len(plan_rows) == 1
    assert {row["user_id"] for row in review_rows + plan_rows} == {"local-owner"}
    assert {row["id"]: json.loads(row["data"]) for row in review_rows} == {
        review["id"]: review for review in expected_reviews
    }
    assert {row["id"]: json.loads(row["data"]) for row in plan_rows} == {
        plan["id"]: {**plan, "user_id": "local-owner"} for plan in expected_plans
    }
    assert all(row["created_at"] == json.loads(row["data"])["created_at"] and not row["deleted"] for row in review_rows)
    assert marker(demo_store) == "imported"


def test_imported_demo_retains_actionable_patterns_and_plan_progress(demo_store):
    from demo_data import seed_bundled_demo
    from echo_analytics import patterns, progress

    seed_bundled_demo("local-owner")
    reviews = demo_store.records("reviews", "local-owner")
    plans = demo_store.records("plans", "local-owner")
    groups = {item["key"]: item for item in patterns(reviews)}
    assert groups["coffee_tasting:negative"]["supporting_review_count"] == 12
    assert groups["coffee_tasting:negative"]["pattern_confidence"] == "high"
    assert groups["group_size:negative"]["supporting_review_count"] == 4
    assert groups["group_size:negative"]["pattern_confidence"] == "medium"
    assert "facilities:request" not in groups
    assert sum(any(topic["topic"] == "facilities" and topic["sentiment"] == "request" for topic in review["topics"]) for review in reviews) == 2
    assert progress(plans[0], reviews)["res"] == "better"


def test_repeat_start_preserves_review_edits_deletions_and_plan_status(demo_store):
    from demo_data import seed_bundled_demo

    assert seed_bundled_demo("local-owner") is True
    reviews = demo_store.records("reviews", "local-owner")
    edited = {**reviews[0], "favorite_en": "Owner corrected this visitor's feedback", "favorite_sw": "Maoni yaliyorekebishwa"}
    deleted = {**reviews[1], "deleted": True}
    plan = {**demo_store.records("plans", "local-owner")[0], "status": "done"}
    demo_store.put("reviews", edited, "local-owner")
    demo_store.put("reviews", deleted, "local-owner")
    demo_store.put("plans", plan, "local-owner")
    before = (stored_rows(demo_store, "reviews"), stored_rows(demo_store, "plans"))

    assert seed_bundled_demo("local-owner") is False
    assert (stored_rows(demo_store, "reviews"), stored_rows(demo_store, "plans")) == before
    assert len(demo_store.records("reviews", "local-owner")) == 224


def test_clearing_seeded_rows_does_not_repopulate_on_next_start(demo_store):
    from demo_data import seed_bundled_demo

    seed_bundled_demo("local-owner")
    with demo_store.connect() as db:
        db.execute("DELETE FROM reviews WHERE user_id='local-owner'")
        db.execute("DELETE FROM plans WHERE user_id='local-owner'")
    assert seed_bundled_demo("local-owner") is False
    assert demo_store.records("reviews", "local-owner") == []
    assert demo_store.records("plans", "local-owner") == []
    assert marker(demo_store) == "imported"


@pytest.mark.parametrize("table,deleted,synthetic", [
    ("reviews", False, False),
    ("reviews", True, False),
    ("reviews", False, True),
    ("plans", False, False),
    ("plans", False, True),
])
def test_existing_account_data_is_never_replaced_or_mixed_with_demo(demo_store, table, deleted, synthetic):
    from demo_data import seed_bundled_demo

    record = {
        "id": "existing-record", "created_at": "2026-01-01T10:00:00+00:00",
        "deleted": deleted, "is_synthetic": synthetic, "topics": [], "status": "trying",
    }
    demo_store.put(table, record, "local-owner")
    before = (stored_rows(demo_store, "reviews"), stored_rows(demo_store, "plans"))
    assert seed_bundled_demo("local-owner") is False
    assert (stored_rows(demo_store, "reviews"), stored_rows(demo_store, "plans")) == before
    assert marker(demo_store) == "skipped-existing-data"

    # A later cleanup must not cause previously declined demo data to reappear.
    with demo_store.connect() as db:
        db.execute(f"DELETE FROM {table} WHERE user_id='local-owner'")
    assert seed_bundled_demo("local-owner") is False
    assert demo_store.records("reviews", "local-owner") == []
    assert demo_store.records("plans", "local-owner") == []


def test_demo_is_restricted_to_noor_and_other_owners_remain_isolated(demo_store):
    from demo_data import seed_bundled_demo

    other_review = {"id": "other-review", "created_at": "2026-01-01", "topics": [], "deleted": False}
    other_plan = {"id": "other-plan", "status": "trying"}
    demo_store.put("reviews", other_review, "other-owner")
    demo_store.put("plans", other_plan, "other-owner")
    with demo_store.connect() as db:
        db.execute("INSERT INTO decisions VALUES('other-owner','guide_quality:positive')")
    before_review = demo_store.records("reviews", "other-owner")
    before_plan = demo_store.records("plans", "other-owner")

    with pytest.raises(ValueError, match="noor"):
        seed_bundled_demo("other-owner")
    assert marker(demo_store) is None
    assert seed_bundled_demo("local-owner") is True
    assert demo_store.records("reviews", "other-owner") == before_review
    assert demo_store.records("plans", "other-owner") == before_plan
    with demo_store.connect() as db:
        assert [tuple(row) for row in db.execute("SELECT * FROM decisions")] == [("other-owner", "guide_quality:positive")]


def test_account_with_only_prior_decisions_is_preserved(demo_store):
    from demo_data import seed_bundled_demo

    with demo_store.connect() as db:
        db.execute("INSERT INTO decisions VALUES('local-owner','coffee_tasting:negative')")
    assert seed_bundled_demo("local-owner") is False
    assert marker(demo_store) == "skipped-existing-data"
    assert demo_store.records("reviews", "local-owner") == []
    assert demo_store.records("plans", "local-owner") == []
    with demo_store.connect() as db:
        assert [tuple(row) for row in db.execute("SELECT * FROM decisions")] == [("local-owner", "coffee_tasting:negative")]


def test_invalid_bundle_leaves_account_empty_and_can_be_retried(demo_store, tmp_path, monkeypatch):
    import demo_data

    bundle = tmp_path / "invalid-bundle"
    bundle.mkdir()
    (bundle / "noor_reviews.json").write_text((DATA / "noor_reviews.json").read_text(encoding="utf-8"), encoding="utf-8")
    (bundle / "noor_plans.json").write_text('{"not": "a list"}', encoding="utf-8")
    monkeypatch.setattr(demo_data, "BUNDLE_DIR", bundle)
    with pytest.raises(ValueError, match="must contain a list"):
        demo_data.seed_bundled_demo("local-owner")
    assert demo_store.records("reviews", "local-owner") == []
    assert demo_store.records("plans", "local-owner") == []
    assert marker(demo_store) is None
    monkeypatch.setattr(demo_data, "BUNDLE_DIR", DATA)
    assert demo_data.seed_bundled_demo("local-owner") is True


def test_plan_id_collision_rolls_back_all_review_inserts(demo_store):
    from demo_data import seed_bundled_demo

    bundled_plan = json.loads((DATA / "noor_plans.json").read_text(encoding="utf-8"))[0]
    existing_plan = {"id": bundled_plan["id"], "status": "done", "description": "Another owner's own plan"}
    demo_store.put("plans", existing_plan, "other-owner")
    with pytest.raises(sqlite3.IntegrityError):
        seed_bundled_demo("local-owner")
    assert demo_store.records("reviews", "local-owner") == []
    assert demo_store.records("plans", "local-owner") == []
    assert demo_store.records("plans", "other-owner") == [existing_plan]
    assert marker(demo_store) is None


def test_simultaneous_starts_import_exactly_once(demo_store):
    from demo_data import seed_bundled_demo

    started = Barrier(2)

    def start():
        started.wait(timeout=10)
        return seed_bundled_demo("local-owner")

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: start(), range(2)))
    assert sorted(results) == [False, True]
    assert len(demo_store.records("reviews", "local-owner")) == 225
    assert len(demo_store.records("plans", "local-owner")) == 1


def test_simultaneous_initialization_creates_one_account_and_one_demo(tmp_path, monkeypatch):
    import echo_api
    import store

    monkeypatch.setattr(store, "DB_PATH", tmp_path / "concurrent-startup.db")
    monkeypatch.setenv("ECHO_SEED_DEMO", "1")
    started = Barrier(2)
    passwords_ready = Barrier(2)
    hash_secret = echo_api.hash_secret

    def synchronized_hash(value):
        hashed = hash_secret(value)
        if value == "coffee2025":
            # Both startup workers have observed the missing account before
            # either can finish preparing its insert, making the race explicit.
            passwords_ready.wait(timeout=10)
        return hashed

    monkeypatch.setattr(echo_api, "hash_secret", synchronized_hash)

    def start():
        started.wait(timeout=10)
        echo_api.initialize()

    with ThreadPoolExecutor(max_workers=2) as executor:
        list(executor.map(lambda _: start(), range(2)))

    with store.connect() as db:
        users = db.execute("SELECT id FROM users WHERE username='noor'").fetchall()
        assert len(users) == 1
        assert db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
    assert len(store.records("reviews", users[0]["id"])) == 225
    assert len(store.records("plans", users[0]["id"])) == 1
    assert marker(store) == "imported"


def test_startup_seeds_by_default_and_opt_out_can_be_enabled_later(tmp_path, monkeypatch):
    import echo_api
    import store

    monkeypatch.setattr(store, "DB_PATH", tmp_path / "startup.db")
    monkeypatch.setenv("ECHO_SEED_DEMO", "0")
    echo_api.initialize()
    with store.connect() as db:
        owner_id = db.execute("SELECT id FROM users WHERE username='noor'").fetchone()[0]
    assert store.records("reviews", owner_id) == []
    assert store.records("plans", owner_id) == []
    assert marker(store) is None

    monkeypatch.delenv("ECHO_SEED_DEMO")
    echo_api.initialize()
    assert len(store.records("reviews", owner_id)) == 225
    assert len(store.records("plans", owner_id)) == 1
    assert marker(store) == "imported"


def test_explicit_startup_option_overrides_environment(tmp_path, monkeypatch):
    import echo_api
    import store

    monkeypatch.setattr(store, "DB_PATH", tmp_path / "explicit-startup.db")
    monkeypatch.delenv("ECHO_SEED_DEMO", raising=False)
    echo_api.initialize(seed_demo=False)
    with store.connect() as db:
        owner_id = db.execute("SELECT id FROM users WHERE username='noor'").fetchone()[0]
    assert store.records("reviews", owner_id) == []

    monkeypatch.setenv("ECHO_SEED_DEMO", "0")
    echo_api.initialize(seed_demo=True)
    assert len(store.records("reviews", owner_id)) == 225
    assert len(store.records("plans", owner_id)) == 1
