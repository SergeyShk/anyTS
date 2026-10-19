# Lexical sophistication

``` {.python .signature}
LexicalStats(source, freq_dict=None)
```

<!-- --8<-- [start:LexicalStats] -->
Lexical sophistication in the manner of TAALES (Kyle, Crossley and Berger, 2018) - how rare the words of a text are: statistics by a frequency dictionary and its unigram model, the shares of the frequency bands of a list of the most frequent lemmas and the lexical density. The statistics by the dictionary are computed when first read, so the bands and the lexical density need no dictionary data.

Raises:

- `SourceTypeError` - a dictionary of another class than that of the library or, without `freq_dict_class`, one without `lookup` and `ipm` or none at all; an `analyze` that does not give `LexicalWord` objects;
- `SourceError` - a source without words.
<!-- --8<-- [end:LexicalStats] -->

=== "Code"

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

        def rank(self, lemma):
            return {"the": 1, "cat": 1500}.get(lemma)


    stats = Lexical("The cat sees the dog")
    stats.print_stats()
    ```

=== "Result"

    ```
                        Statistic                    |  Value
    ------------------------------------------------------------
    Share of words found in the frequency dictionary |   0.60
    Mean frequency (ipm)                             | 33366.67
    Mean frequency of content words (ipm)            |  100.00
    Mean log frequency (lg ipm)                      |   3.80
    Mean log frequency of content words              |   2.00
    Mean range                                       |  39.33
    Mean dispersion (D)                              |   0.96
    Mean surprisal (bits)                            |  12.76
    Unigram perplexity                               | 6931.45
    Share of words in the top 1000                   |   0.40
    Share of words in the top 2000                   |   0.60
    Share of words in the top 5000                   |   0.60
    Share of words in the top 10000                  |   0.60
    Share of words beyond the top 10000              |   0.40
    Lexical density                                  |   0.60
    ```

## Parameters

<!-- --8<-- [start:LexicalStats-parameters] -->
| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `source` | `str` / `Doc` | - | Data source |
| `freq_dict` | `FrequencyDictionary` | `None` | Frequency dictionary; `freq_dict_class()` by default |
<!-- --8<-- [end:LexicalStats-parameters] -->

## Attributes

<!-- --8<-- [start:LexicalStats-attributes] -->
| Attribute | Type | Description |
| :-------- | :--- | :---------- |
| `freq_dict` | `FrequencyDictionary` | Frequency dictionary |
| `words`, `lemmas` | `tuple[str]` | Words and their lemmas; the bands are counted by the lemmas |
| `keys` | `tuple[str]` | Keys of the words in the dictionary |
| `entries` | `tuple[FrequencyEntry / None]` | Entries of the dictionary, `None` for a word out of it |
| `ranks` | `tuple[int / None]` | Ranks of the lemmas, `None` out of the list |
| `n_words`, `n_content_words`, `n_found` | `int` | Number of words, of content words and of words found in the dictionary |
<!-- --8<-- [end:LexicalStats-attributes] -->

## Frequency dictionary { #FrequencyDictionary }

<!-- --8<-- [start:FrequencyDictionary] -->
The dictionary is any object of the protocol `FrequencyDictionary`: `lookup(lemma)` gives the entry of a lemma or `None`, `ipm(lemma)` its frequency per million words or 0, and `min_ipm` the lowest frequency of the dictionary, above zero. An entry (`FrequencyEntry`) has the frequency `ipm`, above zero, the range `range` (the parts of the corpus with the lemma) and the dispersion `dispersion`. Without `freq_dict_class` a dictionary without `lookup` and `ipm` raises `SourceTypeError`.
<!-- --8<-- [end:FrequencyDictionary] -->

<!-- --8<-- [start:FrequencyEntry] -->
`FrequencyEntry` is the entry of a lemma in a `FrequencyDictionary`: `ipm`, `range` and `dispersion`.
<!-- --8<-- [end:FrequencyEntry] -->

## Metrics

<!-- --8<-- [start:LexicalStats-metrics] -->
Every metric is an attribute or a property of the object, and `get_stats` gives them all. A mean is over the words found in the dictionary, and without them it is `nan`.

| Metric | Measures | Range | Higher means |
| :----- | :------- | :---- | :----------- |
| `coverage` | Share of the words found in the dictionary | 0-1 | More words known to the dictionary |
| `mean_ipm`, `mean_ipm_content` | Mean frequency per million words of the words found, of the content words found | Above 0 | More frequent words |
| `mean_log_ipm`, `mean_log_ipm_content` | Mean decimal logarithm of the frequency of the words found, of the content words found | Up to 6 | More frequent words |
| `mean_range` | Mean range of the words found | 0 and above | Words used in more parts of the corpus |
| `mean_dispersion` | Mean dispersion of the words found | That of the dictionary | By the measure of the dictionary |
| [`surprisal`](#surprisal) | Mean surprisal of the words by the unigram model of the dictionary, in bits | 0 and above | Rarer words |
| [`perplexity`](#surprisal) | 2 to the power of the surprisal | 1 and above | Rarer words |
| [`p_top1000`](#bands), [`p_top2000`](#bands), [`p_top5000`](#bands), [`p_top10000`](#bands) | Share of the words with a lemma in the top 1000, 2000, 5000 and 10000 of the list | 0-1, `nan` for a band beyond `top_size` | More frequent words |
| [`p_beyond_top10000`](#bands) | Share of the words with a lemma beyond the top 10000 | 0-1, `nan` for a list shorter than 10000 | Rarer words |
| `lexical_density` | Share of the content words | 0-1 | More content words |
<!-- --8<-- [end:LexicalStats-metrics] -->

<div class="metric-card" markdown>

### Surprisal and perplexity { #surprisal }

`surprisal` · `perplexity`
{ .metric-meta }

<!-- --8<-- [start:calc_surprisal] -->
``` {.python .signature}
calc_surprisal(lemmas, freq_dict)
```

The mean surprisal of the words by the unigram model of a frequency dictionary, in bits; a word out of the dictionary gets its lowest frequency `min_ipm`. The perplexity is 2 to its power.

$$
\frac{1}{N} \sum_{w} -\log_2 \frac{\max(\textrm{ipm}_w, \textrm{min\_ipm})}{10^6}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `lemmas` | `list[str]` | - | Keys of the words in the dictionary |
| `freq_dict` | `FrequencyDictionary` | - | Frequency dictionary |

No words give `nan`; keys that are not a list of strings and a dictionary without `ipm` and `min_ipm` raise `SourceTypeError`, a lowest frequency that is not above zero `ParameterError`.
<!-- --8<-- [end:calc_surprisal] -->

</div>

<div class="metric-card" markdown>

### Frequency bands { #bands }

`p_top1000` · `p_top2000` · `p_top5000` · `p_top10000` · `p_beyond_top10000` · `band_coverage(bands, unique)`
{ .metric-meta }

<!-- --8<-- [start:LexicalStats-bands] -->
The share of the words whose lemma has a rank (`rank`) within the top $N$ of the list, for the bounds 1000, 2000, 5000 and 10000 of `FREQUENCY_BANDS`; the share beyond the top 10000 is the rest, the words out of the list included. A band beyond the size of the list (`top_size`) is `nan`, and so is the share beyond the top 10000 for a list shorter than 10000.

$$
\frac{\textrm{Number of words with a rank up to } N}{\textrm{Number of words}}
$$
<!-- --8<-- [end:LexicalStats-bands] -->

</div>

## Methods

<!-- --8<-- [start:LexicalStats-band_coverage] -->
`band_coverage(bands, unique)` gives the share of the words with a lemma in the top N of the list for every bound N of `bands` (`FREQUENCY_BANDS` by default), or with `unique=True` the share of the distinct lemmas. Bounds that are not a list of integers or a bound out of 1 and `top_size()` raise `ParameterError`.
<!-- --8<-- [end:LexicalStats-band_coverage] -->

=== "Code"

    ``` python
    stats.band_coverage([1000, 2000])
    stats.band_coverage([1000, 2000], unique=True)
    ```

=== "Result"

    ```
    {1000: 0.4, 2000: 0.6}
    {1000: 0.25, 2000: 0.5}
    ```

The other methods - `get_stats`, `to_dataframe`, `print_stats` and `describe` - are those of the [statistics interface](stats.md).

## For library developers { #hooks }

<details class="library-hooks" markdown>
<summary>Language hooks of a subclass</summary>

<!-- --8<-- [start:LexicalStats-hooks] -->
A language library subclasses `LexicalStats`:

| Hook | Kind | Description |
| :--- | :--- | :---------- |
| `analyze(source)` | method | The words of a source as `LexicalWord`: the word, its lemma and whether it is a content word; an abstract method. Numbers (`is_number` of `anyts.utils`) are not words |
| `freq_dict_class` | class attribute | Class of the frequency dictionary, made without arguments when none is given; a dictionary of another class is refused, and without the class a dictionary must be given |
| `dictionary_keys()` | method | Keys of the words in the dictionary; the lemmas by default, or for instance a proper noun by its form |
| `rank(lemma)` | method | Rank of a lemma in the list of the most frequent lemmas, `None` out of it; no list by default |
| `top_size()` | method | Size of the list, the upper bound of `band_coverage`; 10000 by default |
| `stats_desc`, `stats_headers` | class attributes | Statistics of `get_stats` with their descriptions (`anyts.constants.LEXICAL_STATS_DESC` by default), headers of the columns for `print_stats` |
| `messages` | class attribute | Messages of the errors by key; `MESSAGES` by default |

A library takes its own parameters, such as a pipeline or a word extractor, in its `__init__` and passes the source and the dictionary on. An `analyze` that does not give `LexicalWord` objects raises `SourceTypeError`.
<!-- --8<-- [end:LexicalStats-hooks] -->

</details>
