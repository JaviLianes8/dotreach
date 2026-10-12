"""In-process tests of the command line interface through ``main``."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from dotreach._cli import main

DOC = {"user": {"name": "Ada", "roles": ["admin", "editor"]}, "k.e": "é"}


@pytest.fixture
def doc(tmp_path: Path) -> Path:
    path = tmp_path / "doc.json"
    path.write_text(json.dumps(DOC), encoding="utf-8")
    return path


def run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str, str]:
    code = main(list(argv))
    out, err = capsys.readouterr()
    return code, out, err


def test_get_prints_json_and_raw(capsys: pytest.CaptureFixture[str], doc: Path) -> None:
    assert run(capsys, "get", "user.name", str(doc)) == (0, '"Ada"\n', "")
    assert run(capsys, "get", "user.name", "--raw", str(doc)) == (0, "Ada\n", "")
    code, out, _ = run(capsys, "get", "user.roles", "--indent", "0", str(doc))
    assert (code, out) == (0, '["admin", "editor"]\n')


def test_get_default_and_missing(capsys: pytest.CaptureFixture[str], doc: Path) -> None:
    assert run(capsys, "get", "user.age", "--default", "0", str(doc))[:2] == (0, "0\n")
    code, out, err = run(capsys, "get", "user.age", str(doc))
    assert code == 1 and out == "" and "'age'" in err and err.startswith("dotreach: ")


def test_has_uses_the_exit_code(capsys: pytest.CaptureFixture[str], doc: Path) -> None:
    assert run(capsys, "has", "user.roles.1", str(doc)) == (0, "", "")
    assert run(capsys, "has", "user.roles.2", str(doc)) == (1, "", "")


def test_set_parses_json_values(capsys: pytest.CaptureFixture[str], doc: Path) -> None:
    code, out, _ = run(capsys, "set", "user.age", "36", str(doc))
    assert code == 0 and json.loads(out)["user"]["age"] == 36
    _, out, _ = run(capsys, "set", "user.city", "Paris", str(doc))
    assert json.loads(out)["user"]["city"] == "Paris"
    _, out, _ = run(capsys, "set", "user.zip", "007", "--string", str(doc))
    assert json.loads(out)["user"]["zip"] == "007"


def test_set_in_place_and_create_lists(capsys: pytest.CaptureFixture[str], doc: Path) -> None:
    assert run(capsys, "set", "tags.0", "x", "--create-lists", "-i", str(doc)) == (0, "", "")
    assert json.loads(doc.read_text(encoding="utf-8"))["tags"] == ["x"]


def test_in_place_needs_a_file(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("{}"))
    code, _, err = run(capsys, "set", "a", "1", "-i")
    assert code == 1 and "--in-place" in err


def test_delete(capsys: pytest.CaptureFixture[str], doc: Path) -> None:
    _, out, _ = run(capsys, "delete", "user.roles.-1", str(doc))
    assert json.loads(out)["user"]["roles"] == ["admin"]
    assert run(capsys, "delete", "nope", str(doc))[0] == 1
    assert run(capsys, "delete", "nope", "--missing-ok", str(doc))[0] == 0


def test_glob_flatten_unflatten(capsys: pytest.CaptureFixture[str], doc: Path) -> None:
    _, out, _ = run(capsys, "glob", "user.roles.*", str(doc))
    assert json.loads(out) == {"user.roles.0": "admin", "user.roles.1": "editor"}
    _, out, _ = run(capsys, "flatten", "--escape", str(doc))
    flat = json.loads(out)
    assert flat["k\\.e"] == "é"
    flat_file = doc.with_name("flat.json")
    flat_file.write_text(out, encoding="utf-8")
    _, out, _ = run(capsys, "unflatten", "--escape", "--create-lists", str(flat_file))
    assert json.loads(out) == DOC


def test_unflatten_needs_an_object(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    path = tmp_path / "list.json"
    path.write_text("[1]", encoding="utf-8")
    code, _, err = run(capsys, "unflatten", str(path))
    assert code == 1 and "object" in err


def test_reads_stdin(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO('{"a": [1, 2]}'))
    assert run(capsys, "get", "a.-1") == (0, "2\n", "")


def test_input_errors(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{nope", encoding="utf-8")
    code, _, err = run(capsys, "get", "a", str(bad))
    assert code == 1 and "not valid JSON" in err
    bad.write_bytes(b"\xff\xfe\x00")
    assert "UTF-8" in run(capsys, "get", "a", str(bad))[2]
    code, _, err = run(capsys, "get", "a", str(tmp_path / "missing.json"))
    assert code == 1 and "cannot read" in err
    assert run(capsys, "get", "", str(tmp_path / "missing.json"))[0] == 1


def test_usage_errors_exit_one_on_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as info:
        main(["frobnicate"])
    assert info.value.code == 1
    assert "invalid choice" in capsys.readouterr().err


def test_help_shows_runnable_examples(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as info:
        main(["--help"])
    assert info.value.code == 0
    out = capsys.readouterr().out
    assert "examples:" in out and "dotreach get user.name data.json" in out


def test_file_may_follow_options(capsys: pytest.CaptureFixture[str], doc: Path) -> None:
    assert run(capsys, "get", "--raw", "user.name", str(doc))[:2] == (0, "Ada\n")
    assert run(capsys, "get", "user.name", "--raw", str(doc))[:2] == (0, "Ada\n")


def test_unrecognized_arguments_exit_one(capsys: pytest.CaptureFixture[str], doc: Path) -> None:
    with pytest.raises(SystemExit) as info:
        main(["get", "user.name", str(doc), "extra", "more"])
    assert info.value.code == 1
    assert "unrecognized arguments" in capsys.readouterr().err
