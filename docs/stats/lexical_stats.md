# Lexical sophistication

!!! info ""
    **anyts.lexical_stats.LexicalStats**, **anyts.lexical_stats.calc_surprisal()**, **anyts.lexical_stats.is_number()**

## Description

<!-- --8<-- [start:LexicalStats] -->
Lexical sophistication in the manner of TAALES (Kyle, Crossley and Berger, 2018) - how rare the words of a text are in the language: the mean frequency, range and dispersion of the words by a frequency dictionary, the surprisal and the perplexity by its unigram model, the shares of the frequency bands of a list of the most frequent lemmas and the lexical density, the share of the content words. The statistics by the dictionary are computed when first read, so the bands and the lexical density need no dictionary data.

A dictionary of another class than that of the library raises `SourceTypeError`, a source without words `SourceError`.
<!-- --8<-- [end:LexicalStats] -->

## Language hooks

<!-- --8<-- [start:LexicalStats-hooks] -->
A language library subclasses `LexicalStats`:

| Hook | Kind | Description |
| :--: | :--: | :---------: |
| `analyze(source)` | method | The words of a source as `LexicalWord`: the word, its lemma and whether it is a content word; an abstract method, since the lemmas and the parts of speech depend on the language. Numbers (`is_number`) are not words |
| `freq_dict_class` | class attribute | Class of the frequency dictionary, made without arguments when none is given; a dictionary of another class is refused |
| `dictionary_keys()` | method | Keys of the words in the dictionary; the lemmas by default, otherwise for instance a proper noun by its form |
| `rank(lemma)` | method | Rank of a lemma in the list of the most frequent lemmas, `None` out of it; no list by default |
| `top_size()` | method | Size of the list, the upper bound of `band_coverage`; 10000 by default |
| `stats_desc`, `stats_headers` | class attributes | Statistics of `get_stats` with their descriptions, headers of the columns for `print_stats` |
| `messages` | class attribute | Messages of the errors by key; `MESSAGES` by default |

The parameters of a library - a pipeline that parses a string, a word extractor - are those of its `__init__`, which passes the source and the dictionary on.
<!-- --8<-- [end:LexicalStats-hooks] -->

## Frequency dictionary { #FrequencyDictionary }

<!-- --8<-- [start:FrequencyDictionary] -->
The dictionary is any object of the protocol `FrequencyDictionary`: `lookup(lemma)` gives the entry of a lemma or `None`, `ipm(lemma)` its frequency per million words or 0, and `min_ipm` the lowest frequency of the dictionary, above zero. An entry (`FrequencyEntry`) has the frequency `ipm`, above zero, the range `range` (the parts of the corpus with the lemma) and the dispersion `dispersion`. Without `freq_dict_class` a dictionary without `lookup` and `ipm` raises `SourceTypeError`.
<!-- --8<-- [end:FrequencyDictionary] -->

<!-- --8<-- [start:FrequencyEntry] -->
`FrequencyEntry` is the entry of a lemma in a `FrequencyDictionary`: `ipm`, `range` and `dispersion`.
<!-- --8<-- [end:FrequencyEntry] -->

## Parameters

<!-- --8<-- [start:LexicalStats-parameters] -->
| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `source` | str/Doc | `-` | Data source |
| `freq_dict` | FrequencyDictionary | `None` | Frequency dictionary; `freq_dict_class()` by default |
<!-- --8<-- [end:LexicalStats-parameters] -->

## Attributes

<!-- --8<-- [start:LexicalStats-attributes] -->
| Attribute | Type | Description |
| :-------: | :--: | :---------: |
| `words`, `lemmas` | tuple[str] | Words and their lemmas; the bands are counted by the lemmas |
| `keys` | tuple[str] | Keys of the words in the dictionary |
| `entries` | tuple[FrequencyEntry or None] | Entries of the dictionary, `None` for a word out of it |
| `ranks` | tuple[int or None] | Ranks of the lemmas, `None` out of the list |
| `n_words`, `n_content_words`, `n_found` | int | Number of words, of content words and of words found in the dictionary |
| `coverage` | float | Share of words found in the dictionary |
| `mean_ipm`, `mean_ipm_content` | float | Mean frequency of the words found, of the content words found |
| `mean_log_ipm`, `mean_log_ipm_content` | float | Mean decimal logarithm of the frequency, of the words found and of the content words found |
| `mean_range`, `mean_dispersion` | float | Mean range and dispersion of the words found |
| `surprisal`, `perplexity` | float | Mean surprisal in bits (`calc_surprisal`), 2 to its power |
| `p_top1000`, `p_top2000`, `p_top5000`, `p_top10000`, `p_beyond_top10000` | float | Shares of the words with a lemma in the top 1000, 2000, 5000 and 10000 of the list and beyond it |
| `lexical_density` | float | Share of content words |

A mean over no words found is `nan`, and so is a band beyond the size of the list (`top_size`).
<!-- --8<-- [end:LexicalStats-attributes] -->

## Methods

### band_coverage

<!-- --8<-- [start:LexicalStats-band_coverage] -->
`band_coverage(bands, unique)` gives the share of the words with a lemma in the top N of the list for every bound N of `bands` (`FREQUENCY_BANDS` by default), or with `unique=True` the share of the distinct lemmas. Bounds that are not a list of integers or a bound out of 1 and `top_size()` raise `ParameterError`.
<!-- --8<-- [end:LexicalStats-band_coverage] -->

The other methods - `get_stats`, `to_dataframe`, `print_stats` and `describe` - are those of the [statistics interface](stats.md).

## Functions

### calc_surprisal

<!-- --8<-- [start:calc_surprisal] -->
The mean surprisal of the words by the unigram model of a frequency dictionary, in bits; a word out of the dictionary gets its lowest frequency `min_ipm`, so every word has a surprisal. The perplexity is 2 to its power.

Formula:

$$
\frac{1}{N} \sum_{w} -\log_2 \frac{\max(\textrm{ipm}_w, \textrm{min\_ipm})}{10^6}
$$

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `lemmas` | list[str] | `-` | Keys of the words in the dictionary |
| `freq_dict` | FrequencyDictionary | `-` | Frequency dictionary |

No words give `nan`; keys that are not a list of strings and a dictionary without `ipm` and `min_ipm` raise `SourceTypeError`, a lowest frequency that is not above zero `ParameterError`.
<!-- --8<-- [end:calc_surprisal] -->

### is_number

<!-- --8<-- [start:is_number] -->
`is_number(word, pattern)` checks whether a word is a number by a pattern matched against the whole lower-cased word, `NUMBER_PATTERN` of the extractors by default; a language passes its own (ordinals, Roman numerals).
<!-- --8<-- [end:is_number] -->

## Usage example

!!! example "Example"

    ``` python
    from typing import NamedTuple

    from anyts.lexical_stats import LexicalStats, LexicalWord


    class Entry(NamedTuple):
        ipm: float
        range: int
        dispersion: float


    class Frequencies:
        min_ipm = 0.5
        entries = {"the": Entry(50000.0, 40, 0.99), "cat": Entry(100.0, 38, 0.9)}

        def lookup(self, lemma):
            return self.entries.get(lemma)

        def ipm(self, lemma):
            entry = self.lookup(lemma)
            return entry.ipm if entry is not None else 0.0


    class Lexical(LexicalStats):
        freq_dict_class = Frequencies

        def analyze(self, source):
            return [LexicalWord(word, word.lower(), word.lower() != "the") for word in source.split()]


    stats = Lexical("The cat purrs")
    stats.coverage, round(stats.mean_log_ipm, 3), round(stats.surprisal, 3)
    # (0.6666666666666666, 3.349, 12.847)
    ```
