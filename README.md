# Any Texts Statistics (anyTS)

[![Build](https://github.com/SergeyShk/anyTS/actions/workflows/ci.yml/badge.svg)](https://github.com/SergeyShk/anyTS/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**anyTS** is the language-independent core of the text statistics libraries [ruTS](https://github.com/SergeyShk/ruTS) (Russian) and [esTS](https://github.com/SergeyShk/esTS) (Spanish). It holds the code that does not depend on a language, so that it is written, tested and documented once; a language library adds its tokenizer, lemmatizer, spaCy model and rules and re-exports the core under its own names.

> **Status:** in development. The exceptions, the utilities and the extractors are in place; the statistics and the corpus measures follow.

## Planned scope

* **Extraction** - the base of the sentence, word and character N-gram extractors with the tokenizer, the lemmatizer and the number pattern as hooks a language library overrides
* **Lexical diversity** - TTR and its variants, MATTR, MSTTR, MTLD, HD-D, the indices of Simpson and Yule, entropy, the laws of Zipf and Heaps, windowed computation
* **Cohesion and syntax helpers** - overlaps, Dice, givenness and repetition; dependency distances, tree depth, valency and coordination on the labels shared by Universal Dependencies and ClearNLP
* **Corpus measures** - collocations, dispersion, keyness, Burrows's Delta, Zeta, the Mendenhall curve and the comparison of corpora with effect sizes, bootstrap and the Holm correction
* **Exceptions** - one hierarchy whose classes are also built-in exceptions

## Development

The project uses [uv](https://docs.astral.sh/uv/) for dependencies and [ruff](https://docs.astral.sh/ruff/) for linting and formatting. Python 3.11 or newer is required.

```bash
git clone https://github.com/SergeyShk/anyTS.git
cd anyTS

make deps                   # create the environment and install all dependencies
uv run pre-commit install   # hooks: linters on commit, tests on push
make lint                   # ruff check, ruff format --check, mypy
make test-cov               # pytest with doctests and full coverage
make docs-build             # mkdocs build --strict
```

The full list of commands is in `make help`. Contribution guidelines are in [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE.txt)
