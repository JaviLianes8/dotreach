# Local quality gate. Run before every commit. No CI runs in the cloud.
$ErrorActionPreference = "Stop"

python scripts/fetch_upstream.py  # RFC 6901 for the ground truth tests
ruff format --check .
ruff check .
mypy --strict src tests
pytest
