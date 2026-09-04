"""One small keyless RSS collection run.

Usage:
    python scripts/pull_keyless.py --subreddit SkincareAddiction --limit 10

Deliberately small by default. This path is rate limited hard and is a
stopgap pending Reddit API access.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from second_brain.config import load_sources  # noqa: E402
from second_brain.db import connect  # noqa: E402
from second_brain.pull import pull_keyless  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("--subreddit", action="append", required=True)
parser.add_argument("--limit", type=int, default=10)
parser.add_argument("--listing", default="new", choices=["new", "hot", "top", "rising"])
args = parser.parse_args()

conn = connect()
log = pull_keyless(conn, load_sources(), args.subreddit,
                   listing=args.listing, limit=args.limit)
row = conn.execute(
    "SELECT outcome, records_fetched, records_stored, records_duplicate, "
    "records_skipped, detail FROM job_logs WHERE run_id = ?", (log.run_id,)).fetchone()
print(f"run_id     {log.run_id}")
print(f"outcome    {row['outcome']}")
print(f"fetched    {row['records_fetched']}")
print(f"stored     {row['records_stored']} new")
print(f"duplicate  {row['records_duplicate']}")
print(f"skipped    {row['records_skipped']}")
print(f"detail     {row['detail']}")
conn.close()
