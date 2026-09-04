"""Prove the Reddit credentials work. Fetches exactly one real post.

Run this before anything else. If it fails, nothing downstream can succeed.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from second_brain.config import ConfigError  # noqa: E402
from second_brain.joblog import classify_error  # noqa: E402
from second_brain.reddit_client import build_client, verify  # noqa: E402

try:
    print(verify(build_client()))
    print("OK: credentials work, read-only access confirmed.")
except ConfigError as exc:
    print(f"CONFIG PROBLEM\n{exc}")
    sys.exit(1)
except Exception as exc:
    print(f"FAILED [{classify_error(exc)}]: {type(exc).__name__}: {exc}")
    sys.exit(1)
