"""The clock-in record.

Every run writes exactly one row to job_logs, and that row carries a typed
outcome rather than only a count.

Why this matters: five of these outcomes produce zero rows, and only one of
them means nobody was talking. A run that stored 0 records is not evidence of
a quiet week unless the outcome says so. This is the difference between an
empty briefing that is true and an empty briefing that is a silent failure.

Borrowed from the last30days skill (scripts/lib/health.py).
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone

# The closed vocabulary. Nothing outside this list is a valid outcome.
OUTCOMES = (
    "ok",            # ran, stored what we expected
    "no-results",    # ran fine, the source genuinely had nothing new
    "partial",       # some sources worked, some did not
    "rate-limited",  # the source told us to slow down
    "auth-failed",   # credentials rejected: a person must fix this, do not retry
    "unreachable",   # network or the source is down
    "schema-drift",  # the response did not look how we expected: fail loudly
    "degraded",      # ran, but returned far less than normal. The early warning.
)

ZERO_ROW_OUTCOMES = (
    "no-results", "rate-limited", "auth-failed", "unreachable", "schema-drift",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class JobLog:
    """Opens a run, accumulates counts, and closes it with a typed outcome."""

    def __init__(self, conn: sqlite3.Connection, job: str, subreddits: list[str] | None = None):
        self.conn = conn
        self.job = job
        self.run_id = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-{uuid.uuid4().hex[:6]}"
        self.fetched = 0
        self.stored = 0
        self.duplicate = 0
        self.skipped = 0
        self._subreddits = subreddits or []
        self.conn.execute(
            "INSERT INTO job_logs (run_id, job, started_at, subreddits) VALUES (?, ?, ?, ?)",
            (self.run_id, job, _now(), json.dumps(self._subreddits)),
        )
        self.conn.commit()

    def close(self, outcome: str, detail: str = "") -> None:
        if outcome not in OUTCOMES:
            raise ValueError(f"{outcome!r} is not one of {OUTCOMES}")
        self.conn.execute(
            """UPDATE job_logs
                  SET finished_at = ?, outcome = ?, records_fetched = ?,
                      records_stored = ?, records_duplicate = ?, records_skipped = ?,
                      detail = ?
                WHERE run_id = ?""",
            (_now(), outcome, self.fetched, self.stored, self.duplicate,
             self.skipped, detail, self.run_id),
        )
        self.conn.commit()


def classify_error(exc: Exception, status: int | None = None) -> str:
    """Map a failure to the vocabulary.

    Uses the error TEXT as well as any status code, because not every failure
    arrives as a clean HTTP status. Also borrowed from last30days.
    """
    text = f"{type(exc).__name__} {exc}".lower()
    if status == 429 or "429" in text or "too many requests" in text or "rate limit" in text:
        return "rate-limited"
    if status in (401, 403) or "401" in text or "403" in text \
            or "unauthorized" in text or "invalid_grant" in text or "forbidden" in text:
        return "auth-failed"
    if "timeout" in text or "connection" in text or "dns" in text \
            or "unreachable" in text or "resolve" in text:
        return "unreachable"
    if "keyerror" in text or "attributeerror" in text or "typeerror" in text \
            or "json" in text or "schema" in text:
        return "schema-drift"
    return "unreachable"
