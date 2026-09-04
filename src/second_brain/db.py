"""Opening the database and creating it from the committed schema.

The database is one file. The schema that builds it lives in schema.sql and is
tracked in git, so the structure is version-controlled and anyone can rebuild
an empty database from scratch.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
DEFAULT_DB_PATH = REPO_ROOT / "data" / "second_brain.db"


def connect(db_path: Path | str | None = None) -> sqlite3.Connection:
    """Open the database, creating the file and tables if they do not exist."""
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()
    return conn
