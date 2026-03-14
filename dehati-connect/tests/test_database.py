"""
tests/test_database.py — Integration tests for the database layer.

Uses a temporary SQLite file so they never pollute the production DB.
"""

import os
import sys
import tempfile
import pytest

# Point the module at a temp DB before importing
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()
os.environ["DEHATI_DB"] = _tmp_db.name

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import database as db


@pytest.fixture(autouse=True)
def fresh_db():
    """Wipe and re-initialise the database before each test."""
    db.DB_PATH = _tmp_db.name
    # Drop all tables and recreate
    conn = __import__("sqlite3").connect(_tmp_db.name)
    conn.execute("DROP TABLE IF EXISTS ratings")
    conn.execute("DROP TABLE IF EXISTS sms_log")
    conn.execute("DROP TABLE IF EXISTS workers")
    conn.commit()
    conn.close()
    db.init_db()
    yield


# ---------------------------------------------------------------------------
# register_worker
# ---------------------------------------------------------------------------

class TestRegisterWorker:
    def test_insert_new_worker(self):
        row_id = db.register_worker("Ram", "+91100", "ramnagar", "tractor mechanic", "tractor,mechanic")
        assert row_id > 0

    def test_duplicate_phone_returns_zero(self):
        db.register_worker("Ram", "+91100", "ramnagar", "tractor mechanic", "tractor,mechanic")
        row_id = db.register_worker("Ram2", "+91100", "elsewhere", "plumber", "plumber")
        assert row_id == 0

    def test_multiple_workers(self):
        for i in range(5):
            db.register_worker(f"Worker{i}", f"+9110{i}", "patna", "plumber", "plumber")
        with db.get_db() as conn:
            count = conn.execute("SELECT COUNT(*) FROM workers").fetchone()[0]
        assert count == 5


# ---------------------------------------------------------------------------
# search_workers
# ---------------------------------------------------------------------------

class TestSearchWorkers:
    def _seed(self):
        db.register_worker("Alice", "+91200", "ramnagar", "tractor mechanic",
                            "tractor mechanic,tractor,mechanic")
        db.register_worker("Bob",   "+91201", "ballia",   "tractor mechanic",
                            "tractor mechanic,tractor,mechanic")
        db.register_worker("Carol", "+91202", "patna",    "plumber", "plumber")

    def test_search_by_skill_keyword(self):
        self._seed()
        results = db.search_workers("tractor mechanic")
        assert len(results) == 2

    def test_search_with_location(self):
        self._seed()
        results = db.search_workers("tractor mechanic", location="ramnagar")
        assert len(results) == 1
        assert results[0]["name"] == "Alice"

    def test_search_location_fallback(self):
        """If no worker found in location, should fall back to all locations."""
        self._seed()
        results = db.search_workers("tractor mechanic", location="xyz_unknown_place")
        assert len(results) == 2

    def test_search_respects_limit(self):
        for i in range(5):
            db.register_worker(f"M{i}", f"+9130{i}", "anywhere", "mechanic",
                                "mechanic,tractor mechanic")
        results = db.search_workers("mechanic", limit=3)
        assert len(results) <= 3

    def test_unavailable_workers_excluded(self):
        self._seed()
        db.set_availability("+91200", False)
        results = db.search_workers("tractor mechanic")
        names = [r["name"] for r in results]
        assert "Alice" not in names

    def test_search_no_results(self):
        results = db.search_workers("xyz_unknown_skill")
        assert results == []


# ---------------------------------------------------------------------------
# set_availability
# ---------------------------------------------------------------------------

class TestSetAvailability:
    def test_mark_unavailable(self):
        db.register_worker("Dave", "+91300", "patna", "plumber", "plumber")
        changed = db.set_availability("+91300", False)
        assert changed is True
        with db.get_db() as conn:
            row = conn.execute("SELECT available FROM workers WHERE phone=?",
                               ("+91300",)).fetchone()
        assert row["available"] == 0

    def test_mark_available_again(self):
        db.register_worker("Eve", "+91301", "patna", "plumber", "plumber")
        db.set_availability("+91301", False)
        db.set_availability("+91301", True)
        with db.get_db() as conn:
            row = conn.execute("SELECT available FROM workers WHERE phone=?",
                               ("+91301",)).fetchone()
        assert row["available"] == 1

    def test_unknown_phone_returns_false(self):
        changed = db.set_availability("+99999", True)
        assert changed is False


# ---------------------------------------------------------------------------
# add_rating
# ---------------------------------------------------------------------------

class TestAddRating:
    def test_rating_updates_average(self):
        worker_id = db.register_worker("Frank", "+91400", "siwan", "electrician", "electrician")
        db.add_rating(worker_id, "+91000", 4)
        db.add_rating(worker_id, "+91001", 2)
        with db.get_db() as conn:
            row = conn.execute("SELECT rating FROM workers WHERE id=?", (worker_id,)).fetchone()
        assert row["rating"] == pytest.approx(3.0)


# ---------------------------------------------------------------------------
# log_sms
# ---------------------------------------------------------------------------

class TestLogSms:
    def test_log_inbound(self):
        db.log_sms("IN", "+91500", "NEED Plumber", "SEARCH")
        with db.get_db() as conn:
            row = conn.execute("SELECT * FROM sms_log").fetchone()
        assert row["direction"] == "IN"
        assert row["intent"] == "SEARCH"

    def test_log_outbound(self):
        db.log_sms("OUT", "+91500", "Here are 3 plumbers", "SEARCH")
        with db.get_db() as conn:
            row = conn.execute("SELECT * FROM sms_log WHERE direction='OUT'").fetchone()
        assert row is not None
