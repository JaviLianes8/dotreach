"""Contract: the complete promise of every public name, one focused check per claim."""

from __future__ import annotations

import importlib.resources
from types import MappingProxyType
from typing import NamedTuple

import pytest

import dotreach as d


class Point(NamedTuple):
    x: int
    y: int


PUBLIC_API: list[str] = [
    "DotreachError",
    "InvalidPathError",
    "Key",
    "PathIndexError",
    "PathLike",
    "PathNotFoundError",
    "PathTypeError",
    "delete",
    "delete_copy",
    "flatten",
    "get",
    "get_as",
    "glob",
    "has",
    "join_path",
    "leaves",
    "pop",
    "set",
    "set_copy",
    "setdefault",
    "split_path",
    "unflatten",
    "walk",
]


def test_all_lists_exactly_the_public_api() -> None:
    assert sorted(d.__all__) == sorted(PUBLIC_API)
    assert all(hasattr(d, name) for name in d.__all__)


def test_version_is_a_three_part_string() -> None:
    parts = d.__version__.split(".")
    assert len(parts) == 3 and all(part.isdigit() for part in parts)


def test_the_package_ships_type_information() -> None:
    assert importlib.resources.files("dotreach").joinpath("py.typed").is_file()


def test_error_hierarchy_keeps_builtin_compatibility() -> None:
    assert issubclass(d.PathNotFoundError, KeyError)
    assert issubclass(d.PathTypeError, TypeError)
    assert issubclass(d.PathIndexError, IndexError)
    assert issubclass(d.InvalidPathError, ValueError)
    for cls in (d.PathNotFoundError, d.PathTypeError, d.PathIndexError, d.InvalidPathError):
        assert issubclass(cls, d.DotreachError)


def test_get_contract() -> None:
    data = {"a": [{"b": 1}], "0": "key"}
    assert d.get(data, "a.0.b") == 1
    assert d.get(data, ("a", -1, "b")) == 1
    assert d.get(data, "0") == "key"
    assert d.get(data, "a.9", default=None) is None
    with pytest.raises(d.PathNotFoundError) as info:
        d.get(data, "a.0.c")
    assert (info.value.segment, info.value.position, info.value.args) == ("c", 2, ("a.0.c",))
    with pytest.raises(d.InvalidPathError):
        d.get(data, "")


def test_has_contract() -> None:
    assert d.has({"a": None}, "a") and not d.has({"a": None}, "a.b")


def test_get_as_contract() -> None:
    assert d.get_as({"n": 3}, "n", int) == 3
    assert d.get_as({}, "n", int, 7) == 7
    with pytest.raises(d.PathTypeError):
        d.get_as({"n": True}, "n", int)
    with pytest.raises(d.PathTypeError):
        d.get_as({"n": "3"}, "n", int, 0)
    with pytest.raises(d.PathNotFoundError):
        d.get_as({}, "n", int)


def test_set_contract() -> None:
    data: dict[str, object] = {"a": 1}
    assert d.set(data, "a.b", 2) is data and data == {"a": {"b": 2}}
    assert d.set({}, "t.0.x", 1, create_lists=True) == {"t": [{"x": 1}]}
    with pytest.raises(d.PathIndexError):
        d.set({"t": []}, "t.3", 1)
    with pytest.raises(d.PathTypeError):
        d.set({"t": []}, "t.x", 1)


def test_delete_and_pop_contract() -> None:
    data = {"a": {"b": 1, "c": [1, 2]}}
    assert d.delete(data, "a.b") is data and data == {"a": {"c": [1, 2]}}
    assert d.delete(data, "nope", missing_ok=True) is data
    assert d.pop(data, "a.c.-1") == 2 and data == {"a": {"c": [1]}}
    assert d.pop(data, "nope", "dflt") == "dflt"
    with pytest.raises(d.PathNotFoundError):
        d.delete(data, "nope")


def test_setdefault_contract() -> None:
    data: dict[str, object] = {"a": {"b": 1}}
    assert d.setdefault(data, "a.b", 9) == 1
    assert d.setdefault(data, "a.c", 9) == 9 and d.get(data, "a.c") == 9


def test_copy_functions_never_mutate_and_share_untouched_branches() -> None:
    other = {"deep": [1]}
    data = {"a": {"b": 1}, "other": other}
    new = d.set_copy(data, "a.b", 2)
    assert data == {"a": {"b": 1}, "other": other} and new["a"] == {"b": 2}
    assert new["other"] is other
    assert d.delete_copy(data, "a.b") == {"a": {}, "other": other} and data["a"] == {"b": 1}
    point = Point(1, 2)
    assert d.set_copy(point, "0", 5) == point._replace(x=5)
    assert type(d.set_copy(point, "0", 5)) is type(point)
    assert d.set_copy(MappingProxyType({"k": 1}), "k", 2) == {"k": 2}


def test_path_helpers_round_trip() -> None:
    segments = ["a.b", "c\\", "", "d"]
    assert d.split_path(d.join_path(segments)) == segments
    assert d.get({"a.b": 1}, "a\\.b", escape=True) == 1


def test_walk_leaves_flatten_unflatten_contract() -> None:
    data = {"a": {"b": [1, {}]}, "k.e": 2}
    assert list(d.walk(data)) == [(("a", "b", 0), 1), (("a", "b", 1), {}), (("k.e",), 2)]
    assert dict(d.leaves(data)) == {"a.b.0": 1, "a.b.1": {}, "k.e": 2}
    flat = d.flatten(data, escape=True)
    assert d.unflatten(flat, escape=True, create_lists=True) == data
    with pytest.raises(d.PathTypeError):
        d.unflatten({"a": 1, "a.b": 2})


def test_glob_contract() -> None:
    data = {"u": [{"n": "a"}, {"n": "b"}]}
    assert d.glob(data, "u.*.n") == {"u.0.n": "a", "u.1.n": "b"}
    assert d.glob(data, "**.n") == {"u.0.n": "a", "u.1.n": "b"}
    assert d.glob(data, "u.-1") == {"u.1": {"n": "b"}}
    assert d.glob(data, "x.*") == {}
