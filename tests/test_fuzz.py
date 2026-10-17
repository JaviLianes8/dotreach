"""Seeded property tests: every operation checked against plain Python on random data."""

from __future__ import annotations

import copy
import functools
import operator
import random
from typing import Any

import pytest
from conftest import KEY_CHARS, random_key, random_tree

import dotreach as d

SEEDS = range(500)


def native(tree: Any, segments: tuple[Any, ...]) -> Any:
    """The independent oracle: Python's own item access, one segment at a time."""
    return functools.reduce(operator.getitem, segments, tree)


def test_every_leaf_reads_back_by_segments_and_by_escaped_string() -> None:
    for seed in SEEDS:
        tree = random_tree(random.Random(seed))
        for segments, value in d.walk(tree):
            assert d.get(tree, segments) is native(tree, segments) is value
            text = d.join_path(segments)
            assert d.get(tree, text, escape=True) is value
            assert d.split_path(text) == [str(s) for s in segments]


def test_flatten_and_unflatten_round_trip_dicts_with_lists() -> None:
    for seed in SEEDS:
        tree = random_tree(random.Random(seed))
        if not isinstance(tree, dict) or "" in str(list(d.walk(tree))):
            continue
        flat = d.flatten(tree, escape=True)
        assert flat == dict(d.leaves(tree, escape=True))
        has_digit_keys = any(
            isinstance(s, str) and s.removeprefix("-").isdecimal()
            for segments, _ in d.walk(tree)
            for s in segments
        )
        if not has_digit_keys:
            assert d.unflatten(flat, escape=True, create_lists=True) == tree


def _outcome(call: Any, *args: Any, **kwargs: Any) -> Any:
    try:
        return call(*args, **kwargs)
    except d.DotreachError as error:
        return type(error)


def test_set_copy_equals_set_on_a_deep_copy_and_never_mutates() -> None:
    for seed in SEEDS:
        rng = random.Random(seed)
        tree = {"root": random_tree(rng)}
        snapshot = copy.deepcopy(tree)
        for segments, _ in list(d.walk(tree)):
            path = (*segments, random_key(rng)) if rng.random() < 0.3 else segments
            expected = _outcome(d.set, copy.deepcopy(tree), path, "NEW")
            assert _outcome(d.set_copy, tree, path, "NEW") == expected
            if isinstance(expected, dict):
                assert d.get(expected, path) == "NEW"
            assert tree == snapshot


def test_delete_copy_equals_delete_and_pop_returns_the_value() -> None:
    for seed in SEEDS:
        tree = {"root": random_tree(random.Random(seed))}
        for segments, value in list(d.walk(tree)):
            mine = copy.deepcopy(tree)
            assert d.pop(mine, segments) == value
            assert d.delete_copy(tree, segments) == mine == d.delete(copy.deepcopy(tree), segments)


def test_glob_double_star_finds_every_leaf_and_star_every_child() -> None:
    for seed in SEEDS:
        tree = random_tree(random.Random(seed))
        everything = d.glob(tree, "**", escape=True)
        for segments, value in d.walk(tree):
            assert everything[d.join_path(segments)] is value
        if isinstance(tree, (dict, list)):
            children = dict(enumerate(tree)) if isinstance(tree, list) else tree
            expected = {d.join_path([key]): child for key, child in children.items()}
            assert d.glob(tree, "*", escape=True) == expected


@pytest.mark.parametrize("sep", [".", "/", "::", "->", "\\", ".\\"])
def test_split_inverts_join_for_random_segments(sep: str) -> None:
    rng = random.Random(sep)
    alphabet = KEY_CHARS + sep
    for _ in range(2000):
        segments = ["".join(rng.choice(alphabet) for _ in range(rng.randint(0, 5)))]
        segments += [str(rng.randint(-3, 3)) for _ in range(rng.randint(0, 2))]
        if "\\" in sep:  # the escape character cannot also separate
            with pytest.raises(d.InvalidPathError):
                d.join_path(segments, sep)
            continue
        assert d.split_path(d.join_path(segments, sep), sep) == segments


def test_random_text_paths_only_raise_dotreach_errors() -> None:
    rng = random.Random(7)
    for seed in range(300):
        tree = random_tree(random.Random(seed))
        for _ in range(20):
            path = "".join(rng.choice(KEY_CHARS + "²٣*") for _ in range(rng.randint(0, 8)))
            calls: list[tuple[Any, ...]] = [
                (d.get, tree, path, None),
                (d.has, tree, path),
                (d.glob, tree, path),
                (d.set_copy, tree, path, 1),
                (d.delete_copy, tree, path),
                (d.set, copy.deepcopy(tree), path, 1),
                (d.pop, copy.deepcopy(tree), path, None),
            ]
            for function, *args in calls:
                try:
                    function(*args, escape=rng.random() < 0.5)
                except d.DotreachError as error:
                    assert len(str(error)) < 300
