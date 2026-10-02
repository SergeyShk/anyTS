# Keywords

!!! info ""
    **anyts.corpus.keyness()**, **anyts.corpus.check_keyness_params()**, **anyts.corpus.Keyword**, **anyts.corpus.FrequencyReference**

## Description

<!-- --8<-- [start:keyness] -->
Keyword extraction (keyness) for a target corpus against a reference one: the words that occur significantly more often in the target corpus than in the reference.

For every word two values are computed that [Gabrielatos and Marchi](http://eprints.lancs.ac.uk/51449/4/Gabrielatos_Marchi_Keyness.pdf) and [Hardie](http://cass.lancs.ac.uk/log-ratio-an-informal-introduction/) recommend reading together: the log-likelihood $G^2$ with its p-value (the significance of the difference - whether there is one) and Log Ratio (the size of the effect - how large it is). The chosen measure `score` is computed as well and used for the sorting. The measures of significance ($G^2$, chi-square, BIC) and ELL, the effect size of $G^2$, are signed: negative when the word is more frequent in the reference; the other measures of effect (%DIFF, Log Ratio, odds ratio) are directional by construction.

The reference may be a list of words, a mapping of frequencies (its size is the sum of the counts) or a `FrequencyReference`. Words are compared as they are: case, lemmatization and stop words belong to the word extractor, and both corpora have to be extracted the same way.
<!-- --8<-- [end:keyness] -->

## Measures

<!-- --8<-- [start:keyness-measures] -->
For a word of frequency $a$ in a target corpus of size $c$ and of frequency $b$ in a reference corpus of size $d$, $N = c + d$:

| Measure | Key | Formula | Description |
| :------ | :-- | :------ | :---------- |
| Log-likelihood | `log_likelihood` | $G^2 = 2\,(a \ln \frac{a}{E_1} + b \ln \frac{b}{E_2})$, $E_1 = \frac{c\,(a+b)}{N}$, $E_2 = \frac{d\,(a+b)}{N}$ | [Rayson and Garside (2000)](https://ucrel.lancs.ac.uk/llwizard.html); critical values `anyts.constants.G2_CRITICAL_VALUES`: 3.84 for p < 0.05, 6.63 for p < 0.01, 10.83 for p < 0.001, 15.13 for p < 0.0001 |
| Chi-square | `chi2` | $\chi^2 = \frac{N\,\max(\lvert a(d-b) - b(c-a) \rvert - N/2,\ 0)^2}{(a+b)(N-a-b)\,c\,d}$ | with Yates's correction over the 2×2 contingency table; when the correction exceeds the difference, the statistic is zero |
| %DIFF | `diff` | $\frac{NF_a - NF_b}{NF_b} \cdot 100$ | [Gabrielatos and Marchi (2011)](http://eprints.lancs.ac.uk/51449/4/Gabrielatos_Marchi_Keyness.pdf); $NF$ - frequency per million words |
| Log Ratio | `log_ratio` | $\log_2 \frac{NF_a}{NF_b}$ | [Hardie (2014)](http://cass.lancs.ac.uk/log-ratio-an-informal-introduction/); one means the word is twice as frequent in the target corpus |
| BIC | `bic` | $\operatorname{sign}(G^2) \cdot (\lvert G^2 \rvert - \ln N)$ | Wilson (2013); in absolute value above 2 - positive evidence of a difference, above 6 - strong, above 10 - very strong; a negative value with $\lvert G^2 \rvert < \ln N$ means no evidence, not the opposite direction |
| ELL | `ell` | $\frac{G^2}{N \ln \min(E_1, E_2)}$ | Johnston, Berry and Mielke (2006); size of the effect of $G^2$, the share of the greatest possible departure from the expected frequencies, from 0 to 1; `nan` when the least expected frequency is at most one - then the logarithm is zero or negative; just above one the measure grows without bound |
| Odds ratio | `odds_ratio` | $\frac{a / (c - a)}{b / (d - b)}$ | one means equal odds; `inf` if the word fills the whole target corpus, 0 - the whole reference |

A zero frequency in one of the corpora is replaced with 0.5 for %DIFF, Log Ratio and the odds ratio (Hardie 2014). The p-value of $G^2$ comes from the chi-square distribution with one degree of freedom (`calc_p_value`). The measures are available as the functions `calc_log_likelihood`, `calc_chi2`, `calc_diff`, `calc_log_ratio`, `calc_bic`, `calc_ell` and `calc_odds_ratio` with the arguments `(a, b, c, d)` of the module `anyts.corpus.keyness`; their names and descriptions are in `anyts.constants.KEYNESS_MEASURES`.
<!-- --8<-- [end:keyness-measures] -->

## Parameters

<!-- --8<-- [start:keyness-parameters] -->
| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `target` | list[str]/dict[str, int] | `-` | Words of the target corpus or their frequencies |
| `reference` | list[str]/dict[str, float]/FrequencyReference | `-` | Words of the reference corpus, their frequencies or a reference by frequencies |
| `measure` | str | `log_likelihood` | Measure of `anyts.constants.KEYNESS_MEASURES` for `score` and the sorting |
| `min_freq` | int | `1` | Minimum frequency of a keyword in its own corpus |
| `positive` | bool | `True` | Positive keywords (more frequent in the target corpus) or negative ones (more frequent in the reference) |
| `top_n` | int | `None` | Number of keywords; `None` - all of them |
<!-- --8<-- [end:keyness-parameters] -->

<!-- --8<-- [start:check_keyness_params] -->
`check_keyness_params(measure="log_likelihood", min_freq=1, top_n=None)` checks the parameters of `keyness` and raises `ParameterError` unless the measure is one of `KEYNESS_MEASURES`, the minimum frequency is an integer and the number of keywords is `None` or an integer of at least one. A library that builds the reference from a frequency dictionary calls it first, so that a wrong parameter fails before the dictionary is read.
<!-- --8<-- [end:check_keyness_params] -->

## Reference by frequencies

<!-- --8<-- [start:FrequencyReference] -->
`FrequencyReference(counts, size, missing=0.0, key=None, keep=None)` describes a reference corpus by its frequencies alone, such as a frequency dictionary built from a corpus too large to pass as words:

| Field | Type | Default | Description |
| :---: | :--: | :-----: | :---------- |
| `counts` | dict[str, float] | `-` | Frequencies of the keys in the reference corpus |
| `size` | float | `-` | Size of the reference corpus in words |
| `missing` | float | `0.0` | Frequency of a key missing from `counts` |
| `key` | callable | `None` | Key of a word of the target corpus in `counts`, such as its lemma; `None` - the word itself |
| `keep` | callable | `None` | Whether a word of the target corpus is counted; `None` - every word |

The words of the target that `keep` passes are counted under their `key`, and the words it leaves out do not count in the size of the target either; negative keywords come only from the keys of `counts` that `keep` passes. The frequency of a key missing from `counts` is `missing`: a dictionary gives its least frequency, an upper bound of the true one, so such a word may be a positive keyword but never a negative one.
<!-- --8<-- [end:FrequencyReference] -->

## Result

<!-- --8<-- [start:Keyword] -->
A list of `Keyword` named tuples by descending keyness (ties broken by descending frequency and alphabetically, words of an undefined measure last); `pd.DataFrame(keywords)` gives a table.

| Field | Type | Description |
| :---: | :--: | :---------- |
| `word` | str | Word |
| `freq_target` | int | Frequency in the target corpus |
| `freq_reference` | float | Frequency in the reference corpus |
| `ipm_target` | float | Frequency in the target corpus per million words |
| `ipm_reference` | float | Frequency in the reference corpus per million words |
| `g2` | float | Signed $G^2$ |
| `p_value` | float | p-value of $G^2$ |
| `log_ratio` | float | Log Ratio |
| `score` | float | Value of the chosen measure |
<!-- --8<-- [end:Keyword] -->

## Example

!!! example "Example"

    ``` python
    from anyts import WordsExtractor
    from anyts.corpus import FrequencyReference, keyness

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
    # [('at', 3, 3.1), ('birds', 3, 3.1), ('cat', 3, 3.1)]

    [(k.word, round(k.g2, 2)) for k in keyness(target, reference, positive=False, top_n=2)]
    # [('dog', -5.45), ('slept', -3.63)]

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
    # [('bird', 40.0), ('cat', 38.7), ('window', 37.6)]
    ```
