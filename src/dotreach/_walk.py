"""Iterate leaf paths, flatten and unflatten."""

from __future__ import annotations

import copy
from collections.abc import Iterator, Mapping
from typing import Any, TypeVar, overload

from ._errors import PathTypeError, StructureError, shown
from ._path import Key, PathLike, is_container, is_sequence, render, step, to_segments
from ._write import set as _set

P = TypeVar("P", bound=PathLike)


def children(node: Any) -> Iterator[tuple[Any, Any]]:
    """Yield ``(key, child)`` for a mapping or an indexable sequence, else nothing."""
    if isinstance(node, Mapping):
        yield from node.items()
    elif is_sequence(node):
        yield from enumerate(node)


def cycle_error() -> StructureError:
    return StructureError("cannot walk a structure that contains itself")


def walk(obj: Any) -> Iterator[tuple[tuple[Key, ...], Any]]:
    """Yield ``(segments, value)`` for every leaf, depth first, in container order.

    Segments are exact keys and indices, so for str and int keys each tuple can be
    passed straight back to :func:`get`; keys of other types are yielded as they are.
    A leaf is any value that is not a mapping or a sequence, plus every *empty*
    mapping or sequence (so structure round-trips). A non-container root yields
    nothing. Iterative: any depth works, and shared subtrees are visited once per path.

    Raises:
        StructureError: The structure contains itself (a ``ValueError``).

    >>> list(walk({"a": [1, {}]}))
    [(('a', 0), 1), (('a', 1), {})]
    """
    if not is_container(obj):
        return
    keys: list[Any] = []
    active = {id(obj)}
    stack = [(obj, children(obj))]
    while stack:
        node, pending = stack[-1]
        for key, child in pending:
            if is_container(child) and len(child) > 0:
                if id(child) in active:
                    raise cycle_error()
                active.add(id(child))
                keys.append(key)
                stack.append((child, children(child)))
                break
            yield (*keys, key), child
        else:
            stack.pop()
            active.discard(id(node))
            if keys:
                keys.pop()


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
        StructureError: Two leaves render to the same path, for example a key that
            contains the separator (pass ``escape=True`` to keep them distinct), or
            the structure contains itself. A ``ValueError``.

    >>> flatten({"db": {"host": "x", "ports": [5432]}})
    {'db.host': 'x', 'db.ports.0': 5432}
    """
    flat: dict[str, Any] = {}
    for path, value in leaves(obj, sep=sep, escape=escape):
        if path in flat:
            message = f"two leaves flatten to the same path {shown(path)}; try escape=True"
            raise StructureError(message, path)
        flat[path] = value
    return flat


@overload
def unflatten(
    flat: Mapping[str, Any], *, sep: str = ..., escape: bool = ..., create_lists: bool = ...
) -> dict[str, Any]: ...


@overload
def unflatten(
    flat: Mapping[P, Any], *, sep: str = ..., escape: bool = ..., create_lists: bool = ...
) -> dict[Any, Any]: ...


def unflatten(
    flat: Mapping[Any, Any],
    *,
    sep: str = ".",
    escape: bool = False,
    create_lists: bool = False,
) -> dict[Any, Any]:
    """Build a nested dict from a mapping of paths to values; the inverse of :func:`flatten`.

    With ``create_lists=True`` integer segments build lists (indices must arrive in
    order, as :func:`flatten` produces them); otherwise every level is a dict. The
    result is always a dict, so a list root or a digit-only key under
    ``create_lists`` does not come back as it went into :func:`flatten`. String paths
    give a ``dict[str, Any]``; sequence paths may put ``int`` keys at the top.

    Raises:
        PathTypeError: Two paths conflict, such as ``"a"`` holding a value and
            ``"a.b"`` needing ``"a"`` to be a container.
        PathIndexError: Under ``create_lists`` an index skips ahead of the list.
        InvalidPathError: A path is empty or malformed.

    >>> unflatten({"db.host": "x", "db.ports.0": 5432}, create_lists=True)
    {'db': {'host': 'x', 'ports': [5432]}}
    """
    result: dict[Any, Any] = {}
    placed: set[int] = set()
    for path, value in flat.items():
        segments = to_segments(path, sep, escape)
        node: Any = result
        for position, segment in enumerate(segments):
            resolved, child = step(node, segment)
            last = position == len(segments) - 1
            if resolved and (last or not is_container(child) or id(child) in placed):
                message = f"path {shown(path)} conflicts with an earlier path at {shown(segment)}"
                raise PathTypeError(message, path, segment, position)
            if not resolved:
                break
            node = child
        if is_container(value) and len(value) == 0:
            value = copy.copy(value)  # never hand the caller's empty container back
        _set(result, segments, value, create_lists=create_lists)
        placed.add(id(value))
    return result
