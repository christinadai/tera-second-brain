"""Fallback: Reddit's public JSON listings, no credentials.

TEMPORARY. This exists because app registration was blocked, not because it is
the right way to do this. Switch to PRAW the moment credentials work.

Trade-offs, stated so nobody inherits this thinking it is the plan:
  - Anonymous access is rate limited far more aggressively than an app.
  - Reddit answers an anonymous 429 with x-ratelimit-reset and NO Retry-After,
    and wants roughly 40 seconds. Short exponential backoff re-429s every time
    and makes a working source look dead. We wait properly instead.
  - Reddit's terms point programmatic use at the registered API. This is a
    low-volume bridge for one week, not a way to avoid registering.

Standard library only, so it adds no dependency.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

BASE = "https://www.reddit.com"
# Reddit asks for a descriptive agent naming the tool. Do not send a fake browser UA.
USER_AGENT = "tera-second-brain/0.1 (research prototype; keyless fallback)"
RATE_LIMIT_WAIT = 45  # seconds. See module docstring: short backoff does not work.
POLITE_GAP = 2        # seconds between requests, to stay well under the cap


class KeylessError(RuntimeError):
    pass


def _get(url: str, attempts: int = 3) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < attempts:
                reset = exc.headers.get("x-ratelimit-reset")
                wait = RATE_LIMIT_WAIT
                try:
                    if reset:
                        wait = max(int(float(reset)) + 1, 1)
                except (TypeError, ValueError):
                    pass
                time.sleep(wait)
                continue
            raise KeylessError(f"HTTP {exc.code} for {url}") from exc
    raise KeylessError(f"Gave up after {attempts} attempts: {url}")


def fetch_listing(subreddit: str, listing: str = "new", limit: int = 25) -> list[dict]:
    """Return the raw 'data' dict of each post, exactly as Reddit sent it."""
    url = f"{BASE}/r/{subreddit}/{listing}.json?limit={int(limit)}&raw_json=1"
    payload = _get(url)
    try:
        children = payload["data"]["children"]
    except (KeyError, TypeError) as exc:
        raise KeylessError(f"Unexpected response shape from {url}") from exc
    time.sleep(POLITE_GAP)
    return [child["data"] for child in children if child.get("kind") == "t3"]
