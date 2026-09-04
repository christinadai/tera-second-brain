"""Age extraction tests. Run: ./.venv/bin/python tests/test_demographics.py

The negative cases matter more than the positive ones. A percentage, a price,
and a duration all look like "a number near the word I" and none of them are
an age. Getting those wrong would silently corrupt every generation split.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from second_brain.demographics import stated_age, generation, coverage  # noqa: E402

CASES = [
    ("I'm 24 and my skin has been awful lately", 24, "gen_z"),
    ("i am 37 and starting retinol", 37, "millennial"),
    ("as a 52 year old my main concern is firmness", 52, "gen_x"),
    ("28yo, oily skin", 28, "gen_z"),
    ("in my early 30s and noticing fine lines", 30, "millennial"),
    ("just turned 41 last week", 41, "millennial"),
    ("I’m 33, curly hair", 33, "millennial"),      # curly apostrophe
    # Negatives: numbers that are not ages.
    ("I use 10% niacinamide", None, None),
    ("it cost me 45 pounds", None, None),
    ("been using this for 20 years", None, None),
    ("50ml bottle lasted 3 months", None, None),
    ("no age here at all", None, None),
]


def main() -> int:
    failures = 0
    for text, want_age, want_gen in CASES:
        age = stated_age(text)
        gen = generation(age)
        passed = age == want_age and gen == want_gen
        failures += 0 if passed else 1
        print(f"{'PASS' if passed else 'FAIL'}  {text[:46]!r:50} -> {age} / {gen}")

    report = coverage([24, 37, 52, None, None, None, None, None, None, None])
    assert report["coverage_pct"] == 30.0, report
    print(f"\ncoverage report: {report}")
    print(f"{len(CASES) - failures}/{len(CASES)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
