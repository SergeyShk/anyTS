# Stylometry

<!-- --8<-- [start:stylometry] -->
Measures of stylometry and authorship attribution: distances between texts by the frequencies of the most frequent words (Burrows's Delta and its variants, as in [stylo](https://github.com/computationalstylistics/stylo)) and along a text by its windows (rolling Delta), markers of preferred and avoided words (Zeta) and their shares in the segments of corpora, Kilgarriff's chi-square distance between corpora and the Mendenhall curve. The functions work on lists of units of a text: lower-case word forms (the usual choice for Delta), lemmas or character N-grams - case and lemmatization belong to the extractors.
<!-- --8<-- [end:stylometry] -->

## Burrows's Delta { #delta }

<!-- --8<-- [start:frequency_table] -->
``` {.python .signature}
frequency_table(corpus, n_mfw=100, culling=0.0)
```

Builds the table of relative frequencies of a corpus, a dictionary "name of a text → units": rows are the texts, columns the `n_mfw` most frequent units by descending mean relative frequency (alphabetically when equal); `culling` keeps the units that occur in at least the given share of the texts, as in stylo.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `corpus` | `dict[str, list[str]]` | - | Units of the texts by the names of the texts |
| `n_mfw` | `int` | `100` | Number of the most frequent units; `None` - all of them |
| `culling` | `float` | `0.0` | Smallest share of the texts a unit occurs in |

A corpus that is not a mapping of lists of strings raises `SourceTypeError`; an empty corpus, a text without units and no unit left after culling raise `SourceError`, and an `n_mfw` that is not an integer of at least one and a `culling` that is not a number within [0, 1] `ParameterError`.
<!-- --8<-- [end:frequency_table] -->

<!-- --8<-- [start:z_scores] -->
``` {.python .signature}
z_scores(table)
```

Standardizes the columns of a table of frequencies with the sample standard deviation, like `scale()` of R; a column with the same frequency in every text gives zeros.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `table` | `DataFrame` | - | Table of relative frequencies |
<!-- --8<-- [end:z_scores] -->

<!-- --8<-- [start:delta] -->
``` {.python .signature}
delta(corpus, n_mfw=100, variant='burrows', culling=0.0)
```

Computes a symmetric matrix of distances from the z-scores (a `DataFrame` with the names of the texts); at least three texts are needed - with two, the z-scores degenerate to ±1/√2 and the distances do not depend on the frequencies.

The variants (`anyts.constants.DELTA_VARIANTS`), with the formulas of the sources of stylo; $n$ is the number of units, $z_A$ and $z_B$ the vectors of z-scores of the texts:

| Variant | Key | Formula | Source |
| :------ | :-- | :------ | :----- |
| Burrows's Delta | `burrows` | $\frac{1}{n} \sum_i \lvert z_{A,i} - z_{B,i} \rvert$ | Burrows (2002), `dist.delta` |
| Quadratic Delta | `quadratic` | $\frac{1}{n} \sqrt{\sum_i (z_{A,i} - z_{B,i})^2}$ | Argamon (2008), `dist.argamon` |
| Eder's Delta | `eder` | $\sum_i \frac{n - i + 2}{n} \lvert z_{A,i} - z_{B,i} \rvert$, $i$ - rank of the unit by frequency | Eder, `dist.eder` |
| Cosine Delta | `cosine` | $1 - \frac{z_A \cdot z_B}{\lVert z_A \rVert \lVert z_B \rVert}$ | Smith and Aldridge (2011), [Evert et al. (2015)](https://aclanthology.org/W15-0709.pdf), `dist.wurzburg` |

Cosine Delta clusters the texts by author best in the experiments of Evert et al. The usual number of units is 100 to 500 most frequent words, 100-200 for character N-grams.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `corpus` | `dict[str, list[str]]` | - | Units of the texts by the names of the texts |
| `n_mfw` | `int` | `100` | Number of the most frequent units; `None` - all of them |
| `variant` | `str` | `'burrows'` | Variant of Delta of `anyts.constants.DELTA_VARIANTS` |
| `culling` | `float` | `0.0` | Smallest share of the texts a unit occurs in |

The corpus, `n_mfw` and `culling` raise the errors of `frequency_table`; fewer than three texts raise `SourceError`, and an unknown variant `ParameterError`.
<!-- --8<-- [end:delta] -->

<!-- --8<-- [start:delta_profiles] -->
``` {.python .signature}
delta_profiles(reference, samples, n_mfw=100, variant='burrows', culling=0.0, statistics=None)
```

Distances by Delta for authorship attribution. The most frequent units, the culling and the statistics of the z-scores come from the reference texts (the profiles of the authors) or from a separate set `statistics`, such as training windows when the profiles are too few to estimate the spread of the frequencies; the texts under test `samples` get the same units and scaling. The result is the distances from the samples (rows) to the references (columns); the nearest reference is the presumed author. Unlike in `delta`, a sample affects neither the units nor the scaling, so its result does not depend on the other samples.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `reference` | `dict[str, list[str]]` | - | Units of the reference texts by the names of the texts |
| `samples` | `dict[str, list[str]]` | - | Units of the texts under test by the names of the texts |
| `n_mfw` | `int` | `100` | Number of the most frequent units; `None` - all of them |
| `variant` | `str` | `'burrows'` | Variant of Delta of `anyts.constants.DELTA_VARIANTS` |
| `culling` | `float` | `0.0` | Smallest share of the texts a unit occurs in |
| `statistics` | `dict[str, list[str]]` | `None` | Texts of the units and of the statistics of the scaling; `None` - the reference texts |

The corpora, `n_mfw` and `culling` raise the errors of `frequency_table`; fewer than three texts for the statistics raise `SourceError`, and an unknown variant `ParameterError`.
<!-- --8<-- [end:delta_profiles] -->

=== "Code"

    ``` python
    from anyts import WordsExtractor
    from anyts.corpus import delta, delta_profiles, frequency_table

    texts = {
        "A": (
            "The cat was at the window and watched the birds. "
            "The birds flew away and the cat slept at the window."
        ),
        "B": "The dog was on the floor and slept. Then the dog ate and slept again on the floor.",
        "C": "Tomorrow the cat will come back to the window and watch the birds, but the dog will sleep.",
    }
    we = WordsExtractor(lowercase=True)
    corpus = {name: we.extract(text) for name, text in texts.items()}

    frequency_table(corpus, n_mfw=5).round(3)
    delta(corpus, n_mfw=5).round(3)
    delta(corpus, n_mfw=5, variant="cosine").round(3)

    sample = {"?": we.extract("The cat woke up at the window and watched the birds again.")}
    delta_profiles(corpus, sample, n_mfw=5).round(3)
    ```

=== "Result"

    ```
         the    and    dog  slept  birds
    A  0.286  0.095  0.000  0.048  0.095
    B  0.222  0.111  0.111  0.111  0.000
    C  0.222  0.056  0.056  0.000  0.056

           A      B      C
    A  0.000  1.483  1.161
    B  1.483  0.000  1.219
    C  1.161  1.219  0.000

           A      B      C
    A  0.000  1.676  1.273
    B  1.676  0.000  1.525
    C  1.273  1.525  0.000

           A      B      C
    ?  0.499  1.493  0.662
    ```

## Rolling Delta { #rolling_delta }

<!-- --8<-- [start:rolling_delta] -->
``` {.python .signature}
rolling_delta(reference, text, window=5000, step=1000, n_mfw=100, variant='burrows', culling=0.0)
```

Delta along a text, after `rolling.delta` of stylo: the reference texts and the text under test are cut into windows of `window` units every `step` units, the rest shorter than a window dropped. The most frequent units, the culling and the statistics of the z-scores come from the windows of the reference texts, and every window of the text is compared by the variant of Delta with the centroid of the windows of every reference text. The result is the distances from the windows (rows, by the position of their middle in units) to the references (columns); where the nearest reference changes along the text, so does the style - another author of a part of a text written together, a borrowed passage. Unlike stylo, which sums the differences of the raw frequencies, the distances are those of `delta_profiles` over z-scores.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `reference` | `dict[str, list[str]]` | - | Units of the reference texts by the names of the texts |
| `text` | `list[str]` | - | Units of the text under test |
| `window` | `int` | `5000` | Size of a window in units |
| `step` | `int` | `1000` | Distance between the starts of the windows in units |
| `n_mfw` | `int` | `100` | Number of the most frequent units; `None` - all of them |
| `variant` | `str` | `'burrows'` | Variant of Delta of `anyts.constants.DELTA_VARIANTS` |
| `culling` | `float` | `0.0` | Smallest share of the windows of the reference texts a unit occurs in |

A reference corpus that is not a mapping of lists of strings and units of the text that are not a list of strings raise `SourceTypeError`; fewer than two reference texts, a text without units or shorter than a window and fewer than three windows of the reference texts raise `SourceError`. An unknown variant, a `window` or a `step` that is not an integer of at least one, a `step` greater than the window and the `n_mfw` and `culling` that `frequency_table` refuses raise `ParameterError`.
<!-- --8<-- [end:rolling_delta] -->

=== "Code"

    ``` python
    from anyts.corpus import rolling_delta

    rolling_delta(corpus, corpus["A"] + corpus["B"], window=10, step=5, n_mfw=10).round(3)
    ```

=== "Result"

    ```
            A      B      C
    5   0.527  1.337  0.633
    10  0.744  1.155  0.970
    15  0.563  1.227  1.152
    20  1.111  1.077  1.170
    25  1.079  0.353  0.760
    30  1.337  0.166  1.279
    ```

## Zeta { #zeta }

<!-- --8<-- [start:zeta] -->
``` {.python .signature}
zeta(target, comparison, segment_size=2000, top_n=None)
```

Markers of preferred and avoided words after Burrows (2007) and Craig and Kinney (2009). Every text of both corpora is split into segments of about `segment_size` words (the length over the size rounded half up, at least one segment); $DP$ is the share of the segments of a corpus with the word. Zeta is $DP_{target} - DP_{comparison}$, from −1 to 1 (`zeta.craig` in stylo; the classic Zeta of Craig, $DP_{target} + (1 - DP_{comparison})$, is greater by one); the logarithmic Zeta is $\log_2 \frac{DP_{target}}{DP_{comparison}}$ ([Schöch et al. 2018](https://zeta-project.eu/en/keyness-measures/burrows-zeta-logarithmic-zeta/)), a zero share replaced by half a segment. The list goes from the words the target corpus prefers to those it avoids.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `target` | `list[str]` / `list[list[str]]` | - | Words of the target corpus - one text or a list of texts |
| `comparison` | `list[str]` / `list[list[str]]` | - | Words of the comparison corpus |
| `segment_size` | `int` | `2000` | Size of a segment in words |
| `top_n` | `int` | `None` | Number of words from the start of the list; `None` - all of them |

The result is a list of `ZetaScore(word, dp_target, dp_comparison, zeta, log_zeta)` named tuples by descending Zeta, by descending logarithmic Zeta and alphabetically when equal. A corpus that is neither a list of strings nor a list of such lists raises `SourceTypeError`, and a corpus without words `SourceError`; a `segment_size` or a `top_n` that is not an integer of at least one raises `ParameterError`.
<!-- --8<-- [end:zeta] -->

=== "Code"

    ``` python
    from anyts.corpus import zeta

    zeta(corpus["A"], corpus["B"], segment_size=5, top_n=2)
    zeta(corpus["A"], corpus["B"], segment_size=5)[-1]
    ```

=== "Result"

    ```
    [ZetaScore(word='at', dp_target=0.5, dp_comparison=0.0, zeta=0.5, log_zeta=2.0), ZetaScore(word='birds', dp_target=0.5, dp_comparison=0.0, zeta=0.5, log_zeta=2.0)]
    ZetaScore(word='on', dp_target=0.0, dp_comparison=0.5, zeta=-0.5, log_zeta=-2.0)
    ```

<!-- --8<-- [start:zeta_segments] -->
``` {.python .signature}
zeta_segments(corpora, preferred, avoided, segment_size=2000)
```

The shares of the markers of Zeta in the segments of corpora, as `oppose` of stylo places the segments: every text is split into segments as in `zeta`, and a segment gets the shares of the words of the lists `preferred` and `avoided` found in it. With the markers of a target corpus against a comparison corpus, the segments of the target lie high on the left of the plane of the two shares and those of the comparison low on the right; the segments of a disputed text show which group it is near (`zeta_scatter_plot`).

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `corpora` | `dict[str, list[str] / list[list[str]]]` | - | Words of the corpora by name - one text or a list of texts each |
| `preferred` | `Collection[str]` | - | Words the target corpus prefers - the start of the list of `zeta` |
| `avoided` | `Collection[str]` | - | Words the target corpus avoids - the end of the list |
| `segment_size` | `int` | `2000` | Size of a segment in words |

The result is a `DataFrame` of the segments in the order of the corpora and of their texts, with the columns `corpus` (the name of the corpus), `preferred` and `avoided` (the shares of the lists). Corpora that are not a mapping and a corpus or a list of markers that is not a list of strings raise `SourceTypeError`; no corpora, an empty list of markers and a corpus without words `SourceError`, and a `segment_size` that is not an integer of at least one `ParameterError`.
<!-- --8<-- [end:zeta_segments] -->

=== "Code"

    ``` python
    from anyts.corpus import zeta_segments

    scores = zeta(corpus["A"], corpus["B"], segment_size=5)
    preferred = [score.word for score in scores if score.zeta > 0]
    avoided = [score.word for score in scores if score.zeta < 0]
    zeta_segments(corpus, preferred, avoided, segment_size=5).round(3)
    ```

=== "Result"

    ```
       corpus  preferred  avoided
    0       A      0.500    0.000
    1       A      0.375    0.000
    2       A      0.500    0.000
    3       A      0.500    0.143
    4       B      0.125    0.286
    5       B      0.125    0.429
    6       B      0.000    0.429
    7       B      0.125    0.429
    8       C      0.250    0.000
    9       C      0.250    0.000
    10      C      0.250    0.000
    11      C      0.125    0.143
    ```

## Kilgarriff's chi-square { #kilgarriff_chi2 }

<!-- --8<-- [start:kilgarriff_chi2] -->
``` {.python .signature}
kilgarriff_chi2(words_a, words_b, n_mfw=500)
```

The distance between two corpora after [Kilgarriff (2001)](https://www.sketchengine.eu/wp-content/uploads/comparing_corpora_2001.pdf): for the `n_mfw` most frequent words of the joint corpus the expected frequencies in the corpora are proportional to their sizes, $\chi^2 = \sum (O - E)^2 / E$ over the words and both corpora. The greater the value, the more the corpora differ; it grows with the size of the corpora, so only pairs of equal sizes are comparable.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `words_a` | `list[str]` | - | Words of the first corpus |
| `words_b` | `list[str]` | - | Words of the second corpus |
| `n_mfw` | `int` | `500` | Number of the most frequent words of the joint corpus |

Words that are not a list of strings raise `SourceTypeError`, a corpus without words `SourceError`, and an `n_mfw` that is not an integer of at least one `ParameterError`.
<!-- --8<-- [end:kilgarriff_chi2] -->

=== "Code"

    ``` python
    from anyts.corpus import kilgarriff_chi2

    round(kilgarriff_chi2(corpus["A"], corpus["B"], n_mfw=5), 3)
    ```

=== "Result"

    ```
    4.113
    ```

## Mendenhall curve { #mendenhall }

<!-- --8<-- [start:mendenhall_curve] -->
``` {.python .signature}
mendenhall_curve(words)
```

The shares of the words of every length in characters by ascending length (Mendenhall 1887), a profile of the author comparable between texts whatever their size.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `words` | `list[str]` | - | Words of the text |

Words that are not a list of strings raise `SourceTypeError`, and no words `SourceError`.
<!-- --8<-- [end:mendenhall_curve] -->

<!-- --8<-- [start:mendenhall_distance] -->
``` {.python .signature}
mendenhall_distance(words_a, words_b)
```

The Jensen-Shannon distance with base 2 between the Mendenhall curves of two texts, from 0 (the distributions coincide) to 1.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `words_a` | `list[str]` | - | Words of the first text |
| `words_b` | `list[str]` | - | Words of the second text |

Words that are not a list of strings raise `SourceTypeError`, and a text without words `SourceError`.
<!-- --8<-- [end:mendenhall_distance] -->

=== "Code"

    ``` python
    from anyts.corpus import mendenhall_curve, mendenhall_distance

    {length: round(share, 3) for length, share in mendenhall_curve(corpus["A"]).items()}
    round(mendenhall_distance(corpus["A"], corpus["B"]), 3)
    ```

=== "Result"

    ```
    {2: 0.095, 3: 0.524, 4: 0.095, 5: 0.143, 6: 0.095, 7: 0.048}
    0.303
    ```
