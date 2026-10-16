"""Typed errors that name the path and the exact segment that failed."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

_LIMIT = 60


def shown(value: Any) -> str:
    """``repr(value)`` cut to a bounded length, so messages never echo huge input."""
    try:
        text = repr(value)
    except (ValueError, RecursionError):  # an int past str()'s digit limit, deep nesting
        return f"<{type(value).__name__} too large to show>"
    if len(text) <= _LIMIT:
        return text
    return f"{text[: _LIMIT - 20]}...{text[-12:]} ({len(text)} chars)"


class DotreachError(Exception):
    """Base class of every error dotreach raises on purpose.

    Messages quote the path and segment cut to a bounded length; the attributes keep
    them whole.

    Attributes:
        path: The path as the caller passed it (a string or a sequence of segments).
        segment: The segment that failed, or ``None`` when the whole path is at fault.
        position: Zero-based index of ``segment`` within the parsed path, or ``None``.

    >>> import dotreach
    >>> try:
    ...     dotreach.get({"a": {"b": 1}}, "a.x")
    ... except dotreach.DotreachError as error:
    ...     print(error.segment, error.position)
    x 1
    """

    def __init__(
        self,
        message: str,
        path: str | Sequence[str | int] | None = None,
        segment: str | int | None = None,
        position: int | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.path = path
        self.segment = segment
        self.position = position

    def __str__(self) -> str:
        return self.message

    def __reduce__(self) -> tuple[Any, ...]:
        # Keep errors picklable and copyable (process pools, copy.copy).
        return (type(self), (self.message, self.path, self.segment, self.position))


class PathNotFoundError(DotreachError, KeyError):
    """The path does not resolve. Subclasses ``KeyError``.

    For compatibility with releases that raised a bare ``KeyError(path)``,
    ``args[0]`` is the path itself; ``str(error)`` is a readable message.

    >>> import dotreach
    >>> try:
    ...     dotreach.get({"a": 1}, "b")
    ... except KeyError as error:
    ...     print(error.args[0], "|", error)
    b | path 'b' not found: no 'b' (segment 0) in dict
    """

    def __init__(
        self,
        message: str,
        path: str | Sequence[str | int],
        segment: str | int | None = None,
        position: int | None = None,
    ) -> None:
        super().__init__(message, path, segment, position)
        self.args = (path,)


class PathTypeError(DotreachError, TypeError):
    """A segment cannot be applied to the value it meets. Subclasses ``TypeError``.

    >>> import dotreach
    >>> dotreach.set({"a": [1]}, "a.x", 2)
    Traceback (most recent call last):
    dotreach.PathTypeError: list index must be an integer, got 'x' (segment 1)
    """


class PathIndexError(DotreachError, IndexError):
    """A sequence index is out of range for a write. Subclasses ``IndexError``.

    >>> import dotreach
    >>> dotreach.set({"a": [1]}, "a.5", 2)
    Traceback (most recent call last):
    dotreach.PathIndexError: list index '5' (segment 1) out of range for length 1
    """


class InvalidPathError(DotreachError, ValueError):
    """The path itself is malformed, for example empty. Subclasses ``ValueError``.

    >>> import dotreach
    >>> dotreach.get({}, "")
    Traceback (most recent call last):
    dotreach.InvalidPathError: path must not be empty
    """


class StructureError(DotreachError, ValueError):
    """The data cannot be walked as asked. Subclasses ``ValueError``.

    Raised when a structure contains itself, or when two different leaves or matches
    render to the same string path (a key that contains the separator).

    >>> import dotreach
    >>> dotreach.flatten({"a.b": 1, "a": {"b": 2}})
    Traceback (most recent call last):
    dotreach.StructureError: two leaves flatten to the same path 'a.b'; try escape=True
    """
