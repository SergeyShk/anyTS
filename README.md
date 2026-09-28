# Any Texts Statistics (anyTS)

[![Version](https://img.shields.io/pypi/v/anyts?logo=pypi&logoColor=FFE873)](https://pypi.org/project/anyts/)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/anyts.svg?logo=python&logoColor=FFE873)](https://pypi.org/project/anyts/)
[![Build](https://github.com/SergeyShk/anyTS/actions/workflows/ci.yml/badge.svg)](https://github.com/SergeyShk/anyTS/actions/workflows/ci.yml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/SergeyShk/anyTS/blob/master/LICENSE.txt)

**anyTS** is the language-independent core of the text statistics libraries [ruTS](https://github.com/SergeyShk/ruTS) (Russian) and [esTS](https://github.com/SergeyShk/esTS) (Spanish). It holds the code that does not depend on a language, so that it is written, tested and documented once; a language library adds its tokenizer, lemmatizer, [spaCy](https://github.com/explosion/spaCy) model and rules and re-exports the core under its own names.

[Documentation](https://sergeyshk.github.io/anyTS/) · [PyPI](https://pypi.org/project/anyts/)

## Features

* **[Extraction](https://sergeyshk.github.io/anyTS/extractors/sentences/)** - sentence, word and character N-gram extractors whose tokenizer, lemmatizer and number pattern are hooks a language library overrides
* **[Lexical diversity](https://sergeyshk.github.io/anyTS/stats/diversity_stats/)** - 32 metrics: TTR and its variants, MATTR, MSTTR, MTLD, MA-MTLD, MTLD-W, HD-D, the indices of Simpson and Yule, entropy, the laws of Zipf and Heaps, over the whole text or over windows with confidence intervals
* **[Cohesion helpers](https://sergeyshk.github.io/anyTS/stats/cohesion/)** - the overlap of sentences, adjacent and over all pairs, Dice, givenness and repetition
* **[Dependency tree helpers](https://sergeyshk.github.io/anyTS/stats/syntax/)** - dependency distances, tree depth, valency and coordination chains on the labels shared by Universal Dependencies and ClearNLP
* **[Corpus measures](https://sergeyshk.github.io/anyTS/corpus/keyness/)** - keywords against a corpus or a frequency dictionary, collocations, the dispersion of a word, Burrows's Delta and its variants, Zeta, Kilgarriff's chi-square, the Mendenhall curve and the comparison of corpora with effect sizes, a bootstrap by texts and the Holm correction, a KWIC concordance
* **[Visualization](https://sergeyshk.github.io/anyTS/visualizers/zipf/)** - Zipf's law, vocabulary growth and frequency spectrum, sentence lengths, literature fingerprinting, word tree, corpus and stylometric plots, the labels of the plots as a parameter; the machinery of the highlighting of a text by layers
* **[Components](https://sergeyshk.github.io/anyTS/components/)** - the base of the spaCy components that put the statistics into an extension of `Doc`
* **[Datasets](https://sergeyshk.github.io/anyTS/datasets/)** - the base of a dataset: downloading an archive with a checksum, safe extraction and filters of the records
* **[Exceptions](https://sergeyshk.github.io/anyTS/exceptions/)** - one hierarchy whose classes are also built-in exceptions

The reference of every function is a named section that the libraries include in their own documentation, so a formula is described in one place.

## Installation

Requires Python 3.11 or newer.

```bash
pip install anyts
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add anyts
```

The dependencies are numpy, pandas, scipy and spaCy; no trained spaCy model is needed.

## Quick start

```python
>>> from anyts import DiversityStats, SentsExtractor, WordsExtractor

>>> text = "The cat sat on the mat. The dog sat on the log! The cat and the dog slept."

>>> SentsExtractor().extract(text)
('The cat sat on the mat.', 'The dog sat on the log!', 'The cat and the dog slept.')

>>> ds = DiversityStats(WordsExtractor(lowercase=True).extract(text))
>>> ds.ttr, round(ds.entropy, 3)
(0.5, 2.864)
```

A language library subclasses the extractors and overrides their hooks:

```python
>>> class Words(WordsExtractor):
...     def lemmatize(self, word):
...         return {"sat": "sit", "slept": "sleep"}.get(word.lower(), word)

>>> Words(lowercase=True, use_lexemes=True).extract("The cat sat. The dog slept.")
('the', 'cat', 'sit', 'the', 'dog', 'sleep')
```

The corpus measures take lists of words:

```python
>>> from anyts.corpus import keyness

>>> cats = WordsExtractor(lowercase=True).extract("The cat sat on the mat. The cat saw a bird. The cat slept.")
>>> dogs = WordsExtractor(lowercase=True).extract("The dog sat on the log. The dog saw a cat. The dog barked.")
>>> [(keyword.word, round(keyword.log_ratio, 2)) for keyword in keyness(cats, dogs, min_freq=2)]
[('cat', 1.58)]
```

## Development

The project uses [uv](https://docs.astral.sh/uv/) for dependencies and [ruff](https://docs.astral.sh/ruff/) for linting and formatting.

```bash
git clone https://github.com/SergeyShk/anyTS.git
cd anyTS

make deps                   # create the environment and install all dependencies
uv run pre-commit install   # hooks: linters on commit, tests on push
make lint                   # ruff check, ruff format --check, mypy
make test-cov               # pytest with doctests and full coverage
make docs-build             # mkdocs build --strict
```

The full list of commands is in `make help`. Contribution guidelines are in [CONTRIBUTING.md](https://github.com/SergeyShk/anyTS/blob/master/CONTRIBUTING.md).

## License

[MIT](https://github.com/SergeyShk/anyTS/blob/master/LICENSE.txt)
