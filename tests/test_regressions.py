"""Edge cases found in review, each pinned so it cannot come back."""

from __future__ import annotations

import copy
import io
import pickle
from typing import Any, NamedTuple

import pytest

import dotreach as d
from dotreach._cli import main

BACKSLASH = "\\"


class Pair(NamedTuple):
    a: int
    b: int


@pytest.mark.parametrize(
    "error",
    [
        d.PathNotFoundError("msg", "a.b", "b", 1),
        d.PathTypeError("msg", ("a", 0), 0, 1),
        d.PathIndexError("msg", "a.5", "5", 1),
        d.InvalidPathError("msg", ""),
        d.DotreachError("msg"),
    ],
)
def test_errors_survive_pickle_and_copy(error: d.DotreachError) -> None:
    for clone in (pickle.loads(pickle.dumps(error)), copy.copy(error)):
        assert type(clone) is type(error)
        assert (clone.message, clone.path, clone.segment, clone.position) == (
            error.message,
            error.path,
            error.segment,
            error.position,
        )
        assert clone.args == error.args and str(clone) == str(error)


def test_raised_not_found_error_pickles_with_its_path() -> None:
    with pytest.raises(d.PathNotFoundError) as info:
        d.get({}, "a.b")
    clone = pickle.loads(pickle.dumps(info.value))
    assert clone.args == ("a.b",) and clone.segment == "a"


def test_named_tuple_length_change_becomes_plain_tuple() -> None:
    assert d.delete_copy({"p": Pair(1, 2)}, "p.0") == {"p": (2,)}
    grown = d.set_copy({"p": Pair(1, 2)}, "p.2", 5, create_lists=True)
    assert grown == {"p": (1, 2, 5)} and type(grown["p"]) is tuple


@pytest.mark.parametrize(
    ("segments", "sep"),
    [
        (["a:", "b"], "::"),
        ([":b", "a::"], "::"),
        (["x" + BACKSLASH], "."),
        (["a/b" + BACKSLASH + "/"], "/"),
        (["", ""], "."),
        (["a-b", "c"], "->"),
    ],
)
def test_split_and_join_are_exact_inverses(segments: list[str], sep: str) -> None:
    assert d.split_path(d.join_path(segments, sep), sep) == segments


def test_join_path_rejects_an_empty_list() -> None:
    with pytest.raises(d.InvalidPathError):
        d.join_path([])


def test_old_style_escape_still_reads_with_a_multi_character_separator() -> None:
    assert d.split_path("a::b" + BACKSLASH + "::c", "::") == ["a", "b::c"]


def test_unflatten_never_shares_empty_containers_with_the_input() -> None:
    empty: dict[str, Any] = {}
    result = d.unflatten({"a": empty})
    assert result == {"a": {}} and result["a"] is not empty


def test_unflatten_handles_many_shared_prefix_keys() -> None:
    flat = {f"cfg.k{i}": i for i in range(20000)}
    assert len(d.unflatten(flat)["cfg"]) == 20000


def test_glob_refuses_colliding_render() -> None:
    data = {"a.b": 1, "a": {"b": 2}}
    with pytest.raises(ValueError):
        d.glob(data, "**")
    assert d.glob(data, "**", escape=True)["a\\.b"] == 1


class Guarded(dict[str, Any]):
    def __delitem__(self, key: str) -> None:
        raise PermissionError("guarded")


def test_delete_and_pop_go_through_delitem() -> None:
    with pytest.raises(PermissionError):
        d.delete({"g": Guarded(k=1)}, "g.k")
    with pytest.raises(PermissionError):
        d.pop({"g": Guarded(k=1)}, "g.k")


def test_in_place_with_stdin_fails_before_reading(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    class Untouchable(io.StringIO):
        def read(self, size: int | None = -1) -> str:
            raise AssertionError("stdin must not be read")

    monkeypatch.setattr("sys.stdin", Untouchable())
    assert main(["delete", "a", "-i"]) == 1
    assert "--in-place" in capsys.readouterr().err
