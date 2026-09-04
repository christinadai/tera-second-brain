"""Credentials from the environment, collection rules from a readable file.

Two rules that do not bend:
  1. Secrets live in .env, never in code, and .env is gitignored.
  2. Collection rules live in config/sources.yaml, not buried in Python, so
     Amy or Katie can change what we collect without editing code.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCES_PATH = REPO_ROOT / "config" / "sources.yaml"


class ConfigError(RuntimeError):
    """Raised loudly when configuration is missing. Never guessed around."""


def load_credentials() -> dict[str, str]:
    load_dotenv(REPO_ROOT / ".env")
    required = ("REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET", "REDDIT_USER_AGENT")
    values = {key: os.environ.get(key, "").strip() for key in required}
    missing = [key for key, value in values.items() if not value]
    if missing:
        raise ConfigError(
            "Missing credentials: " + ", ".join(missing) + ".\n"
            "Copy .env.example to .env and fill it in. See docs/OPERATIONS.md."
        )
    return values


def load_sources() -> dict:
    if not SOURCES_PATH.exists():
        raise ConfigError(f"No collection rules found at {SOURCES_PATH}")
    return yaml.safe_load(SOURCES_PATH.read_text(encoding="utf-8"))
