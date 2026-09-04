"""One small end-to-end pull: Reddit -> raw, with the run written to job_logs.

Usage:
    python scripts/pull_once.py [--limit N] [--subreddit NAME ...]

Defaults to the manual subreddits in config/sources.yaml plus anything the
discovery pass has recorded there.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from second_brain.config import load_sources  # noqa: E402
from second_brain.db import connect  # noqa: E402
from second_brain.pull import pull  # noqa: E402
from second_brain.reddit_client import build_client  # noqa: E402

parser = argparse.ArgumentParser()
parser.add_argument("--limit", type=int, default=10,
                    help="posts per subreddit (default 10, deliberately small)")
parser.add_argument("--subreddit", action="append", default=None)
args = parser.parse_args()

rules = load_sources()
subs = args.subreddit or (
    [entry["name"] for entry in rules["reddit"].get("manual", [])]
    + list(rules["reddit"].get("discovered", []))
)
if not subs:
    print("No subreddits configured. Edit config/sources.yaml.")
    sys.exit(1)

conn = connect()
log = pull(conn, build_client(), rules, subs, limit=args.limit)
print(f"run_id    {log.run_id}")
row = conn.execute("SELECT outcome, records_fetched, records_stored, "
                   "records_duplicate, records_skipped, detail FROM job_logs "
                   "WHERE run_id = ?", (log.run_id,)).fetchone()
print(f"outcome   {row['outcome']}")
print(f"fetched   {row['records_fetched']}")
print(f"stored    {row['records_stored']} new")
print(f"duplicate {row['records_duplicate']} already had")
print(f"skipped   {row['records_skipped']} dropped by rules")
print(f"detail    {row['detail']}")
conn.close()
