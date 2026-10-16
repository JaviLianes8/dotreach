"""Remove values from nested dicts and lists in place by a dotted path."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ._core import _MISSING, not_found
from ._path import PathLike, as_index, is_mutable, is_sequence, step, to_segments
from ._write import read_only


def _remove(obj: Any, path: PathLike, sep: str, escape: bool) -> tuple[Any, Exception | None]:
    """Detach the value at ``path``; return ``(value, None)`` or ``(None, error)``."""
    segments = to_segments(path, sep, escape)
    node = obj
    for position, segment in enumerate(segments[:-1]):
        resolved, child = step(node, segment)
        if not resolved:
            return None, not_found(path, segments, position, node)
        node = child
    last, position = segments[-1], len(segments) - 1
    index = as_index(last) if is_sequence(node) else None
    if isinstance(node, Mapping) and last in node:
        slot: Any = last
    elif index is not None and -len(node) <= index < len(node):
        slot = index
    else:
        return None, not_found(path, segments, position, node)
    if not is_mutable(node):
        raise read_only(path, last, position, node, "delete")
    value = node[slot]
    del node[slot]
    return value, None


def delete(
    obj: Any, path: PathLike, *, sep: str = ".", missing_ok: bool = False, escape: bool = False
) -> Any:
    """Remove the value at ``path`` in place and return ``obj``.

    A missing path raises ``PathNotFoundError`` (a ``KeyError``) unless
    ``missing_ok`` is true. Removing a list element shifts the ones after it. A value
    held in a read-only container raises ``PathTypeError`` even with ``missing_ok``,
    since it is present.

    >>> delete({"a": {"b": 1, "c": 2}}, "a.b")
    {'a': {'c': 2}}
    >>> delete({"a": 1}, "x.y", missing_ok=True)
    {'a': 1}
    """
    _, error = _remove(obj, path, sep, escape)
    if error is not None and not missing_ok:
        raise error
    return obj


def pop(
    obj: Any, path: PathLike, default: Any = _MISSING, *, sep: str = ".", escape: bool = False
) -> Any:
    """Remove the value at ``path`` and return it, like ``dict.pop`` but nested.

    A missing path returns ``default`` when given, else raises ``PathNotFoundError``.
    A value held in a read-only container raises ``PathTypeError``.

    >>> data = {"tags": ["a", "b"]}
    >>> pop(data, "tags.-1"), data
    ('b', {'tags': ['a']})
    >>> pop(data, "nope", None) is None
    True
    """
    value, error = _remove(obj, path, sep, escape)
    if error is None:
        return value
    if default is _MISSING:
        raise error
    return default
