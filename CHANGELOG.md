# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0]

- First release.
- `get`, `set`, `delete` and `has` for nested dicts and lists by dotted path.
- Integer segments index sequences (negative indices supported); mapping segments
  are always keys, so key/index resolution is unambiguous.
- `get` takes an optional `default`; `delete` takes `missing_ok`; every function
  takes a custom `sep`.
- Fully typed, checked under `mypy --strict`, ships `py.typed`, zero runtime
  dependencies.
