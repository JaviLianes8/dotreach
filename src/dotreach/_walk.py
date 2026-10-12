"""Iterate leaf paths, flatten and unflatten, and match wildcard patterns."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any, TypeVar

from ._errors import PathTypeError
from ._path import Key, PathLike, as_index, is_container, is_sequence, render, step, to_segments
from ._write import set as _set

P = TypeVar("P", bound=PathLike)


def _children(node: Any) -> Iterator[tuple[Key, Any]]:
    if isinstance(node, Mapping):
        yield from node.items()
    elif is_sequence(node):
        yield from enumerate(node)


def _enter(node: Any, stack: list[int]) -> None:
    if id(node) in stack:
        raise ValueError("cannot walk a structure that contains itself")
    stack.append(id(node))


def walk(obj: Any) -> Iterator[tuple[tuple[Key, ...], Any]]:
    """Yield ``(segments, value)`` for every leaf, depth first, in container order.

    Segments are exact keys and indices, so the result is lossless: each tuple can be
    passed straight back to :func:`get`. A leaf is any value that is not a mapping or a
    sequence, plus every *empty* mapping or sequence (so structure round-trips). A
    non-container root has no paths and yields nothing.

    Raises:
        ValueError: The structure contains itself.

    >>> list(walk({"a": [1, {}]}))
    [(('a', 0), 1), (('a', 1), {})]
    """
    stack: list[int] = []

    def visit(node: Any, prefix: tuple[Key, ...]) -> Iterator[tuple[tuple[Key, ...], Any]]:
        _enter(node, stack)
        for key, child in _children(node):
            path = (*prefix, key)
            if is_container(child) and len(child) > 0:
                yield from visit(child, path)
            else:
                yield path, child
        stack.pop()

    if is_container(obj):
        yield from visit(obj, ())


def leaves(obj: Any, *, sep: str = ".", escape: bool = False) -> Iterator[tuple[str, Any]]:
    """Yield ``(path, value)`` for every leaf, with the path as a string.

    Keys are rendered with ``str``. Pass ``escape=True`` to escape separators inside
    keys so every path reads back with ``get(..., escape=True)``.

    >>> dict(leaves({"db": {"host": "x", "ports": [5432]}}))
    {'db.host': 'x', 'db.ports.0': 5432}
    """
    for segments, value in walk(obj):
        yield render(segments, sep, escape), value


def flatten(obj: Any, *, sep: str = ".", escape: bool = False) -> dict[str, Any]:
    """Return a one-level dict mapping every leaf path to its value.

    Raises:
        ValueError: Two leaves render to the same path, for example a key that
            contains the separator; pass ``escape=True`` to keep them distinct.
    """
    flat: dict[str, Any] = {}
    for path, value in leaves(obj, sep=sep, escape=escape):
        if path in flat:
            raise ValueError(f"two leaves flatten to the same path {path!r}; try escape=True")
        flat[path] = value
    return flat


def unflatten(
    flat: Mapping[P, Any],
    *,
    sep: str = ".",
    escape: bool = False,
    create_lists: bool = False,
) -> dict[str, Any]:
    """Build a nested dict from a mapping of paths to values; the inverse of :func:`flatten`.

    With ``create_lists=True`` integer segments build lists (indices must arrive in
    order, as :func:`flatten` produces them); otherwise every level is a dict.

    Raises:
        PathTypeError: Two paths conflict, such as ``"a"`` holding a value and
            ``"a.b"`` needing ``"a"`` to be a container.
    """
    result: dict[str, Any] = {}
    placed: list[int] = []
    for path, value in flat.items():
        segments = to_segments(path, sep, escape)
        node: Any = result
        for position, segment in enumerate(segments):
            resolved, child = step(node, segment)
            last = position == len(segments) - 1
            if resolved and (last or not is_container(child) or id(child) in placed):
                message = f"path {path!r} conflicts with an earlier path at {segment!r}"
                raise PathTypeError(message, path, segment, position)
            if not resolved:
                break
            node = child
        _set(result, segments, value, create_lists=create_lists)
        placed.append(id(value))
    return result


def glob(obj: Any, pattern: PathLike, *, sep: str = ".", escape: bool = False) -> dict[str, Any]:
    """Return every concrete path matching ``pattern`` mapped to its value.

    A ``*`` segment matches any one key or index; ``**`` matches zero or more levels.
    Other segments match exactly, as in :func:`get`. Results keep traversal order and
    negative indices are reported as their positive position.

    >>> glob({"users": [{"name": "Ada"}, {"name": "Lin"}]}, "users.*.name")
    {'users.0.name': 'Ada', 'users.1.name': 'Lin'}
    """
    patterns = to_segments(pattern, sep, escape)
    found: dict[str, Any] = {}
    stack: list[int] = []

    def match(node: Any, index: int, prefix: tuple[Key, ...]) -> None:
        if index == len(patterns):
            found.setdefault(render(prefix, sep, escape), node)
            return
        segment = patterns[index]
        if segment in ("*", "**"):
            if segment == "**":
                match(node, index + 1, prefix)
            if not is_container(node):
                return
            _enter(node, stack)
            following = index if segment == "**" else index + 1
            for key, child in _children(node):
                match(child, following, (*prefix, key))
            stack.pop()
            return
        resolved, child = step(node, segment)
        if resolved:
            position = as_index(segment) if is_sequence(node) else None
            key = position % len(node) if position is not None else segment
            match(child, index + 1, (*prefix, key))

    match(obj, 0, ())
    return found
