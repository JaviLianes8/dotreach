from __future__ import annotations

import copy
from collections import OrderedDict
from typing import Any

import pytest

import dotreach as d


def test_set_copy_creates_missing_levels_and_lists() -> None:
    data: dict[str, Any] = {}
    assert d.set_copy(data, "a.b", 1) == {"a": {"b": 1}} and data == {}
    assert d.set_copy(data, "t.0", "x", create_lists=True) == {"t": ["x"]}


def test_set_copy_rebuilds_tuples_and_keeps_dict_subclasses() -> None:
    data = {"t": (1, (2, 3))}
    assert d.set_copy(data, "t.1.0", 9) == {"t": (1, (9, 3))}
    ordered = OrderedDict(a=1)
    assert type(d.set_copy(ordered, "a", 2)) is OrderedDict


def test_set_copy_appends_to_tuple_with_create_lists() -> None:
    assert d.set_copy((1,), "1", 2, create_lists=True) == (1, 2)


def test_set_copy_errors() -> None:
    with pytest.raises(d.PathIndexError):
        d.set_copy([1], "5", 0)
    with pytest.raises(d.PathTypeError):
        d.set_copy([1], "x", 0)
    with pytest.raises(d.PathTypeError):
        d.set_copy(5, "a", 0)


def test_delete_copy_on_lists_tuples_and_missing() -> None:
    data = {"a": [1, 2, 3], "t": (1, 2)}
    snapshot = copy.deepcopy(data)
    assert d.delete_copy(data, "a.-1") == {"a": [1, 2], "t": (1, 2)}
    assert d.delete_copy(data, "t.0") == {"a": [1, 2, 3], "t": (2,)}
    assert data == snapshot
    with pytest.raises(d.PathNotFoundError):
        d.delete_copy(data, "a.9")
    assert d.delete_copy(data, "x.y", missing_ok=True) is data
    with pytest.raises(d.PathNotFoundError):
        d.delete_copy("text", "0")


def test_walk_empty_and_scalar_roots() -> None:
    assert list(d.walk({})) == []
    assert list(d.walk(5)) == []
    assert list(d.walk("abc")) == []


def test_walk_rejects_cycles() -> None:
    data: dict[str, Any] = {}
    data["self"] = data
    with pytest.raises(ValueError):
        list(d.walk(data))
    with pytest.raises(ValueError):
        d.glob(data, "**")


def test_shared_subtrees_are_not_cycles() -> None:
    shared = {"x": 1}
    assert d.flatten({"a": shared, "b": shared}) == {"a.x": 1, "b.x": 1}


def test_flatten_collision_raises_unless_escaped() -> None:
    data = {"a.b": 1, "a": {"b": 2}}
    with pytest.raises(ValueError):
        d.flatten(data)
    assert d.flatten(data, escape=True) == {"a\\.b": 1, "a.b": 2}


def test_leaves_with_custom_separator() -> None:
    assert dict(d.leaves({"a": {"b": 1}}, sep="/")) == {"a/b": 1}


def test_unflatten_dicts_only_by_default_and_tuple_keys() -> None:
    assert d.unflatten({"a.0": 1}) == {"a": {"0": 1}}
    assert d.unflatten({("a", "b.c"): 1}) == {"a": {"b.c": 1}}


def test_unflatten_conflicts() -> None:
    cases: list[dict[Any, Any]] = [
        {"a.b": 1, "a": 2},
        {"a": {}, "a.b": 1},
        {"a\\.b": 1, ("a.b",): 2},
    ]
    for flat in cases:
        with pytest.raises(d.PathTypeError):
            d.unflatten(flat, escape=True)


def test_unflatten_merges_siblings() -> None:
    assert d.unflatten({"a.b": 1, "a.c": 2}) == {"a": {"b": 1, "c": 2}}


def test_glob_double_star_matches_every_level_including_root() -> None:
    data = {"a": {"b": 1}}
    assert d.glob(data, "**") == {"": data, "a": {"b": 1}, "a.b": 1}
    assert d.glob(data, "a.**.b") == {"a.b": 1}


def test_glob_star_over_list_and_scalar() -> None:
    assert d.glob([10, 20], "*") == {"0": 10, "1": 20}
    assert d.glob({"a": 1}, "a.*") == {}


def test_glob_escaped_keys_and_tuple_patterns() -> None:
    data = {"a.b": {"c": 1}}
    assert d.glob(data, r"a\.b.*", escape=True) == {r"a\.b.c": 1}
    assert d.glob(data, ("a.b", "*")) == {"a.b.c": 1}
