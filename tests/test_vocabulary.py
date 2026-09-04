"""Matcher tests. Run: ./.venv/bin/python tests/test_vocabulary.py

These are regression tests, not decoration. Two of them exist because the
matcher silently missed those exact phrases on its first run.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from second_brain.vocabulary import load_vocabulary, match, coverage_report  # noqa: E402

CASES = [
    # (text, list, canonical or None for "should match nothing")
    ("20x more potent than vitamin c", "claims", "potency claim"),
    ("20 x stronger than anything", "claims", "potency claim"),
    ("30% more effective apparently", "claims", "potency claim"),
    ("10 times more potent", "claims", "potency claim"),
    ("it pills under my sunscreen", "pain_points", "pilling"),
    ("this pilled immediately", "pain_points", "pilling"),
    ("my serum went orange after 6 weeks", "pain_points", "product went bad"),
    ("the before and after pics look photoshopped", "claims", "proof by photo"),
    ("looking for a lip sleeping mask", "product_types", "lip product"),
    ("fragrance gives me a headache", "ingredients", "fragrance"),
    ("it's my holy grail", "delight_signals", "holy grail"),
    ("just adopted a cat today", None, None),
]


def main() -> int:
    terms = load_vocabulary()
    failures = 0
    for text, list_name, canonical in CASES:
        result = match(text, terms)
        passed = result.is_empty() if list_name is None \
            else canonical in result.hits.get(list_name, {})
        if not passed:
            failures += 1
        print(f"{'PASS' if passed else 'FAIL'}  {text!r} -> {canonical or 'no match'}")

    print(f"\n{len(terms)} terms loaded")
    for name, counts in coverage_report(terms).items():
        print(f"  {name:16} {dict(counts)}")
    print(f"\n{len(CASES) - failures}/{len(CASES)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
