# Contributing

Bug reports, ideas and pull requests are welcome.

anyTS is the language-independent core of [ruTS](https://github.com/SergeyShk/ruTS) and [esTS](https://github.com/SergeyShk/esTS). A wrong result that comes from a language - a tokenizer, a lemma, a rule of Russian or Spanish - belongs to the issues of that library; the core takes the bugs of the code it holds.

## Reporting a bug or proposing an idea

Open an [issue](https://github.com/SergeyShk/anyTS/issues/new/choose) using a template. A bug report needs a minimal code example that reproduces it, the expected and actual behaviour, and the versions of anyTS, Python and the OS. A proposal needs the statistic or tool you want and the source (paper, library) it relies on: the library follows published definitions, not formulas of its own.

## Development environment

The project uses [uv](https://docs.astral.sh/uv/) for dependencies and [ruff](https://docs.astral.sh/ruff/) for linting and formatting. Python 3.11 or newer is required.

```bash
git clone https://github.com/SergeyShk/anyTS.git
cd anyTS

make deps                   # create the environment and install all dependencies
uv run pre-commit install   # hooks: linters on commit, tests on push
```

The full list of commands is in `make help`.

## Checks

Before submitting a pull request, these must pass:

```bash
make lint        # ruff check, ruff format --check, mypy
make test-cov    # pytest: tests and docstring examples (doctest), 100% coverage
make docs-build  # mkdocs build --strict, if the documentation changed
```

CI runs the same on Python 3.11-3.14 (Linux) and on Windows and macOS for one Python version.

## What a pull request is expected to contain

- **One topic per pull request.** Unrelated changes go separately.
- **No language inside.** A tokenizer, a lemmatizer, a word list or a rule of one language comes as a class attribute that a library subclass overrides or as a function parameter with a neutral default. Dependency labels are only those shared by Universal Dependencies and ClearNLP (`cc`, `conj`, `parataxis`, `punct`, `ROOT`). Code, docstrings and documentation name no particular library.
- **Tests.** New code is covered by tests in `tests/` (mirroring the package) on neutral tokens; line and branch coverage stays at 100%. The values of new metrics are checked against an example computed by hand or against a reference implementation.
- **Documentation.** The documentation is in English. The reference of every public function or class in `docs/` is a named section, `<!-- --8<-- [start:name] -->` ... `<!-- --8<-- [end:name] -->`, which the libraries include in their own pages: renaming or removing a section breaks their documentation build. A section is named after its function or class; the parts of a class page add a suffix (`WordsExtractor-parameters`, `WordsExtractor-extract`). Headings and examples stay outside the sections, since a library gives its own. Examples in docstrings and documentation show the actual output.
- **Sources.** A new statistic cites the source of its formula in the docstring and on the documentation page; the implementation is checked against it, and differences from other libraries are stated explicitly.
- **Compatibility.** Changes to the behaviour of existing statistics or signatures come with an explanation in the pull request description: it goes into the release notes. Public names and statistic keys change only with a minor version, because the libraries re-export them.
- **Style.** Code is formatted with ruff (`make format`), types are checked with mypy, docstrings are in English in the project format (`Description`, `Arguments`, `Returns`, `Raises`). Comments do not repeat what the code already says.
- **Commits.** Messages in English, imperative mood: "Add ...", "Fix ...", "Remove ...".

The pull request description answers two questions: what was done and why. If it closes an issue, mention its number.

## Repository layout

- `anyts/` - the package.
- `tests/` - tests mirroring the package.
- `docs/` - MkDocs (Material) documentation, `mkdocs.yml` - navigation.
- `.github/workflows/` - CI (`ci.yml`), publishing (`publish.yml`), documentation (`docs.yml`).

The version lives only in `pyproject.toml`; releases are made through GitHub Releases, changes are described in the release notes, there is no separate CHANGELOG file.
