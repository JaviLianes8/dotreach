# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-10-16

First stable release. The public API below is stable under Semantic Versioning: the
names in `dotreach.__all__`, their signatures and defaults, the error classes and the
command line. A 0.2.0 was prepared but never published; its work is part of this
release, so everything here is new since 0.1.0.

### Added

- Typed errors: `DotreachError` with `PathNotFoundError` (a `KeyError`),
  `PathTypeError` (a `TypeError`), `PathIndexError` (an `IndexError`),
  `InvalidPathError` and `StructureError` (both `ValueError`s), each naming the path,
  the failing segment and its position. They show and pickle as `dotreach.<Name>`.
- Sequence paths such as `("a.b", 0)` for keys with dots and non-string keys; the
  `Key` and `PathLike` type aliases.
- Opt-in backslash escaping (`escape=True`) plus `split_path` and `join_path`.
- `get_as` for a checked, statically typed read; `pop`; `setdefault`.
- `create_lists=True` on `set` and `setdefault` to build lists and append.
- `set_copy` and `delete_copy`: non-mutating writes with structural sharing that also
  work through tuples and read-only mappings.
- `walk`, `leaves`, `flatten`, `unflatten` and `glob` (`*` and `**` wildcards). None
  of them recurse, so any nesting depth works; `glob` tries each node once per
  pattern position, so repeated `**` cannot blow up.
- The `dotreach` command: get, has, set, delete, glob, flatten and unflatten over JSON
  from a file or standard input.
- `GUIDE.md` with the full rules, including how RFC 6901 pointers map onto paths.

### Changed

- `set` replaces a value that is not a container with a new dict wherever it sits on
  the path; 0.1 did so in a dict but raised `TypeError` in a list.
- `set` raises `PathTypeError` instead of replacing a tuple (or another read-only
  container) held on the path with a dict; `set_copy` rebuilds it.
- `delete` on a value held in a tuple or read-only mapping raises `PathTypeError`,
  even with `missing_ok=True`; 0.1 raised `KeyError`, or returned silently with
  `missing_ok`.
- `str()` of a not-found error is a readable message such as
  `path 'a.b' not found: no 'b' (segment 1) in dict` instead of the quoted path.
  `args[0]` is still the path. Messages quote paths and keys cut to a bounded length.
- Classifier `Development Status :: 5 - Production/Stable`.

### Fixed

- A path segment made of non-decimal digit characters (such as a superscript) no
  longer crashes with `ValueError` when it meets a list; it simply does not resolve.
- A segment of more digits than Python's `int()` accepts is out of range instead of
  crashing with `ValueError`.

## [0.1.0]

- First release.
- `get`, `set`, `delete` and `has` for nested dicts and lists by dotted path.
- Integer segments index sequences (negative indices supported); mapping segments
  are always keys, so key/index resolution is unambiguous.
- `get` takes an optional `default`; `delete` takes `missing_ok`; every function
  takes a custom `sep`.
- Fully typed, checked under `mypy --strict`, ships `py.typed`, zero runtime
  dependencies.
