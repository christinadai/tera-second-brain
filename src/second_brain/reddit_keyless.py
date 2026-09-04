"""Keyless Reddit collection over public RSS feeds.

WHY THIS EXISTS: Reddit closed self-service API registration, so we have no
client ID or secret. An access request is submitted and pending. Amy approved
trying this route in the meantime, on 3 Sep 2026.

WHAT WORKS, verified by probe on 3 Sep 2026:
    .json listings   HTTP 403 Blocked        <- do not use
    .rss listings    HTTP 200                <- this is the path
    three rapid RSS requests   HTTP 429      <- pacing must be real

Method learned from the last30days skill (lib/reddit_rss.py), which documents
the same 403 on .json and the same fallback to RSS.

THE COST, stated plainly because it shapes what we can conclude:

  1. RSS carries NO SCORE and NO COMMENT COUNT. Every ranking rule that
     depends on engagement is unavailable on this path. Counting how often
     something is said still works. Weighting by how many people upvoted it
     does not. Rows collected this way store NULL, never 0, so nothing later
     mistakes "unknown" for "nobody upvoted it".
  2. RSS gives a truncated body for some posts.
  3. Rate limits are tight and Reddit sends no Retry-After, so we wait long.

Rows collected here are stored with source "reddit-rss" rather than "reddit",
so when API access arrives we can tell which rows came from the weaker path
and re-collect them properly.
"""

from __future__ import annotations

import ssl
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone

import certifi

ATOM = "{http://www.w3.org/2005/Atom}"
BASE = "https://www.reddit.com"

# Names the tool and gives a contact, which is what Reddit asks for.
USER_AGENT = (
    "tera-second-brain/0.1 (pre-launch consumer research; "
    "contact via github.com/christinadai/tera-second-brain)"
)

# Reddit sends no Retry-After on an anonymous 429 and wants roughly 40 seconds.
# Short exponential backoff re-429s every time and makes a live source look
# dead. Documented in the dossier, borrowed from last30days.
RATE_LIMIT_WAIT = 45
POLITE_GAP = 8          # between successful requests
MAX_ATTEMPTS = 3

_SSL = ssl.create_default_context(cafile=certifi.where())


class KeylessError(RuntimeError):
    pass


class RateLimited(KeylessError):
    pass


@dataclass
class RssPost:
    post_id: str          # Reddit fullname, e.g. t3_abc123
    subreddit: str
    title: str
    body: str
    author: str | None
    created_utc: int
    permalink: str

    @property
    def is_usable(self) -> bool:
        return bool(self.post_id and self.permalink)


def _fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=30, context=_SSL) as response:
                return response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                if attempt == MAX_ATTEMPTS:
                    raise RateLimited(f"429 after {attempt} attempts: {url}") from exc
                time.sleep(RATE_LIMIT_WAIT)
                continue
            raise KeylessError(f"HTTP {exc.code} {exc.reason} for {url}") from exc
        except urllib.error.URLError as exc:
            raise KeylessError(f"unreachable: {exc.reason} for {url}") from exc
    raise KeylessError(f"exhausted attempts: {url}")


def _text(node, tag: str) -> str:
    found = node.find(f"{ATOM}{tag}")
    return (found.text or "").strip() if found is not None and found.text else ""


def _parse(xml_text: str, subreddit: str) -> list[RssPost]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise KeylessError(f"feed did not parse as XML: {exc}") from exc

    posts: list[RssPost] = []
    for entry in root.findall(f"{ATOM}entry"):
        post_id = _text(entry, "id")            # already "t3_xxxxx"
        title = _text(entry, "title")
        updated = _text(entry, "updated") or _text(entry, "published")
        link_node = entry.find(f"{ATOM}link")
        permalink = link_node.get("href", "") if link_node is not None else ""
        author_node = entry.find(f"{ATOM}author")
        author = _text(author_node, "name") if author_node is not None else None
        content_node = entry.find(f"{ATOM}content")
        body = (content_node.text or "") if content_node is not None else ""

        created = 0
        if updated:
            try:
                created = int(datetime.fromisoformat(updated).timestamp())
            except ValueError:
                created = 0

        post = RssPost(
            post_id=post_id, subreddit=subreddit, title=title, body=body,
            author=author.lstrip("/u/") if author else None,
            created_utc=created, permalink=permalink,
        )
        if post.is_usable:
            posts.append(post)
    return posts


def fetch_listing(subreddit: str, listing: str = "new", limit: int = 10,
                  time_filter: str = "month") -> list[RssPost]:
    """One RSS listing for one subreddit. Sleeps afterwards, deliberately."""
    if listing not in ("new", "hot", "top", "rising"):
        raise ValueError(f"unsupported listing: {listing}")
    url = f"{BASE}/r/{subreddit}/{listing}.rss?limit={int(limit)}"
    if listing == "top":
        url += f"&t={time_filter}"
    posts = _parse(_fetch(url), subreddit)
    time.sleep(POLITE_GAP)
    return posts
