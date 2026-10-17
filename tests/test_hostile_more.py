"""Hostile input, second part: odd value types, unprintable values and strict JSON."""

from __future__ import annotations

import json
from collections import UserString
from pathlib import Path
from types import MappingProxyType
from typing import Any

import pytest

import dotreach as d
from dotreach._cli import main

HUGE = 10**5000  # str() refuses ints past 4300 digits


def test_user_strings_are_text_and_never_entered() -> None:
    data = {"name": UserString("Ada")}
    assert d.flatten(data) == {"name": "Ada"} and d.glob(data, "**")["name"] == "Ada"
    assert d.get(data, "name.0", None) is None and not d.has(data, "name.0")
    assert d.set({"n": UserString("x")}, "n.0", 1) == {"n": {"0": 1}}


def test_values_too_large_to_print_still_give_short_dotreach_errors() -> None:
    assert d.get({}, ("a", HUGE), None) is None and not d.has({}, ("a", HUGE))
    assert d.delete({}, [HUGE], missing_ok=True) == {}
    with pytest.raises(d.PathNotFoundError) as info:
        d.get({}, [HUGE])
    assert "too large to show" in str(info.value) and len(str(info.value)) < 200
    with pytest.raises(d.StructureError):
        d.flatten({HUGE: 1})
    with pytest.raises(d.StructureError):
        d.glob({HUGE: 1}, "*")


def test_a_deeply_nested_path_object_is_an_invalid_path() -> None:
    deep: Any = {}
    for _ in range(200_000):
        deep = {"k": deep}
    with pytest.raises(d.InvalidPathError) as info:
        d.get({}, ["a", deep])
    assert len(str(info.value)) < 200


def test_unflatten_keeps_empty_read_only_values_as_they_are() -> None:
    proxy: MappingProxyType[str, int] = MappingProxyType({})
    assert d.unflatten({"a": proxy})["a"] is proxy
    assert d.unflatten({"a": ()}) == {"a": ()}


def test_get_as_names_a_tuple_of_types_in_its_error() -> None:
    with pytest.raises(d.PathTypeError, match="int"):
        d.get_as({"a": 1.5}, "a", (int, str))  # type: ignore[call-overload]


def run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str, str]:
    code = main(list(argv))
    out, err = capsys.readouterr()
    return code, out, err


@pytest.mark.parametrize("text", ['{"a": NaN}', '{"a": -Infinity}', '{"a": 1e999}'])
def test_the_command_reads_strict_json_only(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], text: str
) -> None:
    source = tmp_path / "d.json"
    source.write_text(text, encoding="utf-8")
    code, out, err = run(capsys, "get", "a", str(source))
    assert (code, out) == (1, "") and "not valid JSON" in err


def test_set_takes_nan_as_a_string_and_writes_valid_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "d.json"
    source.write_text("{}", encoding="utf-8")
    for value in ("NaN", "Infinity", "1e999", "9" * 5000):
        assert run(capsys, "set", "a", value, "-i", str(source))[0] == 0
        assert json.loads(source.read_text(encoding="utf-8")) == {"a": value}


def test_in_place_never_empties_the_file_when_writing_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "d.json"
    before = '{"a": "\\ud800", "keep": "important"}'
    source.write_text(before, encoding="utf-8")
    code, _, err = run(capsys, "set", "b", "1", "-i", str(source))
    assert code == 1 and "not valid Unicode" in err
    assert source.read_text(encoding="utf-8") == before
    assert [p.name for p in tmp_path.iterdir()] == ["d.json"]  # no temporary file left


def test_in_place_replaces_the_whole_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "d.json"
    source.write_text(json.dumps({"a": "x" * 10_000}), encoding="utf-8")
    assert run(capsys, "set", "a", "y", "-i", "--indent", "0", str(source))[0] == 0
    assert source.read_text(encoding="utf-8") == '{"a": "y"}\n'
    assert [p.name for p in tmp_path.iterdir()] == ["d.json"]


def test_a_huge_indent_is_refused_with_a_short_message(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit):
        main(["flatten", "--indent", "9" * 20_000])
    assert len(capsys.readouterr().err) < 500


def test_a_missing_standard_input_is_an_error_not_a_traceback(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("sys.stdin", None)
    code, out, err = run(capsys, "flatten")
    assert (code, out) == (1, "") and "no standard input" in err


def test_input_errors_name_stdin_consistently(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    class Raw:
        buffer = type("B", (), {"read": staticmethod(lambda: b"\xff")})()

    monkeypatch.setattr("sys.stdin", Raw())
    code, _, err = run(capsys, "flatten")
    assert code == 1 and err == "dotreach: stdin is not UTF-8 text\n"
