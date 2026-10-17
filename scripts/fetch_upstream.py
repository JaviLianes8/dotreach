"""Download the third-party reference files listed in tests/upstream/MANIFEST.json.

They are kept out of the repository. The tests that read them skip until this script
has saved them, and every download must match the size and sha256 in the manifest.

    python scripts/fetch_upstream.py
"""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from pathlib import Path

FOLDER = Path(__file__).resolve().parents[1] / "tests" / "upstream"


def main() -> int:
    manifest = json.loads((FOLDER / "MANIFEST.json").read_text(encoding="utf-8"))
    failed = 0
    for name, entry in manifest.items():
        with urllib.request.urlopen(entry["url"], timeout=60) as response:
            body = response.read()
        digest = hashlib.sha256(body).hexdigest()
        if len(body) != entry["size"] or digest != entry["sha256"]:
            print(f"{name}: got {len(body)} bytes with sha256 {digest}; the manifest differs")
            failed += 1
            continue
        (FOLDER / name).write_bytes(body)
        print(f"{name}: ok")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
