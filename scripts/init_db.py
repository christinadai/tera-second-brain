"""Create an empty database from the committed schema. Safe to re-run."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from second_brain.db import connect, DEFAULT_DB_PATH  # noqa: E402

conn = connect()
tables = [r[0] for r in conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
print(f"Database: {DEFAULT_DB_PATH}")
print(f"Tables:   {', '.join(tables)}")
conn.close()
