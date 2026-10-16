"""Contract: the 1.0.0 promises beyond the basics, one claim per test."""

from __future__ import annotations

import pickle
from collections.abc import Callable
from types import MappingProxyType
from typing import Any

import pytest

import dotreach as d


def test_public_errors_show_and_pickle_under_the_package_name() -> None:
    for cls in (
        d.DotreachError,
        d.InvalidPathError,
        d.PathIndexError,
        d.PathNotFoundError,
        d.PathTypeError,
        d.StructureError,
    ):
        assert cls.__module__ == "dotreach"
        error = cls("m", "p") if cls is not d.PathNotFoundError else cls("m", "p", "p", 0)
        assert type(pickle.loads(pickle.dumps(error))) is cls


def test_structure_error_is_a_value_error_for_collisions_and_cycles() -> None:
    assert issubclass(d.StructureError, ValueError)
    assert issubclass(d.StructureError, d.DotreachError)
    with pytest.raises(d.StructureError) as info:
        d.flatten({"a.b": 1, "a": {"b": 2}})
    assert info.value.path == "a.b"
    loop: list[Any] = []
    loop.append(loop)
    for call in (d.flatten, lambda x: list(d.walk(x)), lambda x: d.glob(x, "*.*")):
        with pytest.raises(d.StructureError):
            call(loop)


def test_set_and_set_copy_follow_one_rule_for_values_on_the_path() -> None:
    for data in ({"a": 5}, {"a": [5]}, {"a": None}):
        path = "a.0.x" if isinstance(data["a"], list) else "a.x"
        assert d.set_copy(data, path, 1) == d.set(dict(data), path, 1)
    for read_only in ((1, 2), MappingProxyType({"0": 1})):
        with pytest.raises(d.PathTypeError) as info:
            d.set({"a": read_only}, "a.0", 9)
        assert "set_copy" in str(info.value) and info.value.position == 1
        assert d.set_copy({"a": read_only}, "a.0", 9)["a"] in ((9, 2), {"0": 9})


def test_set_on_a_read_only_or_scalar_root_is_a_type_error() -> None:
    roots: tuple[Any, ...] = ((1,), MappingProxyType({}), 5, "text", None)
    for root in roots:
        with pytest.raises(d.PathTypeError):
            d.set(root, "0", 1)


def test_delete_names_read_only_containers_even_with_missing_ok() -> None:
    with pytest.raises(d.PathTypeError) as info:
        d.delete({"t": (1,)}, "t.0", missing_ok=True)
    assert "delete_copy" in str(info.value)
    assert d.delete_copy({"t": (1,)}, "t.0") == {"t": ()}


def test_a_separator_with_a_backslash_is_refused_only_when_escaping() -> None:
    assert d.get({"a": {"b": 1}}, "a\\b", sep="\\") == 1
    calls: list[Callable[[], object]] = [
        lambda: d.get({}, "a", sep="\\", escape=True),
        lambda: d.split_path("a", "x\\"),
        lambda: d.join_path(["a"], "\\"),
        lambda: d.flatten({"a": 1}, sep="\\", escape=True),
    ]
    for call in calls:
        with pytest.raises(d.InvalidPathError):
            call()


def test_join_path_takes_only_str_and_int_segments() -> None:
    bads: list[list[Any]] = [[True], [1.5], [None], [("a",)]]
    for bad in bads:
        with pytest.raises(d.InvalidPathError):
            d.join_path(bad)
    assert d.join_path(["a", 0, -1]) == "a.0.-1"


def test_index_rule_is_decimal_text_with_an_optional_minus() -> None:
    data = ["x", "y"]
    for good, value in (("1", "y"), ("-1", "y"), ("01", "y"), ("-0", "x"), (chr(0x661), "y")):
        assert d.get(data, good) == value
    for bad in ("+1", " 1", "1 ", "1_0", "1.0", chr(0xB9), "-", "", "--1"):
        assert d.get(data, (bad,), None) is None and not d.has(data, (bad,))


def test_message_quotes_are_bounded_but_attributes_are_whole() -> None:
    huge = "k" * 10_000
    with pytest.raises(d.PathNotFoundError) as info:
        d.get({}, huge)
    assert len(str(info.value)) < 200 and info.value.path == huge
    assert info.value.args == (huge,) and info.value.segment == huge


def test_glob_reports_each_path_once_in_depth_first_order() -> None:
    data = {"a": {"b": {"c": 1}}, "d": [{"c": 2}]}
    assert list(d.glob(data, "**.**.c")) == ["a.b.c", "d.0.c"]
    assert list(d.glob(data, "**")) == ["", "a", "a.b", "a.b.c", "d", "d.0", "d.0.c"]


def test_bytearray_is_a_value_for_every_function() -> None:
    data = {"a": bytearray(b"xy")}
    assert d.get(data, "a.0", None) is None and not d.has(data, "a.0")
    assert d.set({"a": bytearray(b"xy")}, "a.0", 65) == {"a": {"0": 65}}
    assert d.set_copy(data, "a.0", 65) == {"a": {"0": 65}}
    assert d.set({"a": bytearray(b"xy")}, "a.0.b", 1) == {"a": {"0": {"b": 1}}}
    with pytest.raises(d.PathTypeError):
        d.set(bytearray(b"xy"), "0", 65)
    assert list(d.walk(data)) == [(("a",), bytearray(b"xy"))]


def test_bytearray_and_bytes_are_never_entered_by_copies_deletes_or_globs() -> None:
    for blob in (bytearray(b"xy"), b"xy"):
        data = {"a": blob}
        with pytest.raises(d.PathTypeError):
            d.set_copy(blob, "0", 65)
        assert d.delete(data, "a.0", missing_ok=True) is data and data["a"] == blob
        with pytest.raises(d.PathNotFoundError):
            d.delete({"a": blob}, "a.0")
        with pytest.raises(d.PathNotFoundError):
            d.delete_copy(data, "a.0")
        assert d.delete_copy(data, "a.0", missing_ok=True) is data
        assert d.glob(data, "a.*") == {} and d.get(data, "a.0", None) is None
        assert d.pop(data, "a.0", "none") == "none"


def test_bytes_like_paths_are_invalid() -> None:
    for path in (b"a", bytearray(b"a")):
        with pytest.raises(d.InvalidPathError):
            d.get({97: 1, "a": 1}, path)


def test_an_int_key_equal_to_the_dict_length_is_a_key_not_an_append() -> None:
    assert d.set({1: "a"}, (1,), "b") == {1: "b"}
    assert d.set_copy({1: "a"}, (1,), "b") == {1: "b"}
    assert d.set({0: {}}, (0, 1), "b") == {0: {1: "b"}}


def test_glob_reports_a_dict_key_that_looks_negative_as_written() -> None:
    assert d.glob({"-1": 5}, "-1") == {"-1": 5}
    assert d.glob({"x": {"-1": 5}}, "*.-1") == {"x.-1": 5}


def test_writing_into_a_read_only_root_points_to_the_copy_functions() -> None:
    for root in ((1,), MappingProxyType({"0": 1})):
        with pytest.raises(d.PathTypeError, match=r"read-only .*set_copy"):
            d.set(root, "0", 2)


def test_unflatten_keeps_int_keys_from_sequence_paths() -> None:
    assert d.unflatten({(1, "a"): 2}) == {1: {"a": 2}}
