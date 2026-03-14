-- Dehati-Connect: SMS-based Skill & Labor Directory
-- Database schema for worker registry

-- Workers table: stores registered skilled workers
CREATE TABLE IF NOT EXISTS workers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    phone       TEXT    NOT NULL UNIQUE,
    location    TEXT    NOT NULL,              -- village / block / district
    skill       TEXT    NOT NULL,              -- e.g. "tractor mechanic"
    skill_tags  TEXT    NOT NULL,              -- comma-separated keywords for fast search
    available   INTEGER NOT NULL DEFAULT 1,    -- 1 = available, 0 = busy
    rating      REAL    NOT NULL DEFAULT 5.0,  -- average star rating (1-5)
    jobs_done   INTEGER NOT NULL DEFAULT 0,    -- total completed jobs
    registered_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for fast keyword + location searches
CREATE INDEX IF NOT EXISTS idx_workers_skill_tags ON workers (skill_tags);
CREATE INDEX IF NOT EXISTS idx_workers_location   ON workers (location);
CREATE INDEX IF NOT EXISTS idx_workers_available  ON workers (available);

-- SMS log: every incoming and outgoing SMS is recorded for audit / analytics
CREATE TABLE IF NOT EXISTS sms_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    direction   TEXT    NOT NULL CHECK (direction IN ('IN', 'OUT')),
    phone       TEXT    NOT NULL,
    body        TEXT    NOT NULL,
    intent      TEXT,           -- parsed intent: REGISTER | SEARCH | UNKNOWN
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Ratings table: allow callers to rate a referred worker
CREATE TABLE IF NOT EXISTS ratings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    worker_id   INTEGER NOT NULL REFERENCES workers (id),
    rater_phone TEXT    NOT NULL,
    stars       INTEGER NOT NULL CHECK (stars BETWEEN 1 AND 5),
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
