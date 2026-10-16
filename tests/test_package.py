import importlib
import importlib.metadata
import re
import shutil
import subprocess
import sys
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


def _run(code: str) -> str:
    """Output of a script run in a fresh interpreter"""
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, check=True, text=True
    )
    return result.stdout.strip()


@pytest.mark.parametrize(
    ("module", "absent"),
    [
        ("anyts", ("spacy", "scipy", "matplotlib", "graphviz", "pandas")),
        ("anyts.basic_stats", ("spacy", "scipy", "pandas")),
        ("anyts.readability_stats", ("spacy", "scipy", "pandas")),
        ("anyts.components", ("spacy", "thinc", "scipy")),
        ("anyts.visualizers.highlight", ("spacy", "matplotlib", "graphviz", "pandas")),
        ("anyts.corpus.kwic", ("spacy", "pandas", "matplotlib")),
    ],
)
def test_imports_are_light(module, absent):
    loaded = _run(f"import sys, {module}; print(' '.join(sorted(sys.modules)))").split()
    assert not set(absent) & set(loaded)


def test_no_module_imports_spacy():
    """spaCy is loaded by the documents a user brings, never by the import of the core"""
    code = (
        "import importlib, pkgutil, sys, anyts\n"
        "names = [m.name for m in pkgutil.walk_packages(anyts.__path__, 'anyts.')]\n"
        "for name in names:\n"
        "    importlib.import_module(name)\n"
        "print(len(names), 'spacy' in sys.modules, 'thinc' in sys.modules)"
    )
    n_modules, spacy, thinc = _run(code).split()
    assert int(n_modules) > 30
    assert (spacy, thinc) == ("False", "False")


def test_checks_of_spacy_objects_without_spacy():
    code = (
        "import sys\n"
        "from anyts.utils import check_sequence, is_doc, is_span\n"
        "check_sequence(['the', 'cat'])\n"
        "print(is_doc('the cat'), is_span(['the']), 'spacy' in sys.modules)"
    )
    assert _run(code) == "False False False"


def test_names_of_modules_keep_their_functions():
    # A module imported first does not take the name of its function in the package
    code = (
        "import anyts.visualizers.zipf, anyts.corpus.kwic, anyts.corpus.keyness\n"
        "from anyts.visualizers import zipf, fingerprinting, heaps_plot\n"
        "from anyts.corpus import kwic, keyness, collocations, dispersion\n"
        "import anyts.visualizers as v, anyts.corpus as c\n"
        "names = (zipf, fingerprinting, heaps_plot, kwic, keyness, collocations, dispersion)\n"
        "print(all(callable(f) and type(f).__name__ == 'function' for f in names),"
        " v.zipf is zipf, c.kwic is kwic)"
    )
    assert _run(code) == "True True True"


def test_lazy_packages():
    import anyts.corpus as corpus
    import anyts.visualizers as visualizers

    for package in (corpus, visualizers):
        assert set(package.__all__) <= set(dir(package))
        assert all(getattr(package, name) is not None for name in package.__all__)
        with pytest.raises(AttributeError, match="has no attribute 'missing'"):
            package.missing  # noqa: B018
        with pytest.raises(AttributeError, match="has no attribute '__missing__'"):
            package.__missing__  # noqa: B018
        for name in ("", "a.b"):
            assert not hasattr(package, name)


def test_modules_of_lazy_packages_are_attributes():
    code = (
        "import anyts.corpus, anyts.visualizers\n"
        "print(anyts.corpus.stylometry.__name__, anyts.visualizers.highlight.__name__,"
        " callable(anyts.corpus.kwic))"
    )
    assert _run(code) == "anyts.corpus.stylometry anyts.visualizers.highlight True"


def test_lazy_package_reports_a_missing_dependency(tmp_path, monkeypatch):
    package = tmp_path / "anyts_lazy_fake"
    package.mkdir()
    (package / "__init__.py").write_text(
        "from anyts._lazy import make_lazy\n_MODULES = {}\nmake_lazy(__name__)\n"
    )
    (package / "broken.py").write_text("import anyts_no_such_dependency\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setattr(sys, "modules", dict(sys.modules))
    fake = importlib.import_module("anyts_lazy_fake")
    with pytest.raises(ModuleNotFoundError, match="anyts_no_such_dependency"):
        fake.broken  # noqa: B018
