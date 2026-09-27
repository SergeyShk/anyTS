# Metric functions

## Type-Token Ratio (TTR)

!!! info ""
    **anyts.diversity_stats.calc_ttr()**

<!-- --8<-- [start:calc_ttr] -->
Computation of the Type-Token Ratio (TTR).

The simplest measure of lexical diversity; it is not corrected for text length.

Formula:

$$
\frac{\textrm{Number of lexemes}}{\textrm{Number of words}}
$$

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
<!-- --8<-- [end:calc_ttr] -->

## Root Type-Token Ratio (RTTR)

!!! info ""
    **anyts.diversity_stats.calc_rttr()**

<!-- --8<-- [start:calc_rttr] -->
Computation of the Root Type-Token Ratio (RTTR).

A modification of TTR (Guiraud, 1960).

Formula:

$$
\frac{\textrm{Number of lexemes}}{\sqrt{\textrm{(Number of words)}}}
$$

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
<!-- --8<-- [end:calc_rttr] -->

## Corrected Type-Token Ratio (CTTR)

!!! info ""
    **anyts.diversity_stats.calc_cttr()**

<!-- --8<-- [start:calc_cttr] -->
Computation of the Corrected Type-Token Ratio (CTTR).

A modification of TTR (Carroll, 1964).

Formula:

$$
\frac{\textrm{Number of lexemes}}{\sqrt{2\times\textrm{(Number of words)}}}
$$

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
<!-- --8<-- [end:calc_cttr] -->

## Herdan Type-Token Ratio (HTTR)

!!! info ""
    **anyts.diversity_stats.calc_httr()**

<!-- --8<-- [start:calc_httr] -->
Computation of the Herdan Type-Token Ratio (HTTR).

A logarithmic modification of TTR (Herdan, 1960).

Formula:

$$
\frac{\log_{10} {\textrm{(Number of lexemes)}}}{\log_{10} {{\textrm{(Number of words)}}}}
$$

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
<!-- --8<-- [end:calc_httr] -->

## Summer Type-Token Ratio (STTR)

!!! info ""
    **anyts.diversity_stats.calc_sttr()**

<!-- --8<-- [start:calc_sttr] -->
Computation of the Summer Type-Token Ratio (STTR).

A logarithmic modification of TTR (Summer, 1966).

!!! note "Note"
    The value depends on the logarithm base, 10 by default. See [conventions](diversity_stats.md#conventions). The logarithm of the logarithm is undefined for a text of one lexeme or of no more words than the base, so the value is `nan` there, and so is every window of `calc_windowed` that short.

Formula:

$$
\frac{\log_{10} {\log_{10} {\textrm{(Number of lexemes)}}}}{\log_{10} {\log_{10} {{\textrm{(Number of words)}}}}}
$$

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
| `base` | float | `10` | Logarithm base |
<!-- --8<-- [end:calc_sttr] -->

## Maas Type-Token Ratio (MTTR)

!!! info ""
    **anyts.diversity_stats.calc_mttr()**

<!-- --8<-- [start:calc_mttr] -->
Computation of the Maas Type-Token Ratio (MTTR).

A logarithmic modification of TTR (Maas, 1972).

!!! note "Note"
    The value depends on the logarithm base, 10 by default. See [conventions](diversity_stats.md#conventions).

Formula:

$$
\frac{\log_{10} {\textrm{(Number of words)}}-\log_{10} {\textrm{(Number of lexemes)}}}{\log_{10} {{\textrm{(Number of words)}}}^2}
$$

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
| `base` | float | `10` | Logarithm base |
<!-- --8<-- [end:calc_mttr] -->

## Dugast Type-Token Ratio (DTTR)

!!! info ""
    **anyts.diversity_stats.calc_dttr()**

<!-- --8<-- [start:calc_dttr] -->
Computation of the Dugast Type-Token Ratio (DTTR).

A logarithmic modification of TTR (Dugast, 1978), the reciprocal of the Maas metric.

!!! note "Note"
    The value depends on the logarithm base, 10 by default. See [conventions](diversity_stats.md#conventions). A text without repeated words has an infinite value, like the other reciprocal measures.

Formula:

$$
\frac{\log_{10} {{\textrm{(Number of words)}}}^2}{\log_{10} {\textrm{(Number of words)}}-\log_{10} {\textrm{(Number of lexemes)}}}
$$

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
| `base` | float | `10` | Logarithm base |
<!-- --8<-- [end:calc_dttr] -->

## Moving Average Type-Token Ratio (MATTR)

!!! info ""
    **anyts.diversity_stats.calc_mattr()**

<!-- --8<-- [start:calc_mattr] -->
Computation of the Moving Average Type-Token Ratio (MATTR).

A moving-average modification of TTR (Covington & McFall, 2010). Independent of text length.

Algorithm:

1. Slide a fixed-size window over the text
2. Compute TTR for every window
3. Average the values

!!! note "Note"
    For texts shorter than the window the TTR of the whole text is returned.

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
| `window_len` | int | `50` | Window size |
<!-- --8<-- [end:calc_mattr] -->

## Mean Segmental Type-Token Ratio (MSTTR)

!!! info ""
    **anyts.diversity_stats.calc_msttr()**

<!-- --8<-- [start:calc_msttr] -->
Computation of the Mean Segmental Type-Token Ratio (MSTTR).

A segmentation-based modification of TTR (Johnson, 1944). Independent of text length.

Algorithm:

1. Split the text into fixed-size segments
2. Compute TTR for every segment
3. Average the values

!!! note "Note"
    For texts shorter than the segment the TTR of the whole text is returned; an incomplete last segment is dropped.

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
| `segment_len` | int | `50` | Segment size |
<!-- --8<-- [end:calc_msttr] -->

## Measure of Textual Lexical Diversity (MTLD)

!!! info ""
    **anyts.diversity_stats.calc_mtld()**

<!-- --8<-- [start:calc_mtld] -->
Computation of the Measure of Textual Lexical Diversity (MTLD).

A modification of MSTTR (McCarthy, 2005). Independent of text length.

Algorithm:

1. The text is divided into factors - stretches on which TTR drops to the threshold 0.72 inclusive (`TTR <= 0.72`, see [conventions](diversity_stats.md#conventions))
2. An incomplete factor at the end of the text counts partially, in proportion to how close its TTR came to the threshold
3. The number of words is divided by the number of factors

The refined version of the algorithm makes two passes over the text - forward and backward - and averages the values (McCarthy & Jarvis, 2010).

!!! note "Note"
    The minimum factor length is non-standard (Kyle's lexical-diversity). If no factor completes and TTR never drops below 1, infinity is returned.

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
| `min_len` | int | `10` | Minimum factor length |
| `threshold` | float | `0.72` | TTR threshold for completing a factor |
<!-- --8<-- [end:calc_mtld] -->

## Moving Average Measure of Textual Lexical Diversity (MA-MTLD)

!!! info ""
    **anyts.diversity_stats.calc_mamtld()**

<!-- --8<-- [start:calc_mamtld] -->
Computation of the Moving Average Measure of Textual Lexical Diversity (MA-MTLD).

A moving-window modification of MTLD after MTLD-MA of koRpus: a factor starts at every position of the text, the value is the mean length of completed factors over two passes, forward and backward. Factors not completed by the end of the text are ignored. The values differ from those of koRpus, which makes the forward pass only, closes a factor at TTR strictly below the threshold and drops the factors shorter than its minimum length instead of extending them to it.

!!! warning "Warning"
    If no factor completes, the function returns `nan`. The metric is unstable on short texts.

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
| `min_len` | int | `10` | Minimum factor length |
| `threshold` | float | `0.72` | TTR threshold for completing a factor |
<!-- --8<-- [end:calc_mamtld] -->

## MTLD with a moving window and text wrap (MTLD-W)

!!! info ""
    **anyts.diversity_stats.calc_mtldw()**

<!-- --8<-- [start:calc_mtldw] -->
Computation of MTLD-W (lexical-diversity `mtld_ma_wrap`, TAALED).

A modification of MA-MTLD: a factor starts at every position of the text, and factors not completed by the end of the text continue from its beginning, so all positions get equal weight. A factor cannot be longer than the text.

!!! warning "Warning"
    If TTR does not drop to the threshold even over the whole text, the function returns `nan`. The metric is unstable on texts shorter than 100 words.

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
| `min_len` | int | `10` | Minimum factor length |
| `threshold` | float | `0.72` | TTR threshold for completing a factor |
<!-- --8<-- [end:calc_mtldw] -->

## Hypergeometric Distribution D (HD-D)

!!! info ""
    **anyts.diversity_stats.calc_hdd()**

<!-- --8<-- [start:calc_hdd] -->
Computation of the Hypergeometric Distribution D (HD-D).

An alternative to vocd-D (McCarthy & Jarvis, 2010): instead of drawing random segments of the text, it computes the expected TTR of a random sample of `sample_size` words exactly. For every lexeme the hypergeometric distribution gives the probability that the sample holds it at least once; the sum of these probabilities is the expected number of lexemes in the sample, and HD-D is that number divided by the sample size. The value involves no randomness.

!!! warning "Warning"
    For texts shorter than 50 words and shorter than the sample size the metric is undefined; the function returns `nan`.

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
| `sample_size` | int | `42` | Sample size in words, 35 to 50 in the literature |
<!-- --8<-- [end:calc_hdd] -->

## Simpson's index (D)

!!! info ""
    **anyts.diversity_stats.calc_simpson_index()**

<!-- --8<-- [start:calc_simpson_index] -->
Computation of [Simpson's index](https://en.wikipedia.org/wiki/Diversity_index#Simpson_index).

The probability that two words drawn from the text at random without replacement are the same lexeme. The lower the value, the richer the vocabulary.

!!! warning "Warning"
    For texts shorter than two words the index is undefined; the function returns `nan`. The same holds for the inverse Simpson's index and the Gini-Simpson index.

Formula:

$$
\frac{\sum n\times(n-1)}{\textrm{(Number of words)}\times(\textrm{Number of words}-1)}
$$

where $n$ is the number of occurrences of a lexeme in the text.

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
<!-- --8<-- [end:calc_simpson_index] -->

## Inverse Simpson's index (1/D) { #inverse_simpson_index }

!!! info ""
    **anyts.diversity_stats.calc_inverse_simpson_index()**

<!-- --8<-- [start:calc_inverse_simpson_index] -->
Computation of the [inverse Simpson's index](https://en.wikipedia.org/wiki/Diversity_index#Inverse_Simpson_index), the Hill number of order two.

The higher the value, the richer the vocabulary.

Formula:

$$
\frac{1}{D}
$$

!!! warning "Warning"
    If all words of the text are unique, Simpson's index is 0 and the inverse index is infinity.

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
<!-- --8<-- [end:calc_inverse_simpson_index] -->

## Gini-Simpson index (1-D)

!!! info ""
    **anyts.diversity_stats.calc_gini_simpson_index()**

<!-- --8<-- [start:calc_gini_simpson_index] -->
Computation of the [Gini-Simpson index](https://en.wikipedia.org/wiki/Diversity_index#Gini–Simpson_index).

The probability that two randomly chosen words of the text are different. The higher the value, the richer the vocabulary.

Formula:

$$
1-D
$$

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
<!-- --8<-- [end:calc_gini_simpson_index] -->

## Hapax index (Honoré's R)

!!! info ""
    **anyts.diversity_stats.calc_hapax_index()**, alias **anyts.diversity_stats.calc_honore_r()**

<!-- --8<-- [start:calc_hapax_index] -->
Computation of the [hapax index](https://en.wikipedia.org/wiki/Hapax_legomenon).

!!! quote "Definition"

    A hapax (Greek ἅπαξ λεγόμενον - "said only once") is a word that occurs only once in a certain corpus of texts. For instance, *baciyelmo*, the basin-helmet of Sancho Panza, is a hapax of Cervantes (it occurs only in one chapter of *Don Quixote*).

The metric coincides with Honoré's measure (1979), with the natural logarithm.

Formula:

$$
100\times\frac{\ln {\textrm{(Number of words)}}}{1-\frac{\textrm{Number of hapaxes}}{\textrm{Number of lexemes}}}
$$

!!! warning "Warning"
    If all words of the text are hapaxes, the index is infinity. For texts shorter than two words the index is undefined; the function returns `nan`.

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
<!-- --8<-- [end:calc_hapax_index] -->

## Frequency spectrum { #frequency_spectrum }

!!! info ""
    **anyts.diversity_stats.calc_frequency_spectrum()**

<!-- --8<-- [start:calc_frequency_spectrum] -->
Computation of the frequency spectrum - the number of lexemes $V_i$ occurring exactly $i$ times in the text. The measures below are computed from it; their formulas are checked against Tweedie and Baayen (1998).

Notation: $N$ - number of words, $V$ - number of lexemes, $V_i$ - number of lexemes with frequency $i$, $V_1$ - hapaxes, $V_2$ - dis legomena, $p_k$ - relative frequency of a lexeme.

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
<!-- --8<-- [end:calc_frequency_spectrum] -->

## Yule's characteristic (Yule's K)

!!! info ""
    **anyts.diversity_stats.calc_yule_k()**

<!-- --8<-- [start:calc_yule_k] -->
Computation of Yule's characteristic (Yule, 1944). One of the few measures theoretically independent of text length (Tweedie & Baayen, 1998); in practice it converges as the text grows. The lower the value, the richer the vocabulary. Proportional to Simpson's index: $K \approx 10^4 \cdot D$.

Formula:

$$
K = 10^4\times\frac{\sum_i i^2 V_i - N}{N^2}
$$

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
<!-- --8<-- [end:calc_yule_k] -->

## Inverse Yule's characteristic (Yule's I)

!!! info ""
    **anyts.diversity_stats.calc_yule_i()**

<!-- --8<-- [start:calc_yule_i] -->
Computation of the inverse Yule's characteristic. The higher the value, the richer the vocabulary; if all words of the text are unique, the value is infinity.

Formula:

$$
I = \frac{V^2}{\sum_i i^2 V_i - V}
$$

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
<!-- --8<-- [end:calc_yule_i] -->

## Herdan's Vm

!!! info ""
    **anyts.diversity_stats.calc_herdan_vm()**

<!-- --8<-- [start:calc_herdan_vm] -->
Computation of Herdan's measure (Herdan, 1955). Theoretically independent of text length; the lower the value, the richer the vocabulary.

Formula:

$$
V_m = \sqrt{\sum_i V_i \left(\frac{i}{N}\right)^2 - \frac{1}{V}}
$$

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
<!-- --8<-- [end:calc_herdan_vm] -->

## Sichel's S

!!! info ""
    **anyts.diversity_stats.calc_sichel_s()**

<!-- --8<-- [start:calc_sichel_s] -->
Computation of Sichel's measure (Sichel, 1975) - the share of dis legomena, lexemes with frequency 2, among all lexemes. Stable across texts of different lengths.

Formula:

$$
S = \frac{V_2}{V}
$$

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
<!-- --8<-- [end:calc_sichel_s] -->

## Michéa's M

!!! info ""
    **anyts.diversity_stats.calc_michea_m()**

<!-- --8<-- [start:calc_michea_m] -->
Computation of Michéa's measure (Michéa, 1969) - the reciprocal of Sichel's measure. If the text has no dis legomena, the value is infinity.

Formula:

$$
M = \frac{V}{V_2}
$$

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
<!-- --8<-- [end:calc_michea_m] -->

## Brunet's W

!!! info ""
    **anyts.diversity_stats.calc_brunet_w()**

<!-- --8<-- [start:calc_brunet_w] -->
Computation of Brunet's measure (Brunet, 1978). Values for texts usually lie within 10-20; the lower the value, the richer the vocabulary.

Formula:

$$
W = N^{V^{-a}}, \quad a = 0.172
$$

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
| `a` | float | `0.172` | Exponent |
<!-- --8<-- [end:calc_brunet_w] -->

## Dugast's k

!!! info ""
    **anyts.diversity_stats.calc_dugast_k()**

<!-- --8<-- [start:calc_dugast_k] -->
Computation of Dugast's measure (Dugast, 1979). Not to be confused with Dugast's U - the [DTTR](#dugast-type-token-ratio-dttr) metric.

!!! note "Note"
    The value depends on the logarithm base, 10 by default. The measure is undefined when $\log N \le 1$, that is, for texts no longer than the logarithm base; in that case the function returns `nan`.

Formula:

$$
k = \frac{\log V}{\log \log N}
$$

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
| `base` | float | `10` | Logarithm base |
<!-- --8<-- [end:calc_dugast_k] -->

## Baayen's P

!!! info ""
    **anyts.diversity_stats.calc_baayen_p()**

<!-- --8<-- [start:calc_baayen_p] -->
Computation of Baayen's measure (Baayen, 1991) - the share of hapaxes among all words of the text. Equals the slope of the vocabulary growth curve at the end of the text: the probability that the next word is new (Evert, 2004).

Formula:

$$
P = \frac{V_1}{N}
$$

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
<!-- --8<-- [end:calc_baayen_p] -->

## Hapax ratio { #hapax_ratio }

!!! info ""
    **anyts.diversity_stats.calc_hapax_ratio()**

<!-- --8<-- [start:calc_hapax_ratio] -->
Computation of the share of hapaxes among all lexemes of the text.

Formula:

$$
\frac{V_1}{V}
$$

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
<!-- --8<-- [end:calc_hapax_ratio] -->

## The α₂ exponent { #alpha2 }

!!! info ""
    **anyts.diversity_stats.calc_alpha2()**

<!-- --8<-- [start:calc_alpha2] -->
Computation of the exponent $\alpha_2$ - an estimate of the Zipf-Mandelbrot parameter from the lower part of the frequency spectrum (Evert, 2004). If the text has no hapaxes, the function returns `nan`.

Formula:

$$
\alpha_2 = 1 - \frac{2 V_2}{V_1}
$$

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
<!-- --8<-- [end:calc_alpha2] -->

## Shannon entropy { #entropy }

!!! info ""
    **anyts.diversity_stats.calc_entropy()**

<!-- --8<-- [start:calc_entropy] -->
Computation of the [Shannon entropy](https://en.wikipedia.org/wiki/Diversity_index#Shannon_index) of the lexeme distribution in bits. The higher the value, the richer the vocabulary. The Hill number of order one is $2^H$ ([perplexity](#perplexity)), of order zero - $V$, of order two - the [inverse Simpson's index](#inverse_simpson_index).

Formula:

$$
H = -\sum_k p_k \log_2 p_k
$$

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
<!-- --8<-- [end:calc_entropy] -->

## Evenness { #evenness }

!!! info ""
    **anyts.diversity_stats.calc_evenness()**

<!-- --8<-- [start:calc_evenness] -->
Computation of evenness (Pielou's evenness) - the ratio of the Shannon entropy to its maximum for the given number of lexemes. Ranges from 0 to 1; for texts of a single lexeme it is undefined, the function returns `nan`.

Formula:

$$
\frac{H}{\log_2 V}
$$

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
<!-- --8<-- [end:calc_evenness] -->

## Perplexity { #perplexity }

!!! info ""
    **anyts.diversity_stats.calc_perplexity()**

<!-- --8<-- [start:calc_perplexity] -->
Computation of perplexity - the Hill number of order one, the effective number of lexemes of the text.

Formula:

$$
2^H
$$

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
<!-- --8<-- [end:calc_perplexity] -->

## Zipf's law slope { #zipf_alpha }

!!! info ""
    **anyts.diversity_stats.calc_zipf_alpha()**

<!-- --8<-- [start:calc_zipf_alpha] -->
Computation of the exponent $\alpha$ of [Zipf's law](https://en.wikipedia.org/wiki/Zipf's_law) $f(r) \propto r^{-\alpha}$, where $r$ is the frequency rank of a lexeme. Estimated by linear regression of log frequency on log rank. For natural texts $\alpha$ is close to 1.

!!! note "Note"
    The rank-based least squares estimate is biased; maximum likelihood is more accurate. For texts of a single lexeme the function returns `nan`.

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
<!-- --8<-- [end:calc_zipf_alpha] -->

## Zipf-Mandelbrot fit { #fit_zipf_mandelbrot }

!!! info ""
    **anyts.diversity_stats.fit_zipf_mandelbrot()**, **anyts.diversity_stats.ZipfMandelbrot**

<!-- --8<-- [start:fit_zipf_mandelbrot] -->
Fitting the [Zipf-Mandelbrot law](https://en.wikipedia.org/wiki/Zipf–Mandelbrot_law) $f(r) = C / (r + q)^s$ to the rank-frequency distribution. With $q = 0$ the law reduces to Zipf's law with exponent $s$; the shift $q$ describes the flattening of the curve on the most frequent words that Zipf's law does not capture. The parameters are fitted by least squares in logarithmic coordinates with the constraints $q \ge 0$, $s \ge 0$. Returns a `ZipfMandelbrot` named tuple with the fields `c`, `q`, `s` and `r2` - the coefficient of determination of the fit in logarithmic coordinates.

!!! note "Note"
    For texts of fewer than three lexemes, with identical frequencies of all lexemes and when the fit diverges all fields are `nan`. On short texts the parameters are unstable: the law describes the frequency distribution of large corpora.

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
<!-- --8<-- [end:fit_zipf_mandelbrot] -->

!!! example "Example"

    ``` python
    from anyts.diversity_stats import fit_zipf_mandelbrot

    # the frequencies 12, 6, 4, 3 follow the law f = 12 / r exactly
    words = ["a"] * 12 + ["b"] * 6 + ["c"] * 4 + ["d"] * 3
    fit = fit_zipf_mandelbrot(words)
    round(fit.c, 3), round(fit.q, 3), round(fit.s, 3), round(fit.r2, 3)
    # (12.001, 0.0, 1.0, 1.0)
    ```

## Heaps' law exponent { #heaps_beta }

!!! info ""
    **anyts.diversity_stats.calc_heaps_beta()**, **anyts.diversity_stats.fit_heaps()**, **anyts.diversity_stats.vocabulary_growth()**

<!-- --8<-- [start:calc_heaps_beta] -->
Computation of the exponent $\beta$ of [Heaps' law](https://en.wikipedia.org/wiki/Heaps'_law) $V(N) = K \cdot N^{\beta}$, which describes vocabulary growth with text length. Estimated by linear regression of log vocabulary size on log text length along the vocabulary growth curve. On corpora of millions of words $\beta$ lies within 0.4-0.6; over the growth curve of a single text it is higher (0.6-0.9), so the values are comparable only between texts of similar length.

!!! note "Note"
    The value depends on word order and needs several hundred words or more. For texts shorter than two words the function returns `nan`.

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
<!-- --8<-- [end:calc_heaps_beta] -->

<!-- --8<-- [start:vocabulary_growth] -->
`vocabulary_growth` returns the vocabulary growth curve: the vocabulary size after every word of the text.
<!-- --8<-- [end:vocabulary_growth] -->

<!-- --8<-- [start:fit_heaps] -->
`fit_heaps` fits the law over this curve and returns a `HeapsFit` named tuple with the parameters `k`, `beta` and the coefficient of determination `r2`.
<!-- --8<-- [end:fit_heaps] -->

## Windowed computation { #calc_windowed }

!!! info ""
    **anyts.diversity_stats.calc_windowed()**

<!-- --8<-- [start:calc_windowed] -->
Windowed computation of any metric: its value over consecutive text windows of equal length, the mean, the sample standard deviation and the confidence interval of the mean by Student's distribution. The standard way to compare texts of different lengths; Kubát and Milička's STTR is a windowed TTR with a 1000-word window and a 95% confidence interval. For texts shorter than the window the metric is computed over the whole text as a single window; windows with an undefined metric value (`nan`) are ignored. If the metric is infinite in at least one window (e.g. the inverse Simpson's index on a window of unique words), the mean is infinite and the standard deviation and confidence interval are undefined. Returns a `WindowStats` named tuple with the fields `mean`, `std`, `lower`, `upper` and `n_windows`.

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
| `func` | callable | `-` | Function computing the metric from a list of words |
| `window_len` | int | `100` | Window size |
| `step` | int | `None` | Window step, by default equal to the window size |
| `confidence` | float | `0.95` | Confidence level |
<!-- --8<-- [end:calc_windowed] -->
