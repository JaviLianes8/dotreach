"""The command's ``-i``: atomic, through symlinks, keeping the mode; and output edge cases."""

from __future__ import annotations

import io
import json
import os
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any

import pytest

from dotreach._cli import main

POSIX = pytest.mark.skipif(sys.platform == "win32", reason="POSIX file modes and links")


def run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str, str]:
    code = main(list(argv))
    out, err = capsys.readouterr()
    return code, out, err


@pytest.fixture
def doc(tmp_path: Path) -> Path:
    path = tmp_path / "d.json"
    path.write_text('{"a": 1}', encoding="utf-8")
    return path


@pytest.mark.parametrize("failure", [OSError("disk full"), KeyboardInterrupt()])
def test_a_failed_swap_keeps_the_file_and_leaves_no_temporary(
    doc: Path, monkeypatch: pytest.MonkeyPatch, failure: BaseException
) -> None:
    def broken(*args: Any) -> None:
        raise failure

    monkeypatch.setattr(os, "replace", broken)
    if isinstance(failure, OSError):
        assert main(["set", "b", "2", "-i", str(doc)]) == 1  # reported, not raised
    else:
        with pytest.raises(KeyboardInterrupt):
            main(["set", "b", "2", "-i", str(doc)])
    assert doc.read_text(encoding="utf-8") == '{"a": 1}'
    assert [p.name for p in doc.parent.iterdir()] == ["d.json"]


def test_the_temporary_file_is_made_next_to_the_target(
    doc: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    folders: list[str | None] = []
    real = tempfile.mkstemp

    def spy(*args: Any, **kwargs: Any) -> tuple[int, str]:
        folders.append(str(kwargs.get("dir")))
        return real(*args, **kwargs)

    monkeypatch.setattr(tempfile, "mkstemp", spy)
    assert run(capsys, "set", "b", "2", "-i", str(doc))[0] == 0
    assert folders == [os.path.realpath(doc.parent)]


@POSIX
def test_in_place_keeps_the_file_mode(doc: Path, capsys: pytest.CaptureFixture[str]) -> None:
    os.chmod(doc, 0o640)
    assert run(capsys, "set", "b", "2", "-i", str(doc))[0] == 0
    assert stat.S_IMODE(os.stat(doc).st_mode) == 0o640


def test_in_place_writes_through_a_symlink(doc: Path, capsys: pytest.CaptureFixture[str]) -> None:
    link = doc.parent / "link.json"
    try:
        link.symlink_to(doc)
    except OSError:
        pytest.skip("this system does not let us create symlinks")
    assert run(capsys, "set", "b", "2", "-i", str(link))[0] == 0
    assert link.is_symlink() and json.loads(doc.read_text(encoding="utf-8")) == {"a": 1, "b": 2}


@POSIX
def test_the_mode_comes_from_the_target_not_the_link(
    doc: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    os.chmod(doc, 0o640)
    link = doc.parent / "link.json"
    link.symlink_to(doc.name)
    assert run(capsys, "set", "b", "2", "-i", str(link))[0] == 0
    assert stat.S_IMODE(os.stat(doc).st_mode) == 0o640 and link.is_symlink()


def test_a_link_in_another_folder_writes_next_to_its_target(
    doc: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    other = doc.parent / "other"
    other.mkdir()
    link = other / "link.json"
    try:
        link.symlink_to(doc)
    except OSError:
        pytest.skip("this system does not let us create symlinks")
    folders: list[str] = []
    real = tempfile.mkstemp

    def spy(*args: Any, **kwargs: Any) -> tuple[int, str]:
        folders.append(str(kwargs.get("dir")))
        return real(*args, **kwargs)

    monkeypatch.setattr(tempfile, "mkstemp", spy)
    assert run(capsys, "set", "b", "2", "-i", str(link))[0] == 0
    assert folders == [os.path.realpath(doc.parent)] and list(other.iterdir()) == [link]


@pytest.mark.skipif(sys.platform != "win32", reason="Windows refuses to replace read-only files")
def test_a_read_only_file_on_windows_is_refused_cleanly(
    doc: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    os.chmod(doc, stat.S_IREAD)
    try:
        code, _, err = run(capsys, "set", "b", "2", "-i", str(doc))
        assert code == 1 and err.startswith(f"dotreach: cannot write {doc}: ")
        assert ".tmp" not in err and doc.read_text(encoding="utf-8") == '{"a": 1}'
        assert [p.name for p in doc.parent.iterdir()] == ["d.json"]
    finally:
        os.chmod(doc, stat.S_IREAD | stat.S_IWRITE)


@POSIX
def test_a_folder_that_cannot_be_written_is_a_clean_error(
    doc: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    if getattr(os, "geteuid", lambda: 1)() == 0:
        pytest.skip("root may write anywhere")
    os.chmod(doc.parent, 0o555)
    try:
        code, _, err = run(capsys, "set", "b", "2", "-i", str(doc))
        assert code == 1 and err == f"dotreach: cannot write {doc}: Permission denied\n"
    finally:
        os.chmod(doc.parent, 0o755)


@POSIX
def test_a_hard_link_keeps_the_old_content_as_documented(
    doc: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    other = doc.parent / "other.json"
    os.link(doc, other)
    assert run(capsys, "set", "b", "2", "-i", str(doc))[0] == 0
    assert other.read_text(encoding="utf-8") == '{"a": 1}'


def test_raw_output_of_text_that_is_not_unicode_is_a_clean_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "s.json"
    source.write_text('{"a": "\\ud800"}', encoding="utf-8")
    strict = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    monkeypatch.setattr("sys.stdout", strict)
    assert main(["get", "a", "--raw", str(source)]) == 1
    assert "not valid Unicode" in capsys.readouterr().err


def test_an_unreadable_stdin_is_named_stdin(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class Broken:
        class buffer:
            @staticmethod
            def read() -> bytes:
                raise OSError(5, "Input/output error")

    monkeypatch.setattr("sys.stdin", Broken())
    assert run(capsys, "flatten") == (1, "", "dotreach: cannot read stdin: Input/output error\n")


def test_a_value_nested_too_deeply_for_json_is_taken_as_a_string(
    doc: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    deep = "[" * 200_000 + "]" * 200_000
    assert run(capsys, "set", "b", deep, "-i", str(doc))[0] == 0
    assert json.loads(doc.read_text(encoding="utf-8"))["b"] == deep
