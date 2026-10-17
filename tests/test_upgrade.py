"""Differential check against the 0.1.0 release from PyPI, the only earlier release.

Point ``DOTREACH_V01`` at a folder holding the unpacked 0.1.0 wheel (the folder that
contains ``dotreach/``); the test skips otherwise. For the four 0.1.0 functions on
seeded random data and string paths, 1.0.0 must give the same results and raise the
same built-in error families, except for the changes listed in the CHANGELOG.
"""

from __future__ import annotations

import copy
import importlib.util
import os
import random
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
from conftest import random_key, random_tree

import dotreach as d

FAMILIES = (KeyError, IndexError, TypeError, ValueError)


@pytest.fixture(scope="module")
def old() -> ModuleType:
    folder = os.environ.get("DOTREACH_V01")
    if not folder:
        pytest.skip("set DOTREACH_V01 to an unpacked dotreach 0.1.0 wheel")
    init = Path(folder) / "dotreach" / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        "dotreach_v01", init, submodule_search_locations=[str(init.parent)]
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["dotreach_v01"] = module
    spec.loader.exec_module(module)
    assert module.__version__ == "0.1.0"
    return module


def _outcome(call: Any, *args: Any, **kwargs: Any) -> tuple[str, Any]:
    try:
        return "ok", call(*args, **kwargs)
    except FAMILIES as error:
        family = next(f for f in FAMILIES if isinstance(error, f))
        return family.__name__, error.args[0] if family is KeyError else None


def _paths(tree: Any, rng: random.Random) -> list[str]:
    paths = [".".join(str(s) for s in segments) for segments, _ in d.walk(tree)]
    paths += [p + "." + random_key(rng) for p in paths[:4]] + [random_key(rng), "0", "-1"]
    return paths


def _through_a_scalar_in_a_list(tree: Any, path: str) -> bool:
    """The documented 1.0 change: set replaces a non-container inside a list."""
    parts = path.split(".")
    for n in range(1, len(parts)):
        parent = d.get(tree, ".".join(parts[: n - 1]), None) if n > 1 else tree
        node = d.get(tree, ".".join(parts[:n]), None)
        present = d.has(tree, ".".join(parts[:n]))
        if isinstance(parent, list) and present and not isinstance(node, (dict, list)):
            return True
    return False


def test_the_four_original_functions_behave_as_in_0_1(old: ModuleType) -> None:
    changed = compared = 0
    for seed in range(400):
        rng = random.Random(seed)
        tree = random_tree(rng)
        for path in _paths(tree, rng):
            assert _outcome(d.get, tree, path, "D") == _outcome(old.get, tree, path, "D")
            assert _outcome(d.has, tree, path) == _outcome(old.has, tree, path)
            for missing_ok in (False, True):
                mine, theirs = copy.deepcopy(tree), copy.deepcopy(tree)
                assert _outcome(d.delete, mine, path, missing_ok=missing_ok) == _outcome(
                    old.delete, theirs, path, missing_ok=missing_ok
                )
                assert mine == theirs
            mine, theirs = copy.deepcopy(tree), copy.deepcopy(tree)
            new_result = _outcome(d.set, mine, path, "V")
            old_result = _outcome(old.set, theirs, path, "V")
            compared += 1
            if new_result != old_result:
                assert old_result[0] == "TypeError" and new_result[0] == "ok", (seed, path)
                assert _through_a_scalar_in_a_list(tree, path), (seed, path)
                changed += 1
            else:
                assert mine == theirs, (seed, path)
    assert compared > 3000 and changed > 0


def test_a_superscript_segment_no_longer_crashes(old: ModuleType) -> None:
    with pytest.raises(ValueError):
        old.get(["x"], "²")
    assert d.get(["x"], "²", None) is None
