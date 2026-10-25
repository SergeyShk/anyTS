"""The examples of the documentation: every Code block of a page runs, and gives its Result"""

import ast
import contextlib
import io
import pprint
import re
from collections.abc import Callable
from pathlib import Path

import matplotlib
import pytest

DOCS = Path(__file__).parents[1] / "docs"
FENCE = re.compile(r"^(\s*)```(.*)$")
TAB = re.compile(r'^(\s*)=== "(Code|Result)"')
# The lines of a traceback that a Result abridges
TRACEBACK = re.compile(r"^\s*(Traceback \(most recent call last\):|\.\.\.)\s*$", re.M)


def blocks(text: str) -> list[tuple[str, str, str, int]]:
    """Fenced blocks of a page: the tab they are in (code, result or none), their language,
    their text and their line"""
    found = []
    lines = text.split("\n")
    tab: tuple[str, int] | None = None
    index = 0
    while index < len(lines):
        line = lines[index]
        if match := TAB.match(line):
            tab = (match[2].lower(), len(match[1]))
        elif match := FENCE.match(line):
            indent, info = match[1], match[2].strip()
            end = index + 1
            while not re.match(rf"^{indent}```\s*$", lines[end]):
                end += 1
            body = "\n".join(row[len(indent) :] for row in lines[index + 1 : end])
            kind = tab[0] if tab and len(indent) > tab[1] else "none"
            found.append((kind, info, body, index + 1))
            index = end
        elif line.strip() and not line.startswith((" ", "\t")):
            tab = None
        index += 1
    return found


def run(code: str, namespace: dict[str, object]) -> list[tuple[str, object]]:
    """Outputs of the statements of a block, one after another as in an interpreter: the
    printed text, the values of the expressions and the errors by their last line"""
    outputs: list[tuple[str, object]] = []
    for statement in ast.parse(code).body:
        printed = io.StringIO()
        value = None
        try:
            with contextlib.redirect_stdout(printed):
                if isinstance(statement, ast.Expr):
                    value = eval(
                        compile(ast.Expression(statement.value), "<docs>", "eval"), namespace
                    )
                else:
                    exec(compile(ast.Module([statement], []), "<docs>", "exec"), namespace)
        except Exception as error:
            outputs.append(("print", printed.getvalue()))
            module, name = type(error).__module__, type(error).__name__
            outputs.append(
                ("error", f"{name if module == 'builtins' else f'{module}.{name}'}: {error}")
            )
            continue
        outputs.append(("print", printed.getvalue()))
        # An object without a readable form, such as a function a decorator returns, shows nothing
        if value is not None and not re.search(r" at 0x[0-9a-f]+>$", repr(value)):
            outputs.append(("value", value))
    return outputs


def shown(outputs: list[tuple[str, object]], form: Callable[[object], str]) -> str:
    """The outputs as a Result block writes them, the values in a form, without whitespace"""
    text = "".join(form(item) if kind == "value" else str(item) for kind, item in outputs)
    return re.sub(r"\s+", "", text)


def matches(outputs: list[tuple[str, object]], expected: str) -> bool:
    """Whether the outputs give the Result, whatever the whitespace and the form of the values"""
    wanted = re.sub(r"\s+", "", TRACEBACK.sub("", expected))
    forms = (repr, str, lambda value: pprint.pformat(value, sort_dicts=False))
    return any(shown(outputs, form) == wanted for form in forms)


PAGES = sorted(page for page in DOCS.rglob("*.md") if '=== "Code"' in page.read_text())


@pytest.mark.examples
@pytest.mark.parametrize("page", PAGES, ids=lambda page: str(page.relative_to(DOCS)))
def test_examples_give_their_results(page, tmp_path, monkeypatch):
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    monkeypatch.chdir(tmp_path)
    namespace: dict[str, object] = {"__name__": "__main__"}
    items = blocks(page.read_text(encoding="utf-8"))
    for index, (kind, language, body, line) in enumerate(items):
        if language != "python" or kind == "result":
            continue
        outputs = run(body, namespace)
        where = f"{page.relative_to(DOCS)}:{line}"
        result = items[index + 1] if index + 1 < len(items) else None
        if kind == "code" and result is not None and result[0] == "result":
            assert matches(outputs, result[2]), f"{where}: {outputs}"
        else:
            errors = [item for item_kind, item in outputs if item_kind == "error"]
            assert not errors, f"{where}: {errors}"
    plt.close("all")
