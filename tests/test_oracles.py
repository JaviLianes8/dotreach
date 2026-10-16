"""Differential checks against independent implementations: glom and jmespath.

Neither is a dependency. Install them (``pip install glom jmespath``) to run these
tests; they skip otherwise. Every case is seeded, so a failure reproduces exactly.
"""

from __future__ import annotations

import json
import random
from typing import Any

import pytest
from conftest import random_key, random_tree

import dotreach as d

SEEDS = range(300)
MISS = object()


def _paths(tree: Any, rng: random.Random) -> list[tuple[Any, ...]]:
    """Every leaf path, every interior prefix, and a few that do not resolve."""
    found: set[tuple[Any, ...]] = set()
    for segments, _ in d.walk(tree):
        found.update(segments[:n] for n in range(1, len(segments) + 1))
    misses = [(*p, random_key(rng)) for p in list(found)[:5]] + [(random_key(rng),), (7,)]
    return sorted(found, key=repr) + misses


def _decimal(text: str) -> bool:
    return text.removeprefix("-").isdecimal()


def test_get_agrees_with_glom_on_exact_paths() -> None:
    glom = pytest.importorskip("glom")
    compared = 0
    for seed in SEEDS:
        rng = random.Random(seed)
        tree = random_tree(rng)
        for segments in _paths(tree, rng):
            mine = d.get(tree, segments, MISS)
            parent = d.get(tree, segments[:-1], MISS) if len(segments) > 1 else tree
            if isinstance(parent, str):
                continue  # glom indexes into strings; dotreach never does (documented)
            last = segments[-1]
            if isinstance(parent, list) and isinstance(last, str) and not _decimal(last):
                assert mine is MISS  # glom also takes " 0", "+1" and "1_0" (documented)
                continue
            theirs = glom.glom(tree, glom.Path(*segments), default=MISS)
            assert mine is theirs or mine == theirs, (seed, segments)
            compared += 1
    assert compared > 2000


def test_string_paths_agree_with_glom_where_keys_are_plain() -> None:
    glom = pytest.importorskip("glom")
    for seed in SEEDS:
        rng = random.Random(seed)
        tree = random_tree(rng)
        for segments, value in d.walk(tree):
            text = ".".join(str(s) for s in segments)
            if any(not str(s).isalnum() for s in segments):
                continue  # glom has its own escaping and wildcard rules for symbols
            assert d.get(tree, text) == glom.glom(tree, text) == value, (seed, text)


def _jmespath(segments: tuple[Any, ...]) -> str:
    parts = []
    for segment in segments:
        if isinstance(segment, int):
            parts.append(f"[{segment}]")
        else:
            parts.append(("." if parts else "") + json.dumps(segment))
    return "".join(parts)


def test_get_agrees_with_jmespath_including_negative_indices() -> None:
    jmespath = pytest.importorskip("jmespath")
    for seed in SEEDS:
        rng = random.Random(seed)
        tree = random_tree(rng)
        if not isinstance(tree, dict):
            continue
        for segments, value in d.walk(tree):
            assert jmespath.search(_jmespath(segments), tree) == value, (seed, segments)
            lists = [i for i, s in enumerate(segments) if isinstance(s, int)]
            if lists:
                i = lists[-1]
                size = len(d.get(tree, segments[:i]))
                negative = (*segments[:i], int(segments[i]) - size, *segments[i + 1 :])
                assert d.get(tree, negative) == jmespath.search(_jmespath(negative), tree)


def test_one_level_wildcards_agree_with_jmespath_projections() -> None:
    jmespath = pytest.importorskip("jmespath")
    checked = 0
    for seed in SEEDS:
        rng = random.Random(seed)
        tree = {"root": random_tree(rng)}
        for segments, _ in d.walk(tree):
            for n in range(1, len(segments)):
                prefix = segments[:n]
                node = d.get(tree, prefix)
                star = "[*]" if isinstance(node, list) else ".*"
                theirs = jmespath.search(_jmespath(prefix) + star, tree)
                found = d.glob(tree, (*prefix, "*"), escape=True)
                mine = [v for v in found.values() if v is not None]
                assert mine == theirs, (seed, prefix)  # projections drop nulls
                checked += 1
    assert checked > 500
