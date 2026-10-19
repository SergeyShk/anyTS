# Keywords

``` {.python .signature}
keyness(target, reference, measure='log_likelihood', min_freq=1, positive=True, top_n=None)
```

<!-- --8<-- [start:keyness] -->
Keyword extraction (keyness) for a target corpus against a reference one: the words that occur significantly more often in the target corpus than in the reference.

Every word gets two values that [Gabrielatos and Marchi](http://eprints.lancs.ac.uk/51449/4/Gabrielatos_Marchi_Keyness.pdf) and [Hardie](http://cass.lancs.ac.uk/log-ratio-an-informal-introduction/) recommend reading together: the log-likelihood $G^2$ with its p-value (whether there is a difference) and Log Ratio (how large it is), plus the chosen measure `score`, which sorts the list. The measures of significance ($G^2$, chi-square, BIC) and ELL, the effect size of $G^2$, are negative when the word is more frequent in the reference; %DIFF, Log Ratio and the odds ratio are directional by construction.

The reference may be a list of words, a mapping of frequencies (its size is the sum of the counts) or a `FrequencyReference`. Words are compared as they are: case, lemmatization and stop words belong to the word extractor, and both corpora have to be extracted the same way.
<!-- --8<-- [end:keyness] -->

=== "Code"

    ``` python
    from anyts import WordsExtractor
    from anyts.corpus import keyness

    we = WordsExtractor(lowercase=True)
    target = we.extract(
        "The cat was at the window and watched the birds. The birds flew away and the cat "
        "fell asleep at the window. Tomorrow the cat will be at the window and watch the birds."
    )
    reference = we.extract(
        "The dog was on the floor and slept. Then the dog ate and slept again. "
        "Tomorrow the dog will go for a walk."
    )

    [(k.word, k.freq_target, round(k.g2, 2)) for k in keyness(target, reference, top_n=3)]
    [(k.word, round(k.g2, 2)) for k in keyness(target, reference, positive=False, top_n=2)]
    ```

=== "Result"

    ```
    [('at', 3, 3.1), ('birds', 3, 3.1), ('cat', 3, 3.1)]
    [('dog', -5.45), ('slept', -3.63)]
    ```

## Parameters

<!-- --8<-- [start:keyness-parameters] -->
| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `target` | `list[str]` / `dict[str, int]` | - | Words of the target corpus or their frequencies |
| `reference` | `list[str]` / `dict[str, float]` / `FrequencyReference` | - | Words of the reference corpus, their frequencies or a reference by frequencies |
| `measure` | `str` | `'log_likelihood'` | Measure of `anyts.constants.KEYNESS_MEASURES` for `score` and the sorting |
| `min_freq` | `int` | `1` | Minimum frequency of a keyword in its own corpus |
| `positive` | `bool` | `True` | Positive keywords (more frequent in the target corpus) or negative ones (more frequent in the reference) |
| `top_n` | `int` | `None` | Number of keywords; `None` - all of them |

The parameters and the target corpus are checked by `check_keyness_params`. A reference that is not a list of strings, a counter or a `FrequencyReference` raises `SourceTypeError`, and a negative, `nan` or infinite frequency of a counter and an empty corpus raise `SourceError`.
<!-- --8<-- [end:keyness-parameters] -->

<!-- --8<-- [start:check_keyness_params] -->
``` {.python .signature}
check_keyness_params(measure='log_likelihood', min_freq=1, top_n=None, target=None)
```

Checks the parameters of `keyness` before a frequency dictionary is read: it raises `ParameterError` unless the measure is one of `KEYNESS_MEASURES`, the minimum frequency is an integer and the number of keywords is `None` or an integer of at least one. With `target` it also raises `SourceTypeError` unless the target corpus is a list of strings or a mapping of strings to whole frequencies, and `SourceError` for a negative, nan or infinite frequency.
<!-- --8<-- [end:check_keyness_params] -->

## Reference by frequencies

<!-- --8<-- [start:FrequencyReference] -->
``` {.python .signature}
FrequencyReference(counts, size, missing=0.0, key=None, keep=None)
```

A reference corpus described by its frequencies alone, such as a frequency dictionary built from a corpus too large to pass as words:

| Field | Type | Default | Description |
| :---- | :--- | :------ | :---------- |
| `counts` | `dict[str, float]` | - | Frequencies of the keys in the reference corpus |
| `size` | `float` | - | Size of the reference corpus in words |
| `missing` | `float` | `0.0` | Frequency of a key missing from `counts` |
| `key` | `Callable` | `None` | Key of a word of the target corpus in `counts`, such as its lemma; `None` - the word itself |
| `keep` | `Callable` | `None` | Whether a word of the target corpus is counted; `None` - every word |

Only the words of the target that `keep` passes are counted, under their `key`, in the frequencies and in the size alike. A key missing from `counts` has the frequency `missing`, such as the least frequency of a dictionary: an upper bound, so its word may be a positive keyword but never a negative one. Negative keywords come only from the keys of `counts` that `keep` passes. A frequency is checked as it is read, so a large dictionary is not gone through for positive keywords: one that is not a number raises `SourceTypeError`, and a negative, `nan` or infinite one `SourceError`. A `size` or a `missing` that is not a finite number or is negative raises `ParameterError`, and a `key` or a `keep` that cannot be called `SourceTypeError`.
<!-- --8<-- [end:FrequencyReference] -->

=== "Code"

    ``` python
    from anyts.corpus import FrequencyReference

    # Frequencies of the lemmas in a dictionary of a million words
    counts = {
        "the": 60_000.0,
        "and": 28_000.0,
        "at": 5_000.0,
        "be": 6_000.0,
        "was": 9_000.0,
        "will": 3_000.0,
        "cat": 50.0,
        "window": 60.0,
        "bird": 40.0,
        "watch": 90.0,
        "away": 400.0,
        "tomorrow": 100.0,
    }
    lemmas = {"birds": "bird", "watched": "watch"}
    dictionary = FrequencyReference(
        counts, size=1_000_000, missing=0.1, key=lambda word: lemmas.get(word, word)
    )
    [(k.word, round(k.g2, 1)) for k in keyness(target, dictionary, top_n=3)]
    ```

=== "Result"

    ```
    [('bird', 40.0), ('cat', 38.7), ('window', 37.6)]
    ```

## Result

<!-- --8<-- [start:Keyword] -->
``` {.python .signature}
Keyword(word, freq_target, freq_reference, ipm_target, ipm_reference, g2, p_value, log_ratio, score)
```

A list of `Keyword` named tuples by descending keyness (ties broken by descending frequency and alphabetically, words of an undefined measure last); `pd.DataFrame(keywords)` gives a table.

| Field | Type | Description |
| :---- | :--- | :---------- |
| `word` | `str` | Word |
| `freq_target` | `int` | Frequency in the target corpus |
| `freq_reference` | `float` | Frequency in the reference corpus |
| `ipm_target` | `float` | Frequency in the target corpus per million words |
| `ipm_reference` | `float` | Frequency in the reference corpus per million words |
| `g2` | `float` | Signed $G^2$ |
| `p_value` | `float` | p-value of $G^2$ |
| `log_ratio` | `float` | Log Ratio |
| `score` | `float` | Value of the chosen measure |
<!-- --8<-- [end:Keyword] -->

## Measures

<!-- --8<-- [start:keyness-measures] -->
The measures of `measure` by key, with their names and descriptions in `anyts.constants.KEYNESS_MEASURES`:

| Key | Measures | Range | Higher means |
| :-- | :------- | :---- | :----------- |
| [`log_likelihood`](#log_likelihood) | Significance of the difference of the frequencies | Any number | A more significant excess in the target corpus |
| [`chi2`](#chi2) | Significance of the difference, with Yates's correction | Any number | A more significant excess in the target corpus |
| [`diff`](#diff) | Difference of the frequencies per million, in percent of the reference | Above −100 | A larger excess in the target corpus |
| [`log_ratio`](#log_ratio) | Binary logarithm of the ratio of the frequencies per million | Any number | A larger excess in the target corpus |
| [`bic`](#bic) | Evidence of the difference: $G^2$ penalized by the size of the corpora | Any number | Stronger evidence of an excess in the target corpus, for a word more frequent there |
| [`ell`](#ell) | Effect size of $G^2$ | −1 to 1 as a rule, `nan` for small expected frequencies | A larger excess in the target corpus |
| [`odds_ratio`](#odds_ratio) | Ratio of the odds of the word in the corpora | 0 to `inf`, `nan` if the word fills both corpora | Higher odds in the target corpus |

Every measure is a function of the module `anyts.corpus.keyness` of the frequencies of a word and the sizes of the corpora, $N = c + d$:

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `a` | `float` | - | Frequency of the word in the target corpus |
| `b` | `float` | - | Frequency of the word in the reference corpus |
| `c` | `float` | - | Size of the target corpus |
| `d` | `float` | - | Size of the reference corpus |

A zero frequency in one of the corpora is replaced with 0.5 for %DIFF, Log Ratio and the odds ratio (Hardie 2014).
<!-- --8<-- [end:keyness-measures] -->

<div class="metric-card" markdown>

### Log-likelihood { #log_likelihood }

`log_likelihood` · `g2` · `p_value` · [Rayson and Garside (2000)](https://ucrel.lancs.ac.uk/llwizard.html)
{ .metric-meta }

<!-- --8<-- [start:calc_log_likelihood] -->
``` {.python .signature}
calc_log_likelihood(a, b, c, d)
```

The log-likelihood of the frequencies of the word against the expected ones $E_1$ and $E_2$; a term of zero frequency is zero. The critical values are `anyts.constants.G2_CRITICAL_VALUES`: 3.84 for p < 0.05, 6.63 for p < 0.01, 10.83 for p < 0.001, 15.13 for p < 0.0001. The sign is negative when the word is more frequent in the reference.

$$
G^2 = 2 \left(a \ln \frac{a}{E_1} + b \ln \frac{b}{E_2}\right), \quad E_1 = \frac{c\,(a+b)}{N}, \quad E_2 = \frac{d\,(a+b)}{N}
$$
<!-- --8<-- [end:calc_log_likelihood] -->

<!-- --8<-- [start:calc_p_value] -->
``` {.python .signature}
calc_p_value(g2)
```

The p-value of a $G^2$ or a chi-square, whatever its sign, by the chi-square distribution with one degree of freedom; an array of values gives an array.
<!-- --8<-- [end:calc_p_value] -->

</div>

<div class="metric-card" markdown>

### Chi-square { #chi2 }

`chi2`
{ .metric-meta }

<!-- --8<-- [start:calc_chi2] -->
``` {.python .signature}
calc_chi2(a, b, c, d)
```

The chi-square with Yates's correction over the 2×2 contingency table of the word and the other words of each corpus. When the correction exceeds the difference, the statistic is zero. The sign is negative when the word is more frequent in the reference.

$$
\chi^2 = \frac{N\,\max(\lvert a(d-b) - b(c-a) \rvert - N/2,\ 0)^2}{(a+b)(N-a-b)\,c\,d}
$$
<!-- --8<-- [end:calc_chi2] -->

</div>

<div class="metric-card" markdown>

### %DIFF { #diff }

`diff` · [Gabrielatos and Marchi (2011)](http://eprints.lancs.ac.uk/51449/4/Gabrielatos_Marchi_Keyness.pdf)
{ .metric-meta }

<!-- --8<-- [start:calc_diff] -->
``` {.python .signature}
calc_diff(a, b, c, d)
```

The difference of the frequencies $NF$ per million words, in percent of the frequency in the reference.

$$
\frac{NF_a - NF_b}{NF_b} \cdot 100
$$
<!-- --8<-- [end:calc_diff] -->

</div>

<div class="metric-card" markdown>

### Log Ratio { #log_ratio }

`log_ratio` · [Hardie (2014)](http://cass.lancs.ac.uk/log-ratio-an-informal-introduction/)
{ .metric-meta }

<!-- --8<-- [start:calc_log_ratio] -->
``` {.python .signature}
calc_log_ratio(a, b, c, d)
```

The binary logarithm of the ratio of the frequencies $NF$ per million words: one means the word is twice as frequent in the target corpus.

$$
\log_2 \frac{NF_a}{NF_b}
$$
<!-- --8<-- [end:calc_log_ratio] -->

</div>

<div class="metric-card" markdown>

### BIC { #bic }

`bic` · Wilson (2013)
{ .metric-meta }

<!-- --8<-- [start:calc_bic] -->
``` {.python .signature}
calc_bic(a, b, c, d)
```

The Bayesian information criterion of $G^2$. In absolute value above 2 it is positive evidence of a difference, above 6 strong, above 10 very strong; a value of the sign opposite to $G^2$, when $\lvert G^2 \rvert < \ln N$, means no evidence, not the opposite direction.

$$
\operatorname{sign}(G^2) \cdot (\lvert G^2 \rvert - \ln N)
$$
<!-- --8<-- [end:calc_bic] -->

</div>

<div class="metric-card" markdown>

### ELL { #ell }

`ell` · Johnston, Berry and Mielke (2006)
{ .metric-meta }

<!-- --8<-- [start:calc_ell] -->
``` {.python .signature}
calc_ell(a, b, c, d)
```

The effect size of $G^2$: the share of the greatest possible departure from the expected frequencies $E_1$ and $E_2$. It grows without bound as the least expected frequency nears one and is `nan` when that frequency is at most one (a logarithm of zero or below). The sign is negative when the word is more frequent in the reference.

$$
\frac{G^2}{N \ln \min(E_1, E_2)}
$$
<!-- --8<-- [end:calc_ell] -->

</div>

<div class="metric-card" markdown>

### Odds ratio { #odds_ratio }

`odds_ratio`
{ .metric-meta }

<!-- --8<-- [start:calc_odds_ratio] -->
``` {.python .signature}
calc_odds_ratio(a, b, c, d)
```

The ratio of the odds of the word in the two corpora: one means equal odds. A word that fills the whole target corpus gives `inf`, the whole reference 0, both `nan`.

$$
\frac{a / (c - a)}{b / (d - b)}
$$
<!-- --8<-- [end:calc_odds_ratio] -->

</div>
