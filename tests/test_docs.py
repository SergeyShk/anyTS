"""The named sections of the documentation that the language libraries include"""

import inspect
import re
from pathlib import Path

import pytest

from anyts import cohesion, diversity_stats, exceptions, extractors, syntax, utils
from anyts.corpus import collocations, compare, dispersion, keyness, stylometry

DOCS = Path(__file__).parents[1] / "docs"
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
        *(
            name
            for module in (collocations, compare, dispersion, keyness, stylometry)
            for name in public_names(module)
        ),
    }
    assert public_names(exceptions) == []
    assert required <= documented, sorted(required - documented)
