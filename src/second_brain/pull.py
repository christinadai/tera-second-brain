"""Stage 1 and 2: ask Reddit for posts, write them down exactly as received.

Nothing is cleaned or interpreted here. The only judgement this module makes is
which posts to drop on sight (deleted, removed, stickied, bots), and even that
is driven by config/sources.yaml rather than hardcoded.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

import praw

from .joblog import JobLog, classify_error


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).isoformat(timespec="seconds")


def _should_drop(body: str, author: str | None, stickied: bool, rules: dict) -> bool:
    drop = rules.get("drop", {})
    if drop.get("deleted", True) and body.strip() == "[deleted]":
        return True
    if drop.get("removed", True) and body.strip() == "[removed]":
        return True
    if drop.get("stickied", True) and stickied:
        return True
    if author and author in (drop.get("authors") or []):
        return True
    return False


def _store(conn: sqlite3.Connection, row: dict) -> bool:
    """Insert one record. Returns True if new, False if we already had it.

    Uses INSERT OR IGNORE on the post_id primary key, so re-running a pull
    never changes the numbers and never creates duplicates.
    """
    cur = conn.execute(
        """INSERT OR IGNORE INTO raw
           (post_id, source, subreddit, kind, parent_id, permalink, created_utc,
            fetched_at, run_id, score, num_comments, payload)
           VALUES (:post_id, :source, :subreddit, :kind, :parent_id, :permalink,
                   :created_utc, :fetched_at, :run_id, :score, :num_comments, :payload)""",
        row,
    )
    return cur.rowcount > 0


def pull(conn: sqlite3.Connection, client: praw.Reddit, rules: dict,
         subreddits: list[str], limit: int | None = None) -> JobLog:
    """Run one collection pass. Always closes the job log with a typed outcome."""
    reddit_rules = rules["reddit"]
    post_limit = limit if limit is not None else reddit_rules.get("post_limit", 100)
    listing = reddit_rules.get("listing", "new")
    log = JobLog(conn, job="pull_reddit", subreddits=subreddits)
    failures: list[str] = []
    worked: list[str] = []

    try:
        for name in subreddits:
            try:
                sub = client.subreddit(name)
                submissions = getattr(sub, listing)(limit=post_limit)
                for post in submissions:
                    log.fetched += 1
                    author = str(post.author) if post.author else None
                    if _should_drop(post.selftext or "", author, post.stickied, reddit_rules):
                        log.skipped += 1
                        continue
                    payload = {
                        "id": post.id, "title": post.title, "selftext": post.selftext,
                        "author": author, "score": post.score,
                        "num_comments": post.num_comments,
                        "created_utc": post.created_utc, "permalink": post.permalink,
                        "link_flair_text": post.link_flair_text,
                        "upvote_ratio": post.upvote_ratio,
                    }
                    new = _store(conn, {
                        "post_id": post.fullname, "source": "reddit",
                        "subreddit": name, "kind": "post", "parent_id": None,
                        "permalink": f"https://reddit.com{post.permalink}",
                        "created_utc": int(post.created_utc),
                        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        "run_id": log.run_id, "score": post.score,
                        "num_comments": post.num_comments,
                        "payload": json.dumps(payload, ensure_ascii=False),
                    })
                    log.stored += 1 if new else 0
                    log.duplicate += 0 if new else 1
                conn.commit()
                worked.append(name)
            except Exception as exc:  # one bad subreddit must not kill the run
                failures.append(f"r/{name}: {classify_error(exc)} ({exc})")

        conn.commit()
        if failures and worked:
            log.close("partial", "; ".join(failures))
        elif failures:
            log.close(classify_error(Exception(failures[0])), "; ".join(failures))
        elif log.stored == 0 and log.duplicate == 0:
            log.close("no-results", "Ran cleanly, nothing matched.")
        else:
            log.close("ok", f"Collected from {len(worked)} subreddit(s).")
    except Exception as exc:
        log.close(classify_error(exc), f"{type(exc).__name__}: {exc}")
        raise
    return log


# ---------------------------------------------------------------------------
# Keyless path. Temporary, pending Reddit API access. See reddit_keyless.py.
# ---------------------------------------------------------------------------

def pull_keyless(conn: sqlite3.Connection, rules: dict, subreddits: list[str],
                 listing: str = "new", limit: int = 10) -> JobLog:
    """Collect over public RSS instead of the API. Same tables, same job log.

    Rows land with source "reddit-rss" and NULL score/num_comments, because RSS
    carries neither. NULL, never 0: "we do not know" and "nobody upvoted it"
    must not be confusable when ranking later.
    """
    from . import reddit_keyless as rk

    reddit_rules = rules["reddit"]
    log = JobLog(conn, job="pull_reddit_rss", subreddits=subreddits)
    failures: list[str] = []
    worked: list[str] = []

    try:
        for name in subreddits:
            try:
                posts = rk.fetch_listing(name, listing=listing, limit=limit)
                for post in posts:
                    log.fetched += 1
                    if _should_drop(post.body, post.author, False, reddit_rules):
                        log.skipped += 1
                        continue
                    payload = {
                        "id": post.post_id, "title": post.title,
                        "selftext_html": post.body, "author": post.author,
                        "permalink": post.permalink, "created_utc": post.created_utc,
                        "_collected_via": "rss",
                        "_score_unavailable": True,
                    }
                    new = _store(conn, {
                        "post_id": post.post_id, "source": "reddit-rss",
                        "subreddit": name, "kind": "post", "parent_id": None,
                        "permalink": post.permalink,
                        "created_utc": post.created_utc,
                        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                        "run_id": log.run_id,
                        "score": None,          # RSS gives no score. NULL, not 0.
                        "num_comments": None,   # same.
                        "payload": json.dumps(payload, ensure_ascii=False),
                    })
                    log.stored += 1 if new else 0
                    log.duplicate += 0 if new else 1
                conn.commit()
                worked.append(name)
            except rk.RateLimited as exc:
                failures.append(f"r/{name}: rate-limited ({exc})")
            except Exception as exc:
                failures.append(f"r/{name}: {classify_error(exc)} ({exc})")

        conn.commit()
        if failures and worked:
            log.close("partial", "; ".join(failures))
        elif failures:
            outcome = "rate-limited" if "rate-limited" in failures[0] \
                else classify_error(Exception(failures[0]))
            log.close(outcome, "; ".join(failures))
        elif log.stored == 0 and log.duplicate == 0:
            log.close("no-results", "Ran cleanly, feed was empty.")
        else:
            log.close("ok", f"RSS collection from {len(worked)} subreddit(s). "
                            f"No scores available on this path.")
    except Exception as exc:
        log.close(classify_error(exc), f"{type(exc).__name__}: {exc}")
        raise
    return log
