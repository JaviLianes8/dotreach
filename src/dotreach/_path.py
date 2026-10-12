"""Path parsing, escaping and the single-step resolution rule shared by every function."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping, MutableSequence, Sequence
from typing import Any, TypeAlias

from ._errors import InvalidPathError

Key: TypeAlias = str | int
"""One path segment: a mapping key, or an integer index into a sequence."""

PathLike: TypeAlias = str | Sequence[str | int]
"""A dotted string such as ``"a.b.0"`` or an explicit sequence such as ``("a", "b", 0)``."""

MISSING: Any = object()
_ESC = "\\"


def split_path(path: str, sep: str = ".") -> list[str]:
    """Split ``path`` on ``sep``, honouring backslash escapes.

    ``\\<sep>`` yields a literal separator inside a segment and ``\\\\`` a literal
    backslash; any other backslash is kept as is. ``split_path(join_path(s)) == s``
    for any list of string segments.

    >>> split_path(r"files.report\\.pdf.size")
    ['files', 'report.pdf', 'size']
    """
    if not sep:
        raise InvalidPathError("sep must not be empty", path)
    segments: list[str] = []
    current: list[str] = []
    i, n = 0, len(path)
    while i < n:
        if path.startswith(_ESC + sep, i):
            current.append(sep)
            i += 1 + len(sep)
        elif path.startswith(_ESC + _ESC, i):
            current.append(_ESC)
            i += 2
        elif path.startswith(sep, i):
            segments.append("".join(current))
            current = []
            i += len(sep)
        else:
            current.append(path[i])
            i += 1
    segments.append("".join(current))
    return segments


def join_path(segments: Sequence[str | int], sep: str = ".") -> str:
    """Join segments into a string path, escaping backslashes and separators.

    The inverse of :func:`split_path`. Integer segments are written in decimal.

    >>> join_path(["files", "report.pdf", "size"])
    'files.report\\\\.pdf.size'
    """
    if not sep:
        raise InvalidPathError("sep must not be empty", list(segments))
    parts = []
    for segment in segments:
        text = str(segment).replace(_ESC, _ESC + _ESC)
        parts.append(text.replace(sep, _ESC + sep))
    return sep.join(parts)


def to_segments(path: PathLike, sep: str = ".", escape: bool = False) -> list[Key]:
    """Parse any accepted path form into a non-empty list of segments."""
    if isinstance(path, str):
        if not path:
            raise InvalidPathError("path must not be empty", path)
        if not sep:
            raise InvalidPathError("sep must not be empty", path)
        return list(split_path(path, sep) if escape else path.split(sep))
    if isinstance(path, (bytes, bytearray)) or not isinstance(path, Sequence):
        raise InvalidPathError(f"path must be a string or a sequence, got {path!r}")
    segments = list(path)
    if not segments:
        raise InvalidPathError("path must not be empty", path)
    for position, segment in enumerate(segments):
        if isinstance(segment, bool) or not isinstance(segment, (str, int)):
            message = f"segment {position} of {path!r} must be str or int, got {segment!r}"
            raise InvalidPathError(message, path, None, position)
    return segments


def render(segments: Sequence[Key], sep: str, escape: bool) -> str:
    """Render concrete segments as a string path."""
    return join_path(segments, sep) if escape else sep.join(str(s) for s in segments)


def as_index(segment: Key) -> int | None:
    """Return the integer index a segment denotes, or None if it is not one."""
    if isinstance(segment, int):
        return None if isinstance(segment, bool) else segment
    digits = segment[1:] if segment.startswith("-") else segment
    return int(segment) if digits.isdecimal() else None


def is_sequence(value: Any) -> bool:
    """Whether ``value`` is a sequence dotreach indexes into (never str or bytes)."""
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def is_container(value: Any) -> bool:
    """Whether ``value`` is a mapping or an indexable sequence."""
    return isinstance(value, Mapping) or is_sequence(value)


def is_mutable(value: Any) -> bool:
    """Whether ``value`` is a container that can be written in place."""
    return isinstance(value, (MutableMapping, MutableSequence))


def step(container: Any, segment: Key) -> tuple[bool, Any]:
    """Advance one segment into a container, reporting whether it resolved."""
    if isinstance(container, Mapping):
        if segment in container:
            return True, container[segment]
        return False, None
    if is_sequence(container):
        index = as_index(segment)
        if index is None:
            return False, None
        try:
            return True, container[index]
        except IndexError:
            return False, None
    return False, None


def type_name(value: Any) -> str:
    """Short type name used in error messages."""
    return type(value).__name__
