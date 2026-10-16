# Corpus comparison

!!! info ""
    **anyts.corpus.compare_features()**, **anyts.corpus.check_comparison_params()**, **anyts.corpus.compare_values()**, **anyts.corpus.calc_cohen_d()**, **anyts.corpus.calc_cliff_delta()**, **anyts.corpus.bootstrap_median_diff()**, **anyts.corpus.holm_correction()**, **anyts.corpus.split_windows()**, **anyts.corpus.sentence_rhythm()**

## Description

<!-- --8<-- [start:compare_features] -->
Comparing two corpora feature by feature. Each corpus comes as a table of the features of its windows - texts split into parts of about the same size, so that the features do not depend on the length of the texts. `compare_features(table_a, table_b, labels, n_bootstrap, seed)` compares the tables column by column and returns one row per feature, sorted by descending absolute Cliff's delta, the features without statistics last. The bootstrap resamples whole texts by the level `text` of the index of a table; a table without that level has every row taken for a text of its own. A column missing from one of the tables gives `nan`.
<!-- --8<-- [end:compare_features] -->

## Statistics

<!-- --8<-- [start:compare_features-statistics] -->
For a feature with the values $x_1 \dots x_{n_A}$ in corpus A and $y_1 \dots y_{n_B}$ in corpus B (undefined and infinite values dropped; with fewer than two values on a side - `nan`):

| Column | Description |
| :----- | :---------- |
| `mean_A`, `mean_B`, `median_A`, `median_B` | means and medians |
| `median_diff`, `ci_low`, `ci_high` | the difference of the medians and its 95% percentile bootstrap interval: both sets are resampled `n_bootstrap` times (`bootstrap_median_diff`) |
| `cohen_d` | $d = (\bar{x} - \bar{y}) / s$, $s$ - the pooled standard deviation; 0.2 - a small effect, 0.5 - medium, 0.8 - large (`calc_cohen_d`) |
| `cliff_delta` | $\delta = P(x > y) - P(x < y)$ from −1 to 1; $\lvert\delta\rvert$ < 0.147 - a negligible effect, < 0.33 - small, < 0.474 - medium, large otherwise (Romano et al. 2006; `calc_cliff_delta`) |
| `auc` | the feature as a classifier on its own: the share of the pairs of windows where the value in A is greater than in B, ties counted as half; $\delta = 2 \cdot AUC - 1$, 0.5 - the feature does not tell the corpora apart |
| `u`, `p_value` | the Mann-Whitney U statistic and the two-sided p-value (`scipy.stats.mannwhitneyu`) |
| `p_holm` | the p-value with Holm's correction for the number of features (`holm_correction`) |
| `n_A`, `n_B` | number of windows with a defined value |
| `n_texts_A`, `n_texts_B` | number of texts behind those windows |

The names of the columns are `anyts.corpus.COMPARISON_COLUMNS`, with `A` and `B` replaced by the labels of the corpora. Cliff's delta and the AUC come from the same U statistic and agree with each other; Cohen's d is sensitive to outliers and to departures from normality, so it is best read next to the delta.

!!! warning "Windows of one text are not independent"
    The test and the effect sizes take every window for an independent observation, and the windows of one text are not. With few texts in a corpus the p-values are too small and reflect the texts chosen as much as the corpora. The bootstrap resamples whole texts instead (a cluster bootstrap), so its interval accounts for the spread between the texts; it needs at least two texts on each side and is rough with only a few.
<!-- --8<-- [end:compare_features-statistics] -->

## Parameters

<!-- --8<-- [start:compare_features-parameters] -->
| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `table_a` | DataFrame | `-` | Features of the windows of the first corpus, one row per window |
| `table_b` | DataFrame | `-` | Features of the windows of the second corpus |
| `labels` | tuple[str, str] | `("A", "B")` | Names of the corpora for the columns, two strings that give distinct columns |
| `n_bootstrap` | int | `1000` | Number of bootstrap samples |
| `seed` | int/Generator | `0` | Seed of the random number generator, a non-negative integer, or a numpy `Generator`; `None` - a random one |
<!-- --8<-- [end:compare_features-parameters] -->

<!-- --8<-- [start:check_comparison_params] -->
`check_comparison_params(labels=("A", "B"), n_bootstrap=1000, seed=0)` checks the parameters of `compare_features` and raises `ParameterError` unless the labels are two strings that give distinct columns (`("diff", "B")` would repeat `median_diff`), the number of bootstrap samples is an integer of at least one and the seed is `None`, a non-negative integer or a numpy `Generator`. Called before the tables are built from texts, it reports a wrong parameter before the texts are processed.
<!-- --8<-- [end:check_comparison_params] -->

!!! example "Example"

    ``` python
    import pandas as pd

    from anyts.corpus import compare_features

    short = pd.DataFrame({"length": [14.0, 15.0, 13.0, 16.0]})
    long = pd.DataFrame({"length": [33.0, 35.0, 31.0, 29.0]})
    result = compare_features(short, long, labels=("short", "long"), n_bootstrap=200)
    result.loc[
        "length", ["mean_short", "mean_long", "median_diff", "ci_low", "ci_high", "cliff_delta"]
    ].tolist()
    # [14.5, 32.0, -17.5, -20.5, -14.5, -1.0]
    ```

## Functions of the statistics

<!-- --8<-- [start:compare_values] -->
`compare_values(values_a, values_b, n_bootstrap=1000, rng=None, texts_a=None, texts_b=None)` compares two sets of values of one feature, undefined and infinite values - a missing value (`None`, `NA`) included - dropped together with their texts, and returns the values of one row in the order of `anyts.corpus.COMPARISON_COLUMNS`, `p_holm` left `nan`; `texts_a` and `texts_b` give the text of every value for the bootstrap.
<!-- --8<-- [end:compare_values] -->

<!-- --8<-- [start:calc_cohen_d] -->
`calc_cohen_d(values_a, values_b)` - Cohen's d with the pooled sample variances (ddof=1); `nan` with fewer than two values on a side or without spread.
<!-- --8<-- [end:calc_cohen_d] -->

<!-- --8<-- [start:calc_cliff_delta] -->
`calc_cliff_delta(values_a, values_b)` - Cliff's delta, the share of the pairs where the first value is greater minus the share where it is smaller; `nan` for an empty set or an undefined value. It is computed by sorting, in $O((n_A + n_B) \log n_B)$ time and linear memory.
<!-- --8<-- [end:calc_cliff_delta] -->

<!-- --8<-- [start:bootstrap_median_diff] -->
`bootstrap_median_diff(values_a, values_b, n_bootstrap=1000, rng=None, confidence=0.95, texts_a=None, texts_b=None)` - the percentile bootstrap interval of the difference of the medians. With `texts_a` and `texts_b` whole texts are resampled, and the median of a draw is that of the values of the drawn texts put together; with fewer than two texts on a side the interval is `nan`.
<!-- --8<-- [end:bootstrap_median_diff] -->

<!-- --8<-- [start:holm_correction] -->
`holm_correction(p_values)` - Holm's correction for multiple comparisons: the p-values are sorted in ascending order, the i-th is multiplied by (m − i + 1), where m is the number of defined values, then the running maximum is taken and capped at one; `nan` stays `nan`, and a p-value outside [0, 1] raises `ParameterError`.
<!-- --8<-- [end:holm_correction] -->

!!! example "Example"

    ``` python
    from anyts.corpus import calc_cliff_delta, calc_cohen_d, holm_correction

    round(calc_cohen_d([2, 4, 6, 8], [1, 3, 5, 7]), 3)
    # 0.387
    calc_cliff_delta([2, 4, 6, 8], [1, 3, 5, 7])
    # 0.25
    holm_correction([0.01, 0.04, 0.03]).round(3).tolist()
    # [0.03, 0.06, 0.06]
    ```

## Windows of a text { #split_windows }

<!-- --8<-- [start:split_windows] -->
`split_windows(text, window, min_words)` cuts a text into consecutive windows of exactly `window` words, so that the features that depend on the length are comparable between the windows of different texts. The incomplete rest at the end is a window only when it holds at least `min_words` words; by default a whole window, so the rest is dropped. A boundary goes before the first word of a window and the opening marks before it, so the punctuation stays in the windows; a symmetric mark, such as a straight quote or the dash of an aside, closes the previous window when it is glued to its last word or follows a closing mark. The windows are stripped of whitespace; `window=None` gives the whole text. The words and their positions come from `tokenize`, the words of `WordsExtractor` by default, and the marks of a language are parameters.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | str | `-` | Text string |
| `window` | int | `1000` | Size of a window in words; `None` - the whole text |
| `min_words` | int | `None` | Smallest number of words in a window; `None` - a whole window, or one word without a window |
| `tokenize` | Callable | `None` | Words of a text with their start and end positions |
| `opening_marks` | Collection[str] | `OPENING_MARKS` | Marks that open a phrase |
| `symmetric_marks` | Collection[str] | `SYMMETRIC_MARKS` | Opening marks that close a phrase as well |
| `closing_marks` | Collection[str] | `CLOSING_MARKS` | Marks that close a phrase |
| `messages` | dict[str, str] | `MESSAGES` | Messages of the errors by key |

A text that is not a string, a tokenizer that is not callable and marks that are not a collection of strings raise `SourceTypeError`, a window or `min_words` that is not an integer of at least one, `min_words` above the window and a mark of more than one character `ParameterError`. A text without words or shorter than `min_words` gives an empty list.
<!-- --8<-- [end:split_windows] -->

The marks of the core are those of `anyts.constants`: quotes, brackets and dashes open a phrase, the straight quotes and the dashes are symmetric, and the final marks, the comma, the semicolon, the closing brackets, guillemet and quotes close one.

## Rhythm of the sentences { #sentence_rhythm }

<!-- --8<-- [start:sentence_rhythm] -->
`sentence_rhythm(lengths)` gives the features of the rhythm of the sentences from their lengths in words: the mean length `sents_mean`, the standard deviation `sents_std`, the coefficient of variation `sents_cv` and the autocorrelation at lag 1 `sents_autocorr`, the link between the lengths of neighbouring sentences (Yule, 1939). The deviation needs two sentences, the autocorrelation three of unequal lengths and the coefficient of variation a mean above zero, otherwise they are `nan`, as are all of them without sentences; lengths that are not a list of integers raise `SourceTypeError`, a negative length `ParameterError`. The messages of the errors are the keyword `messages`.
<!-- --8<-- [end:sentence_rhythm] -->

!!! example "Example"

    ``` python
    from anyts.corpus import sentence_rhythm, split_windows

    split_windows("One two three four five", 2, min_words=1)
    # ['One two', 'three four', 'five']
    {key: round(value, 3) for key, value in sentence_rhythm([4, 8, 2, 7]).items()}
    # {'sents_mean': 5.25, 'sents_std': 2.754, 'sents_cv': 0.525, 'sents_autocorr': -0.794}
    ```
