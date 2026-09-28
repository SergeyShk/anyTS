# Stylometry

!!! info ""
    **anyts.corpus.delta()**, **anyts.corpus.delta_profiles()**, **anyts.corpus.frequency_table()**, **anyts.corpus.z_scores()**, **anyts.corpus.zeta()**, **anyts.corpus.kilgarriff_chi2()**, **anyts.corpus.mendenhall_curve()**, **anyts.corpus.mendenhall_distance()**

## Description

<!-- --8<-- [start:stylometry] -->
Measures of stylometry and authorship attribution: distances between texts by the frequencies of the most frequent words (Burrows's Delta and its variants, as in [stylo](https://github.com/computationalstylistics/stylo)), markers of preferred and avoided words (Zeta), Kilgarriff's chi-square distance between corpora and the Mendenhall curve. The functions work on lists of units of a text: lower-case word forms (the usual choice for Delta), lemmas or character N-grams - case and lemmatization belong to the extractors.
<!-- --8<-- [end:stylometry] -->

## Burrows's Delta { #delta }

<!-- --8<-- [start:frequency_table] -->
A corpus is a dictionary "name of a text → units". `frequency_table(corpus, n_mfw=100, culling=0.0)` builds the table of relative frequencies: rows are the texts, columns the `n_mfw` most frequent units by descending mean relative frequency (alphabetically when equal); `culling` keeps the units that occur in at least the given share of the texts, as in stylo.
<!-- --8<-- [end:frequency_table] -->

<!-- --8<-- [start:z_scores] -->
`z_scores(table)` standardizes the columns with the sample standard deviation, like `scale()` of R; a column with the same frequency in every text gives zeros.
<!-- --8<-- [end:z_scores] -->

<!-- --8<-- [start:delta] -->
`delta` computes a symmetric matrix of distances from the z-scores (a `DataFrame` with the names of the texts); at least three texts are needed - with two, the z-scores degenerate to ±1/√2 and the distances do not depend on the frequencies.

Variants (`anyts.constants.DELTA_VARIANTS`), with the formulas of the sources of stylo; $n$ is the number of units, $z_A$ and $z_B$ the vectors of z-scores of the texts:

| Variant | Key | Formula | Source |
| :------ | :-- | :------ | :----- |
| Burrows's Delta | `burrows` | $\frac{1}{n} \sum_i \lvert z_{A,i} - z_{B,i} \rvert$ | Burrows (2002), `dist.delta` |
| Quadratic Delta | `quadratic` | $\frac{1}{n} \sqrt{\sum_i (z_{A,i} - z_{B,i})^2}$ | Argamon (2008), `dist.argamon` |
| Eder's Delta | `eder` | $\sum_i \frac{n - i + 2}{n} \lvert z_{A,i} - z_{B,i} \rvert$, $i$ - rank of the unit by frequency | Eder, `dist.eder` |
| Cosine Delta | `cosine` | $1 - \frac{z_A \cdot z_B}{\lVert z_A \rVert \lVert z_B \rVert}$ | Smith and Aldridge (2011), [Evert et al. (2015)](https://aclanthology.org/W15-0709.pdf), `dist.wurzburg` |

Cosine Delta clusters the texts by author best in the experiments of Evert et al. The usual number of units is 100 to 500 most frequent words, 100-200 for character N-grams.

Parameters of `delta`:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `corpus` | dict[str, list[str]] | `-` | Units of the texts by the names of the texts |
| `n_mfw` | int | `100` | Number of the most frequent units; `None` - all of them |
| `variant` | str | `burrows` | Variant of Delta of `anyts.constants.DELTA_VARIANTS` |
| `culling` | float | `0.0` | Smallest share of the texts a unit occurs in |
<!-- --8<-- [end:delta] -->

<!-- --8<-- [start:delta_profiles] -->
For authorship attribution there is `delta_profiles(reference, samples, n_mfw, variant, culling, statistics)`: the most frequent units, the culling and the statistics of the z-scores come from the reference texts `reference` (the profiles of the authors) or from a separate set `statistics` - for instance, the training windows when the profiles are too few to estimate the spread of the frequencies; the texts under test `samples` are described by the same units and scaled by the same statistics. The result is the distances from the texts under test to the reference ones, and the nearest reference in a row is the presumed author. Unlike in `delta`, the texts under test affect neither the units nor the scaling, so the result for a text does not depend on the texts passed along with it.
<!-- --8<-- [end:delta_profiles] -->

!!! example "Example"

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
    #      the    and    dog  slept  birds
    # A  0.286  0.095  0.000  0.048  0.095
    # B  0.222  0.111  0.111  0.111  0.000
    # C  0.222  0.056  0.056  0.000  0.056

    delta(corpus, n_mfw=5).round(3)
    #        A      B      C
    # A  0.000  1.483  1.161
    # B  1.483  0.000  1.219
    # C  1.161  1.219  0.000

    delta(corpus, n_mfw=5, variant="cosine").round(3)
    #        A      B      C
    # A  0.000  1.676  1.273
    # B  1.676  0.000  1.525
    # C  1.273  1.525  0.000

    sample = {"?": we.extract("The cat woke up at the window and watched the birds again.")}
    delta_profiles(corpus, sample, n_mfw=5).round(3)
    #        A      B      C
    # ?  0.499  1.493  0.662
    ```

## Zeta { #zeta }

<!-- --8<-- [start:zeta] -->
Markers of preferred and avoided words after Burrows (2007) and Craig and Kinney (2009). Every text of both corpora is split into segments of about `segment_size` words (the number of segments is the ratio of the length to the size rounded half up, at least one), and for a word the share of the segments of each corpus where it occurs ($DP$) is computed. Zeta is the difference of the shares $DP_{target} - DP_{comparison}$ from −1 to 1 (`zeta.craig` in the notation of stylo; the classic Zeta of Craig $DP_{target} + (1 - DP_{comparison})$ is greater by one), the logarithmic Zeta is $\log_2 \frac{DP_{target}}{DP_{comparison}}$ ([Schöch et al. 2018](https://zeta-project.eu/en/keyness-measures/burrows-zeta-logarithmic-zeta/)), a zero share replaced by half a segment. The list starts with the words the target corpus prefers and ends with the avoided ones.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `target` | list[str]/list[list[str]] | `-` | Words of the target corpus - one text or a list of texts |
| `comparison` | list[str]/list[list[str]] | `-` | Words of the comparison corpus |
| `segment_size` | int | `2000` | Size of a segment in words |
| `top_n` | int | `None` | Number of words from the start of the list; `None` - all of them |

The result is a list of `ZetaScore(word, dp_target, dp_comparison, zeta, log_zeta)` named tuples by descending Zeta, by descending logarithmic Zeta and alphabetically when equal.
<!-- --8<-- [end:zeta] -->

!!! example "Example"

    ``` python
    from anyts.corpus import zeta

    zeta(corpus["A"], corpus["B"], segment_size=5, top_n=2)
    # [ZetaScore(word='at', dp_target=0.5, dp_comparison=0.0, zeta=0.5, log_zeta=2.0),
    #  ZetaScore(word='birds', dp_target=0.5, dp_comparison=0.0, zeta=0.5, log_zeta=2.0)]

    zeta(corpus["A"], corpus["B"], segment_size=5)[-1]
    # ZetaScore(word='on', dp_target=0.0, dp_comparison=0.5, zeta=-0.5, log_zeta=-2.0)
    ```

## Kilgarriff's chi-square { #kilgarriff_chi2 }

<!-- --8<-- [start:kilgarriff_chi2] -->
The distance between two corpora after [Kilgarriff (2001)](https://www.sketchengine.eu/wp-content/uploads/comparing_corpora_2001.pdf): for the `n_mfw` most frequent words of the joint corpus the expected frequencies in the corpora are proportional to their sizes, $\chi^2 = \sum (O - E)^2 / E$ over the words and both corpora. The greater the value, the more the corpora differ; the value grows with the size of the corpora, so pairs of corpora are comparable with each other at equal sizes.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `words_a` | list[str] | `-` | Words of the first corpus |
| `words_b` | list[str] | `-` | Words of the second corpus |
| `n_mfw` | int | `500` | Number of the most frequent words of the joint corpus |
<!-- --8<-- [end:kilgarriff_chi2] -->

!!! example "Example"

    ``` python
    from anyts.corpus import kilgarriff_chi2

    round(kilgarriff_chi2(corpus["A"], corpus["B"], n_mfw=5), 3)
    # 4.113
    ```

## Mendenhall curve { #mendenhall }

<!-- --8<-- [start:mendenhall_curve] -->
`mendenhall_curve(words)` - the shares of the words of every length in characters (Mendenhall 1887), a profile of the author comparable between texts whatever their size.
<!-- --8<-- [end:mendenhall_curve] -->

<!-- --8<-- [start:mendenhall_distance] -->
`mendenhall_distance(words_a, words_b)` - the Jensen-Shannon distance with base 2 between the curves, from 0 (the distributions coincide) to 1.
<!-- --8<-- [end:mendenhall_distance] -->

!!! example "Example"

    ``` python
    from anyts.corpus import mendenhall_curve, mendenhall_distance

    {length: round(share, 3) for length, share in mendenhall_curve(corpus["A"]).items()}
    # {2: 0.095, 3: 0.524, 4: 0.095, 5: 0.143, 6: 0.095, 7: 0.048}

    round(mendenhall_distance(corpus["A"], corpus["B"]), 3)
    # 0.303
    ```
