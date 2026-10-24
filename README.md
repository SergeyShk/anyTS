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
* **[Statistics interface](https://sergeyshk.github.io/anyTS/stats/stats/)** - the base of every class of statistics: a dictionary of the statistics, nested or flat, a pandas frame, a printed table and the reading of a statistic by its scale
* **[Basic statistics](https://sergeyshk.github.io/anyTS/stats/basic_stats/)** - sentences, words, syllables, letters, long and complex words, punctuation marks by type, with the syllables of a language library
* **[Readability metrics](https://sergeyshk.github.io/anyTS/stats/readability_stats/)** - Flesch reading ease, Flesch-Kincaid, Coleman-Liau, ARI, SMOG, Gunning fog, LIX, RIX, Legibilidad µ, the consensus grade, the school stage and the reading time, with the coefficients of a language library
* **[Unadapted readability formulas](https://sergeyshk.github.io/anyTS/stats/unadapted_readability_stats/)** - FORCAST, Linsear Write, Powers-Sumner-Kearl, McAlpine EFLAW, the Wiener Sachtextformeln, Dickes-Steiwer, Gulpease, Fucks, Strain, ELF and Wheeler-Smith with their original coefficients, to compare texts of one language
* **[Lexical diversity](https://sergeyshk.github.io/anyTS/stats/diversity_stats/)** - 32 metrics: TTR and its variants, MATTR, MSTTR, MTLD, MA-MTLD, MTLD-W, HD-D, the indices of Simpson and Yule, entropy, the laws of Zipf and Heaps, over the whole text or over windows with confidence intervals
* **[Lexical sophistication](https://sergeyshk.github.io/anyTS/stats/lexical_stats/)** - the base of the statistics by a frequency dictionary in the manner of TAALES: coverage, mean frequency, range and dispersion, surprisal and perplexity, frequency bands and lexical density
* **[Style metrics](https://sergeyshk.github.io/anyTS/stats/style_stats/)** - the base of the SEO metrics (nausea, water, spam, naturalness by Zipf's law, keyword density) and of the markers of the officialese, with the lists and the morphology of a language library
* **[Cohesion statistics](https://sergeyshk.github.io/anyTS/stats/cohesion_stats/)** - the base of the referential cohesion in the manner of Coh-Metrix: the overlap of nouns, arguments and content words, adjacent and over all pairs, Dice, with the next two sentences and between paragraphs in the manner of TAACO, givenness, the repetition of the tense and the aspect, and the connectors of a dictionary with the context rules of a language, with the words and the features of a language library
* **[Syntactic statistics](https://sergeyshk.github.io/anyTS/stats/syntax_stats/)** - the base of the statistics of the dependency tree: dependency distances, tree depth, valency, coordination chains, clauses, modifiers of a noun, prepositional chains, participial clauses, the passive, negations, split predicates, the words before the root, the order of the subjects and the objects, the similarity of adjacent sentences and the T-units and phrases of L2SCA, with the clauses and the constructions of a language library; tree helpers on the labels shared by Universal Dependencies and ClearNLP and the verb form of a predicate by its auxiliaries
* **[Morphological statistics](https://sergeyshk.github.io/anyTS/stats/morph_stats/)** - the base of the counts of the parts of speech and of the features of Universal Dependencies, word by word or by value, with the markers and the analysis of a language library
* **[Phonetic statistics](https://sergeyshk.github.io/anyTS/stats/phon_stats/)** - the base of the statistics of the sounds: classes of the sounds, consonant clusters, hiatuses, entropy of the CV patterns, alliteration and assonance by a repetition index, open syllables, with the transcription and the syllables of a language library
* **[Corpus measures](https://sergeyshk.github.io/anyTS/corpus/keyness/)** - keywords against a corpus or a frequency dictionary, collocations, the dispersion of a word, Burrows's Delta and its variants, Zeta, Kilgarriff's chi-square, the Mendenhall curve and the comparison of corpora with effect sizes, a bootstrap by texts and the Holm correction, a KWIC concordance
* **[Visualization](https://sergeyshk.github.io/anyTS/visualizers/zipf/)** - Zipf's law, vocabulary growth and frequency spectrum, sentence lengths, literature fingerprinting, word tree, corpus and stylometric plots, the labels of the plots as a parameter; the highlighting of a text by layers
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

The dependencies are numpy, pandas, scipy, spaCy, matplotlib and graphviz; no trained spaCy model is needed. Rendering the word tree and the network of collocations also needs the executables of [Graphviz](https://graphviz.org/download/).

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
make lint                   # ruff check --fix, ruff format, mypy
make test-cov               # pytest with doctests and full coverage
make docs-build             # mkdocs build --strict
```

The full list of commands is in `make help`. Contribution guidelines are in [CONTRIBUTING.md](https://github.com/SergeyShk/anyTS/blob/master/CONTRIBUTING.md).

## License

[MIT](https://github.com/SergeyShk/anyTS/blob/master/LICENSE.txt)
