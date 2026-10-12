from __future__ import annotations

import pytest

import dotreach as d


def test_split_path_plain_and_empty_segments() -> None:
    assert d.split_path("a.b.c") == ["a", "b", "c"]
    assert d.split_path("a..b") == ["a", "", "b"]


def test_split_path_escapes() -> None:
    assert d.split_path(r"a\.b.c") == ["a.b", "c"]
    assert d.split_path(r"a\\.b") == ["a\\", "b"]
    assert d.split_path(r"a\b") == ["a\\b"]
    assert d.split_path("a\\") == ["a\\"]


def test_split_path_multi_character_separator() -> None:
    assert d.split_path(r"a::b\::c", "::") == ["a", "b::c"]


def test_join_path_escapes_and_renders_integers() -> None:
    assert d.join_path(["a.b", 0, "c\\d"]) == r"a\.b.0.c\\d"


def test_empty_separator_is_rejected() -> None:
    with pytest.raises(d.InvalidPathError):
        d.split_path("a", "")
    with pytest.raises(d.InvalidPathError):
        d.join_path(["a"], "")
    with pytest.raises(d.InvalidPathError):
        d.get({"a": 1}, "a", sep="")


def test_without_escape_backslashes_are_literal() -> None:
    assert d.get({"a\\": {"b": 1}}, r"a\.b") == 1


def test_sequence_paths_use_exact_keys() -> None:
    data = {1: "int key", "a.b": {"c": [5, 6]}}
    assert d.get(data, [1]) == "int key"
    assert d.get(data, ("a.b", "c", -1)) == 6
    assert d.get(data, ("a.b", "c", "0")) == 5


@pytest.mark.parametrize("bad", [(), [], b"a.b", ("a", 1.5), ("a", True), 5])
def test_malformed_paths_are_rejected(bad: object) -> None:
    with pytest.raises(d.InvalidPathError):
        d.get({}, bad)  # type: ignore[arg-type]


def test_unicode_digits_are_not_indices() -> None:
    assert d.get(["x"], "²", default="none") == "none"


def test_error_messages_name_the_segment() -> None:
    with pytest.raises(d.PathNotFoundError) as info:
        d.get({"a": {"b": 1}}, "a.x.y")
    assert "'x'" in str(info.value) and "segment 1" in str(info.value)
    assert info.value.path == "a.x.y"


def test_custom_separator_with_escape() -> None:
    assert d.get({"a/b": {"c": 1}}, r"a\/b/c", sep="/", escape=True) == 1
