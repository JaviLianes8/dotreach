"""Match wildcard patterns against nested data without recursion or repeated work."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from ._errors import StructureError, shown
from ._path import PathLike, as_index, is_container, is_sequence, render, step, to_segments
from ._walk import children, cycle_error

_WILD = ("*", "**")


def glob(obj: Any, pattern: PathLike, *, sep: str = ".", escape: bool = False) -> dict[str, Any]:
    """Return every concrete path matching ``pattern`` mapped to its value.

    A ``*`` segment matches any one key or index; ``**`` matches zero or more levels,
    so ``"**"`` alone lists the root (as ``""``) and every node. Other segments match
    exactly, as in :func:`get`. Results keep depth-first traversal order and negative
    indices are reported as their positive position. Each node is tried at most once
    per pattern position, so several ``**`` never multiply the work.

    Raises:
        StructureError: Two different matches render to the same string path (a key
            that contains the separator; pass ``escape=True``), or a wildcard meets a
            structure that contains itself. A ``ValueError``.
        InvalidPathError: The pattern is empty or malformed.

    >>> glob({"users": [{"name": "Ada"}, {"name": "Lin"}]}, "users.*.name")
    {'users.0.name': 'Ada', 'users.1.name': 'Lin'}
    """
    patterns = to_segments(pattern, sep, escape)
    found: dict[str, Any] = {}
    origin: dict[str, tuple[Any, ...]] = {}
    # Each distinct concrete path gets one small integer, so a state is (path id, index).
    links: dict[tuple[int, Any], int] = {}
    parents: list[tuple[int, Any]] = [(-1, None)]
    seen: set[tuple[int, int]] = set()
    owners: dict[int, int] = {}  # id(node) -> path id of the frame expanding it

    def link(parent: int, key: Any) -> int:
        number = links.setdefault((parent, key), len(parents))
        if number == len(parents):
            parents.append((parent, key))
        return number

    def keys_of(number: int) -> tuple[Any, ...]:
        keys: list[Any] = []
        while number > 0:
            number, key = parents[number]
            keys.append(key)
        return tuple(reversed(keys))

    def successors(node: Any, path: int, index: int) -> Iterator[tuple[Any, int, int]]:
        segment = patterns[index]
        if segment == "**":
            yield node, path, index + 1
        if segment in _WILD:
            following = index if segment == "**" else index + 1
            for key, child in children(node):
                yield child, link(path, key), following
            return
        resolved, child = step(node, segment)
        if resolved:
            position = as_index(segment) if is_sequence(node) else None
            key = position % len(node) if position is not None else segment
            yield child, link(path, key), index + 1

    stack: list[tuple[int, Iterator[tuple[Any, int, int]], bool]] = []

    def push(node: Any, path: int, index: int) -> None:
        if (path, index) in seen:
            return
        seen.add((path, index))
        if index == len(patterns):
            keys = keys_of(path)
            text = render(keys, sep, escape)
            if origin.setdefault(text, keys) != keys:
                message = f"two matches render to the same path {shown(text)}; try escape=True"
                raise StructureError(message, text)
            found[text] = node
            return
        owner = patterns[index] in _WILD and is_container(node)
        if owner:
            if owners.get(id(node), path) != path:
                raise cycle_error()
            owner = id(node) not in owners
            owners[id(node)] = path
        stack.append((id(node) if owner else -1, successors(node, path, index), owner))

    push(obj, 0, 0)
    while stack:
        node_id, pending, owner = stack[-1]
        following = next(pending, None)
        if following is None:
            stack.pop()
            if owner:
                del owners[node_id]
            continue
        push(*following)
    return found
