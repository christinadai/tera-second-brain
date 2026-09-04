-- tera Second Brain: database schema.
--
-- Three tables, three jobs:
--   raw             what Reddit said, copied down exactly and never edited
--   cleaned_labeled that same text tidied up and labelled
--   job_logs        the clock-in record: when we collected, how much, what happened
--
-- Ranking is NOT stored. It is computed by SQL over cleaned_labeled each time a
-- briefing is built, so re-ranking is free and never needs re-collecting.

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------------
-- raw: the shoebox of receipts. Written once, never updated in place.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS raw (
    post_id       TEXT PRIMARY KEY,        -- Reddit's stable ID, e.g. "t3_abc123"
    source        TEXT NOT NULL,           -- "reddit" today; room for more later
    subreddit     TEXT NOT NULL,
    kind          TEXT NOT NULL,           -- "post" or "comment"
    parent_id     TEXT,                    -- for comments: the post they belong to
    permalink     TEXT NOT NULL,           -- traceability: one click back to source
    created_utc   INTEGER NOT NULL,        -- when the author posted it
    fetched_at    TEXT NOT NULL,           -- when we collected it (ISO-8601 UTC)
    run_id        TEXT NOT NULL,           -- which run brought it in
    score         INTEGER,                 -- upvotes at fetch time
    num_comments  INTEGER,
    payload       TEXT NOT NULL,           -- the untouched API response, as JSON
    FOREIGN KEY (run_id) REFERENCES job_logs(run_id)
);

CREATE INDEX IF NOT EXISTS idx_raw_subreddit  ON raw(subreddit);
CREATE INDEX IF NOT EXISTS idx_raw_created    ON raw(created_utc);
CREATE INDEX IF NOT EXISTS idx_raw_run        ON raw(run_id);

-- ---------------------------------------------------------------------------
-- cleaned_labeled: the tidy spreadsheet made from the receipts.
-- Populated from week 2. Defined now so the schema is complete and reviewable.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cleaned_labeled (
    post_id         TEXT PRIMARY KEY,
    body            TEXT NOT NULL,      -- normalised text
    content_hash    TEXT NOT NULL,      -- hash of body: catches reposts
    -- rule-based matches (regex over a vocabulary, no model involved)
    product_types   TEXT,               -- JSON array
    ingredients     TEXT,               -- JSON array
    claims          TEXT,               -- JSON array
    -- model-assigned labels (judgement, one call per post)
    pain_point      TEXT,
    skepticism_kind TEXT,
    proof_invoked   TEXT,
    -- Gen Z proxy: ONLY set when the author states an age in the text.
    -- Never inferred from slang or subreddit. NULL means "not stated".
    stated_age      INTEGER,
    labeled_at      TEXT,
    FOREIGN KEY (post_id) REFERENCES raw(post_id)
);

CREATE INDEX IF NOT EXISTS idx_cl_hash      ON cleaned_labeled(content_hash);
CREATE INDEX IF NOT EXISTS idx_cl_stated_age ON cleaned_labeled(stated_age);

-- ---------------------------------------------------------------------------
-- job_logs: one row per run. The typed outcome is the point of this table.
-- A count alone cannot tell a quiet week from a broken pull.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS job_logs (
    run_id            TEXT PRIMARY KEY,
    job               TEXT NOT NULL,     -- e.g. "pull_reddit"
    started_at        TEXT NOT NULL,
    finished_at       TEXT,
    outcome           TEXT,              -- see OUTCOMES in joblog.py
    records_fetched   INTEGER DEFAULT 0,
    records_stored    INTEGER DEFAULT 0, -- new rows
    records_duplicate INTEGER DEFAULT 0, -- already had them: expected, not an error
    records_skipped   INTEGER DEFAULT 0, -- deleted/removed/filtered out
    subreddits        TEXT,              -- JSON array: what this run actually asked for
    detail            TEXT               -- human-readable note, especially on failure
);

CREATE INDEX IF NOT EXISTS idx_job_started ON job_logs(started_at);
CREATE INDEX IF NOT EXISTS idx_job_outcome ON job_logs(outcome);
