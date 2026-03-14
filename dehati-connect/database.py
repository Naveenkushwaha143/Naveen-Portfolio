"""
database.py — SQLite helpers for Dehati-Connect.

All SQL is parameterised to prevent injection.
"""

import os
import sqlite3
from contextlib import contextmanager
from typing import Generator, List, Optional

DB_PATH = os.environ.get("DEHATI_DB", "dehati_connect.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------

@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Yield a database connection with row-factory set."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Enforce foreign-key constraints
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create tables if they do not yet exist."""
    with open(SCHEMA_PATH, "r", encoding="utf-8") as fh:
        ddl = fh.read()
    with get_db() as conn:
        conn.executescript(ddl)


# ---------------------------------------------------------------------------
# Worker operations
# ---------------------------------------------------------------------------

def register_worker(name: str, phone: str, location: str,
                    skill: str, skill_tags: str) -> int:
    """
    Insert a new worker record.

    Returns the new row id, or 0 if the phone number is already registered.
    """
    sql = """
        INSERT OR IGNORE INTO workers (name, phone, location, skill, skill_tags)
        VALUES (?, ?, ?, ?, ?)
    """
    with get_db() as conn:
        cur = conn.execute(sql, (name, phone, location.lower(),
                                 skill.lower(), skill_tags.lower()))
        return cur.lastrowid or 0


def search_workers(keyword: str, location: Optional[str] = None,
                   limit: int = 3) -> List[sqlite3.Row]:
    """
    Return up to *limit* available workers whose skill_tags contain *keyword*.

    Results are ranked by rating DESC, then jobs_done DESC so the best
    workers appear first.

    If *location* is provided the search is narrowed to that location first;
    if no results are found the location filter is dropped so the caller
    always gets a useful response.
    """
    base_sql = """
        SELECT id, name, phone, skill, location, rating, jobs_done
        FROM   workers
        WHERE  available = 1
          AND  skill_tags LIKE ?
        {location_clause}
        ORDER  BY rating DESC, jobs_done DESC
        LIMIT  ?
    """
    kw_param = f"%{keyword.lower()}%"

    def _run(loc: Optional[str]) -> List[sqlite3.Row]:
        if loc:
            sql = base_sql.format(location_clause="AND location LIKE ?")
            params = (kw_param, f"%{loc.lower()}%", limit)
        else:
            sql = base_sql.format(location_clause="")
            params = (kw_param, limit)
        with get_db() as conn:
            return conn.execute(sql, params).fetchall()

    rows = _run(location)
    if not rows and location:
        # Broaden: ignore location filter
        rows = _run(None)
    return rows


def set_availability(phone: str, available: bool) -> bool:
    """Toggle a worker's availability. Returns True if the record was found."""
    with get_db() as conn:
        cur = conn.execute(
            "UPDATE workers SET available = ? WHERE phone = ?",
            (1 if available else 0, phone),
        )
        return cur.rowcount > 0


def add_rating(worker_id: int, rater_phone: str, stars: int) -> None:
    """Persist a new rating and recalculate the worker's average."""
    with get_db() as conn:
        conn.execute(
            "INSERT INTO ratings (worker_id, rater_phone, stars) VALUES (?, ?, ?)",
            (worker_id, rater_phone, stars),
        )
        conn.execute(
            """
            UPDATE workers
            SET    rating = (SELECT AVG(stars) FROM ratings WHERE worker_id = ?)
            WHERE  id = ?
            """,
            (worker_id, worker_id),
        )


# ---------------------------------------------------------------------------
# SMS log
# ---------------------------------------------------------------------------

def log_sms(direction: str, phone: str, body: str, intent: Optional[str] = None) -> None:
    """Record an inbound or outbound SMS in the audit log."""
    with get_db() as conn:
        conn.execute(
            "INSERT INTO sms_log (direction, phone, body, intent) VALUES (?, ?, ?, ?)",
            (direction, phone, body, intent),
        )
