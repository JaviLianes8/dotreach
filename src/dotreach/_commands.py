"""The work behind each command line subcommand, kept apart from argument parsing."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ._core import get, has
from ._walk import flatten, glob, unflatten
from ._write import delete
from ._write import set as set_value


class CliError(Exception):
    """A user-facing command line error."""


def _load(source: str) -> Any:
    try:
        if source == "-":
            raw = getattr(sys.stdin, "buffer", None)
            text = raw.read().decode("utf-8-sig") if raw is not None else sys.stdin.read()
        else:
            text = Path(source).read_text(encoding="utf-8-sig")
    except OSError as error:
        raise CliError(f"cannot read {source}: {error.strerror or error}") from None
    except UnicodeDecodeError:
        raise CliError(f"{source} is not UTF-8 text") from None
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        name = "stdin" if source == "-" else source
        raise CliError(f"{name} is not valid JSON: {error}") from None


def _dump(value: Any, indent: int) -> str:
    return json.dumps(value, indent=indent or None, ensure_ascii=False)


def _value(text: str, as_string: bool) -> Any:
    if as_string:
        return text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _emit(args: argparse.Namespace, document: Any) -> int:
    output = _dump(document, args.indent)
    if getattr(args, "in_place", False):
        Path(args.file).write_text(output + "\n", encoding="utf-8")
        return 0
    print(output)
    return 0


def _get(args: argparse.Namespace, data: Any, opts: dict[str, Any]) -> int:
    if args.default is not None:
        value = get(data, args.path, _value(args.default, False), **opts)
    else:
        value = get(data, args.path, **opts)
    if args.raw and isinstance(value, str):
        print(value)
    else:
        print(_dump(value, args.indent))
    return 0


def _unflatten(args: argparse.Namespace, data: Any, opts: dict[str, Any]) -> int:
    if not isinstance(data, dict):
        raise CliError("unflatten expects a JSON object of {path: value}")
    return _emit(args, unflatten(data, create_lists=args.create_lists, **opts))


def run(args: argparse.Namespace) -> int:
    """Execute the parsed subcommand and return its exit code."""
    if getattr(args, "in_place", False) and args.file == "-":
        raise CliError("--in-place needs a FILE, not stdin")
    data = _load(args.file)
    opts: dict[str, Any] = {"sep": args.sep, "escape": args.escape}
    command = args.command
    if command == "get":
        return _get(args, data, opts)
    if command == "has":
        return 0 if has(data, args.path, **opts) else 1
    if command == "set":
        value = _value(args.value, args.string)
        set_value(data, args.path, value, create_lists=args.create_lists, **opts)
        return _emit(args, data)
    if command == "delete":
        return _emit(args, delete(data, args.path, missing_ok=args.missing_ok, **opts))
    if command == "glob":
        print(_dump(glob(data, args.pattern, **opts), args.indent))
        return 0
    if command == "flatten":
        print(_dump(flatten(data, **opts), args.indent))
        return 0
    return _unflatten(args, data, opts)
