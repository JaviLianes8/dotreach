"""Read nested dicts and lists by a dotted path."""

from __future__ import annotations

from typing import Any, TypeVar, overload

from ._errors import PathNotFoundError, PathTypeError
from ._path import MISSING, Key, PathLike, step, to_segments, type_name

T = TypeVar("T")
D = TypeVar("D")

_MISSING: Any = MISSING


def not_found(path: PathLike, segments: list[Key], position: int, at: Any) -> PathNotFoundError:
    """Build the error for a path that stops resolving at ``position``."""
    segment = segments[position]
    message = f"path {path!r} not found: no {segment!r} (segment {position}) in {type_name(at)}"
    return PathNotFoundError(message, path, segment, position)


def resolve(
    obj: Any, path: PathLike, sep: str, escape: bool
) -> tuple[Any, PathNotFoundError | None]:
    """Walk the whole path; return ``(value, None)`` or ``(None, error)``."""
    segments = to_segments(path, sep, escape)
    current = obj
    for position, segment in enumerate(segments):
        parent = current
        resolved, current = step(current, segment)
        if not resolved:
            return None, not_found(path, segments, position, parent)
    return current, None


def get(
    obj: Any, path: PathLike, default: Any = _MISSING, *, sep: str = ".", escape: bool = False
) -> Any:
    """Return the value at ``path``, or ``default`` if the path does not resolve.

    Args:
        obj: The root mapping or sequence.
        path: A dotted string (``"a.b.0"``) or a sequence of segments (``("a", "b", 0)``).
            Mapping segments are keys; sequence segments are integer indices, negative
            allowed. Strings and bytes are never indexed into.
        default: Returned when the path does not resolve. Omit it to raise instead.
        sep: The separator for string paths.
        escape: When true, ``\\.`` in a string path is a literal separator inside a key.

    Raises:
        PathNotFoundError: The path does not resolve and no ``default`` was given. It
            subclasses ``KeyError`` and names the failing segment and its position.
        InvalidPathError: The path is empty or malformed (a ``ValueError``).

    >>> get({"user": {"roles": ["admin", "editor"]}}, "user.roles.-1")
    'editor'
    """
    value, error = resolve(obj, path, sep, escape)
    if error is None:
        return value
    if default is _MISSING:
        raise error
    return default


def has(obj: Any, path: PathLike, *, sep: str = ".", escape: bool = False) -> bool:
    """Return whether ``path`` resolves to a value in ``obj`` (``None`` counts as a value).

    >>> has({"a": {"b": None}}, "a.b")
    True
    """
    return resolve(obj, path, sep, escape)[1] is None


@overload
def get_as(
    obj: Any, path: PathLike, type_: type[T], *, sep: str = ..., escape: bool = ...
) -> T: ...


@overload
def get_as(
    obj: Any, path: PathLike, type_: type[T], default: D, *, sep: str = ..., escape: bool = ...
) -> T | D: ...


def get_as(
    obj: Any,
    path: PathLike,
    type_: type[Any],
    default: Any = _MISSING,
    *,
    sep: str = ".",
    escape: bool = False,
) -> Any:
    """Return the value at ``path`` checked against ``type_``, typed for the checker.

    A missing path returns ``default`` when given and raises ``PathNotFoundError``
    otherwise. A value of the wrong type always raises ``PathTypeError``, even when a
    default is given: a wrong type is a data error, not an absence. ``bool`` is not
    accepted where ``int`` or ``float`` is asked for, although it subclasses ``int``.

    >>> port: int = get_as({"server": {"port": 8080}}, "server.port", int)
    """
    value, error = resolve(obj, path, sep, escape)
    if error is not None:
        if default is _MISSING:
            raise error
        return default
    wrong_bool = isinstance(value, bool) and type_ in (int, float)
    if wrong_bool or not isinstance(value, type_):
        message = f"path {path!r} holds {type_name(value)}, expected {type_.__name__}"
        raise PathTypeError(message, path)
    return value
