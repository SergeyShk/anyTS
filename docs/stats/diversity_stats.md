# Lexical diversity metrics

!!! info ""
    **anyts.diversity_stats.DiversityStats**

## Description

<!-- --8<-- [start:DiversityStats] -->
A class for computing the main [lexical diversity](https://en.wikipedia.org/wiki/Lexical_diversity) metrics of a text from its words.

!!! note "Note"
    The metrics are computed by accessing an attribute or by calling `get_stats`.
<!-- --8<-- [end:DiversityStats] -->

## Language hooks

<!-- --8<-- [start:DiversityStats-hooks] -->
The class takes the words as given: a language library extracts them from its sources (a string, a [spaCy](https://github.com/explosion/spaCy) `Doc`) and lower-cases them, since every metric counts lexemes. A library overrides two class attributes in a subclass: `stats_desc`, the metrics of `get_stats` with their descriptions for `print_stats` (`anyts.constants.DIVERSITY_STATS_DESC` by default), and `stats_headers`, the two column headers of `print_stats`. Error messages come from the class attribute `messages`, `MESSAGES` by default.
<!-- --8<-- [end:DiversityStats-hooks] -->

## Parameters

<!-- --8<-- [start:DiversityStats-parameters] -->
| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `words` | Iterable[str] | `-` | Words of the text: a sequence or an iterator of strings |
| `window_len` | int | `50` | Window size for MATTR and segment size for MSTTR (`MATTR_WINDOW_LEN`) |
| `mtld_threshold` | float | `0.72` | TTR threshold for MTLD, MA-MTLD and MTLD-W (`MTLD_TTR_THRESHOLD`) |
| `mtld_min_len` | int | `10` | Minimum factor length for MTLD, MA-MTLD and MTLD-W (`MTLD_MIN_LEN`) |
| `hdd_sample_size` | int | `42` | Sample size for HD-D (`HDD_SAMPLE_SIZE`) |
| `log_base` | float | `10` | Logarithm base for the Summer, Maas and Dugast metrics (`DIVERSITY_LOG_BASE`) |

Words that are not a sequence or an iterator of strings raise `SourceTypeError`, and so do a string, a `Doc`, a set and a table; no words raise `SourceError`.
<!-- --8<-- [end:DiversityStats-parameters] -->

<!-- --8<-- [start:check_params] -->
The parameters are checked by `check_params(window_len, mtld_threshold, mtld_min_len, hdd_sample_size, log_base, *, messages=MESSAGES)`, which raises `ParameterError` for a window, a sample size or a minimum factor length out of range, a threshold outside (0, 1) or a logarithm base not above 1. Called before the words are extracted, it reports a wrong parameter before an empty text.
<!-- --8<-- [end:check_params] -->

## Conventions { #conventions }

<!-- --8<-- [start:DiversityStats-conventions] -->
Some metrics depend on conventions that differ between libraries. All of them except the comparison with the MTLD threshold are class parameters:

| Parameter | Default | Other libraries |
| :-------: | :-----: | :-------------: |
| Logarithm base for Summer, Maas, Dugast's U and Dugast's k | 10 | LexicalRichness, textcomplexity and zipfR - natural |
| MATTR window and MSTTR segment | 50 | quanteda and koRpus - 100 |
| TTR threshold for MTLD | 0.72 | 0.66-0.75 in the literature |
| Comparison with the MTLD threshold | a factor closes at TTR ≤ 0.72 (McCarthy & Jarvis, 2010) | lexical-diversity and TAALED - strict `<`; the values differ when TTR hits the threshold exactly |
| Minimum MTLD factor length | 10 | koRpus - only in MTLD-MA, dropping shorter factors instead of extending them; LexicalRichness and textcomplexity - not applied |
| HD-D sample size | 42 | 35-50 in the literature |

According to Zenker and Kyle (2021), MATTR, MTLD and HD-D are stable on texts of 50-200 words and longer, MTLD-W, MA-MTLD and Maas are unstable on short texts, and the TTR family never stabilizes. Texts of different lengths are compared by the [windowed computation](#windowed) with confidence intervals.
<!-- --8<-- [end:DiversityStats-conventions] -->

## Attributes

<!-- --8<-- [start:DiversityStats-attributes] -->
| Attribute | Type | Description |
| :-------: | :--: | :---------: |
| `words` | tuple[str] | Tuple of the words |
| `window_len`, `mtld_threshold`, `mtld_min_len`, `hdd_sample_size`, `log_base` | int/float | Parameters of the metrics, changeable on the object |
| `frequency_spectrum` | dict[int, int] | Frequency spectrum - the number of lexemes with a given frequency |
| `ttr` | float | Type-Token Ratio (TTR) |
| `rttr` | float | Root Type-Token Ratio (RTTR) |
| `cttr` | float | Corrected Type-Token Ratio (CTTR) |
| `httr` | float | Herdan Type-Token Ratio (HTTR) |
| `sttr` | float | Summer Type-Token Ratio (STTR) |
| `mttr` | float | Maas Type-Token Ratio (MTTR) |
| `dttr` | float | Dugast Type-Token Ratio (DTTR) |
| `mattr` | float | Moving Average Type-Token Ratio (MATTR) |
| `msttr` | float | Mean Segmental Type-Token Ratio (MSTTR) |
| `mtld` | float | Measure of Textual Lexical Diversity (MTLD) |
| `mamtld` | float | Moving Average Measure of Textual Lexical Diversity (MA-MTLD) |
| `mtldw` | float | MTLD with a moving window and text wrap (MTLD-W) |
| `hdd` | float | Hypergeometric Distribution D (HD-D) |
| `simpson_index` | float | Simpson's index (D) |
| `inverse_simpson_index` | float | Inverse Simpson's index (1/D) |
| `gini_simpson_index` | float | Gini-Simpson index (1-D) |
| `hapax_index` | float | Hapax index, a.k.a. Honoré's R |
| `honore_r` | float | Alias for the hapax index |
| `yule_k` | float | Yule's characteristic (Yule's K) |
| `yule_i` | float | Inverse Yule's characteristic (Yule's I) |
| `herdan_vm` | float | Herdan's Vm |
| `sichel_s` | float | Sichel's S |
| `michea_m` | float | Michéa's M |
| `brunet_w` | float | Brunet's W |
| `dugast_k` | float | Dugast's k |
| `baayen_p` | float | Baayen's P |
| `hapax_ratio` | float | Share of hapaxes among lexemes |
| `alpha2` | float | The α₂ exponent |
| `entropy` | float | Shannon entropy in bits |
| `evenness` | float | Evenness - the ratio of entropy to its maximum |
| `perplexity` | float | Perplexity |
| `zipf_alpha` | float | Zipf's law slope |
| `heaps_beta` | float | Heaps' law exponent |

!!! note "Note"
    Every metric can also be computed by its [function](diversity_stats_funcs.md).
<!-- --8<-- [end:DiversityStats-attributes] -->

## Methods

### windowed

<!-- --8<-- [start:DiversityStats-windowed] -->
Windowed computation of a metric by its name with [`calc_windowed`](diversity_stats_funcs.md#calc_windowed): the mean of its values over consecutive windows of equal length, the sample standard deviation and the confidence interval of the mean. The edge cases (short texts, `nan` and infinite values) are described there.

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `stat` | str | `-` | Metric name from `get_stats` |
| `window_len` | int | `100` | Window size |
| `step` | int | `None` | Window step, by default the window size (windows do not overlap) |
| `confidence` | float | `0.95` | Confidence level |

Returns a `WindowStats` named tuple with the fields `mean`, `std`, `lower`, `upper` and `n_windows`. An unknown metric name raises `UnknownStatError`; a window size or a step that is not an integer of at least one and a confidence level that is not a number in (0, 1) raise `ParameterError`.
<!-- --8<-- [end:DiversityStats-windowed] -->

!!! example "Example"

    ``` python
    from anyts import DiversityStats

    ds = DiversityStats("a b c d e b c f g h g i g j k".split())
    ds.windowed("ttr", window_len=5)
    # WindowStats(mean=0.9333333333333332, std=0.11547005383792512, lower=0.6464898180167025, upper=1.220176848649964, n_windows=3)
    ds.windowed("ttr", window_len=5, step=2).n_windows
    # 6
    ```

### get_stats

<!-- --8<-- [start:DiversityStats-get_stats] -->
Returns a dictionary with the computed lexical diversity metrics of `stats_desc`.
<!-- --8<-- [end:DiversityStats-get_stats] -->

!!! example "Example"

    _Code_:

    ``` python
    from anyts import DiversityStats

    ds = DiversityStats("a b c d e b c f g h g i g j k".split())
    ds.get_stats()
    ```

    _Result_:

    ``` bash
    {'ttr': 0.7333333333333333,
    'rttr': 2.840187787218772,
    'cttr': 2.008316044185609,
    'httr': 0.8854692840710255,
    'sttr': 0.2500605793160848,
    'mttr': 0.09738250756232528,
    'dttr': 10.268784661968118,
    'mattr': 0.7333333333333333,
    'msttr': 0.7333333333333333,
    'mtld': 15.0,
    'mamtld': 12.0,
    'mtldw': 13.25,
    'hdd': nan,
    'simpson_index': 0.047619047619047616,
    'inverse_simpson_index': 21.0,
    'gini_simpson_index': 0.9523809523809523,
    'hapax_index': 992.9517404041437,
    'yule_k': 444.44444444444446,
    'yule_i': 8.642857142857142,
    'herdan_vm': 0.1421338109037403,
    'sichel_s': 0.18181818181818182,
    'michea_m': 5.5,
    'brunet_w': 6.00637847898991,
    'dugast_k': 14.783895126869226,
    'baayen_p': 0.5333333333333333,
    'hapax_ratio': 0.7272727272727273,
    'alpha2': 0.5,
    'entropy': 3.3232314287976203,
    'evenness': 0.9606293157795304,
    'perplexity': 10.009038104159247,
    'zipf_alpha': 0.4884512334695912,
    'heaps_beta': 0.8366147342060046}
    ```

### print_stats

<!-- --8<-- [start:DiversityStats-print_stats] -->
Prints a table with the computed lexical diversity metrics, their descriptions from `stats_desc` and the headers from `stats_headers`.
<!-- --8<-- [end:DiversityStats-print_stats] -->

The frame of the metrics (`to_dataframe`) and their reading (`describe`) are those of the [statistics interface](stats.md).

The example continues the previous one:

!!! example "Example"

    _Code_:

    ``` python
    ds.print_stats()
    ```

    _Result_:

    ``` bash
                                    Metric                                 |  Value
    ----------------------------------------------------------------------------------
    Type-Token Ratio (TTR)                                                 |   0.73
    Root Type-Token Ratio (RTTR)                                           |   2.84
    Corrected Type-Token Ratio (CTTR)                                      |   2.01
    Herdan Type-Token Ratio (HTTR)                                         |   0.89
    Summer Type-Token Ratio (STTR)                                         |   0.25
    Maas Type-Token Ratio (MTTR)                                           |   0.10
    Dugast Type-Token Ratio (DTTR)                                         |  10.27
    Moving Average Type-Token Ratio (MATTR)                                |   0.73
    Mean Segmental Type-Token Ratio (MSTTR)                                |   0.73
    Measure of Textual Lexical Diversity (MTLD)                            |  15.00
    Moving Average Measure of Textual Lexical Diversity (MA-MTLD)          |  12.00
    Moving Average Measure of Textual Lexical Diversity with Wrap (MTLD-W) |  13.25
    Hypergeometric Distribution D (HD-D)                                   |   nan
    Simpson's index (D)                                                    |   0.05
    Inverse Simpson's index (1/D)                                          |  21.00
    Gini-Simpson index (1-D)                                               |   0.95
    Hapax index (Honoré's R)                                               |  992.95
    Yule's characteristic K                                                |  444.44
    Yule's inverse characteristic I                                        |   8.64
    Herdan's Vm                                                            |   0.14
    Sichel's S                                                             |   0.18
    Michéa's M                                                             |   5.50
    Brunet's W                                                             |   6.01
    Dugast's k                                                             |  14.78
    Baayen's P                                                             |   0.53
    Hapax ratio                                                            |   0.73
    Exponent α₂                                                            |   0.50
    Shannon entropy (bits)                                                 |   3.32
    Evenness                                                               |   0.96
    Perplexity                                                             |  10.01
    Zipf's law slope (α)                                                   |   0.49
    Heaps' law exponent (β)                                                |   0.84
    ```
