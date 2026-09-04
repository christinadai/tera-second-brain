"""Authenticated read-only Reddit client.

Read-only: this system never posts, votes, or comments. It only reads.
"""

from __future__ import annotations

import praw

from .config import load_credentials


def build_client() -> praw.Reddit:
    creds = load_credentials()
    client = praw.Reddit(
        client_id=creds["REDDIT_CLIENT_ID"],
        client_secret=creds["REDDIT_CLIENT_SECRET"],
        user_agent=creds["REDDIT_USER_AGENT"],
        check_for_async=False,
    )
    client.read_only = True
    return client


def verify(client: praw.Reddit) -> str:
    """Prove the credentials work by fetching one real thing.

    Returns a short human-readable description of what came back. Raises on
    failure so the caller can classify it into a typed outcome.
    """
    submission = next(client.subreddit("SkincareAddiction").new(limit=1))
    return f"r/SkincareAddiction newest post: {submission.id} {submission.title[:60]!r}"
