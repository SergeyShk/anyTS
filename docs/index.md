# Any Texts Statistics (anyTS)

**anyTS** is the language-independent core of the text statistics libraries [ruTS](https://github.com/SergeyShk/ruTS) (Russian) and [esTS](https://github.com/SergeyShk/esTS) (Spanish). It holds the code that does not depend on a language, so that it is written, tested and documented once; a language library adds its tokenizer, lemmatizer, [spaCy](https://github.com/explosion/spaCy) model and rules and re-exports the core under its own names.

!!! warning "Status"
    The project is in development: the [exceptions](exceptions.md), the [utilities](utils.md) and the extractors of [sentences](extractors/sentences.md), [words](extractors/words.md) and [character N-grams](extractors/char_ngrams.md) are in place, and so are the [lexical diversity metrics](stats/diversity_stats.md) and the helpers of [cohesion](stats/cohesion.md) and of the [dependency tree](stats/syntax.md); the corpus measures follow.

## Planned scope

*   **Extraction** - the base of the sentence, word and character N-gram extractors with the tokenizer, the lemmatizer and the number pattern as hooks a language library overrides
*   **Lexical diversity** - TTR and its variants, MATTR, MSTTR, MTLD, HD-D, the indices of Simpson and Yule, entropy, the laws of Zipf and Heaps, windowed computation
*   **Cohesion and syntax helpers** - overlaps, Dice, givenness and repetition; dependency distances, tree depth, valency and coordination on the labels shared by Universal Dependencies and ClearNLP
*   **Corpus measures** - collocations, dispersion, keyness, Burrows's Delta, Zeta, the Mendenhall curve and the comparison of corpora with effect sizes, bootstrap and the Holm correction
*   **Exceptions** - one hierarchy whose classes are also built-in exceptions

The reference of every function is a named section that the libraries include in their own documentation, so a formula is described in one place.
