"""Hostile input: huge, deep, cyclic and malformed data never crash, hang or flood."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

import dotreach as d
from dotreach._cli import main

DEPTH = 100_000


def chain(depth: int, key: Any = "k") -> Any:
    """``{"k": {"k": ... {"leaf": 1}}}`` built without recursion."""
    node: Any = {"leaf": 1}
    for _ in range(depth):
        node = {key: node} if key != 0 else [node]
    return node


def timed(seconds: float, call: Any, *args: Any, **kwargs: Any) -> Any:
    start = time.perf_counter()
    result = call(*args, **kwargs)
    assert time.perf_counter() - start < seconds, call
    return result


def test_deep_structures_work_at_any_depth_in_linear_time() -> None:
    for key in ("k", 0):
        data = chain(DEPTH, key)
        path = [key] * DEPTH + ["leaf"]
        assert timed(10, d.get, data, path) == 1
        assert list(timed(10, list, d.walk(data))) == [(tuple(path), 1)]
        flat = timed(10, d.flatten, data)
        assert list(flat.values()) == [1] and len(flat) == 1
        assert timed(10, d.glob, data, "**.leaf") == flat
        assert timed(10, d.get, timed(10, d.set_copy, data, path, 2), path) == 2
        assert timed(10, d.has, timed(10, d.delete_copy, data, path), path[:-1])
        rebuilt = timed(10, d.unflatten, flat, create_lists=True)
        assert d.get(rebuilt, next(iter(flat))) == 1  # == itself recurses on deep data


def test_many_double_stars_do_not_multiply_the_work() -> None:
    data = chain(60)
    pattern = ".".join(["**"] * 40 + ["leaf"])
    assert timed(10, d.glob, data, pattern) == {".".join(["k"] * 60 + ["leaf"]): 1}
    pattern = ".".join(["**", "*"] * 20 + ["leaf"])
    assert len(timed(10, d.glob, data, pattern)) == 1


def test_shared_subtrees_are_matched_at_every_path_but_not_called_cycles() -> None:
    shared: list[Any] = [1, 2]
    data = {"a": [shared] * 3, "b": shared}
    assert len(d.glob(data, "**")) == 1 + 1 + 3 + 3 * 2 + 1 + 2
    assert len(d.flatten(data)) == 3 * 2 + 2


@pytest.mark.parametrize("call", [d.walk, d.flatten, lambda x: d.glob(x, "**")])
def test_a_structure_that_contains_itself_is_a_structure_error(call: Any) -> None:
    data: dict[str, Any] = {"a": [1]}
    data["a"].append(data)
    with pytest.raises(d.StructureError):
        list(call(data))


def test_cycles_do_not_matter_when_a_path_is_finite() -> None:
    data: dict[str, Any] = {"x": 1}
    data["self"] = data
    assert d.get(data, "self.self.self.x") == 1
    assert d.glob(data, "self.*.x") == {"self.self.x": 1}
    assert d.set_copy(data, "self.y", 2)["self"]["y"] == 2


def test_huge_numbers_as_indices_are_simply_out_of_range() -> None:
    nines = "9" * 100_000
    assert timed(5, d.get, [1], nines, None) is None
    assert timed(5, d.get, [1], "-" + nines, None) is None
    with pytest.raises(d.PathIndexError):
        d.set([1], nines, 0)
    with pytest.raises(d.PathIndexError):
        d.set_copy([1], nines, 0)
    assert d.get(["x"], "0" * 5000 + "0") == "x"
    assert d.get(["x", "y", "z"], "-" + "0" * 5000 + "1") == "z"
    assert d.get(["x", "y", "z"], "0" * 5000 + "1") == "y"


def test_error_messages_stay_short_for_huge_paths_and_keys() -> None:
    huge = "a" * 1_000_000
    cases: list[Callable[[], object]] = [
        lambda: d.get({}, huge),
        lambda: d.get({"a": 1}, ("a", huge)),
        lambda: d.set([1], huge, 1),
        lambda: d.set_copy([1], huge, 1),
        lambda: d.get_as({"a": huge}, "a", int),
        lambda: d.get({}, [1.5] * 10_000),  # type: ignore[list-item]
        lambda: d.get({}, ("a", huge.encode())),  # type: ignore[arg-type]
        lambda: d.unflatten({huge: 1, huge + ".b": 2}),
        lambda: d.flatten({huge + ".b": 1, huge: {"b": 2}}),
    ]
    for case in cases:
        with pytest.raises(d.DotreachError) as info:
            case()
        assert len(str(info.value)) < 200


def test_the_command_reports_input_nested_too_deeply(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    deep = tmp_path / "deep.json"
    deep.write_text("[" * 200_000 + "]" * 200_000, encoding="utf-8")
    assert main(["get", "0", str(deep)]) == 1
    err = capsys.readouterr().err
    assert err.startswith("dotreach: ") and "nested too deeply" in err


@pytest.mark.parametrize("indent", ["-1", "65", "x"])
def test_the_command_refuses_an_unusable_indent(indent: str) -> None:
    with pytest.raises(SystemExit) as info:
        main(["flatten", "--indent", indent])
    assert info.value.code == 1


def test_a_closed_output_pipe_ends_quietly(tmp_path: Path) -> None:
    src = str(Path(d.__file__).resolve().parents[1])
    env = {**os.environ, "PYTHONPATH": src + os.pathsep + os.environ.get("PYTHONPATH", "")}
    big = tmp_path / "big.json"
    big.write_text("{" + ",".join(f'"k{i}": {i}' for i in range(200_000)) + "}", encoding="utf-8")
    process = subprocess.Popen(
        [sys.executable, "-m", "dotreach._cli", "flatten", str(big)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    assert process.stdout is not None and process.stderr is not None
    assert process.stdout.read(10)
    process.stdout.close()
    err = process.stderr.read()
    assert process.wait(timeout=60) == 1
    assert err == b""
