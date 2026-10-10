"""Read and mutate nested dicts and lists by a dotted path."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping, MutableSequence, Sequence
from typing import Any

_MISSING: Any = object()


def _segments(path: str, sep: str) -> list[str]:
    if not path:
        raise ValueError("path must not be empty")
    return path.split(sep)


def _as_index(segment: str) -> int | None:
    """Return the integer index a segment denotes, or None if it is not one."""
    digits = segment[1:] if segment.startswith("-") else segment
    return int(segment) if digits.isdigit() else None


def _is_readable_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _is_descendable(value: Any) -> bool:
    return isinstance(value, (MutableMapping, MutableSequence))


def _step(container: Any, segment: str) -> tuple[bool, Any]:
    """Advance one segment into a container, reporting whether it resolved."""
    if isinstance(container, Mapping):
        if segment in container:
            return True, container[segment]
        return False, None
    if _is_readable_sequence(container):
        index = _as_index(segment)
        if index is None:
            return False, None
        try:
            return True, container[index]
        except IndexError:
            return False, None
    return False, None


def get(obj: Any, path: str, default: Any = _MISSING, *, sep: str = ".") -> Any:
    """Return the value at ``path``, or ``default`` if the path does not resolve.

    Mapping segments are used as keys; sequence segments as integer indices
    (negative allowed). With no ``default``, a missing path raises ``KeyError``.
    """
    current = obj
    for segment in _segments(path, sep):
        resolved, current = _step(current, segment)
        if not resolved:
            if default is _MISSING:
                raise KeyError(path)
            return default
    return current


def has(obj: Any, path: str, *, sep: str = ".") -> bool:
    """Return whether ``path`` resolves to a value in ``obj``."""
    current = obj
    for segment in _segments(path, sep):
        resolved, current = _step(current, segment)
        if not resolved:
            return False
    return True


def _descend_for_set(container: Any, segment: str) -> Any:
    if isinstance(container, MutableMapping):
        nxt = container.get(segment, _MISSING)
        if not _is_descendable(nxt):
            nxt = {}
            container[segment] = nxt
        return nxt
    if isinstance(container, MutableSequence):
        index = _as_index(segment)
        if index is None:
            raise TypeError(f"list index must be an integer, got {segment!r}")
        return container[index]
    raise TypeError(f"cannot descend into {type(container).__name__} at {segment!r}")


def _assign(container: Any, segment: str, value: Any) -> None:
    if isinstance(container, MutableMapping):
        container[segment] = value
        return
    if isinstance(container, MutableSequence):
        index = _as_index(segment)
        if index is None:
            raise TypeError(f"list index must be an integer, got {segment!r}")
        container[index] = value
        return
    raise TypeError(f"cannot set {segment!r} on {type(container).__name__}")


def set(obj: Any, path: str, value: Any, *, sep: str = ".") -> Any:
    """Set ``value`` at ``path`` and return ``obj``.

    Missing intermediate mapping keys are created as dicts. Sequence elements
    must already exist: an out-of-range index raises ``IndexError``.
    """
    segments = _segments(path, sep)
    current = obj
    for segment in segments[:-1]:
        current = _descend_for_set(current, segment)
    _assign(current, segments[-1], value)
    return obj


def delete(obj: Any, path: str, *, sep: str = ".", missing_ok: bool = False) -> Any:
    """Remove the value at ``path`` and return ``obj``.

    A missing path raises ``KeyError`` unless ``missing_ok`` is true.
    """
    segments = _segments(path, sep)
    current = obj
    for segment in segments[:-1]:
        resolved, current = _step(current, segment)
        if not resolved:
            if missing_ok:
                return obj
            raise KeyError(path)
    last = segments[-1]
    if isinstance(current, MutableMapping) and last in current:
        del current[last]
        return obj
    if isinstance(current, MutableSequence):
        index = _as_index(last)
        if index is not None:
            try:
                del current[index]
            except IndexError:
                pass
            else:
                return obj
    if missing_ok:
        return obj
    raise KeyError(path)
