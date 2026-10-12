"""Mutate nested dicts and lists in place by a dotted path."""

from __future__ import annotations

from collections.abc import MutableMapping, MutableSequence
from typing import Any

from ._core import _MISSING, not_found, resolve
from ._errors import PathIndexError, PathTypeError
from ._path import Key, PathLike, as_index, is_mutable, step, to_segments, type_name


def _index_or_raise(path: PathLike, segment: Key, position: int) -> int:
    index = as_index(segment)
    if index is None:
        message = f"list index must be an integer, got {segment!r} (segment {position})"
        raise PathTypeError(message, path, segment, position)
    return index


def _fresh(next_segment: Key, create_lists: bool) -> Any:
    index = as_index(next_segment)
    return [] if create_lists and index is not None and index >= 0 else {}


def _out_of_range(path: PathLike, segment: Key, position: int, size: int) -> PathIndexError:
    message = f"list index {segment!r} (segment {position}) out of range for length {size}"
    return PathIndexError(message, path, segment, position)


def _descend(
    path: PathLike, segments: list[Key], position: int, container: Any, create_lists: bool
) -> Any:
    segment = segments[position]
    if isinstance(container, MutableMapping):
        nxt = container.get(segment, _MISSING)
        if not is_mutable(nxt):
            nxt = _fresh(segments[position + 1], create_lists)
            container[segment] = nxt
        return nxt
    if isinstance(container, MutableSequence):
        index = _index_or_raise(path, segment, position)
        if create_lists and index == len(container):
            nxt = _fresh(segments[position + 1], create_lists)
            container.append(nxt)
            return nxt
        try:
            return container[index]
        except IndexError:
            raise _out_of_range(path, segment, position, len(container)) from None
    message = f"cannot descend into {type_name(container)} at {segment!r} (segment {position})"
    raise PathTypeError(message, path, segment, position)


def _assign(
    path: PathLike, segment: Key, position: int, container: Any, value: Any, create_lists: bool
) -> None:
    if isinstance(container, MutableMapping):
        container[segment] = value
        return
    if isinstance(container, MutableSequence):
        index = _index_or_raise(path, segment, position)
        if create_lists and index == len(container):
            container.append(value)
            return
        try:
            container[index] = value
        except IndexError:
            raise _out_of_range(path, segment, position, len(container)) from None
        return
    message = f"cannot set {segment!r} on {type_name(container)} (segment {position})"
    raise PathTypeError(message, path, segment, position)


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

    Missing intermediate keys, and intermediate values that are not mutable
    containers, become new dicts. Existing sequence elements are replaced; by default
    an out-of-range index raises ``PathIndexError`` (an ``IndexError``).

    With ``create_lists=True`` a missing intermediate becomes a list when the next
    segment is a non-negative integer, and an index equal to the list length appends,
    so ``set({}, "tags.0", "x", create_lists=True)`` gives ``{"tags": ["x"]}``.

    Raises:
        PathTypeError: A non-integer segment meets a list, or the path runs into a
            value that cannot be written (a ``TypeError``).
        PathIndexError: A list index is out of range.
        InvalidPathError: The path is empty or malformed.
    """
    segments = to_segments(path, sep, escape)
    current = obj
    for position in range(len(segments) - 1):
        current = _descend(path, segments, position, current, create_lists)
    last = len(segments) - 1
    _assign(path, segments[last], last, current, value, create_lists)
    return obj


def _parent(obj: Any, path: PathLike, segments: list[Key]) -> tuple[Any, Exception | None]:
    current = obj
    for position, segment in enumerate(segments[:-1]):
        parent = current
        resolved, current = step(current, segment)
        if not resolved:
            return None, not_found(path, segments, position, parent)
    return current, None


def _remove(obj: Any, path: PathLike, sep: str, escape: bool) -> tuple[Any, Exception | None]:
    """Detach the value at ``path``; return ``(value, None)`` or ``(None, error)``."""
    segments = to_segments(path, sep, escape)
    container, error = _parent(obj, path, segments)
    if error is not None:
        return None, error
    last = segments[-1]
    if isinstance(container, MutableMapping) and last in container:
        return container.pop(last), None
    if isinstance(container, MutableSequence):
        index = as_index(last)
        if index is not None:
            try:
                return container.pop(index), None
            except IndexError:
                pass
    return None, not_found(path, segments, len(segments) - 1, container)


def delete(
    obj: Any, path: PathLike, *, sep: str = ".", missing_ok: bool = False, escape: bool = False
) -> Any:
    """Remove the value at ``path`` in place and return ``obj``.

    A missing path raises ``PathNotFoundError`` (a ``KeyError``) unless
    ``missing_ok`` is true. Removing a list element shifts the ones after it.
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
    """
    value, error = _remove(obj, path, sep, escape)
    if error is None:
        return value
    if default is _MISSING:
        raise error
    return default


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
    """
    value, error = resolve(obj, path, sep, escape)
    if error is None:
        return value
    set(obj, path, default, sep=sep, escape=escape, create_lists=create_lists)
    return default
