"""Typed errors that name the path and the exact segment that failed."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any


class DotreachError(Exception):
    """Base class of every error dotreach raises on purpose.

    Attributes:
        path: The path as the caller passed it (a string or a sequence of segments).
        segment: The segment that failed, or ``None`` when the whole path is at fault.
        position: Zero-based index of ``segment`` within the parsed path, or ``None``.
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
    """A segment cannot be applied to the value it meets. Subclasses ``TypeError``."""


class PathIndexError(DotreachError, IndexError):
    """A sequence index is out of range for a write. Subclasses ``IndexError``."""


class InvalidPathError(DotreachError, ValueError):
    """The path itself is malformed, for example empty. Subclasses ``ValueError``."""
