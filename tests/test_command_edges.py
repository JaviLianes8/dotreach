"""Command and library edges that need a subprocess or an odd input."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

import dotreach as d
from dotreach._cli import main


def test_indent_takes_ascii_digits_only() -> None:
    with pytest.raises(SystemExit):
        main(["flatten", "--indent", chr(0x661)])


def test_escaped_rendering_also_refuses_unprintable_keys() -> None:
    with pytest.raises(d.StructureError):
        d.flatten({10**5000: 1}, escape=True)


def test_unflatten_places_non_empty_values_as_given() -> None:
    inner = {"x": 1}
    assert d.unflatten({"a": inner})["a"] is inner


def test_python_dash_m_runs_the_command(tmp_path: Path) -> None:
    src = str(Path(d.__file__).resolve().parents[1])
    env = {**os.environ, "PYTHONPATH": src + os.pathsep + os.environ.get("PYTHONPATH", "")}
    result = subprocess.run(
        [sys.executable, "-m", "dotreach", "get", "a"],
        input='{"a": [1]}',
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    assert (result.returncode, result.stdout) == (0, "[\n  1\n]\n")
