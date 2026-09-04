"""Age, and only when the author states it themselves.

Reddit exposes no age field. The only trustworthy signal is an age a person
writes in their own words. This module extracts exactly that and nothing else.

Deliberately NOT inferred from: slang, subreddit, writing style, product
choices, or anything else. Those correlate weakly with age and would produce
confident nonsense. A generation split covering 8% of posts and saying so is
worth more than one covering 100% of posts by guessing.
"""

from __future__ import annotations

import re

# Generation bands. Boundaries are the commonly used ones and are approximate;
# they are stated here so the choice is visible rather than buried in a query.
# Birth years, converted to age ranges as of 2026.
GENERATIONS = (
    ("gen_z",      18, 29),   # born ~1997-2008
    ("millennial", 30, 45),   # born ~1981-1996
    ("gen_x",      46, 61),   # born ~1965-1980
    ("boomer",     62, 80),   # born ~1946-1964
)

# Only phrasings where the number is unambiguously the author's own age.
_PATTERNS = (
    r"\bi(?:'|’)?m\s+(\d{2})\b(?!\s*(?:%|percent|ml|g\b|quid|pounds|dollars))",
    r"\bi\s+am\s+(\d{2})\b",
    r"\b(?:as\s+)?a\s+(\d{2})\s*(?:yo|y/o|yr|year)[\s-]*old\b",
    r"\b(\d{2})\s*(?:yo|y/o)\b",
    r"\b(\d{2})\s*years?\s+old\b",
    r"\bin\s+my\s+(?:early|mid|late)\s+(\d{2})s\b",
    r"\bturning\s+(\d{2})\b",
    r"\bjust\s+turned\s+(\d{2})\b",
)

_COMPILED = tuple(re.compile(p, re.IGNORECASE) for p in _PATTERNS)

MIN_AGE, MAX_AGE = 13, 89


def stated_age(text: str) -> int | None:
    """The age the author states, or None. None is the common case and is fine."""
    if not text:
        return None
    found: list[int] = []
    for pattern in _COMPILED:
        for raw in pattern.findall(text):
            try:
                age = int(raw)
            except ValueError:
                continue
            if MIN_AGE <= age <= MAX_AGE:
                found.append(age)
    if not found:
        return None
    # "in my early 30s" gives 30. If several ages appear, the post is probably
    # about more than one person, so take the first and let the count speak.
    return found[0]


def generation(age: int | None) -> str | None:
    if age is None:
        return None
    for name, low, high in GENERATIONS:
        if low <= age <= high:
            return name
    return None


def coverage(ages: list[int | None]) -> dict:
    """How much of a sample actually stated an age.

    Every generation finding must be reported alongside this number. A split
    built on 6% of posts is a hint, not a result, and the briefing has to say so.
    """
    total = len(ages)
    stated = [a for a in ages if a is not None]
    counts: dict[str, int] = {}
    for age in stated:
        gen = generation(age)
        if gen:
            counts[gen] = counts.get(gen, 0) + 1
    return {
        "posts": total,
        "stated_age": len(stated),
        "coverage_pct": round(100 * len(stated) / total, 1) if total else 0.0,
        "by_generation": counts,
    }
