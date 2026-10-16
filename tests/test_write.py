from __future__ import annotations

from typing import Any

import pytest

import dotreach as d


def test_set_create_lists_builds_and_appends() -> None:
    data: dict[str, Any] = {}
    d.set(data, "a.0.b", 1, create_lists=True)
    d.set(data, "a.1.b", 2, create_lists=True)
    d.set(data, "a.0.c", 3, create_lists=True)
    assert data == {"a": [{"b": 1, "c": 3}, {"b": 2}]}


def test_set_create_lists_negative_next_segment_makes_a_dict() -> None:
    assert d.set({}, "a.-1", 1, create_lists=True) == {"a": {"-1": 1}}


def test_set_create_lists_gap_raises_index_error() -> None:
    with pytest.raises(d.PathIndexError) as info:
        d.set({"a": []}, "a.2.b", 1, create_lists=True)
    assert info.value.segment == "2" and info.value.position == 1


def test_set_without_create_lists_keeps_dict_behaviour() -> None:
    assert d.set({}, "a.0", 1) == {"a": {"0": 1}}


def test_set_refuses_to_replace_a_read_only_container() -> None:
    data: dict[str, Any] = {"a": (1, 2)}
    with pytest.raises(d.PathTypeError) as info:
        d.set(data, "a.b", 1)
    assert data == {"a": (1, 2)} and (info.value.segment, info.value.position) == ("b", 1)
    assert d.set_copy(data, "a.0", 9) == {"a": (9, 2)}


def test_set_replaces_a_scalar_in_a_list_like_one_in_a_dict() -> None:
    assert d.set({"a": [1]}, "a.0.b", 2) == {"a": [{"b": 2}]}
    assert d.set({"a": 1}, "a.b", 2) == {"a": {"b": 2}}
    assert d.set({"a": [None]}, "a.0.0", 2, create_lists=True) == {"a": [[2]]}


def test_set_intermediate_list_index_out_of_range() -> None:
    with pytest.raises(d.PathIndexError):
        d.set({"a": [{}]}, "a.4.b", 2)


def test_set_negative_index_replaces_from_the_end() -> None:
    data = {"a": [1, 2]}
    d.set(data, "a.-1", 9)
    assert data == {"a": [1, 9]}


def test_set_with_tuple_path_and_int_key() -> None:
    data: dict[Any, Any] = {}
    d.set(data, (1, "x"), "v")
    assert data == {1: {"x": "v"}}


def test_delete_negative_index_and_missing_paths() -> None:
    data = {"a": [1, 2, 3]}
    d.delete(data, "a.-1")
    assert data == {"a": [1, 2]}
    for path in ("a.5", "a.x", "z.y", "a.0.q"):
        with pytest.raises(d.PathNotFoundError):
            d.delete(data, path)
        assert d.delete(data, path, missing_ok=True) is data


def test_delete_from_a_read_only_container_is_a_type_error() -> None:
    from types import MappingProxyType

    for data, path in (({"a": MappingProxyType({"b": 1})}, "a.b"), ({"t": (1, 2)}, "t.0")):
        with pytest.raises(d.PathTypeError):
            d.delete(data, path, missing_ok=True)
        with pytest.raises(d.PathTypeError):
            d.pop(data, path, None)
    assert d.delete({"t": (1, 2)}, "t.5", missing_ok=True) == {"t": (1, 2)}


def test_pop_without_default_raises() -> None:
    with pytest.raises(d.PathNotFoundError):
        d.pop({}, "a")


def test_setdefault_creates_lists_when_asked() -> None:
    data: dict[str, Any] = {}
    assert d.setdefault(data, "a.0", "x", create_lists=True) == "x"
    assert data == {"a": ["x"]}


def test_setdefault_none_default() -> None:
    data: dict[str, Any] = {}
    assert d.setdefault(data, "a") is None and data == {"a": None}


def test_get_as_typed_results() -> None:
    data = {"s": "x", "f": 1.5, "l": [1], "b": False}
    assert d.get_as(data, "s", str) == "x"
    assert d.get_as(data, "f", float) == 1.5
    assert d.get_as(data, "l", list) == [1]
    assert d.get_as(data, "b", bool) is False
    with pytest.raises(d.PathTypeError):
        d.get_as(data, "b", float)
