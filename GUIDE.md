# dotreach guide

Everything the library and the command promise, in one place. Every function takes
the root object first and a path second.

## The path

A path is either:

- a **string**, split on `sep` (default `"."`): `"user.roles.0"`; or
- a **sequence** of `str` and `int` segments: `("user", "roles", 0)`.

An empty path is an `InvalidPathError`, as is an empty `sep`, a `bytes` path, or a
segment that is not `str`/`int` (`bool` is rejected on purpose). The type aliases
`Key` (one segment) and `PathLike` (a whole path) are exported for annotations.

### How one segment is read

- On a **mapping**, the segment is a key, exactly as given. A string path always
  produces string keys; use a sequence path to reach an `int` key.
- On a **sequence** (list, tuple, any `Sequence` that is not `str`/`bytes`), the
  segment must be an integer: an `int`, or text made only of decimal digits with an
  optional leading `-`, such as `"2"`, `"-1"` or `"02"`. Decimal digits are those of
  `str.isdecimal`, so other scripts' digits count too (`"١"`, Arabic-Indic one, is
  `1`), as with Python's `int()`. Negative indices count from
  the end. Text with a `+`, spaces, underscores or a decimal point is not an index,
  even though Python's `int()` would accept some of it. A number too large for any
  sequence is simply out of range.
- Anything else (numbers, text, `None`) cannot be entered: the path does not
  resolve there. Text means `str`, `bytes`, `bytearray` and `collections.UserString`:
  they are sequences to Python, but dotreach treats them as single values everywhere.

### Escaping

With `escape=True`, a backslash before any character of the separator, or before
another backslash, makes that character literal; any other backslash stays as is.
`join_path` and `split_path` apply the same rule and are exact inverses for any
non-empty list of segments, multi-character separators included. Escaping needs a
separator without a backslash: `split_path`, `join_path` and every `escape=True` call
raise `InvalidPathError` otherwise (a plain `sep="\\"` without escaping is fine).

```python
from dotreach import get, join_path

get({"report.pdf": 1}, r"report\.pdf", escape=True)   # 1
join_path(["a.b", 0])                                 # 'a\\.b.0'
```

Escaping is off by default so that paths written for 0.1 keep their meaning.

### Compared with JSON Pointer

RFC 6901 pointers map onto sequence paths: decode `~1` and `~0` in each token and
pass the tokens as a tuple. The test suite checks every example of the RFC this way.
The differences: dotreach also accepts leading zeros, negative indices (`-0` is
index 0) and non-ASCII decimal digits in indices, and it has no path for the whole document (an empty path is
invalid).

## Reading

| Function | Returns | When the path is missing |
|---|---|---|
| `get(obj, path, default=...)` | the value | `default`, or `PathNotFoundError` |
| `has(obj, path)` | `bool` | `False` (a stored `None` is present) |
| `get_as(obj, path, type_, default=...)` | the value, typed `T` | `default`, or `PathNotFoundError` |

A malformed path raises `InvalidPathError` in all three, `has` included. `get_as`
checks `isinstance(value, type_)` and raises `PathTypeError` on a mismatch, even when
a default is given: a wrong type is bad data, not an absence. `bool` is not accepted
for `int` or `float`, and `type_` must be a class.

## Writing in place

`set(obj, path, value, create_lists=False)` writes and returns `obj`.

- A missing intermediate, or one holding a value that is not a container (a number,
  a string, `None`), becomes a new `dict`, whether it sits in a dict or in a list.
- A container that cannot be written in place (a tuple, a read-only mapping) is
  never replaced: `set` raises `PathTypeError` and the message points to `set_copy`.
- Existing list elements are replaced; negative indices work.
- An out-of-range index raises `PathIndexError`; a non-integer segment on a list, or a
  root that is not a writable container, raises `PathTypeError`.
- With `create_lists=True`, a missing intermediate becomes a `list` when the next
  segment is a non-negative integer, and an index equal to the list length appends.
  Gaps still raise `PathIndexError`.

`delete(obj, path, missing_ok=False)` removes and returns `obj`. `pop(obj, path,
default=...)` removes and returns the value. A value held in a read-only container
raises `PathTypeError` from both, even with `missing_ok` or a default, since it is
present. `setdefault(obj, path, default=None)` returns the existing value, or sets
and returns `default`.

## Writing without mutation

`set_copy` and `delete_copy` take the same arguments as `set` and `delete` and return
a new root. Only the containers along the path are copied; every other branch is
shared with the original. They follow the same rules as `set` and `delete`, except
that read-only containers on the path are rebuilt instead of refused: tuples come
back as tuples (a named tuple keeps its type unless its length changes, then it
becomes a plain tuple) and read-only mappings as `dict`s. Dict and list subclasses
keep their type via `copy.copy`. `delete_copy` with `missing_ok=True` returns the
original object when the path is absent.

## Iterating and reshaping

- `walk(obj)` yields `(segments_tuple, value)` for every leaf, depth first. Segments are
  the exact keys and indices, so for `str` and `int` keys each tuple goes straight
  back into `get`; keys of other types are yielded as they are.
- `leaves(obj, sep=".", escape=False)` yields `(string_path, value)`.
- `flatten(obj, ...)` returns `dict(leaves(obj, ...))` and raises `StructureError` if
  two leaves render to the same string (a key containing the separator); `escape=True`
  keeps them distinct.
- `unflatten(flat, create_lists=False, ...)` rebuilds nesting and raises
  `PathTypeError` when two paths conflict (`"a"` and `"a.b"`). With `create_lists`,
  integer segments build lists and must arrive in order, as `flatten` produces them.

A leaf is any non-container value plus every empty container; a root that is not a
container has no paths, so `walk(5)` yields nothing and `flatten(5)` is `{}`. So
`unflatten(flatten(x, escape=True), escape=True)` rebuilds any dict whose keys are
non-empty strings, with lists coming back as dicts keyed `"0"`, `"1"`, and so on.
With `create_lists=True` lists come back as lists, provided no dict in `x` has
digit-only keys (those would turn into lists too). `unflatten` always returns a dict,
so a list root does not round-trip, and an empty key cannot (an empty path is
invalid). Empty containers in the input are copied, never shared with the result.

These functions do not recurse, so they work at any nesting depth. A structure that
contains itself raises `StructureError`; shared subtrees are fine and are visited
once per path that reaches them.

## Wildcards

`glob(obj, pattern)` returns `{concrete_path: value}` for every match, in depth-first
order. A `*` segment matches any one key or index; `**` matches zero or more levels,
so `"**"` alone lists the root (as `""`) and every node. Other segments match as in
`get`; a negative index is reported as its positive position. Each node is tried at
most once per pattern position, so several `**` in one pattern never multiply the
work. If two different matches render to the same string (a key that contains the
separator), `glob` raises `StructureError` like `flatten`; `escape=True` keeps them
apart. A key named `*` or `**` can only be matched by a wildcard.

## Errors

| Error | Also a | Raised when |
|---|---|---|
| `PathNotFoundError` | `KeyError` | a read, delete or pop finds no value |
| `PathTypeError` | `TypeError` | a segment cannot apply, a type check fails, paths conflict, a read-only container is written |
| `PathIndexError` | `IndexError` | a write index is out of range |
| `InvalidPathError` | `ValueError` | the path or separator is malformed |
| `StructureError` | `ValueError` | the data contains itself, or two paths render alike |

All share the base `DotreachError` with `.path`, `.segment` and `.position` (the
zero-based segment index) where known. Messages quote paths and keys cut to a short
length, so huge input never floods a log; the attributes keep them whole.
`PathNotFoundError.args[0]` is the path, as the bare `KeyError(path)` of 0.1 was.
Errors raised by your own containers are passed through unchanged: a `dict` subclass
that refuses a deletion, or an `array.array` that refuses a value of the wrong type,
raises its own exception, not a `DotreachError`.

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

Every command also takes `--sep`, `--escape` and `--indent N` (0 to 64, 0 for
compact). `FILE` defaults to standard input. Input must be strict JSON: `NaN`,
`Infinity` and numbers too large for a float (such as `1e999`) are refused, and the
output is always strict JSON too. `VALUE` is parsed the same way when it is valid
JSON and taken as a string otherwise (so `NaN` becomes the string `"NaN"`);
`--string` forces a string. `-i` writes the result to a temporary file next to
`FILE` and then replaces `FILE` with it, so a failure leaves `FILE` as it was. Errors print `dotreach: <message>` on stderr and exit 1,
input nested too deeply for Python's JSON reader included; `has` exits 1 when the path
is absent, so check stderr to tell an absent path from an unreadable file. A reader
that closes the output early (`| head`) ends the command quietly with exit 1. A path
that starts with `-` goes after `--`: `dotreach get -- -1 data.json`.

## Upgrading from 0.1

The four 0.1 functions keep their signatures, and for JSON-shaped data (dicts, lists
and scalars) their errors still subclass the built-in exception 0.1 raised. What
changed is listed in the
[changelog](https://github.com/JaviLianes8/dotreach/blob/main/CHANGELOG.md):

- `set` replaces a non-container value inside a list instead of raising `TypeError`;
- `set` raises `PathTypeError` instead of replacing a tuple or read-only mapping on
  the path with a dict;
- `delete` on a value held in a tuple or read-only mapping raises `PathTypeError` (a
  `TypeError`, not a `KeyError`), even with `missing_ok=True`;
- a segment of non-ASCII digits that `int()` cannot read, such as a superscript, no
  longer escapes as a bare `ValueError`;
- the not-found message is readable text (`args[0]` is still the path).
