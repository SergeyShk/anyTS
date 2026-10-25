"""The named sections of the documentation that the language libraries include"""

import ast
import importlib
import inspect
import re
from pathlib import Path

import pytest

from anyts import (
    basic_stats,
    cohesion_stats,
    components,
    constants,
    datasets,
    diversity_stats,
    exceptions,
    extractors,
    lexical_stats,
    morph_stats,
    phon_stats,
    readability_stats,
    stats,
    style_stats,
    syntax_stats,
    unadapted_readability_stats,
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
        *public_names(cohesion_stats),
        *public_names(syntax_stats),
        *public_names(datasets),
        *public_names(components),
        *public_names(basic_stats),
        *public_names(readability_stats),
        *public_names(stats),
        *public_names(style_stats),
        *public_names(lexical_stats),
        "LexicalStats",
        *public_names(phon_stats),
        "PhonStats",
        *public_names(morph_stats),
        *public_names(unadapted_readability_stats),
        "BasicStats",
        "StatsComponent",
        "Dataset",
        *(name for module in CORPUS_MODULES for name in public_names(module)),
        *(name for module in VISUALIZER_MODULES for name in public_names(module)),
    }
    assert public_names(exceptions) == []
    assert required <= documented, sorted(required - documented)


def public_constants(module) -> list[str]:
    """Names in upper case a module assigns itself"""
    names = []
    for node in ast.parse(inspect.getsource(module)).body:
        targets = node.targets if isinstance(node, ast.Assign) else []
        if isinstance(node, ast.AnnAssign):
            targets = [node.target]
        names += [
            target.id
            for target in targets
            if isinstance(target, ast.Name)
            and target.id.isupper()
            and not target.id.startswith("_")
        ]
    return names


MODULES = [
    constants,
    basic_stats,
    cohesion_stats,
    components,
    datasets,
    diversity_stats,
    extractors,
    lexical_stats,
    morph_stats,
    phon_stats,
    readability_stats,
    stats,
    style_stats,
    syntax_stats,
    unadapted_readability_stats,
    utils,
    *CORPUS_MODULES,
    *VISUALIZER_MODULES,
]
# A signature block of a page: ``` {.python .signature} with one call on one line
SIGNATURE = re.compile(r"^``` \{\.python \.signature\}\n(\w+)\((.*)\)\n```$", re.MULTILINE)


def test_public_constants_are_named():
    text = "\n".join(page.read_text(encoding="utf-8") for page in PAGES)
    modules = MODULES
    unnamed = sorted(
        {
            name
            for module in modules
            for name in public_constants(module)
            if not re.search(rf"\b{name}\b", text)
        }
    )
    assert not unnamed, f"constants not named in the docs: {unnamed}"


def default_text(value: object) -> str:
    """A default as a signature block writes it: a literal, a qualified name or a constant"""
    if value is None or isinstance(value, bool | int | float | str | tuple):
        return repr(value)
    if callable(value) and hasattr(value, "__qualname__"):
        return value.__qualname__
    for module in MODULES:
        for name, constant in vars(module).items():
            if name.isupper() and constant is value:
                return name
    return repr(value)


def signature_text(target: object) -> str:
    """The parameters of a callable as a signature block writes them"""
    parts = []
    keyword_only = False
    for param in inspect.signature(target).parameters.values():
        if param.kind is param.KEYWORD_ONLY and not keyword_only:
            parts.append("*")
            keyword_only = True
        if param.kind is param.VAR_POSITIONAL:
            parts.append(f"*{param.name}")
            keyword_only = True
        elif param.kind is param.VAR_KEYWORD:
            parts.append(f"**{param.name}")
        elif param.default is param.empty:
            parts.append(param.name)
        else:
            parts.append(f"{param.name}={default_text(param.default)}")
    return ", ".join(parts)


def page_target(page: Path, name: str) -> object:
    """A callable of a page: from the module named after the page, or the only one with the name"""
    parts = page.relative_to(DOCS).with_suffix("").parts
    folders = {"stats": parts[-1], "utils": "utils", "extractors": "extractors"}
    module_name = "anyts." + folders.get(parts[0], ".".join(parts))
    try:
        module = importlib.import_module(module_name)
    except ImportError:
        module = None
    if module is not None and name in vars(module):
        return vars(module)[name]
    targets = {id(vars(m)[name]): vars(m)[name] for m in MODULES if name in vars(m)}
    return next(iter(targets.values())) if len(targets) == 1 else None


def test_signatures_match_the_code():
    found = 0
    for page in PAGES:
        for name, written in SIGNATURE.findall(page.read_text(encoding="utf-8")):
            target = page_target(page, name)
            assert target is not None, f"{page.relative_to(DOCS)}: {name} is not in the package"
            assert written == signature_text(target), (
                f"{page.relative_to(DOCS)}: {name}({written}) differs from the code"
            )
            found += 1
    assert found


PARAMETER_TABLE = "| Parameter | Type | Default | Description |"
TABLE_ROW = re.compile(r"^\|\s*`\*{0,2}(\w+)`\s*\|[^|]*\|\s*(.*?)\s*\|")
# Parameters a section leaves to its prose: the core functions take join_hyphens besides the
# parameters the libraries share
UNTABULATED = {"sentence_lengths_plot": {"join_hyphens"}}


# A key of a family of measures that links to the card of its function
MEASURE_KEY = re.compile(r"^\| \[`(\w+)`\]\(#\1\)", re.MULTILINE)


def parameter_tables(page: Path) -> list[tuple[str | None, str, list[tuple[str, str]]]]:
    """Parameter tables of a page: the named section they are in, the callable of the signature
    block above them, and the names and defaults of their rows"""
    tables = []
    lines = page.read_text(encoding="utf-8").split("\n")
    section, signed = None, ""
    for index, line in enumerate(lines):
        for kind, name in MARKER.findall(line):
            section = name if kind == "start" else None
        if line == "``` {.python .signature}":
            signed = lines[index + 1].partition("(")[0]
        if line.strip() != PARAMETER_TABLE:
            continue
        rows = []
        for row in lines[index + 2 :]:
            if not row.startswith("|"):
                break
            match = TABLE_ROW.match(row)
            assert match, (
                f"{page.relative_to(DOCS)}: a row of a parameter table without a name: {row}"
            )
            rows.append((match[1], match[2].strip("`")))
        tables.append((section, signed, rows))
    return tables


def written_default(written: str, value: object) -> bool:
    """Whether a table writes a default: as a signature block does, in other quotes, or as the
    name of a constant that holds it"""
    if written in (default_text(value), default_text(value).replace("'", '"')):
        return True
    return any(
        written in vars(module) and written.isupper() and vars(module)[written] == value
        for module in MODULES
    )


def test_parameter_tables_match_the_code():
    # The tables of a callable: those of its section and of its sections -parameters and -hooks,
    # in order, a method by the section Class-method; a table outside the sections belongs to the
    # signature block above it, the table of a family of measures to each function it links
    documented: dict[tuple[Path, str, bool], tuple[object, list[tuple[str, str]]]] = {}
    for page in PAGES:
        texts = sections(page)
        for section, signed, rows in parameter_tables(page):
            if section is None:
                bases = [signed]
            elif section.endswith("-measures"):
                bases = [f"calc_{key}" for key in MEASURE_KEY.findall(texts[section])]
            else:
                bases = [re.sub(r"-(parameters|hooks)$", "", section)]
            assert bases, f"{page.relative_to(DOCS)}: {section} links no measures"
            for base in bases:
                name, _, method = base.partition("-")
                target = page_target(page, name)
                if method:
                    target = getattr(target, method, None)
                where = f"{page.relative_to(DOCS)}: {section or base}"
                assert callable(target), f"{where} names no callable"
                key = (page, base, section is not None)
                documented.setdefault(key, (target, []))[1].extend(rows)
    assert documented
    for (page, base, in_section), (target, rows) in documented.items():
        # The sections of a component leave the pipeline and the name to the libraries
        params = [
            param
            for param in inspect.signature(target).parameters.values()
            if param.name != "self"
            and not (in_section and base.endswith("Component") and param.name in ("nlp", "name"))
            and param.name not in UNTABULATED.get(base, ())
        ]
        where = f"{page.relative_to(DOCS)}: {base}"
        assert [name for name, _ in rows] == [param.name for param in params], where
        for (name, written), param in zip(rows, params, strict=True):
            if param.default is param.empty:
                assert written == "-", f"{where}: {name} has no default"
            else:
                assert written_default(written, param.default), f"{where}: {name} = {written}"
