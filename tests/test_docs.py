"""Every example in README.md and GUIDE.md runs, and every value it shows is the result."""

from __future__ import annotations

import ast
import json
import re
import shlex
from pathlib import Path
from typing import Any

import pytest

from dotreach._cli import main

ROOT = Path(__file__).resolve().parent.parent
FENCE = re.compile(r"```(\w*)\n(.*?)```", re.S)


def blocks(name: str, language: str) -> list[str]:
    text = (ROOT / name).read_text(encoding="utf-8")
    return [body for lang, body in FENCE.findall(text) if lang == language]


def shown_value(comment: str) -> Any:
    """The Python literal a ``# comment`` starts with, or a marker when it has none."""
    cuts = [m.start() for m in re.finditer(r",? \(|  |, ", comment)] + [len(comment)]
    for cut in cuts:
        try:
            return ast.literal_eval(comment[:cut].strip())
        except (ValueError, SyntaxError):
            continue
    return NotImplemented


def run_python(name: str) -> int:
    namespace: dict[str, Any] = {}
    checked = 0
    for block in blocks(name, "python"):
        lines = block.splitlines()
        for node in ast.parse(block).body:
            end = (node.end_lineno or node.lineno) - 1
            line = lines[end]
            comment = line.split("  # ", 1)[1] if "  # " in line else ""
            following = lines[end + 1].strip() if end + 1 < len(lines) else ""
            if not comment and following.startswith("# "):
                comment = following[2:]
            if isinstance(node, ast.Expr):
                value = eval(compile(ast.Expression(node.value), name, "eval"), namespace)
            else:
                exec(compile(ast.Module([node], []), name, "exec"), namespace)
                targets = getattr(node, "targets", None) or [getattr(node, "target", None)]
                target = targets[0]
                value = namespace.get(target.id) if isinstance(target, ast.Name) else NotImplemented
            expected = shown_value(comment) if comment else NotImplemented
            if expected is not NotImplemented and value is not NotImplemented:
                assert value == expected, (name, line)
                checked += 1
    return checked


def test_readme_python_examples_run_and_show_their_results() -> None:
    assert run_python("README.md") == 19


def test_guide_python_examples_run_and_show_their_results() -> None:
    assert run_python("GUIDE.md") == 2


def test_readme_command_examples_run_as_shown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    sample = re.search(r"With `data.json` holding `(.*?)`", readme)
    assert sample is not None
    monkeypatch.chdir(tmp_path)
    ran = 0
    for line in blocks("README.md", "")[1].splitlines():
        parts = re.split(r"\s{2,}", line.strip(), maxsplit=1)
        command, note = parts[0], parts[1] if len(parts) > 1 else ""
        if "|" in command:
            continue  # pipes are exercised by the end to end test
        Path("data.json").write_text(sample.group(1), encoding="utf-8")
        args = shlex.split(command)[1:]
        code = main(args)
        out = capsys.readouterr().out
        assert code == 0, line
        if note.startswith('"') or note.isalnum():
            assert out.strip() == note.strip(), line
        if "-i" in args:
            assert out == "" and json.loads(Path("data.json").read_text())["user"]["age"] == 36
        ran += 1
    assert ran == 6
