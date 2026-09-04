"""Stage 4: match the vocabulary against cleaned text. Rules, not a model.

Matching an ingredient name has a right answer, so it is regex. Deciding what
kind of complaint a post contains needs reading comprehension, so that is the
classifier's job, not this module's.

Two things this module does that matter more than the matching itself:

  1. It records WHICH terms fired, not just that something matched, so a
     briefing line can be traced to the word that caused it.
  2. It reports candidate unmatched terms, so vocabulary rot shows up as data.
     A missing term produces silence, not an error. Silence is the danger.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import yaml

VOCAB_DIR = Path(__file__).resolve().parents[2] / "config" / "vocabulary"

# Lists that hold terms, and which file they live in.
LIST_FILES = {
    "product_types": "product_types.yaml",
    "ingredients": "ingredients.yaml",
    "claims": "ingredients.yaml",
    "pain_points": "pain_points.yaml",
    "delight_signals": "pain_points.yaml",
    "brands": "brands.yaml",
}

VALID_SOURCES = ("provisional", "alma", "observed")

# Apostrophes are the single most common reason a term silently fails to match.
# "dog's nose" would not match the alias "dog nose", and "it's plant based"
# would not match "its plant based". Reddit posts also mix straight and curly
# apostrophes freely. So both text and aliases are normalised the same way:
# curly quotes folded to straight, then apostrophes removed entirely.
_APOSTROPHES = str.maketrans({"\u2019": "'", "\u02bc": "'", "\u2018": "'"})


def normalize(text: str) -> str:
    return (text or "").translate(_APOSTROPHES).replace("'", "")


@dataclass
class Term:
    canonical: str
    list_name: str
    source: str
    pattern: re.Pattern
    aliases: list[str]


@dataclass
class MatchResult:
    """What fired, per list, with the exact alias that caused each hit."""
    hits: dict[str, dict[str, list[str]]] = field(default_factory=dict)

    def canonicals(self, list_name: str) -> list[str]:
        return sorted(self.hits.get(list_name, {}))

    def is_empty(self) -> bool:
        return not any(self.hits.values())


def _compile(aliases: list[str], patterns: list[str] | None = None) -> re.Pattern:
    """One case-insensitive alternation per term.

    `aliases` are literal phrases, escaped and word-boundary wrapped. Longest
    first so "lip sleeping mask" wins over "lip mask" at the same position.

    `patterns` are raw regex, for shapes a literal cannot express. The case that
    forced this: "20x more potent" has a digit before the x, so the leading
    word-boundary guard on a literal alias "x more potent" never fires.
    """
    parts = []
    ordered = sorted((normalize(a).strip() for a in aliases if a.strip()),
                     key=len, reverse=True)
    if ordered:
        joined = "|".join(re.escape(a) for a in ordered)
        parts.append(rf"(?<!\w)(?:{joined})(?!\w)")
    for raw in patterns or []:
        parts.append(f"(?:{raw})")
    if not parts:
        raise ValueError("term has neither aliases nor patterns")
    return re.compile("|".join(parts), re.IGNORECASE)


def load_vocabulary(vocab_dir: Path | None = None) -> list[Term]:
    directory = vocab_dir or VOCAB_DIR
    cache: dict[str, dict] = {}
    terms: list[Term] = []

    for list_name, filename in LIST_FILES.items():
        if filename not in cache:
            path = directory / filename
            cache[filename] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for entry in cache[filename].get(list_name, []) or []:
            source = entry.get("source", "provisional")
            if source not in VALID_SOURCES:
                raise ValueError(
                    f"{entry.get('canonical')!r} in {filename} has source "
                    f"{source!r}, not one of {VALID_SOURCES}"
                )
            aliases = entry.get("aliases") or []
            patterns = entry.get("patterns") or []
            if not aliases and not patterns:
                raise ValueError(
                    f"{entry.get('canonical')!r} in {filename} has no aliases or patterns"
                )
            terms.append(Term(
                canonical=entry["canonical"],
                list_name=list_name,
                source=source,
                pattern=_compile(aliases, patterns),
                aliases=aliases,
            ))
    return terms


def match(text: str, terms: list[Term]) -> MatchResult:
    result = MatchResult()
    normalized = normalize(text)
    for term in terms:
        found = term.pattern.findall(normalized)
        if found:
            bucket = result.hits.setdefault(term.list_name, {})
            bucket[term.canonical] = sorted({f.lower() for f in found})
    return result


# Words too common to be worth reporting as an unmatched candidate.
_STOPWORDS = set("""
a an and are as at be been but by for from had has have how i if in is it its me my
of on or so than that the their them then there these they this to too was we were
what when which who why will with you your just really very much more most some any
like get got dont doesnt didnt im ive its about after all also am can cant could
do does going know make made need not now one out over see should still sure take
than think time try use used using want way well
""".split())


def unmatched_terms(text: str, terms: list[Term], top: int = 20) -> list[tuple[str, int]]:
    """Frequent words in the text that no vocabulary term claimed.

    This is the vocabulary rot detector. Reviewed weekly: anything here that is
    a real skincare term is a gap, and gets added with source `observed`.
    """
    lowered = normalize(text).lower()
    claimed: set[str] = set()
    for term in terms:
        for hit in term.pattern.findall(lowered):
            claimed.update(hit.lower().split())

    words = re.findall(r"[a-z][a-z'-]{2,}", lowered)
    counts = Counter(w for w in words if w not in _STOPWORDS and w not in claimed)
    return counts.most_common(top)


def coverage_report(terms: list[Term]) -> dict[str, Counter]:
    """How much of the vocabulary is still guessed rather than observed."""
    report: dict[str, Counter] = {}
    for term in terms:
        report.setdefault(term.list_name, Counter())[term.source] += 1
    return report
