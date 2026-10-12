"""Non-mutating writes: return a new structure, copying only the containers on the path."""

from __future__ import annotations

import copy
from collections.abc import Mapping, MutableMapping, MutableSequence
from typing import Any

from ._core import not_found
from ._errors import PathIndexError, PathNotFoundError, PathTypeError
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
            message = f"list index must be an integer, got {segment!r} (segment {position})"
            raise PathTypeError(message, path, segment, position)
        size = len(node)
        if appendable and index == size:
            return index
        if not -size <= index < size:
            message = f"list index {segment!r} (segment {position}) out of range for length {size}"
            raise PathIndexError(message, path, segment, position)
        return index % size
    message = f"cannot set {segment!r} on {type_name(node)} (segment {position})"
    raise PathTypeError(message, path, segment, position)


def _set_in(
    node: Any, path: PathLike, segments: list[Key], position: int, value: Any, lists: bool
) -> Any:
    key = _key_for(path, segments, position, node, lists)
    if position == len(segments) - 1:
        return _shallow_with(node, key, value)
    exists = (isinstance(node, Mapping) and key in node) or (is_sequence(node) and key < len(node))
    child = node[key] if exists else None
    if not is_container(child):
        nxt = as_index(segments[position + 1])
        child = [] if lists and nxt is not None and nxt >= 0 else {}
    return _shallow_with(node, key, _set_in(child, path, segments, position + 1, value, lists))


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
    replaced. Named tuples keep their type unless their length changes; read-only
    mappings come back as dicts. Missing intermediates and ``create_lists`` behave as
    in :func:`set`, with one difference that follows from copying: any value on the
    path that is not a container (including ``None`` inside a list) is replaced by a
    new dict, where :func:`set` raises ``PathTypeError`` inside a list.
    """
    segments = to_segments(path, sep, escape)
    return _set_in(obj, path, segments, 0, value, create_lists)


def _delete_in(node: Any, path: PathLike, segments: list[Key], position: int) -> Any:
    segment = segments[position]
    if isinstance(node, Mapping):
        if segment not in node:
            raise not_found(path, segments, position, node)
        key: Any = segment
    elif is_sequence(node) and (index := as_index(segment)) is not None:
        if not -len(node) <= index < len(node):
            raise not_found(path, segments, position, node)
        key = index % len(node)
    else:
        raise not_found(path, segments, position, node)
    if position == len(segments) - 1:
        return _shallow_with(node, key, None, remove=True)
    return _shallow_with(node, key, _delete_in(node[key], path, segments, position + 1))


def delete_copy(
    obj: Any, path: PathLike, *, sep: str = ".", missing_ok: bool = False, escape: bool = False
) -> Any:
    """Return a copy of ``obj`` without the value at ``path``; ``obj`` is never modified.

    A missing path raises ``PathNotFoundError`` unless ``missing_ok`` is true, in
    which case ``obj`` itself is returned unchanged. Copies only the path's containers.
    """
    segments = to_segments(path, sep, escape)
    try:
        return _delete_in(obj, path, segments, 0)
    except PathNotFoundError:
        if missing_ok:
            return obj
        raise
