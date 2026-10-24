# Any Texts Statistics (anyTS)

**anyTS** is the language-independent core of the text statistics libraries [ruTS](https://github.com/SergeyShk/ruTS) (Russian) and [esTS](https://github.com/SergeyShk/esTS) (Spanish). It holds the code that does not depend on a language, so that it is written, tested and documented once; a language library adds its tokenizer, lemmatizer, [spaCy](https://github.com/explosion/spaCy) model and rules and re-exports the core under its own names.

## Features

<div class="grid cards" markdown>

-   :material-scissors-cutting:{ .lg .middle } __Extraction__

    ---

    Extract [sentences](extractors/sentences.md), [words](extractors/words.md) and [character N-grams](extractors/char_ngrams.md) with extractors whose tokenizer, lemmatizer and number pattern are hooks a language library overrides

    [:octicons-arrow-right-24: Extraction](extractors/sentences.md)

-   :material-table-large:{ .lg .middle } __Statistics interface__

    ---

    Give the statistics of every class through one interface: a dictionary, nested or flat, a pandas frame, a printed table and the reading of a statistic by its scale

    [:octicons-arrow-right-24: Statistics interface](stats/stats.md)

-   :material-counter:{ .lg .middle } __Basic statistics__

    ---

    Count sentences, words, syllables, letters and punctuation marks by type, with the syllables of a language library

    [:octicons-arrow-right-24: Basic statistics](stats/basic_stats.md)

-   :material-book-open-variant:{ .lg .middle } __Readability__

    ---

    Compute Flesch reading ease, Flesch-Kincaid, Coleman-Liau, ARI, SMOG, Gunning fog, LIX, RIX, Legibilidad µ, the consensus grade and the reading time, with the coefficients of a language library

    [:octicons-arrow-right-24: Readability metrics](stats/readability_stats.md)

-   :material-chart-bell-curve:{ .lg .middle } __Lexical diversity__

    ---

    Compute Type-Token Ratio and its variants, MATTR, MSTTR, MTLD, MA-MTLD, MTLD-W, HD-D, the indices of Simpson and Yule, entropy, the laws of Zipf and Heaps, over the whole text or over windows with confidence intervals

    [:octicons-arrow-right-24: Lexical diversity metrics](stats/diversity_stats.md)

-   :material-school:{ .lg .middle } __Lexical sophistication__

    ---

    Measure a text by a frequency dictionary in the manner of TAALES: coverage, mean frequency, range and dispersion, surprisal and perplexity, frequency bands and lexical density

    [:octicons-arrow-right-24: Lexical sophistication](stats/lexical_stats.md)

-   :material-feather:{ .lg .middle } __Style__

    ---

    Compute the SEO metrics (nausea, water, spam, naturalness by Zipf's law, keyword density) and the markers of the officialese, with the lists and the morphology of a language library

    [:octicons-arrow-right-24: Style metrics](stats/style_stats.md)

-   :material-link-variant:{ .lg .middle } __Cohesion__

    ---

    Measure the cohesion between sentences in the manner of Coh-Metrix - the overlap of nouns, arguments and content words, adjacent and over all pairs, Dice, givenness, the repetition of the tense and the aspect - and find the connectors of a dictionary with the context rules of a language, with the words and the features of a language library

    [:octicons-arrow-right-24: Cohesion statistics](stats/cohesion_stats.md)

-   :material-file-tree:{ .lg .middle } __Syntax__

    ---

    Compute the statistics of the dependency tree - dependency distances, tree depth, valency, coordination chains, clauses, modifiers of a noun, prepositional chains, participial clauses, the passive, negations, split predicates, the words before the root and the order of the subjects and the objects - with the clauses and the constructions of a language library, on [tree helpers](stats/syntax_stats.md#get_words) that read the labels shared by Universal Dependencies and ClearNLP and the verb form of a predicate by its auxiliaries

    [:octicons-arrow-right-24: Syntactic statistics](stats/syntax_stats.md)

-   :material-tag-text:{ .lg .middle } __Morphology__

    ---

    Count the parts of speech and the features of Universal Dependencies by value or word by word, with the descriptions of the values, the markers and the analysis of a language library

    [:octicons-arrow-right-24: Morphological statistics](stats/morph_stats.md)

-   :material-waveform:{ .lg .middle } __Phonetics__

    ---

    Compute classes of the sounds, consonant clusters, hiatuses, entropy of the CV patterns, alliteration and assonance by the [repetition index](stats/phon_stats.md#repetition_index), open syllables, with the transcription and the syllables of a language library

    [:octicons-arrow-right-24: Phonetic statistics](stats/phon_stats.md)

-   :material-bookshelf:{ .lg .middle } __Corpus measures__

    ---

    Compare corpora by [keywords](corpus/keyness.md) against a corpus or a frequency dictionary, [collocations](corpus/collocations.md), the [dispersion](corpus/dispersion.md) of a word, [stylometry](corpus/stylometry.md) (Burrows's Delta and its variants, Zeta, Kilgarriff's chi-square, the Mendenhall curve), the [comparison](corpus/compare.md) of corpora feature by feature with effect sizes, a bootstrap by texts and the Holm correction, and a [KWIC concordance](corpus/kwic.md)

    [:octicons-arrow-right-24: Corpus measures](corpus/keyness.md)

-   :material-chart-scatter-plot:{ .lg .middle } __Visualization__

    ---

    Plot [Zipf's law](visualizers/zipf.md), [vocabulary growth](visualizers/vocabulary.md), [sentence lengths](visualizers/sentences.md), [literature fingerprinting](visualizers/fingerprinting.md), a [word tree](visualizers/word_tree.md), [corpus](visualizers/corpus.md) and [stylometric](visualizers/stylometry.md) measures, with the labels of the plots as a parameter, and [highlight](visualizers/highlight.md) a text by the layers of a language library

    [:octicons-arrow-right-24: Visualization](visualizers/zipf.md)

-   :material-pipe:{ .lg .middle } __Components__

    ---

    Build components of spaCy pipelines that put the statistics into an extension of `Doc`

    [:octicons-arrow-right-24: Components](components.md)

-   :material-database:{ .lg .middle } __Datasets__

    ---

    Download an archive with a checksum, extract it safely and filter the records

    [:octicons-arrow-right-24: Datasets](datasets.md)

-   :material-alert-circle-outline:{ .lg .middle } __Exceptions__

    ---

    Catch errors of one hierarchy whose classes are also built-in exceptions

    [:octicons-arrow-right-24: Exceptions](exceptions.md)

</div>

The reference of every function is a named section that the libraries include in their own documentation, so a formula is described in one place.

## Installation

Requires Python 3.11 or newer.

``` bash
pip install anyts
```

The dependencies are on the [Installation](installation.md) page.

## Quick start

=== "Code"

    ``` python
    from anyts import DiversityStats, SentsExtractor, WordsExtractor

    text = "The cat sat on the mat. The dog sat on the log! The cat and the dog slept."
    SentsExtractor().extract(text)

    ds = DiversityStats(WordsExtractor(lowercase=True).extract(text))
    ds.ttr, round(ds.entropy, 3)
    ```

=== "Result"

    ```
    ('The cat sat on the mat.', 'The dog sat on the log!', 'The cat and the dog slept.')
    (0.5, 2.864)
    ```

A language library subclasses the extractors and overrides their hooks:

=== "Code"

    ``` python
    class Words(WordsExtractor):
        def lemmatize(self, word):
            return {"sat": "sit", "slept": "sleep"}.get(word.lower(), word)


    Words(lowercase=True, use_lexemes=True).extract("The cat sat. The dog slept.")
    ```

=== "Result"

    ```
    ('the', 'cat', 'sit', 'the', 'dog', 'sleep')
    ```

The corpus measures take lists of words:

=== "Code"

    ``` python
    from anyts.corpus import keyness

    cats = WordsExtractor(lowercase=True).extract("The cat sat on the mat. The cat saw a bird. The cat slept.")
    dogs = WordsExtractor(lowercase=True).extract("The dog sat on the log. The dog saw a cat. The dog barked.")
    [(keyword.word, round(keyword.log_ratio, 2)) for keyword in keyness(cats, dogs, min_freq=2)]
    ```

=== "Result"

    ```
    [('cat', 1.58)]
    ```
