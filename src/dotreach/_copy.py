"""Non-mutating writes: return a new structure, copying only the containers on the path."""

from __future__ import annotations

import copy
from collections.abc import Mapping, MutableMapping, MutableSequence
from typing import Any

from ._core import not_found
from ._errors import PathIndexError, PathNotFoundError, PathTypeError, shown
from ._path import Key, PathLike, as_index, is_container, is_sequence, to_segments, type_name


def _shallow_with(node: Any, key: Any, value: Any, *, remove: bool = False) -> Any:
    """Copy ``node`` with ``key`` replaced (or removed), keeping its type where possible."""
    if isinstance(node, (MutableMapping, MutableSequence)):
        new = copy.copy(node)
        if remove:
            del new[key]
        elif isinstance(new, MutableSequence) and key == len(new):
            new.append(value)
        else:
            new[key] = value
        return new
    if isinstance(node, Mapping):
        items = dict(node)
        if remove:
            del items[key]
        else:
            items[key] = value
        return items
    elements = list(node)
    if remove:
        del elements[key]
    elif key == len(elements):
        elements.append(value)
    else:
        elements[key] = value
    make = getattr(type(node), "_make", None)
    if make is not None and len(elements) == len(node):
        return make(elements)
    return tuple(elements)  # a named tuple whose length changes becomes a plain tuple


def _key_for(
    path: PathLike, segments: list[Key], position: int, node: Any, appendable: bool
) -> Any:
    segment = segments[position]
    if isinstance(node, Mapping):
        return segment
    if is_sequence(node):
        index = as_index(segment)
        if index is None:
            message = f"list index must be an integer, got {shown(segment)} (segment {position})"
            raise PathTypeError(message, path, segment, position)
        size = len(node)
        if appendable and index == size:
            return index
        if not -size <= index < size:
            message = (
                f"list index {shown(segment)} (segment {position}) out of range for length {size}"
            )
            raise PathIndexError(message, path, segment, position)
        return index % size
    message = f"cannot set {shown(segment)} on {type_name(node)} (segment {position})"
    raise PathTypeError(message, path, segment, position)


def set_copy(
    obj: Any,
    path: PathLike,
    value: Any,
    *,
    sep: str = ".",
    escape: bool = False,
    create_lists: bool = False,
) -> Any:
    """Return a copy of ``obj`` with ``value`` at ``path``; ``obj`` is never modified.

    Only the containers along the path are copied (structural sharing); everything
    else is shared with the original. Unlike :func:`set`, this works on immutable
    structures too: tuples and read-only mappings on the path are rebuilt rather than
    refused. Named tuples keep their type unless their length changes; read-only
    mappings come back as dicts. Missing intermediates, values that are not containers
    and ``create_lists`` behave as in :func:`set`.

    Raises:
        PathTypeError: A non-integer segment meets a sequence, or the root is not a
            container.
        PathIndexError: A sequence index is out of range.
        InvalidPathError: The path is empty or malformed.

    >>> data = {"user": {"name": "Ada"}, "tags": ("a", "b")}
    >>> set_copy(data, "tags.0", "z")
    {'user': {'name': 'Ada'}, 'tags': ('z', 'b')}
    >>> set_copy(data, "user.name", "Lin")["user"] is data["user"], data["user"]
    (False, {'name': 'Ada'})
    """
    segments = to_segments(path, sep, escape)
    nodes: list[tuple[Any, Any]] = []
    node = obj
    for position in range(len(segments)):
        key = _key_for(path, segments, position, node, create_lists)
        nodes.append((node, key))
        if position == len(segments) - 1:
            break
        exists = key in node if isinstance(node, Mapping) else key < len(node)
        node = node[key] if exists else None
        if not is_container(node):
            nxt = as_index(segments[position + 1])
            node = [] if create_lists and nxt is not None and nxt >= 0 else {}
    for parent, key in reversed(nodes):
        value = _shallow_with(parent, key, value)
    return value


def _delete_chain(obj: Any, path: PathLike, segments: list[Key]) -> list[tuple[Any, Any]]:
    nodes: list[tuple[Any, Any]] = []
    node = obj
    for position, segment in enumerate(segments):
        index = as_index(segment) if is_sequence(node) else None
        if isinstance(node, Mapping) and segment in node:
            key: Any = segment
        elif index is not None and -len(node) <= index < len(node):
            key = index % len(node)
        else:
            raise not_found(path, segments, position, node)
        nodes.append((node, key))
        node = node[key]
    return nodes


def delete_copy(
    obj: Any, path: PathLike, *, sep: str = ".", missing_ok: bool = False, escape: bool = False
) -> Any:
    """Return a copy of ``obj`` without the value at ``path``; ``obj`` is never modified.

    A missing path raises ``PathNotFoundError`` unless ``missing_ok`` is true, in
    which case ``obj`` itself is returned unchanged. Copies only the path's containers,
    so tuples and read-only mappings on the path work too.

    >>> data = {"a": (1, 2, 3), "b": {"c": 1}}
    >>> delete_copy(data, "a.-1"), data["a"]
    ({'a': (1, 2), 'b': {'c': 1}}, (1, 2, 3))
    >>> delete_copy(data, "x.y", missing_ok=True) is data
    True
    """
    segments = to_segments(path, sep, escape)
    try:
        nodes = _delete_chain(obj, path, segments)
    except PathNotFoundError:
        if missing_ok:
            return obj
        raise
    parent, key = nodes[-1]
    value = _shallow_with(parent, key, None, remove=True)
    for parent, key in reversed(nodes[:-1]):
        value = _shallow_with(parent, key, value)
    return value
