# Contributing

Thanks for taking the time. This project keeps a small, predictable shape.

## Setup

```
pip install -r requirements-dev.txt
```

## Reference checks

Some tests compare dotreach with outside references and skip when those are absent:

- `python scripts/fetch_upstream.py` saves RFC 6901 into `tests/upstream/` (checked
  against the sha256 in `MANIFEST.json`; the file itself is never committed).
- `pip install glom jmespath` enables the differential tests in `tests/test_oracles.py`.
- `DOTREACH_V01=<folder>` pointing at an unpacked 0.1.0 wheel enables
  `tests/test_upgrade.py`; `DOTREACH_E2E_PYPI=1` lets the end to end test install
  0.1.0 from PyPI and upgrade it to the built wheel.

## Before you open a pull request

- Keep public API in `src/dotreach/__init__.py`; internals live in `_`-prefixed modules.
- Add a test for the behaviour you change. Tests use temporary folders, and only the
  opt-in checks above reach the network.
- Run `scripts/check.ps1` (format, lint, types, tests) and make sure it passes.
- One logical change per commit, imperative subject line.

Open an issue first if the change is large or shifts the public API.
