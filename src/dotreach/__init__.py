"""Typed, zero-dependency get/set/delete/has on nested dicts and lists by dotted path."""

from __future__ import annotations

from ._copy import delete_copy, set_copy
from ._core import get, get_as, has
from ._errors import (
    DotreachError,
    InvalidPathError,
    PathIndexError,
    PathNotFoundError,
    PathTypeError,
)
from ._path import Key, PathLike, join_path, split_path
from ._version import __version__ as __version__
from ._walk import flatten, glob, leaves, unflatten, walk
from ._write import delete, pop, set, setdefault

__all__ = [
    "DotreachError",
    "InvalidPathError",
    "Key",
    "PathIndexError",
    "PathLike",
    "PathNotFoundError",
    "PathTypeError",
    "delete",
    "delete_copy",
    "flatten",
    "get",
    "get_as",
    "glob",
    "has",
    "join_path",
    "leaves",
    "pop",
    "set",
    "set_copy",
    "setdefault",
    "split_path",
    "unflatten",
    "walk",
]
