"""Contract: edges found by the blind mutation round, one claim per test."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import threading
from collections import UserString
from pathlib import Path
from types import MappingProxyType
from typing import Any

import pytest

import dotreach as d
from dotreach._cli import main
from dotreach._errors import shown

SRC = str(Path(d.__file__).resolve().parents[1])


def bounded(seconds: float, call: Any, *args: Any) -> Any:
    """Run ``call`` in a daemon thread and fail the test if it does not finish in time."""
    box: list[tuple[bool, Any]] = []

    def target() -> None:
        try:
            box.append((True, call(*args)))
        except BaseException as error:  # handed back to the test thread
            box.append((False, error))

    worker = threading.Thread(target=target, daemon=True)
    worker.start()
    worker.join(seconds)
    assert box, f"{call} did not finish in {seconds} s"
    finished, result = box[0]
    if not finished:
        raise result
    return result


def test_work_that_once_hung_finishes_quickly() -> None:
    with pytest.raises(d.InvalidPathError):
        bounded(5, d.split_path, "a.b", "")
    assert bounded(5, d.flatten, {"s": UserString("abc")}) == {"s": "abc"}
    chain: Any = {"leaf": 1}
    for _ in range(30):
        chain = {"k": chain}
    assert len(bounded(10, d.glob, chain, ".".join(["**"] * 25 + ["leaf"]))) == 1


def test_setdefault_reads_with_the_same_escaping_it_writes_with() -> None:
    data = {"a.b": 1}
    assert d.setdefault(data, r"a\.b", 2, escape=True) == 1 and data == {"a.b": 1}


def test_delete_copy_reaches_the_lowest_negative_index() -> None:
    assert d.delete_copy((1, 2), "-2") == (2,)
    assert d.delete_copy([1, 2], "-2") == [2]


def test_set_copy_returns_read_only_mappings_as_plain_dicts() -> None:
    assert type(d.set_copy(MappingProxyType({"a": 1}), "a", 2)) is dict


def test_error_positions_and_segments_point_at_the_first_failure() -> None:
    with pytest.raises(d.InvalidPathError) as bad:
        d.get({}, ["a", 1.5])  # type: ignore[list-item]
    assert bad.value.position == 1
    for call in (d.delete, d.pop):
        with pytest.raises(d.PathNotFoundError) as missing:
            call({}, "a.b")
        assert (missing.value.segment, missing.value.position) == ("a", 0)


def test_shown_keeps_sixty_characters_and_cuts_longer_reprs_the_same_way() -> None:
    assert shown("x" * 58) == repr("x" * 58)
    cut = shown("x" * 100)
    assert cut == repr("x" * 100)[:40] + "..." + repr("x" * 100)[-12:] + " (102 chars)"


def run(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str, str]:
    code = main(list(argv))
    out, err = capsys.readouterr()
    return code, out, err


def test_indent_accepts_its_documented_bounds(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("sys.stdin", io.StringIO('{"a": [1]}'))
        assert run(capsys, "get", "a", "--indent", "64")[:2] == (0, "[\n" + " " * 64 + "1\n]\n")


def test_a_dash_after_options_means_standard_input(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO('{"a": "x"}'))
    assert run(capsys, "get", "a", "--raw", "-") == (0, "x\n", "")


@pytest.mark.parametrize("stdin", [False, True])
def test_a_byte_order_mark_is_accepted(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    stdin: bool,
) -> None:
    data = b"\xef\xbb\xbf" + b'{"a": 1}'
    if stdin:
        monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(data)))
        assert run(capsys, "get", "a") == (0, "1\n", "")
    else:
        source = tmp_path / "bom.json"
        source.write_bytes(data)
        assert run(capsys, "get", "a", str(source)) == (0, "1\n", "")


def test_a_file_name_the_system_refuses_is_a_clean_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code, out, err = run(capsys, "get", "a", "bad\0name")
    assert (code, out) == (1, "") and err.startswith("dotreach: ")


def _module(*args: str, stdin: str) -> subprocess.CompletedProcess[bytes]:
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONIOENCODING", "PYTHONUTF8")}
    env["PYTHONPATH"] = SRC + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-m", "dotreach", *args],
        input=stdin.encode("utf-8"),
        capture_output=True,
        env=env,
        timeout=60,
    )


def test_python_dash_m_returns_the_command_exit_code() -> None:
    assert _module("has", "zz", stdin='{"a": 1}').returncode == 1
    assert _module("has", "a", stdin='{"a": 1}').returncode == 0


def test_the_script_writes_utf_8_whatever_the_console_encoding() -> None:
    result = _module("get", "a", stdin=json.dumps({"a": "日本"}, ensure_ascii=False))
    assert (result.returncode, result.stdout.decode("utf-8").strip()) == (0, '"日本"')
