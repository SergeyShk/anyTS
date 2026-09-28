# Any Texts Statistics (anyTS)

**anyTS** is the language-independent core of the text statistics libraries [ruTS](https://github.com/SergeyShk/ruTS) (Russian) and [esTS](https://github.com/SergeyShk/esTS) (Spanish). It holds the code that does not depend on a language, so that it is written, tested and documented once; a language library adds its tokenizer, lemmatizer, [spaCy](https://github.com/explosion/spaCy) model and rules and re-exports the core under its own names.

## Features

*   extract [sentences](extractors/sentences.md), [words](extractors/words.md) and [character N-grams](extractors/char_ngrams.md) with extractors whose tokenizer, lemmatizer and number pattern are hooks a language library overrides
*   count the [basic statistics](stats/basic_stats.md) of a text - sentences, words, syllables, letters and punctuation marks by type - with the syllables of a language library
*   compute the [readability metrics](stats/readability_stats.md) of a text - Flesch reading ease, Flesch-Kincaid, Coleman-Liau, ARI, SMOG, Gunning fog, LIX, RIX, Legibilidad µ, the consensus grade and the reading time - with the coefficients of a language library
*   compute [lexical diversity metrics](stats/diversity_stats.md) (Type-Token Ratio and its variants, MATTR, MSTTR, MTLD, MA-MTLD, MTLD-W, HD-D, the indices of Simpson and Yule, entropy, the laws of Zipf and Heaps), over the whole text or over windows with confidence intervals
*   measure [cohesion](stats/cohesion.md) between sentences: overlaps, adjacent and over all pairs, Dice, givenness and repetition
*   walk the [dependency tree](stats/syntax.md): dependency distances, tree depth, valency and coordination chains on the labels shared by Universal Dependencies and ClearNLP, with a word the tokenizer split at its hyphens taken for one on request
*   compare corpora with the measures of corpus linguistics: [keywords](corpus/keyness.md) against a corpus or a frequency dictionary, [collocations](corpus/collocations.md), the [dispersion](corpus/dispersion.md) of a word, [stylometry](corpus/stylometry.md) (Burrows's Delta and its variants, Zeta, Kilgarriff's chi-square, the Mendenhall curve), the [comparison](corpus/compare.md) of corpora feature by feature with effect sizes, a bootstrap by texts and the Holm correction, and a [KWIC concordance](corpus/kwic.md)
*   plot [Zipf's law](visualizers/zipf.md), [vocabulary growth](visualizers/vocabulary.md), [sentence lengths](visualizers/sentences.md), [literature fingerprinting](visualizers/fingerprinting.md), a [word tree](visualizers/word_tree.md), [corpus](visualizers/corpus.md) and [stylometric](visualizers/stylometry.md) measures, with the labels of the plots as a parameter, and [highlight](visualizers/highlight.md) a text by the layers of a language library
*   build [components](components.md) of spaCy pipelines that put the statistics into an extension of `Doc`
*   build [datasets](datasets.md): download an archive with a checksum, extract it safely and filter the records
*   catch errors of one [hierarchy](exceptions.md) whose classes are also built-in exceptions

The reference of every function is a named section that the libraries include in their own documentation, so a formula is described in one place.

## Installation

Requires Python 3.11 or newer.

``` bash
pip install anyts
```

The dependencies are on the [Installation](installation.md) page.

## Quick start

``` python
>>> from anyts import DiversityStats, SentsExtractor, WordsExtractor

>>> text = "The cat sat on the mat. The dog sat on the log! The cat and the dog slept."

>>> SentsExtractor().extract(text)
('The cat sat on the mat.', 'The dog sat on the log!', 'The cat and the dog slept.')

>>> ds = DiversityStats(WordsExtractor(lowercase=True).extract(text))
>>> ds.ttr, round(ds.entropy, 3)
(0.5, 2.864)
```

A language library subclasses the extractors and overrides their hooks:

``` python
>>> class Words(WordsExtractor):
...     def lemmatize(self, word):
...         return {"sat": "sit", "slept": "sleep"}.get(word.lower(), word)

>>> Words(lowercase=True, use_lexemes=True).extract("The cat sat. The dog slept.")
('the', 'cat', 'sit', 'the', 'dog', 'sleep')
```

The corpus measures take lists of words:

``` python
>>> from anyts.corpus import keyness

>>> cats = WordsExtractor(lowercase=True).extract("The cat sat on the mat. The cat saw a bird. The cat slept.")
>>> dogs = WordsExtractor(lowercase=True).extract("The dog sat on the log. The dog saw a cat. The dog barked.")
>>> [(keyword.word, round(keyword.log_ratio, 2)) for keyword in keyness(cats, dogs, min_freq=2)]
[('cat', 1.58)]
```
