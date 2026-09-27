import importlib
import importlib.metadata
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

import anyts

ROOT = Path(__file__).parents[1]


def test_version():
    assert re.fullmatch(r"\d+\.\d+\.\d+(\.dev\d+)?", anyts.__version__)
    assert anyts.__version__ != "0.0.0"


def test_metadata():
    assert "language-independent" in anyts.__description__
    assert "__version__" in anyts.__all__
    assert anyts.__all__ == sorted(anyts.__all__)


def test_version_fallback(monkeypatch):
    def missing(name):
        raise importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(importlib.metadata, "version", missing)
    try:
        assert importlib.reload(anyts).__version__ == "0.0.0"
    finally:
        monkeypatch.undo()
        importlib.reload(anyts)
    assert anyts.__version__ != "0.0.0"


def test_package_data():
    assert (Path(anyts.__file__).parent / "py.typed").is_file()


@pytest.mark.skipif(shutil.which("uv") is None, reason="the wheel is built by uv")
def test_wheel_contents(tmp_path):
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(tmp_path), str(ROOT)],
        capture_output=True,
        check=True,
    )
    (wheel,) = tmp_path.glob("*.whl")
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
    assert "anyts/py.typed" in names
    assert all(name.startswith(("anyts/", "anyts-")) for name in names)
