"""Shared helpers: pinned third-party sources and random JSON-shaped data."""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

import pytest

UPSTREAM = Path(__file__).parent / "upstream"


def upstream(name: str) -> str:
    """Return a source saved by scripts/fetch_upstream.py, or skip the test."""
    path = UPSTREAM / name
    if not path.is_file():
        pytest.skip(f"{name} not fetched; run python scripts/fetch_upstream.py")
    return path.read_text(encoding="utf-8")


KEY_CHARS = "ab.\\/:0-1~ é"


def random_key(rng: random.Random) -> str:
    """A short key that often holds separators, backslashes and digits."""
    return "".join(rng.choice(KEY_CHARS) for _ in range(rng.randint(1, 4)))


def random_tree(rng: random.Random, depth: int = 4) -> Any:
    """A random JSON-shaped value: dicts, lists, scalars and empty containers."""
    roll = rng.random()
    if depth == 0 or roll < 0.3:
        return rng.choice([None, True, 0, -7, 2.5, "", "x", "a.b", [], {}])
    if roll < 0.65:
        return {random_key(rng): random_tree(rng, depth - 1) for _ in range(rng.randint(0, 4))}
    return [random_tree(rng, depth - 1) for _ in range(rng.randint(0, 4))]
