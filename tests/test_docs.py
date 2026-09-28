"""The named sections of the documentation that the language libraries include"""

import importlib
import inspect
import re
from pathlib import Path

import pytest

from anyts import (
    basic_stats,
    cohesion,
    components,
    datasets,
    diversity_stats,
    exceptions,
    extractors,
    readability_stats,
    syntax,
    utils,
)

DOCS = Path(__file__).parents[1] / "docs"
# The subpackages rebind the names of some of their modules to their functions
CORPUS_MODULES = [
    importlib.import_module(f"anyts.corpus.{name}")
    for name in ("collocations", "compare", "dispersion", "keyness", "kwic", "stylometry")
]
VISUALIZER_MODULES = [
    importlib.import_module(f"anyts.visualizers.{name}")
    for name in (
        "corpus",
        "fingerprinting",
        "highlight",
        "sentences",
        "stylometry",
        "vocabulary",
        "word_tree",
        "zipf",
    )
]
PAGES = sorted(DOCS.rglob("*.md"))
# The marker and the name rule of pymdownx.snippets
MARKER = re.compile(r"-{1,}8<-{1,}[ \t]+\[[ \t]*(start|end)[ \t]*:[ \t]*([^\]\s]*)[ \t]*\]")
NAME = re.compile(r"[a-z][-_0-9a-z]*", re.IGNORECASE)


def sections(page: Path) -> dict[str, str]:
    """Sections of a page by their names, checked for pairing"""
    names: dict[str, str] = {}
    open_name = None
    for line_no, line in enumerate(page.read_text(encoding="utf-8").splitlines(), 1):
        if open_name is not None:
            names[open_name] += line + "\n"
        for kind, name in MARKER.findall(line):
            where = f"{page.relative_to(DOCS)}:{line_no}"
            assert NAME.fullmatch(name), f"{where}: invalid section name {name!r}"
            if kind == "start":
                assert open_name is None, f"{where}: {name} starts inside {open_name}"
                assert name not in names, f"{where}: duplicate section {name}"
                open_name = name
                names[name] = ""
            else:
                assert open_name == name, f"{where}: end of {name} closes {open_name}"
                open_name = None
    assert open_name is None, f"{page.relative_to(DOCS)}: {open_name} is not closed"
    return names


@pytest.mark.parametrize("page", PAGES, ids=[str(page.relative_to(DOCS)) for page in PAGES])
def test_sections_are_paired(page):
    sections(page)


# The pages a section may link to: a library has them under the same names
SHARED_PAGES = {"diversity_stats.md", "diversity_stats_funcs.md"}
LINK = re.compile(r"\]\(([^)\s]+)\)")


@pytest.mark.parametrize("page", PAGES, ids=[str(page.relative_to(DOCS)) for page in PAGES])
def test_sections_link_to_shared_pages(page):
    for name, text in sections(page).items():
        for target in LINK.findall(text):
            path = target.split("#")[0]
            assert (
                not path or target.startswith(("http://", "https://")) or path in SHARED_PAGES
            ), f"{page.relative_to(DOCS)}: section {name} links to {target}"


def public_names(module) -> list[str]:
    return [
        name
        for name, value in vars(module).items()
        if not name.startswith("_")
        and (inspect.isfunction(inspect.unwrap(value)) or inspect.isclass(value))
        and value.__module__ == module.__name__
        and not inspect.isabstract(value)
        and getattr(value, "__name__", name) == name
        and not (inspect.isclass(value) and issubclass(value, BaseException | tuple))
    ]


def test_public_api_has_sections():
    pages = [sections(page) for page in PAGES]
    documented = {name for page in pages for name in page}
    # A family of measure functions is documented by the table of its measures section
    documented |= {
        mention
        for page in pages
        for name, text in page.items()
        if name.endswith("-measures")
        for mention in re.findall(r"`(\w+)`", text)
    }
    required = {
        "exceptions",
        *public_names(utils),
        *public_names(extractors),
        *public_names(diversity_stats),
        *public_names(cohesion),
        *public_names(syntax),
        *public_names(datasets),
        *public_names(components),
        *public_names(basic_stats),
        *public_names(readability_stats),
        "BasicStats",
        "StatsComponent",
        "Dataset",
        *(name for module in CORPUS_MODULES for name in public_names(module)),
        *(name for module in VISUALIZER_MODULES for name in public_names(module)),
    }
    assert public_names(exceptions) == []
    assert required <= documented, sorted(required - documented)
