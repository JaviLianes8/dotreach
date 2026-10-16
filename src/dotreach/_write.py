"""Mutate nested dicts and lists in place by a dotted path."""

from __future__ import annotations

from collections.abc import MutableMapping, MutableSequence
from typing import Any

from ._core import resolve
from ._errors import PathIndexError, PathTypeError, shown
from ._path import (
    Key,
    PathLike,
    as_index,
    is_container,
    is_mutable,
    to_segments,
    type_name,
)


def _index_or_raise(path: PathLike, segment: Key, position: int) -> int:
    index = as_index(segment)
    if index is None:
        message = f"list index must be an integer, got {shown(segment)} (segment {position})"
        raise PathTypeError(message, path, segment, position)
    return index


def _fresh(next_segment: Key, create_lists: bool) -> Any:
    index = as_index(next_segment)
    return [] if create_lists and index is not None and index >= 0 else {}


def _out_of_range(path: PathLike, segment: Key, position: int, size: int) -> PathIndexError:
    where = f"(segment {position}) out of range for length {size}"
    return PathIndexError(f"list index {shown(segment)} {where}", path, segment, position)


def read_only(path: PathLike, segment: Key, position: int, node: Any, verb: str) -> PathTypeError:
    where = f"{shown(segment)} in read-only {type_name(node)} (segment {position})"
    message = f"cannot {verb} {where}; use {verb}_copy"
    return PathTypeError(message, path, segment, position)


def _slot(path: PathLike, segments: list[Key], position: int, node: Any, lists: bool) -> Any:
    """Return the key or index ``segments[position]`` writes in ``node``."""
    segment = segments[position]
    if isinstance(node, MutableMapping):
        return segment
    if isinstance(node, MutableSequence) and is_mutable(node):
        index = _index_or_raise(path, segment, position)
        if lists and index == len(node):
            return index
        if not -len(node) <= index < len(node):
            raise _out_of_range(path, segment, position, len(node))
        return index % len(node)
    if is_container(node):
        raise read_only(path, segment, position, node, "set")
    message = f"cannot set {shown(segment)} on {type_name(node)} (segment {position})"
    raise PathTypeError(message, path, segment, position)


def _put(node: Any, slot: Any, value: Any) -> None:
    if isinstance(node, MutableSequence) and slot == len(node):
        node.append(value)
    else:
        node[slot] = value


def set(
    obj: Any,
    path: PathLike,
    value: Any,
    *,
    sep: str = ".",
    escape: bool = False,
    create_lists: bool = False,
) -> Any:
    """Set ``value`` at ``path`` in place and return ``obj``.

    A missing intermediate, or one holding a value that is not a container (a number,
    a string, ``None``), becomes a new dict, in a dict or in a list alike. Existing
    sequence elements are replaced; an out-of-range index raises ``PathIndexError``.
    A container that cannot be written in place (a tuple, a read-only mapping) is
    never replaced: it raises ``PathTypeError`` (use :func:`set_copy` to rebuild it).

    With ``create_lists=True`` a missing intermediate becomes a list when the next
    segment is a non-negative integer, and an index equal to the list length appends.

    Raises:
        PathTypeError: A non-integer segment meets a list, or the path runs into a
            read-only container or the root is not a container (a ``TypeError``).
        PathIndexError: A list index is out of range.
        InvalidPathError: The path is empty or malformed.

    >>> set({"user": {"name": "Ada"}}, "user.age", 36)
    {'user': {'name': 'Ada', 'age': 36}}
    >>> set({}, "tags.0", "x", create_lists=True)
    {'tags': ['x']}
    """
    segments = to_segments(path, sep, escape)
    node = obj
    last = len(segments) - 1
    for position in range(last):
        slot = _slot(path, segments, position, node, create_lists)
        resolved = slot in node if isinstance(node, MutableMapping) else slot < len(node)
        child = node[slot] if resolved else None
        if not is_mutable(child):
            if is_container(child):
                raise read_only(path, segments[position + 1], position + 1, child, "set")
            child = _fresh(segments[position + 1], create_lists)
            _put(node, slot, child)
        node = child
    _put(node, _slot(path, segments, last, node, create_lists), value)
    return obj


def setdefault(
    obj: Any,
    path: PathLike,
    default: Any = None,
    *,
    sep: str = ".",
    escape: bool = False,
    create_lists: bool = False,
) -> Any:
    """Return the value at ``path``, first setting it to ``default`` if it is missing.

    Like ``dict.setdefault`` but nested: intermediates are created as by :func:`set`.

    >>> data = {"prefs": {"theme": "light"}}
    >>> setdefault(data, "prefs.theme", "dark"), setdefault(data, "prefs.lang", "en")
    ('light', 'en')
    """
    value, error = resolve(obj, path, sep, escape)
    if error is None:
        return value
    set(obj, path, default, sep=sep, escape=escape, create_lists=create_lists)
    return default
