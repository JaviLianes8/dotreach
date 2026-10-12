# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0]

Everything is additive: the 0.1 functions keep their signatures and behaviour, and
every new error subclasses the built-in exception 0.1 raised.

### Added

- Typed errors: `DotreachError` with `PathNotFoundError` (a `KeyError`),
  `PathTypeError` (a `TypeError`), `PathIndexError` (an `IndexError`) and
  `InvalidPathError` (a `ValueError`), each naming the path, the failing segment and
  its position.
- Sequence paths such as `("a.b", 0)` for keys with dots and non-string keys.
- Opt-in backslash escaping (`escape=True`) plus `split_path` and `join_path`.
- `get_as` for a checked, statically typed read; `pop`; `setdefault`.
- `create_lists=True` on `set` and `setdefault` to build lists and append.
- `set_copy` and `delete_copy`: non-mutating writes with structural sharing that also
  work through tuples and read-only mappings.
- `walk`, `leaves`, `flatten`, `unflatten` and `glob` (`*` and `**` wildcards).
- The `dotreach` command: get, has, set, delete, glob, flatten and unflatten over JSON
  from a file or standard input.
- `GUIDE.md` with the full rules.

### Fixed

- A path segment made of non-decimal digit characters (such as a superscript) no
  longer crashes with `ValueError` when it meets a list; it simply does not resolve.

## [0.1.0]

- First release.
- `get`, `set`, `delete` and `has` for nested dicts and lists by dotted path.
- Integer segments index sequences (negative indices supported); mapping segments
  are always keys, so key/index resolution is unambiguous.
- `get` takes an optional `default`; `delete` takes `missing_ok`; every function
  takes a custom `sep`.
- Fully typed, checked under `mypy --strict`, ships `py.typed`, zero runtime
  dependencies.
