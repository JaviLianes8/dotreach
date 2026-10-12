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
    r"""Split ``path`` on ``sep``, honouring backslash escapes.

    A backslash before any character of ``sep``, or before another backslash, makes
    that character literal, so ``\.`` is a dot inside a key and ``\\`` a
    backslash. Any other backslash is kept as is. ``split_path(join_path(s, sep), sep)
    == s`` for any non-empty list of string segments.

    >>> split_path(r"files.report\.pdf.size")
    ['files', 'report.pdf', 'size']
    """
    if not sep:
        raise InvalidPathError("sep must not be empty", path)
    special = sep + _ESC
    segments: list[str] = []
    current: list[str] = []
    i, n = 0, len(path)
    while i < n:
        if path[i] == _ESC and i + 1 < n and path[i + 1] in special:
            current.append(path[i + 1])
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
    r"""Join segments into a string path, escaping backslashes and separator characters.

    The inverse of :func:`split_path`. Integer segments are written in decimal. Every
    character of ``sep`` inside a segment is escaped, so multi-character separators
    round-trip too.

    Raises:
        InvalidPathError: ``segments`` is empty or ``sep`` is empty.

    >>> join_path(["files", "report.pdf", "size"])
    'files.report\\.pdf.size'
    """
    if not sep:
        raise InvalidPathError("sep must not be empty", list(segments))
    if not segments:
        raise InvalidPathError("cannot join an empty list of segments", list(segments))
    special = set(sep + _ESC)
    parts = ["".join(_ESC + ch if ch in special else ch for ch in str(s)) for s in segments]
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
    """Render concrete segments as a string path (the root renders as ``""``)."""
    if not segments:
        return ""
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
