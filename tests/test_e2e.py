"""Real end to end test: build a wheel, install it, drive the installed script.

No mocks. The project is built into a wheel, the wheel is installed into a throwaway
virtual environment, and the real ``dotreach`` executable is run over ``subprocess``
against real files and real standard input.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import venv
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
DOC = {"user": {"name": "Ada", "roles": ["admin", "editor"]}}


def _exe(env: Path, name: str) -> Path:
    scripts = env / ("Scripts" if sys.platform == "win32" else "bin")
    return scripts / (name + (".exe" if sys.platform == "win32" else ""))


@pytest.fixture(scope="module")
def wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build the project into a wheel and return its path."""
    dist = tmp_path_factory.mktemp("dist")
    subprocess.run(
        [sys.executable, "-m", "pip", "wheel", "--no-deps", "-w", str(dist), str(ROOT)],
        check=True,
        capture_output=True,
        timeout=600,
    )
    wheels = list(dist.glob("dotreach-*.whl"))
    assert len(wheels) == 1, wheels
    return wheels[0]


@pytest.fixture(scope="module")
def cli(tmp_path_factory: pytest.TempPathFactory, wheel: Path) -> Path:
    """Install the wheel into a fresh venv and return the script path."""
    env = tmp_path_factory.mktemp("venv")
    venv.create(env, with_pip=True)
    subprocess.run(
        [str(_exe(env, "python")), "-m", "pip", "install", "--no-index", str(wheel)],
        check=True,
        capture_output=True,
        timeout=600,
    )
    script = _exe(env, "dotreach")
    assert script.is_file()
    return script


@pytest.fixture
def doc(tmp_path: Path) -> Path:
    path = tmp_path / "data.json"
    path.write_text(json.dumps(DOC), encoding="utf-8")
    return path


def _run(cli: Path, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(cli), *args], input=stdin, capture_output=True, text=True, timeout=60
    )


def test_get_from_file(cli: Path, doc: Path) -> None:
    result = _run(cli, "get", "user.roles.-1", str(doc))
    assert (result.returncode, result.stdout.strip(), result.stderr) == (0, '"editor"', "")


def test_get_from_stdin_raw(cli: Path) -> None:
    result = _run(cli, "get", "a.b", "--raw", stdin='{"a": {"b": "hi"}}')
    assert (result.returncode, result.stdout.strip()) == (0, "hi")


def test_missing_path_errors_to_stderr(cli: Path, doc: Path) -> None:
    result = _run(cli, "get", "user.age", str(doc))
    assert result.returncode == 1 and result.stdout == ""
    assert "'age'" in result.stderr


def test_has_exit_codes(cli: Path, doc: Path) -> None:
    assert _run(cli, "has", "user.name", str(doc)).returncode == 0
    assert _run(cli, "has", "user.nope", str(doc)).returncode == 1


def test_set_in_place_then_delete(cli: Path, doc: Path) -> None:
    assert _run(cli, "set", "user.age", "36", "-i", str(doc)).returncode == 0
    assert json.loads(doc.read_text(encoding="utf-8"))["user"]["age"] == 36
    result = _run(cli, "delete", "user.roles.0", "--indent", "0", str(doc))
    assert json.loads(result.stdout)["user"]["roles"] == ["editor"]


def test_flatten_pipes_into_unflatten(cli: Path, doc: Path) -> None:
    flat = _run(cli, "flatten", str(doc))
    assert json.loads(flat.stdout)["user.roles.1"] == "editor"
    back = _run(cli, "unflatten", "--create-lists", stdin=flat.stdout)
    assert back.returncode == 0 and json.loads(back.stdout) == DOC


def test_glob(cli: Path, doc: Path) -> None:
    result = _run(cli, "glob", "**.name", str(doc))
    assert json.loads(result.stdout) == {"user.name": "Ada"}


def test_version_and_help(cli: Path) -> None:
    from dotreach import __version__

    assert _run(cli, "--version").stdout.strip() == f"dotreach {__version__}"
    assert "examples:" in _run(cli, "--help").stdout


def test_installed_library_imports(cli: Path) -> None:
    code = "import dotreach as d; print(d.set_copy({'a': 1}, 'b.c', 2))"
    result = subprocess.run(
        [str(cli.parent / cli.name.replace("dotreach", "python")), "-c", code],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.stdout.strip() == "{'a': 1, 'b': {'c': 2}}"


@pytest.mark.skipif(
    not os.environ.get("DOTREACH_E2E_PYPI"), reason="set DOTREACH_E2E_PYPI=1 to use the network"
)
def test_upgrade_from_the_pypi_release_in_place(
    tmp_path_factory: pytest.TempPathFactory, wheel: Path
) -> None:
    env = tmp_path_factory.mktemp("upgrade")
    venv.create(env, with_pip=True)
    python = str(_exe(env, "python"))
    pip = [python, "-m", "pip", "install", "-q", "--no-cache-dir", "--disable-pip-version-check"]
    subprocess.run([*pip, "dotreach==0.1.0"], check=True, capture_output=True, timeout=600)
    code = "import dotreach as d; print(d.__version__, d.get({'a': [1, 2]}, 'a.-1'))"
    before = subprocess.run([python, "-c", code], capture_output=True, text=True, timeout=60)
    assert before.stdout.split() == ["0.1.0", "2"]
    subprocess.run([*pip, str(wheel)], check=True, capture_output=True, timeout=600)
    after = subprocess.run([python, "-c", code], capture_output=True, text=True, timeout=60)
    assert after.stdout.split() == ["1.0.0", "2"]
    result = subprocess.run(
        [str(_exe(env, "dotreach")), "get", "a.0"],
        input='{"a": [7]}',
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert (result.returncode, result.stdout.strip()) == (0, "7")
