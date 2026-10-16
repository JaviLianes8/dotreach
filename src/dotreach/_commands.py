"""The work behind each command line subcommand, kept apart from argument parsing."""

from __future__ import annotations

import argparse
import contextlib
import errno
import json
import math
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from ._core import get, has
from ._delete import delete
from ._errors import shown
from ._glob import glob
from ._walk import flatten, unflatten
from ._write import set as set_value


class CliError(Exception):
    """A user-facing command line error."""


class PipeClosed(Exception):
    """Standard output was closed by its reader (``| head``)."""


def _out(text: str) -> None:
    # A reader that went away shows up as EPIPE, or as EINVAL on Windows pipes.
    try:
        print(text)
        sys.stdout.flush()
    except OSError as error:
        if error.errno in (errno.EPIPE, errno.EINVAL):
            raise PipeClosed from None
        raise


def _not_json(text: str) -> Any:
    raise ValueError(f"{text} is not a JSON number")


def _finite(text: str) -> float:
    number = float(text)
    if math.isinf(number):
        raise ValueError(f"{shown(text)} is too large for a JSON number")
    return number


def _parse(text: str) -> Any:
    """Strict JSON: no NaN or Infinity, and no number too large to keep as a float."""
    return json.loads(text, parse_constant=_not_json, parse_float=_finite)


def _load(source: str) -> Any:
    name = "stdin" if source == "-" else source
    try:
        if source == "-":
            if sys.stdin is None:
                raise CliError("there is no standard input to read")
            raw = getattr(sys.stdin, "buffer", None)
            text = raw.read().decode("utf-8-sig") if raw is not None else sys.stdin.read()
        else:
            text = Path(source).read_text(encoding="utf-8-sig")
    except OSError as error:
        raise CliError(f"cannot read {name}: {error.strerror or error}") from None
    except UnicodeDecodeError:
        raise CliError(f"{name} is not UTF-8 text") from None
    try:
        return _parse(text)
    except RecursionError:
        raise CliError(f"{name} is nested too deeply to read") from None
    except ValueError as error:
        raise CliError(f"{name} is not valid JSON: {error}") from None


def _dump(value: Any, indent: int) -> str:
    try:
        text = json.dumps(value, indent=indent or None, ensure_ascii=False, allow_nan=False)
        text.encode("utf-8")
    except RecursionError:
        raise CliError("the result is nested too deeply to write") from None
    except UnicodeEncodeError:
        raise CliError("the result holds text that is not valid Unicode") from None
    except ValueError:
        raise CliError("the result holds a number JSON cannot represent") from None
    return text


def _value(text: str, as_string: bool) -> Any:
    if as_string:
        return text
    try:
        return _parse(text)
    except (ValueError, RecursionError):
        return text


def _replace(path: Path, text: str) -> None:
    # Write a sibling file, then swap it in, so a failure never leaves FILE half written.
    data = text.encode("utf-8")
    handle, temp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
        os.replace(temp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(temp)
        raise


def _emit(args: argparse.Namespace, document: Any) -> int:
    output = _dump(document, args.indent)
    if getattr(args, "in_place", False):
        _replace(Path(args.file), output + "\n")
        return 0
    _out(output)
    return 0
    _out(output)
    return 0


def _get(args: argparse.Namespace, data: Any, opts: dict[str, Any]) -> int:
    if args.default is not None:
        value = get(data, args.path, _value(args.default, False), **opts)
    else:
        value = get(data, args.path, **opts)
    if args.raw and isinstance(value, str):
        _out(value)
    else:
        _out(_dump(value, args.indent))
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
        _out(_dump(glob(data, args.pattern, **opts), args.indent))
        return 0
    if command == "flatten":
        _out(_dump(flatten(data, **opts), args.indent))
        return 0
    return _unflatten(args, data, opts)
