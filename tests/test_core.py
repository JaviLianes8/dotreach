from __future__ import annotations

import pytest

import dotreach


def test_get_reaches_a_nested_mapping_key() -> None:
    assert dotreach.get({"a": {"b": {"c": 1}}}, "a.b.c") == 1


def test_get_uses_integer_segments_as_list_indices() -> None:
    assert dotreach.get({"a": {"b": [10, 20, 30]}}, "a.b.1") == 20


def test_get_supports_negative_list_indices() -> None:
    assert dotreach.get({"items": [1, 2, 3]}, "items.-1") == 3


def test_get_returns_default_when_the_path_is_absent() -> None:
    assert dotreach.get({"a": 1}, "a.b.c", default=None) is None


def test_get_without_a_default_raises_key_error() -> None:
    with pytest.raises(KeyError):
        dotreach.get({"a": 1}, "missing")


def test_get_does_not_index_into_strings() -> None:
    assert dotreach.get({"name": "hi"}, "name.0", default="fallback") == "fallback"


def test_get_treats_a_string_key_as_a_key_not_an_index() -> None:
    assert dotreach.get({"0": "zero"}, "0") == "zero"


def test_get_accepts_a_custom_separator() -> None:
    assert dotreach.get({"a": {"b": 2}}, "a/b", sep="/") == 2


def test_empty_path_is_rejected() -> None:
    with pytest.raises(ValueError):
        dotreach.get({"a": 1}, "")


def test_has_reports_presence() -> None:
    data = {"a": {"b": None}}
    assert dotreach.has(data, "a.b") is True
    assert dotreach.has(data, "a.c") is False


def test_set_creates_missing_intermediate_dicts() -> None:
    data: dict[str, object] = {}
    dotreach.set(data, "a.b.c", 9)
    assert data == {"a": {"b": {"c": 9}}}


def test_set_overwrites_a_scalar_in_the_path_with_a_dict() -> None:
    data: dict[str, object] = {"a": 1}
    dotreach.set(data, "a.b", 2)
    assert data == {"a": {"b": 2}}


def test_set_updates_an_existing_list_element() -> None:
    data = {"items": [1, 2, 3]}
    dotreach.set(data, "items.1", 99)
    assert data["items"] == [1, 99, 3]


def test_set_out_of_range_list_index_raises_index_error() -> None:
    with pytest.raises(IndexError):
        dotreach.set({"items": [1]}, "items.5", 0)


def test_set_rejects_a_non_integer_index_into_a_list() -> None:
    with pytest.raises(TypeError):
        dotreach.set({"items": [1]}, "items.x", 0)


def test_set_returns_the_root_object() -> None:
    data: dict[str, object] = {}
    assert dotreach.set(data, "a", 1) is data


def test_delete_removes_a_nested_key() -> None:
    data = {"a": {"b": {"c": 1}, "d": 2}}
    dotreach.delete(data, "a.b.c")
    assert data == {"a": {"b": {}, "d": 2}}


def test_delete_removes_a_list_element() -> None:
    data = {"items": [1, 2, 3]}
    dotreach.delete(data, "items.0")
    assert data["items"] == [2, 3]


def test_delete_missing_path_raises_key_error() -> None:
    with pytest.raises(KeyError):
        dotreach.delete({"a": 1}, "a.b.c")


def test_delete_missing_path_is_silent_when_allowed() -> None:
    data = {"a": 1}
    assert dotreach.delete(data, "nope", missing_ok=True) is data
    assert data == {"a": 1}


def test_tuples_are_readable() -> None:
    assert dotreach.get({"pair": (10, 20)}, "pair.1") == 20


def test_set_on_an_immutable_root_raises_type_error() -> None:
    with pytest.raises(TypeError):
        dotreach.set((1, 2, 3), "1", 9)
