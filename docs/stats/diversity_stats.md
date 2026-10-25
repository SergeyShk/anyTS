# Lexical diversity metrics

``` {.python .signature}
DiversityStats(words, window_len=50, mtld_threshold=0.72, mtld_min_len=10, hdd_sample_size=42, log_base=10)
```

<!-- --8<-- [start:DiversityStats] -->
The main [lexical diversity](https://en.wikipedia.org/wiki/Lexical_diversity) metrics of a text, computed from its words.
<!-- --8<-- [end:DiversityStats] -->

Raises:

- `SourceTypeError` - words that are not a sequence or an iterator of strings, and a string, a `Doc`, a set or a table;
- `SourceError` - no words;
- `ParameterError` - a parameter that `check_params` rejects.

=== "Code"

    ``` python
    from anyts import DiversityStats

    ds = DiversityStats("a b c d e b c f g h g i g j k".split())
    ds.print_stats()
    ```

=== "Result"

    ```
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
    Orlov's Z (words)                                                      |   nan
    Hapax ratio                                                            |   0.73
    Exponent α₂                                                            |   0.50
    Shannon entropy (bits)                                                 |   3.32
    Evenness                                                               |   0.96
    Perplexity                                                             |  10.01
    Zipf's law slope (α)                                                   |   0.49
    Heaps' law exponent (β)                                                |   0.84
    Burstiness of the frequent lexemes                                     |   nan
    ```

## Parameters

<!-- --8<-- [start:DiversityStats-parameters] -->
| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `words` | `Iterable[str]` | - | Words of the text: a sequence or an iterator of strings |
| `window_len` | `int` | `50` | Window size for MATTR and segment size for MSTTR (`MATTR_WINDOW_LEN`) |
| `mtld_threshold` | `float` | `0.72` | TTR threshold for MTLD, MA-MTLD and MTLD-W (`MTLD_TTR_THRESHOLD`) |
| `mtld_min_len` | `int` | `10` | Minimum factor length for MTLD, MA-MTLD and MTLD-W (`MTLD_MIN_LEN`) |
| `hdd_sample_size` | `int` | `42` | Sample size for HD-D (`HDD_SAMPLE_SIZE`) |
| `log_base` | `float` | `10` | Logarithm base for the Summer, Maas and Dugast metrics (`DIVERSITY_LOG_BASE`) |
<!-- --8<-- [end:DiversityStats-parameters] -->

<!-- --8<-- [start:DiversityStats-attributes] -->
The object keeps the words in `words`, a tuple, and the five parameters under their names, changeable on the object. `frequency_spectrum` is the frequency spectrum of the words (`calc_frequency_spectrum`), and `honore_r` an alias of `hapax_index`.
<!-- --8<-- [end:DiversityStats-attributes] -->

## Conventions { #conventions }

<!-- --8<-- [start:DiversityStats-conventions] -->
Some metrics depend on conventions that differ between libraries. All of them except the comparison with the MTLD threshold are class parameters:

| Parameter | Default | Other libraries |
| :-------- | :------ | :-------------- |
| Logarithm base for Summer, Maas, Dugast's U and Dugast's k | `10` | LexicalRichness, textcomplexity and zipfR - natural |
| MATTR window and MSTTR segment | `50` | quanteda and koRpus - 100 |
| TTR threshold for MTLD | `0.72` | 0.66-0.75 in the literature |
| Comparison with the MTLD threshold | a factor closes at TTR ≤ 0.72 (McCarthy & Jarvis, 2010) | lexical-diversity and TAALED - strict `<`; the values differ when TTR hits the threshold exactly |
| Minimum MTLD factor length | `10` | koRpus - only in MTLD-MA, dropping shorter factors instead of extending them; LexicalRichness and textcomplexity - not applied |
| HD-D sample size | `42` | 35-50 in the literature |

According to Zenker and Kyle (2021), MATTR, MTLD and HD-D are stable on texts of 50-200 words and longer, MTLD-W, MA-MTLD and Maas are unstable on short texts, and the TTR family never stabilizes. Texts of different lengths are compared by the [windowed computation](#windowed) with confidence intervals.
<!-- --8<-- [end:DiversityStats-conventions] -->

## Metrics

<!-- --8<-- [start:DiversityStats-metrics] -->
Every metric is a property of the object, computed on each access by the function of its card with the parameters of the object, and `get_stats` gives them all.

| Metric | Measures | Range | Higher means |
| :----- | :------- | :---- | :----------- |
| [`ttr`](#ttr) | Share of the lexemes among the words | 0-1 | A richer vocabulary |
| [`rttr`](#rttr) | Lexemes against the square root of the words | 0 and above | A richer vocabulary |
| [`cttr`](#cttr) | Lexemes against the square root of twice the words | 0 and above | A richer vocabulary |
| [`httr`](#httr) | Lexemes against the words in logarithms | 0-1 | A richer vocabulary |
| [`sttr`](#sttr) | Lexemes against the words in double logarithms | 1 and below, `nan` for one lexeme or a text no longer than the base | A richer vocabulary |
| [`mttr`](#mttr) | Repetition of the words in logarithms | 0 and above | A poorer vocabulary |
| [`dttr`](#dttr) | Reciprocal of the Maas metric | 0 and above, `inf` without repeated words | A richer vocabulary |
| [`mattr`](#mattr) | Mean TTR of a moving window | 0-1 | A richer vocabulary |
| [`msttr`](#msttr) | Mean TTR of consecutive segments | 0-1 | A richer vocabulary |
| [`mtld`](#mtld) | Words per factor, a stretch on which TTR drops to the threshold | Above 0, `inf` without repeated words | A richer vocabulary |
| [`mamtld`](#mamtld) | Mean length of the factors starting at every word | Up to the number of words, `nan` if no factor completes | A richer vocabulary |
| [`mtldw`](#mtldw) | Mean length of the factors starting at every word, the text wrapped | Up to the number of words, `nan` if no factor completes | A richer vocabulary |
| [`hdd`](#hdd) | Expected TTR of a random sample | 0-1, `nan` below 50 words or the sample size | A richer vocabulary |
| [`simpson_index`](#simpson_index) | Chance that two words are the same lexeme | 0-1, `nan` below two words | A poorer vocabulary |
| [`inverse_simpson_index`](#inverse_simpson_index) | Effective number of lexemes of order two | 1 and above, `inf` without repeated words, `nan` below two words | A richer vocabulary |
| [`gini_simpson_index`](#gini_simpson_index) | Chance that two words are different lexemes | 0-1, `nan` below two words | A richer vocabulary |
| [`hapax_index`](#hapax_index) | Share of the hapaxes among the lexemes against the length | 0 and above, `inf` without repeated words, `nan` below two words | A richer vocabulary |
| [`yule_k`](#yule_k) | Repetition of the words | 0-10 000, `nan` below two words | A poorer vocabulary |
| [`yule_i`](#yule_i) | Inverse of Yule's K | Above 0, `inf` without repeated words, `nan` below two words | A richer vocabulary |
| [`herdan_vm`](#herdan_vm) | Unevenness of the frequencies | 0-1, `nan` below two words | A poorer vocabulary |
| [`sichel_s`](#sichel_s) | Share of the dis legomena among the lexemes | 0-1 | More lexemes used twice |
| [`michea_m`](#michea_m) | Lexemes per dis legomenon | 1 and above, `inf` without dis legomena | Fewer lexemes used twice |
| [`brunet_w`](#brunet_w) | Words against the lexemes | 1 to the number of words | A poorer vocabulary |
| [`dugast_k`](#dugast_k) | Lexemes against the words in logarithms | 0 and above, `nan` for a text no longer than the base | A richer vocabulary |
| [`baayen_p`](#baayen_p) | Share of the hapaxes among the words | 0-1 | A faster growing vocabulary |
| [`orlov_z`](#orlov_z) | Text length in words at which the law of Zipf fits the vocabulary best | Above 0, `nan` without a solution, `inf` beyond floats | A richer vocabulary |
| [`hapax_ratio`](#hapax_ratio) | Share of the hapaxes among the lexemes | 0-1 | More lexemes used once |
| [`alpha2`](#alpha2) | Shape of the lower frequency spectrum | 1 and below, `nan` without hapaxes | More hapaxes against dis legomena |
| [`entropy`](#entropy) | Information per word in bits | 0 and above | A richer vocabulary |
| [`evenness`](#evenness) | Entropy against its maximum | 0-1, `nan` for one lexeme | More even frequencies |
| [`perplexity`](#perplexity) | Effective number of lexemes | 1 to the number of lexemes | A richer vocabulary |
| [`zipf_alpha`](#zipf_alpha) | Fall of the frequency with the rank | 0 and above, `nan` for one lexeme | Frequencies falling faster |
| [`heaps_beta`](#heaps_beta) | Growth of the vocabulary with the length | 0 and above, `nan` below two words | A faster growing vocabulary |
| [`burstiness`](#burstiness) | Mean burstiness of the lexemes of five occurrences or more | -1 to 1, `nan` without them | Words used in bursts |
<!-- --8<-- [end:DiversityStats-metrics] -->

<div class="metric-card" markdown>

### Type-Token Ratio (TTR) { #ttr }

`ttr`
{ .metric-meta }

<!-- --8<-- [start:calc_ttr] -->
``` {.python .signature}
calc_ttr(text)
```

The simplest measure of lexical diversity; it is not corrected for text length.

$$
\frac{\textrm{Number of lexemes}}{\textrm{Number of words}}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
<!-- --8<-- [end:calc_ttr] -->

</div>

<div class="metric-card" markdown>

### Root Type-Token Ratio (RTTR) { #rttr }

`rttr`
{ .metric-meta }

<!-- --8<-- [start:calc_rttr] -->
``` {.python .signature}
calc_rttr(text)
```

A modification of TTR (Guiraud, 1960).

$$
\frac{\textrm{Number of lexemes}}{\sqrt{\textrm{(Number of words)}}}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
<!-- --8<-- [end:calc_rttr] -->

</div>

<div class="metric-card" markdown>

### Corrected Type-Token Ratio (CTTR) { #cttr }

`cttr`
{ .metric-meta }

<!-- --8<-- [start:calc_cttr] -->
``` {.python .signature}
calc_cttr(text)
```

A modification of TTR (Carroll, 1964).

$$
\frac{\textrm{Number of lexemes}}{\sqrt{2\times\textrm{(Number of words)}}}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
<!-- --8<-- [end:calc_cttr] -->

</div>

<div class="metric-card" markdown>

### Herdan Type-Token Ratio (HTTR) { #httr }

`httr`
{ .metric-meta }

<!-- --8<-- [start:calc_httr] -->
``` {.python .signature}
calc_httr(text)
```

A logarithmic modification of TTR (Herdan, 1960).

$$
\frac{\log_{10} {\textrm{(Number of lexemes)}}}{\log_{10} {{\textrm{(Number of words)}}}}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
<!-- --8<-- [end:calc_httr] -->

</div>

<div class="metric-card" markdown>

### Summer Type-Token Ratio (STTR) { #sttr }

`sttr`
{ .metric-meta }

<!-- --8<-- [start:calc_sttr] -->
``` {.python .signature}
calc_sttr(text, base=10)
```

A logarithmic modification of TTR (Summer, 1966). The value depends on the logarithm base (see the [conventions](#conventions)). It is `nan` for a text of one lexeme, where the numerator is undefined, and for a text no longer than the base ($\log \log N \le 0$), including such windows of `calc_windowed`.

$$
\frac{\log_{10} {\log_{10} {\textrm{(Number of lexemes)}}}}{\log_{10} {\log_{10} {{\textrm{(Number of words)}}}}}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
| `base` | `float` | `10` | Logarithm base (`DIVERSITY_LOG_BASE`) |

A `base` that is not a finite number above 1 raises `ParameterError`.
<!-- --8<-- [end:calc_sttr] -->

</div>

<div class="metric-card" markdown>

### Maas Type-Token Ratio (MTTR) { #mttr }

`mttr`
{ .metric-meta }

<!-- --8<-- [start:calc_mttr] -->
``` {.python .signature}
calc_mttr(text, base=10)
```

A logarithmic modification of TTR (Maas, 1972). The value depends on the logarithm base (see the [conventions](#conventions)).

$$
\frac{\log_{10} {\textrm{(Number of words)}}-\log_{10} {\textrm{(Number of lexemes)}}}{\log_{10} {{\textrm{(Number of words)}}}^2}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
| `base` | `float` | `10` | Logarithm base (`DIVERSITY_LOG_BASE`) |

A `base` that is not a finite number above 1 raises `ParameterError`.
<!-- --8<-- [end:calc_mttr] -->

</div>

<div class="metric-card" markdown>

### Dugast Type-Token Ratio (DTTR) { #dttr }

`dttr`
{ .metric-meta }

<!-- --8<-- [start:calc_dttr] -->
``` {.python .signature}
calc_dttr(text, base=10)
```

A logarithmic modification of TTR (Dugast, 1978), the reciprocal of the Maas metric. The value depends on the logarithm base (see the [conventions](#conventions)). A text without repeated words has an infinite value.

$$
\frac{\log_{10} {{\textrm{(Number of words)}}}^2}{\log_{10} {\textrm{(Number of words)}}-\log_{10} {\textrm{(Number of lexemes)}}}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
| `base` | `float` | `10` | Logarithm base (`DIVERSITY_LOG_BASE`) |

A `base` that is not a finite number above 1 raises `ParameterError`.
<!-- --8<-- [end:calc_dttr] -->

</div>

<div class="metric-card" markdown>

### Moving Average Type-Token Ratio (MATTR) { #mattr }

`mattr`
{ .metric-meta }

<!-- --8<-- [start:calc_mattr] -->
``` {.python .signature}
calc_mattr(text, window_len=50)
```

A moving-average modification of TTR (Covington & McFall, 2010), independent of text length: a window of fixed size slides over the text, and the TTR of every window is averaged. For texts shorter than the window the TTR of the whole text is returned.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
| `window_len` | `int` | `50` | Window size (`MATTR_WINDOW_LEN`) |

A `window_len` that is not an integer of at least one raises `ParameterError`.
<!-- --8<-- [end:calc_mattr] -->

</div>

<div class="metric-card" markdown>

### Mean Segmental Type-Token Ratio (MSTTR) { #msttr }

`msttr`
{ .metric-meta }

<!-- --8<-- [start:calc_msttr] -->
``` {.python .signature}
calc_msttr(text, segment_len=50)
```

A segmentation-based modification of TTR (Johnson, 1944), independent of text length: the text is split into segments of fixed size, and the TTR of every segment is averaged; an incomplete last segment is dropped. For texts shorter than the segment the TTR of the whole text is returned.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
| `segment_len` | `int` | `50` | Segment size (`MATTR_WINDOW_LEN`) |

A `segment_len` that is not an integer of at least one raises `ParameterError`.
<!-- --8<-- [end:calc_msttr] -->

</div>

<div class="metric-card" markdown>

### Measure of Textual Lexical Diversity (MTLD) { #mtld }

`mtld`
{ .metric-meta }

<!-- --8<-- [start:calc_mtld] -->
``` {.python .signature}
calc_mtld(text, min_len=10, threshold=0.72)
```

A modification of MSTTR (McCarthy, 2005), independent of text length: the number of words divided by the number of factors, the stretches on which TTR drops to the threshold (`TTR <= threshold`, see the [conventions](#conventions)). An incomplete last factor counts in proportion to how close its TTR came to the threshold. The value is the mean of a forward and a backward pass (McCarthy & Jarvis, 2010). The minimum factor length is non-standard (Kyle's lexical-diversity), and a `min_len` of 0 disables it. If no factor completes and TTR never drops below 1, the value is infinity.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
| `min_len` | `int` | `10` | Minimum factor length (`MTLD_MIN_LEN`) |
| `threshold` | `float` | `0.72` | TTR threshold for completing a factor (`MTLD_TTR_THRESHOLD`) |

A `min_len` that is not a non-negative integer and a `threshold` that is not a number in (0, 1) raise `ParameterError`.
<!-- --8<-- [end:calc_mtld] -->

</div>

<div class="metric-card" markdown>

### Moving Average Measure of Textual Lexical Diversity (MA-MTLD) { #mamtld }

`mamtld`
{ .metric-meta }

<!-- --8<-- [start:calc_mamtld] -->
``` {.python .signature}
calc_mamtld(text, min_len=10, threshold=0.72, step=1)
```

A moving-window modification of MTLD after MTLD-MA of koRpus: a factor starts at every position of the text, and the value is the mean length of the completed factors over a forward and a backward pass. koRpus makes the forward pass only, closes a factor at TTR strictly below the threshold and drops factors shorter than the minimum length instead of extending them. With a `step` of k a factor starts at every k-th position from either end, as `MTLDMA.steps` of koRpus, and the computation takes about k times less. If no factor completes, the value is `nan`. The metric is unstable on short texts.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
| `min_len` | `int` | `10` | Minimum factor length (`MTLD_MIN_LEN`) |
| `threshold` | `float` | `0.72` | TTR threshold for completing a factor (`MTLD_TTR_THRESHOLD`) |
| `step` | `int` | `1` | Distance between the starts of the factors |

A `min_len` that is not a non-negative integer, a `threshold` that is not a number in (0, 1) and a `step` that is not an integer above 0 raise `ParameterError`.
<!-- --8<-- [end:calc_mamtld] -->

</div>

<div class="metric-card" markdown>

### MTLD with a moving window and text wrap (MTLD-W) { #mtldw }

`mtldw`
{ .metric-meta }

<!-- --8<-- [start:calc_mtldw] -->
``` {.python .signature}
calc_mtldw(text, min_len=10, threshold=0.72)
```

A modification of MA-MTLD after `mtld_ma_wrap` of lexical-diversity and TAALED: factors not completed by the end of the text continue from its beginning, so all positions get equal weight. A factor cannot be longer than the text. If no factor completes, because the text is shorter than `min_len` or TTR drops to the threshold from no start, the value is `nan`. The metric is unstable on texts shorter than 100 words.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
| `min_len` | `int` | `10` | Minimum factor length (`MTLD_MIN_LEN`) |
| `threshold` | `float` | `0.72` | TTR threshold for completing a factor (`MTLD_TTR_THRESHOLD`) |

A `min_len` that is not a non-negative integer and a `threshold` that is not a number in (0, 1) raise `ParameterError`.
<!-- --8<-- [end:calc_mtldw] -->

</div>

<div class="metric-card" markdown>

### Hypergeometric Distribution D (HD-D) { #hdd }

`hdd`
{ .metric-meta }

<!-- --8<-- [start:calc_hdd] -->
``` {.python .signature}
calc_hdd(text, sample_size=42)
```

An alternative to vocd-D (McCarthy & Jarvis, 2010): the exact expected TTR of a random sample of `sample_size` words, without drawing samples. The hypergeometric distribution gives the probability that the sample holds each lexeme at least once; HD-D is the sum of these probabilities divided by the sample size. For texts shorter than 50 words or than the sample size the metric is undefined, and the value is `nan`.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
| `sample_size` | `int` | `42` | Sample size in words (`HDD_SAMPLE_SIZE`) |

A `sample_size` that is not an integer of at least one raises `ParameterError`.
<!-- --8<-- [end:calc_hdd] -->

</div>

<div class="metric-card" markdown>

### Simpson's index (D) { #simpson_index }

`simpson_index` · [Wikipedia](https://en.wikipedia.org/wiki/Diversity_index#Simpson_index)
{ .metric-meta }

<!-- --8<-- [start:calc_simpson_index] -->
``` {.python .signature}
calc_simpson_index(text)
```

The probability that two words drawn from the text at random without replacement are the same lexeme; $n$ is the number of occurrences of a lexeme in the text. For texts shorter than two words the index is undefined, and the value is `nan`; the same holds for the inverse Simpson's index and the Gini-Simpson index.

$$
\frac{\sum n\times(n-1)}{\textrm{(Number of words)}\times(\textrm{Number of words}-1)}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
<!-- --8<-- [end:calc_simpson_index] -->

</div>

<div class="metric-card" markdown>

### Inverse Simpson's index (1/D) { #inverse_simpson_index }

`inverse_simpson_index` · [Wikipedia](https://en.wikipedia.org/wiki/Diversity_index#Inverse_Simpson_index)
{ .metric-meta }

<!-- --8<-- [start:calc_inverse_simpson_index] -->
``` {.python .signature}
calc_inverse_simpson_index(text)
```

An estimate of the Hill number of order two ($1/\sum_k p_k^2$) from pairs drawn without replacement. If all words of the text are unique, Simpson's index is 0 and the inverse index is infinity.

$$
\frac{1}{D}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
<!-- --8<-- [end:calc_inverse_simpson_index] -->

</div>

<div class="metric-card" markdown>

### Gini-Simpson index (1-D) { #gini_simpson_index }

`gini_simpson_index` · [Wikipedia](https://en.wikipedia.org/wiki/Diversity_index#Gini–Simpson_index)
{ .metric-meta }

<!-- --8<-- [start:calc_gini_simpson_index] -->
``` {.python .signature}
calc_gini_simpson_index(text)
```

The probability that two randomly chosen words of the text are different.

$$
1-D
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
<!-- --8<-- [end:calc_gini_simpson_index] -->

</div>

<div class="metric-card" markdown>

### Hapax index (Honoré's R) { #hapax_index }

`hapax_index` · `honore_r` · [Wikipedia](https://en.wikipedia.org/wiki/Hapax_legomenon)
{ .metric-meta }

<!-- --8<-- [start:calc_hapax_index] -->
``` {.python .signature}
calc_hapax_index(text)
```

A hapax (Greek ἅπαξ λεγόμενον - "said only once") is a word that occurs only once in a corpus: *baciyelmo*, Sancho Panza's word for the barber's basin that Don Quixote takes for a helmet, is a hapax of Cervantes (chapter 44 of the first part of *Don Quixote*). The index coincides with Honoré's measure (1979), with the natural logarithm. If all words of the text are hapaxes, the index is infinity; for texts shorter than two words it is undefined, and the value is `nan`. `calc_honore_r` is the same function.

$$
100\times\frac{\ln {\textrm{(Number of words)}}}{1-\frac{\textrm{Number of hapaxes}}{\textrm{Number of lexemes}}}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
<!-- --8<-- [end:calc_hapax_index] -->

</div>

<div class="metric-card" markdown>

### Frequency spectrum { #frequency_spectrum }

`frequency_spectrum`
{ .metric-meta }

<!-- --8<-- [start:calc_frequency_spectrum] -->
``` {.python .signature}
calc_frequency_spectrum(text)
```

The number of lexemes $V_i$ occurring exactly $i$ times in the text, as a dictionary by the frequency $i$ in ascending order. The hapax index, Yule's K and I, Herdan's Vm, Sichel's S, Michéa's M, Baayen's P, the hapax ratio and the α₂ exponent are computed from it, with the formulas of Tweedie and Baayen (1998).

Notation: $N$ - number of words, $V$ - number of lexemes, $V_i$ - number of lexemes with frequency $i$, $V_1$ - hapaxes, $V_2$ - dis legomena, $p_k$ - relative frequency of a lexeme.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
<!-- --8<-- [end:calc_frequency_spectrum] -->

</div>

<div class="metric-card" markdown>

### Yule's characteristic (Yule's K) { #yule_k }

`yule_k`
{ .metric-meta }

<!-- --8<-- [start:calc_yule_k] -->
``` {.python .signature}
calc_yule_k(text)
```

Yule's characteristic (Yule, 1944), one of the few measures theoretically independent of text length (Tweedie & Baayen, 1998); in practice it converges as the text grows. It is proportional to Simpson's index: $K \approx 10^4 \cdot D$. For texts shorter than two words the value is `nan`.

$$
K = 10^4\times\frac{\sum_i i^2 V_i - N}{N^2}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
<!-- --8<-- [end:calc_yule_k] -->

</div>

<div class="metric-card" markdown>

### Inverse Yule's characteristic (Yule's I) { #yule_i }

`yule_i`
{ .metric-meta }

<!-- --8<-- [start:calc_yule_i] -->
``` {.python .signature}
calc_yule_i(text)
```

The inverse Yule's characteristic. If all words of the text are unique, the value is infinity; for texts shorter than two words it is `nan`.

$$
I = \frac{V^2}{\sum_i i^2 V_i - V}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
<!-- --8<-- [end:calc_yule_i] -->

</div>

<div class="metric-card" markdown>

### Herdan's Vm { #herdan_vm }

`herdan_vm`
{ .metric-meta }

<!-- --8<-- [start:calc_herdan_vm] -->
``` {.python .signature}
calc_herdan_vm(text)
```

Herdan's measure (Herdan, 1955), theoretically independent of text length. For texts shorter than two words the value is `nan`.

$$
V_m = \sqrt{\sum_i V_i \left(\frac{i}{N}\right)^2 - \frac{1}{V}}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
<!-- --8<-- [end:calc_herdan_vm] -->

</div>

<div class="metric-card" markdown>

### Sichel's S { #sichel_s }

`sichel_s`
{ .metric-meta }

<!-- --8<-- [start:calc_sichel_s] -->
``` {.python .signature}
calc_sichel_s(text)
```

Sichel's measure (Sichel, 1975) - the share of dis legomena, lexemes with frequency 2, among all lexemes. Stable across texts of different lengths.

$$
S = \frac{V_2}{V}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
<!-- --8<-- [end:calc_sichel_s] -->

</div>

<div class="metric-card" markdown>

### Michéa's M { #michea_m }

`michea_m`
{ .metric-meta }

<!-- --8<-- [start:calc_michea_m] -->
``` {.python .signature}
calc_michea_m(text)
```

Michéa's measure (Michéa, 1969) - the reciprocal of Sichel's measure. If the text has no dis legomena, the value is infinity.

$$
M = \frac{V}{V_2}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
<!-- --8<-- [end:calc_michea_m] -->

</div>

<div class="metric-card" markdown>

### Brunet's W { #brunet_w }

`brunet_w`
{ .metric-meta }

<!-- --8<-- [start:calc_brunet_w] -->
``` {.python .signature}
calc_brunet_w(text, a=0.172)
```

Brunet's measure (Brunet, 1978). Values for texts usually lie within 10-20.

$$
W = N^{V^{-a}}, \quad a = 0.172
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
| `a` | `float` | `0.172` | Exponent (`BRUNET_W_EXPONENT`) |

An `a` that is not a finite number raises `ParameterError`.
<!-- --8<-- [end:calc_brunet_w] -->

</div>

<div class="metric-card" markdown>

### Dugast's k { #dugast_k }

`dugast_k`
{ .metric-meta }

<!-- --8<-- [start:calc_dugast_k] -->
``` {.python .signature}
calc_dugast_k(text, base=10)
```

Dugast's measure (Dugast, 1979), not to be confused with Dugast's U - the [DTTR](#dttr) metric. The value depends on the logarithm base. For texts no longer than the base ($\log N \le 1$) the measure is undefined, and the value is `nan`.

$$
k = \frac{\log V}{\log \log N}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
| `base` | `float` | `10` | Logarithm base (`DIVERSITY_LOG_BASE`) |

A `base` that is not a finite number above 1 raises `ParameterError`.
<!-- --8<-- [end:calc_dugast_k] -->

</div>

<div class="metric-card" markdown>

### Baayen's P { #baayen_p }

`baayen_p`
{ .metric-meta }

<!-- --8<-- [start:calc_baayen_p] -->
``` {.python .signature}
calc_baayen_p(text)
```

Baayen's measure (Baayen, 1991) - the share of hapaxes among all words of the text. It equals the slope of the vocabulary growth curve at the end of the text: the probability that the next word is new (Evert, 2004).

$$
P = \frac{V_1}{N}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
<!-- --8<-- [end:calc_baayen_p] -->

</div>

<div class="metric-card" markdown>

### Orlov's Z { #orlov_z }

`orlov_z` · [Tweedie and Baayen 1998](https://doi.org/10.1023/A:1001749303137)
{ .metric-meta }

<!-- --8<-- [start:calc_orlov_z] -->
``` {.python .signature}
calc_orlov_z(text)
```

The text length at which the law of Zipf fits the vocabulary best (Orlov 1983): the solution $Z$ for $N$ words, $V$ lexemes and the share $p$ of the most frequent lexeme. The right side has a minimum over $Z$, and $Z$ is the solution above it; it is `nan` when $V$ lies at or below that minimum or when every word is a lexeme of its own, and `inf` when $V$ comes so close to $N$ that $Z$ overflows a float. With Yule's K, Z separated the authors best among the measures Tweedie and Baayen compared.

$$
V = \frac{Z}{\ln(pZ)} \cdot \frac{N}{N - Z} \cdot \ln \frac{N}{Z}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
<!-- --8<-- [end:calc_orlov_z] -->

=== "Code"

    ``` python
    from anyts.diversity_stats import calc_orlov_z

    calc_orlov_z("the cat saw the dog and the dog saw a bird near the old tree".split())
    ```

=== "Result"

    ```
    59.99999999999961
    ```

</div>

<div class="metric-card" markdown>

### Hapax ratio { #hapax_ratio }

`hapax_ratio`
{ .metric-meta }

<!-- --8<-- [start:calc_hapax_ratio] -->
``` {.python .signature}
calc_hapax_ratio(text)
```

The share of hapaxes among all lexemes of the text.

$$
\frac{V_1}{V}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
<!-- --8<-- [end:calc_hapax_ratio] -->

</div>

<div class="metric-card" markdown>

### The α₂ exponent { #alpha2 }

`alpha2`
{ .metric-meta }

<!-- --8<-- [start:calc_alpha2] -->
``` {.python .signature}
calc_alpha2(text)
```

An estimate of the Zipf-Mandelbrot parameter from the lower part of the frequency spectrum (Evert, 2004). If the text has no hapaxes, the value is `nan`.

$$
\alpha_2 = 1 - \frac{2 V_2}{V_1}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
<!-- --8<-- [end:calc_alpha2] -->

</div>

<div class="metric-card" markdown>

### Shannon entropy { #entropy }

`entropy` · [Wikipedia](https://en.wikipedia.org/wiki/Diversity_index#Shannon_index)
{ .metric-meta }

<!-- --8<-- [start:calc_entropy] -->
``` {.python .signature}
calc_entropy(text)
```

The entropy of the lexeme distribution in bits. The Hill number of order one is $2^H$ ([perplexity](#perplexity)), of order zero - $V$; the [inverse Simpson's index](#inverse_simpson_index) estimates the one of order two.

$$
H = -\sum_k p_k \log_2 p_k
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
<!-- --8<-- [end:calc_entropy] -->

</div>

<div class="metric-card" markdown>

### Evenness { #evenness }

`evenness`
{ .metric-meta }

<!-- --8<-- [start:calc_evenness] -->
``` {.python .signature}
calc_evenness(text)
```

Pielou's evenness - the ratio of the Shannon entropy to its maximum for the given number of lexemes. For texts of a single lexeme it is undefined, and the value is `nan`.

$$
\frac{H}{\log_2 V}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
<!-- --8<-- [end:calc_evenness] -->

</div>

<div class="metric-card" markdown>

### Perplexity { #perplexity }

`perplexity`
{ .metric-meta }

<!-- --8<-- [start:calc_perplexity] -->
``` {.python .signature}
calc_perplexity(text)
```

The Hill number of order one, the effective number of lexemes of the text.

$$
2^H
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
<!-- --8<-- [end:calc_perplexity] -->

</div>

<div class="metric-card" markdown>

### Zipf's law slope { #zipf_alpha }

`zipf_alpha` · [Wikipedia](https://en.wikipedia.org/wiki/Zipf's_law)
{ .metric-meta }

<!-- --8<-- [start:calc_zipf_alpha] -->
``` {.python .signature}
calc_zipf_alpha(text)
```

The exponent $\alpha$ of Zipf's law $f(r) \propto r^{-\alpha}$, where $r$ is the frequency rank of a lexeme, estimated by linear regression of log frequency on log rank. For natural texts $\alpha$ is close to 1. The rank-based least squares estimate is biased; maximum likelihood is more accurate. For texts of a single lexeme the value is `nan`.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
<!-- --8<-- [end:calc_zipf_alpha] -->

</div>

<div class="metric-card" markdown>

### Zipf-Mandelbrot fit { #fit_zipf_mandelbrot }

[Wikipedia](https://en.wikipedia.org/wiki/Zipf–Mandelbrot_law)
{ .metric-meta }

<!-- --8<-- [start:fit_zipf_mandelbrot] -->
``` {.python .signature}
fit_zipf_mandelbrot(text)
```

Fits the Zipf-Mandelbrot law $f(r) = C / (r + q)^s$ to the rank-frequency distribution. With $q = 0$ it is Zipf's law with exponent $s$; the shift $q$ captures the flattening of the curve on the most frequent words. The fit is by least squares in logarithmic coordinates with $q \ge 0$, $s \ge 0$; the lexemes of zero frequency in a counter are left out. The result is a `ZipfMandelbrot` named tuple with the fields `c`, `q`, `s` and `r2` - the coefficient of determination of the fit in logarithmic coordinates. All fields are `nan` for texts of fewer than three lexemes, with identical frequencies of all lexemes or when the fit diverges. The parameters are unstable on short texts: the law describes large corpora.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` / `Counter` | - | List of words or a counter of their frequencies |

A counter whose words are not strings or whose frequencies are not numbers raises `SourceTypeError`, and a negative, `nan` or infinite frequency `SourceError` (`check_counts`).
<!-- --8<-- [end:fit_zipf_mandelbrot] -->

=== "Code"

    ``` python
    from anyts.diversity_stats import fit_zipf_mandelbrot

    # the frequencies 12, 6, 4, 3 follow the law f = 12 / r exactly
    words = ["a"] * 12 + ["b"] * 6 + ["c"] * 4 + ["d"] * 3
    fit = fit_zipf_mandelbrot(words)
    round(fit.c, 3), round(fit.q, 3), round(fit.s, 3), round(fit.r2, 3)
    ```

=== "Result"

    ```
    (12.001, 0.0, 1.0, 1.0)
    ```

</div>

<div class="metric-card" markdown>

### Heaps' law exponent { #heaps_beta }

`heaps_beta` · [Wikipedia](https://en.wikipedia.org/wiki/Heaps'_law)
{ .metric-meta }

<!-- --8<-- [start:calc_heaps_beta] -->
``` {.python .signature}
calc_heaps_beta(text)
```

The exponent $\beta$ of Heaps' law $V(N) = K \cdot N^{\beta}$ of vocabulary growth with text length, estimated by linear regression of log vocabulary size on log text length along the growth curve. On corpora of millions of words $\beta$ lies within 0.4-0.6, on a single text within 0.6-0.9, so the values are comparable only between texts of similar length. The value depends on word order and needs several hundred words or more. For texts shorter than two words the value is `nan`.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
<!-- --8<-- [end:calc_heaps_beta] -->

<!-- --8<-- [start:vocabulary_growth] -->
``` {.python .signature}
vocabulary_growth(text)
```

The vocabulary growth curve of a list of words: the vocabulary size after every word of the text.
<!-- --8<-- [end:vocabulary_growth] -->

<!-- --8<-- [start:fit_heaps] -->
``` {.python .signature}
fit_heaps(text)
```

Fits Heaps' law over the vocabulary growth curve of a list of words, as `calc_heaps_beta` does, and returns a `HeapsFit` named tuple with the parameters `k`, `beta` and the coefficient of determination `r2`, all `nan` for texts shorter than two words; `r2` is `nan` for a text of one lexeme too.
<!-- --8<-- [end:fit_heaps] -->

</div>

<div class="metric-card" markdown>

### Burstiness { #burstiness }

`burstiness` · [Kim and Jo 2016](https://doi.org/10.1103/PhysRevE.94.032311)
{ .metric-meta }

<!-- --8<-- [start:calc_burstiness] -->
``` {.python .signature}
calc_burstiness(text, min_freq=5)
```

How a lexeme comes in bursts rather than spread over the text, by the burstiness of Kim and Jo, which corrects that of Goh and Barabási for a finite number $n$ of events, averaged over the lexemes of `min_freq` occurrences or more (`BURSTINESS_MIN_FREQ`). For the $n$ occurrences of a lexeme, $r$ is the coefficient of variation of their $n$ intervals, the one from the last to the first around the end of the text included. The value is −1 for occurrences at equal intervals, the one around the end included (*a x a x* is −1, *a x a x a* about −0.69), near 0 for a rare lexeme at random places and up to 1 for occurrences in bursts; `nan` without such lexemes.

$$
A_n = \frac{\sqrt{n + 1} \cdot r - \sqrt{n - 1}}{(\sqrt{n + 1} - 2) \cdot r + \sqrt{n - 1}}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
| `min_freq` | `int` | `5` | Smallest number of occurrences of a lexeme measured |

A `min_freq` that is not an integer of at least 2 raises `ParameterError`.
<!-- --8<-- [end:calc_burstiness] -->

=== "Code"

    ``` python
    from anyts.diversity_stats import calc_burstiness

    calc_burstiness("a x a x a x a x a x".split()), calc_burstiness("a a a a a x x x x x".split())
    ```

=== "Result"

    ```
    (-1.0, 0.18350341907227388)
    ```

</div>

<div class="metric-card" markdown>

### Windowed computation { #windowed }

`windowed(stat)`
{ .metric-meta }

``` {.python .signature}
calc_windowed(text, func, window_len=100, step=None, confidence=0.95, *, messages=MESSAGES)
```

<!-- --8<-- [start:calc_windowed] -->
The values of a metric over consecutive windows of equal length give their mean, their sample standard deviation and the confidence interval of the mean by Student's distribution. The standard way to compare texts of different lengths; Kubát and Milička's standardized TTR (not Summer's STTR) is a windowed TTR with a 1000-word window and a 95% interval. A text shorter than the window is a single window; `nan` windows are ignored. With fewer than two windows of a defined value the deviation and the interval are `nan`, and without any the mean too. A metric infinite in any window (e.g. the inverse Simpson's index on a window of unique words) makes the mean infinite and the deviation and the interval `nan`. The result is a `WindowStats` named tuple with the fields `mean`, `std`, `lower`, `upper` and `n_windows`, the number of the windows of a defined value.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
| `func` | `Callable` | - | Function computing the metric from a list of words |
| `window_len` | `int` | `100` | Window size |
| `step` | `int` | `None` | Window step; the window size by default, so the windows do not overlap |
| `confidence` | `float` | `0.95` | Confidence level |
| `messages` | `dict[str, str]` | `MESSAGES` | Messages of the errors by key |

A `func` that cannot be called raises `SourceTypeError`; a `window_len` or a `step` that is not an integer of at least one and a `confidence` that is not a number in (0, 1) raise `ParameterError`.
<!-- --8<-- [end:calc_windowed] -->

</div>

<!-- --8<-- [start:diversity-checks] -->
Every function checks its words with `check_words`: a `text` that is a string, a `Doc`, an iterator, a set or a table, or whose words are not strings, raises `SourceTypeError`; `fit_zipf_mandelbrot` takes a counter too.
<!-- --8<-- [end:diversity-checks] -->

## Methods

<!-- --8<-- [start:DiversityStats-windowed] -->
`windowed(stat, window_len=100, step=None, confidence=0.95)` computes a metric of `get_stats` by its name over windows: `calc_windowed` with the function of the metric and the parameters of the object. The other arguments, the result and the errors are those of `calc_windowed`; an unknown name raises `UnknownStatError`.
<!-- --8<-- [end:DiversityStats-windowed] -->

=== "Code"

    ``` python
    ds.windowed("ttr", window_len=5)
    ds.windowed("ttr", window_len=5, step=2).n_windows
    ```

=== "Result"

    ```
    WindowStats(mean=0.9333333333333332, std=0.11547005383792512, lower=0.6464898180167025, upper=1.220176848649964, n_windows=3)
    6
    ```

<!-- --8<-- [start:DiversityStats-get_stats] -->
`get_stats()` returns a dictionary of the computed metrics of `stats_desc`.
<!-- --8<-- [end:DiversityStats-get_stats] -->

<!-- --8<-- [start:DiversityStats-print_stats] -->
`print_stats()` prints a table of the computed metrics with their descriptions of `stats_desc` under the headers of `stats_headers`.
<!-- --8<-- [end:DiversityStats-print_stats] -->

The frame of the metrics (`to_dataframe`) and their reading (`describe`) are those of the [statistics interface](stats.md).

## For library developers { #hooks }

<details class="library-hooks" markdown>
<summary>Language hooks of a subclass</summary>

<!-- --8<-- [start:DiversityStats-hooks] -->
A language library subclasses `DiversityStats`. The class takes the words as given: the library extracts them from its sources (a string, a [spaCy](https://github.com/explosion/spaCy) `Doc`) and lower-cases them, since every metric counts lexemes.

| Hook | Kind | Description |
| :--- | :--- | :---------- |
| `stats_desc` | class attribute | Metrics of `get_stats` with their descriptions for `print_stats`; `anyts.constants.DIVERSITY_STATS_DESC` by default |
| `stats_headers` | class attribute | The two headers of the columns of `print_stats`; `("Metric", "Value")` by default |
| `messages` | class attribute | Messages of the errors by key; `MESSAGES` by default |
<!-- --8<-- [end:DiversityStats-hooks] -->

``` {.python .signature}
check_params(window_len=50, mtld_threshold=0.72, mtld_min_len=10, hdd_sample_size=42, log_base=10, *, messages=MESSAGES)
```

<!-- --8<-- [start:check_params] -->
Checks the parameters of the metrics: a `window_len` or an `hdd_sample_size` that is not an integer of at least one, an `mtld_min_len` that is not a non-negative integer, an `mtld_threshold` that is not a number in (0, 1) and a `log_base` that is not a finite number above 1 raise `ParameterError`. Called before the words are extracted, it reports a wrong parameter before an empty text.
<!-- --8<-- [end:check_params] -->

</details>
