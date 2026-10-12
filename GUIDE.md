# dotreach guide

Everything the library and the command promise, in one place. Every function takes
the root object first and a path second.

## The path

A path is either:

- a **string**, split on `sep` (default `"."`): `"user.roles.0"`; or
- a **sequence** of `str` and `int` segments: `("user", "roles", 0)`.

An empty path is an `InvalidPathError`, as is an empty `sep`, a `bytes` path, or a
segment that is not `str`/`int` (`bool` is rejected on purpose).

### How one segment is read

- On a **mapping**, the segment is a key, exactly as given. A string path always
  produces string keys; use a sequence path to reach an `int` key.
- On a **sequence** (list, tuple, any `Sequence` that is not `str`/`bytes`), the
  segment must be an integer, given as `int` or as decimal text like `"2"` or `"-1"`.
  Negative indices count from the end.
- Anything else (numbers, strings, `None`) cannot be entered: the path does not
  resolve there.

### Escaping

With `escape=True`, a backslash before any character of the separator, or before
another backslash, makes that character literal; any other backslash stays as is.
`join_path` and `split_path` apply the same rule and are exact inverses for any
non-empty list of segments, multi-character separators included (`join_path([])`
raises `InvalidPathError`, since an empty path is not a path):

```python
get({"report.pdf": 1}, r"report\.pdf", escape=True)   # 1
join_path(["a.b", 0])                                 # 'a\\.b.0'
```

Escaping is off by default so that paths written for 0.1 keep their meaning.

## Reading

| Function | Returns | When the path is missing |
|---|---|---|
| `get(obj, path, default=...)` | the value | `default`, or `PathNotFoundError` |
| `has(obj, path)` | `bool` | `False` (a stored `None` is present) |
| `get_as(obj, path, type_, default=...)` | the value, typed `T` | `default`, or `PathNotFoundError` |

`get_as` checks `isinstance(value, type_)` and raises `PathTypeError` on a mismatch,
even when a default is given: a wrong type is bad data, not an absence. `bool` is not
accepted for `int` or `float`.

## Writing in place

`set(obj, path, value, create_lists=False)` writes and returns `obj`.

- A missing intermediate key, or one holding a value that is not a mutable container
  (a number, a string, a tuple), becomes a new `dict`.
- Existing list elements are replaced; negative indices work.
- An out-of-range index raises `PathIndexError`; a non-integer segment on a list, or a
  path that runs into a value that cannot be written, raises `PathTypeError`.
- With `create_lists=True`, a missing intermediate becomes a `list` when the next
  segment is a non-negative integer, and an index equal to the list length appends.
  Gaps still raise `PathIndexError`.

`delete(obj, path, missing_ok=False)` removes and returns `obj`. `pop(obj, path,
default=...)` removes and returns the value. `setdefault(obj, path, default=None)`
returns the existing value, or sets and returns `default`.

## Writing without mutation

`set_copy` and `delete_copy` take the same arguments as `set` and `delete` and return
a new root. Only the containers along the path are copied; every other branch is
shared with the original. Because nothing is written in place they also work through
tuples (rebuilt; a named tuple keeps its type unless its length changes, then it
becomes a plain tuple) and read-only mappings (returned as a `dict`). Dict and list
subclasses keep their type via `copy.copy`. `delete_copy` with `missing_ok=True`
returns the original object when the path is absent.

Where `set` and `set_copy` differ: `set_copy` can enter a tuple on the path and
rebuild it, where `set` replaces a tuple held in a dict with a new dict. And
`set_copy` replaces any non-container value on the path with a new dict, including
one inside a list, where `set` raises `PathTypeError`.

## Iterating and reshaping

- `walk(obj)` yields `(segments_tuple, value)` for every leaf, depth first. Segments are
  the exact keys and indices, so each tuple goes straight back into `get`.
- `leaves(obj, sep=".", escape=False)` yields `(string_path, value)`.
- `flatten(obj, ...)` returns `dict(leaves(obj, ...))` and raises `ValueError` if two
  leaves render to the same string (a key containing the separator); `escape=True`
  keeps them distinct.
- `unflatten(flat, create_lists=False, ...)` rebuilds nesting and raises
  `PathTypeError` when two paths conflict (`"a"` and `"a.b"`). With `create_lists`,
  integer segments build lists and must arrive in order, as `flatten` produces them.

A leaf is any non-container value plus every empty container, so
`unflatten(flatten(x, escape=True), escape=True)` rebuilds any dict whose keys are
non-empty strings, with lists coming back as dicts keyed `"0"`, `"1"`, and so on.
With `create_lists=True` lists come back as lists, provided no dict in `x` has
digit-only keys (those would turn into lists too). `unflatten` always returns a dict,
so a list root does not round-trip, and an empty key cannot (an empty path is
invalid). Empty containers in the input are copied, never shared with the result.
A structure that contains itself raises `ValueError`; shared subtrees are fine.

## Wildcards

`glob(obj, pattern)` returns `{concrete_path: value}` for every match. A `*` segment
matches any one key or index; `**` matches zero or more levels, so `"**"` alone lists
the root (as `""`) and every node. Other segments match as in `get`; a negative index
is reported as its positive position. If two different matches render to the same
string (a key that contains the separator), `glob` raises `ValueError` like `flatten`;
`escape=True` keeps them apart.

## Errors

| Error | Also a | Raised when |
|---|---|---|
| `PathNotFoundError` | `KeyError` | a read, delete or pop finds no value |
| `PathTypeError` | `TypeError` | a segment cannot apply, a type check fails, paths conflict |
| `PathIndexError` | `IndexError` | a write index is out of range |
| `InvalidPathError` | `ValueError` | the path or separator is malformed |

All share the base `DotreachError` with `.path`, `.segment` and `.position` (the
zero-based segment index) where known. `PathNotFoundError.args[0]` is the path, as
the bare `KeyError(path)` of 0.1 was.

## Command line

```
dotreach get PATH [FILE] [--default JSON] [--raw]
dotreach has PATH [FILE]
dotreach set PATH VALUE [FILE] [--string] [--create-lists] [-i]
dotreach delete PATH [FILE] [--missing-ok] [-i]
dotreach glob PATTERN [FILE]
dotreach flatten [FILE]
dotreach unflatten [FILE] [--create-lists]
```

Every command also takes `--sep`, `--escape` and `--indent N` (0 for compact). `FILE`
defaults to standard input. `VALUE` is parsed as JSON when it is valid JSON and taken
as a string otherwise; `--string` forces a string. `-i` writes the result back to
`FILE`. Errors print `dotreach: <message>` on stderr and exit 1; `has` exits 1 when
the path is absent, so check stderr to tell an absent path from an unreadable file.
A path that starts with `-` goes after `--`:
`dotreach get -- -1 data.json`.
