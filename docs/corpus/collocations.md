# Collocations

<!-- --8<-- [start:collocations] -->
``` {.python .signature}
collocations(words, window=5, measure='logdice', min_freq=2, node=None, top_n=None)
```

Collocation extraction - pairs of words that occur together more often than independence would give: fixed expressions, terminology, the combinatorics of a word. The measures of association are those of [Sketch Engine](https://www.sketchengine.eu/wp-content/uploads/ske-statistics.pdf) and of [`nltk.metrics.association`](https://www.nltk.org/api/nltk.metrics.association.html).

Pairs are ordered, as in NLTK: the right word occurs at most `window` words after the left one, each pair of positions counted once; `window=1` gives bigrams. The measures take the pair frequency divided by the window (Church and Hanks 1990, as in NLTK), which keeps the expected frequency independent of the window and Dice and the minimum sensitivity at most one; `freq_pair` stays undivided. So with `window > 1` an always adjacent pair gets a logDice of $14 - \log_2 window$ (13 at a window of 2), not 14 as in Sketch Engine with its raw co-occurrence; 14 needs a pair at every distance within the window. `node` keeps the pairs with the given word on either side.

Words are compared as they are: case, lemmatization and stop words belong to the word extractor; lemmas suit fixed expressions, word forms suit grammatical constructions.
<!-- --8<-- [end:collocations] -->

=== "Code"

    ``` python
    from anyts import WordsExtractor
    from anyts.corpus import collocations

    words = WordsExtractor(lowercase=True).extract(
        "The cat was at the window and watched the birds. The birds flew away and the cat "
        "fell asleep at the window. Tomorrow the cat will be at the window and watch the birds."
    )

    collocations(words, window=2, top_n=1)
    [
        (c.left, c.right, round(c.score, 2))
        for c in collocations(words, window=1, node="cat", min_freq=1, measure="mi")[:2]
    ]
    ```

=== "Result"

    ```
    [Collocation(left='at', right='window', freq_left=3, freq_right=3, freq_pair=3, score=13.0)]
    [('cat', 'fell', 3.5), ('cat', 'was', 3.5)]
    ```

## Parameters

<!-- --8<-- [start:collocations-parameters] -->
| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `words` | `list[str]` | - | Words of the text in order |
| `window` | `int` | `5` | Greatest distance between the words of a pair |
| `measure` | `str` | `'logdice'` | Measure of `anyts.constants.COLLOCATION_MEASURES` |
| `min_freq` | `int` | `2` | Minimum frequency of a pair |
| `node` | `str` | `None` | Word whose combinatorics is needed; `None` - every pair |
| `top_n` | `int` | `None` | Number of collocations; `None` - all of them |

Words that are not a list of strings raise `SourceTypeError`, and no words `SourceError`. An unknown measure, a `window` or a `top_n` that is not an integer of at least one, a `min_freq` that is not an integer and a `node` that is not a string raise `ParameterError`.
<!-- --8<-- [end:collocations-parameters] -->

## Result

<!-- --8<-- [start:Collocation] -->
``` {.python .signature}
Collocation(left, right, freq_left, freq_right, freq_pair, score)
```

A list of `Collocation` named tuples by descending measure and frequency of the pair (ties broken alphabetically); `pd.DataFrame(found)` gives a table.

| Field | Type | Description |
| :---- | :--- | :---------- |
| `left` | `str` | Left word |
| `right` | `str` | Right word, occurring within the window after the left one |
| `freq_left` | `int` | Frequency of the left word |
| `freq_right` | `int` | Frequency of the right word |
| `freq_pair` | `int` | Frequency of the co-occurrence |
| `score` | `float` | Value of the chosen measure |
<!-- --8<-- [end:Collocation] -->

## Measures

<!-- --8<-- [start:collocations-measures] -->
The measures of `measure` by key, with their names and descriptions in `anyts.constants.COLLOCATION_MEASURES`:

| Key | Measures | Range | Higher means |
| :-- | :------- | :---- | :----------- |
| [`mi`](#mi) | Frequency of the pair against the expected one, in bits | Any number | A stronger association |
| [`mi3`](#mi3) | MI with the frequency of the pair cubed | Any number | A stronger association |
| [`t_score`](#t_score) | Difference of the observed and the expected frequency of the pair | Any number | A surer association |
| [`dice`](#dice) | Share of the pair in the occurrences of the two words | 0-1 | A stronger association |
| [`logdice`](#logdice) | Dice coefficient on a logarithmic scale | 14 and below | A stronger association |
| [`log_likelihood`](#log_likelihood) | Significance of the association | 0 and above | A more significant association |
| [`npmi`](#npmi) | MI normalized by the information of the pair | −1 to 1 | A stronger association |
| [`min_sensitivity`](#min_sensitivity) | Smaller share of the pair in the occurrences of either word | 0-1 | A stronger association |

Every measure is a function of the module `anyts.corpus.collocations` of the frequencies of the words and of the pair and the number of words:

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `freq_a` | `int` | - | Frequency $f_a$ of the first word |
| `freq_b` | `int` | - | Frequency $f_b$ of the second word |
| `freq_ab` | `float` | - | Frequency $f_{ab}$ of the pair |
| `n` | `int` | - | Number of words $N$ of the text |

A pair of zero frequency gives `nan` for MI, MI³, the t-score, logDice and NPMI.
<!-- --8<-- [end:collocations-measures] -->

<div class="metric-card" markdown>

### Mutual information { #mi }

`mi` · Church and Hanks (1990)
{ .metric-meta }

<!-- --8<-- [start:calc_mi] -->
``` {.python .signature}
calc_mi(freq_a, freq_b, freq_ab, n)
```

The pointwise mutual information of the two words; it overrates rare pairs.

$$
\log_2 \frac{f_{ab} N}{f_a f_b}
$$
<!-- --8<-- [end:calc_mi] -->

</div>

<div class="metric-card" markdown>

### MI³ { #mi3 }

`mi3` · Oakes (1998)
{ .metric-meta }

<!-- --8<-- [start:calc_mi3] -->
``` {.python .signature}
calc_mi3(freq_a, freq_b, freq_ab, n)
```

The mutual information with the frequency of the pair cubed, which favours frequent pairs.

$$
\log_2 \frac{f_{ab}^3 N}{f_a f_b}
$$
<!-- --8<-- [end:calc_mi3] -->

</div>

<div class="metric-card" markdown>

### t-score { #t_score }

`t_score` · Church et al. (1991)
{ .metric-meta }

<!-- --8<-- [start:calc_t_score] -->
``` {.python .signature}
calc_t_score(freq_a, freq_b, freq_ab, n)
```

The difference of the observed and the expected frequency of the pair over the root of the observed one; it favours frequent pairs.

$$
\frac{f_{ab} - f_a f_b / N}{\sqrt{f_{ab}}}
$$
<!-- --8<-- [end:calc_t_score] -->

</div>

<div class="metric-card" markdown>

### Dice coefficient { #dice }

`dice`
{ .metric-meta }

<!-- --8<-- [start:calc_dice] -->
``` {.python .signature}
calc_dice(freq_a, freq_b, freq_ab, n)
```

The share of the pair in the occurrences of the two words; it does not depend on the size of the text.

$$
\frac{2 f_{ab}}{f_a + f_b}
$$
<!-- --8<-- [end:calc_dice] -->

</div>

<div class="metric-card" markdown>

### logDice { #logdice }

`logdice` · [Rychlý (2008)](https://www.sketchengine.eu/glossary/logdice/)
{ .metric-meta }

<!-- --8<-- [start:calc_logdice] -->
``` {.python .signature}
calc_logdice(freq_a, freq_b, freq_ab, n)
```

The Dice coefficient on a binary logarithmic scale, the default measure, as in Sketch Engine. It does not depend on the size of the text; below zero the link is weak.

$$
14 + \log_2 \frac{2 f_{ab}}{f_a + f_b}
$$
<!-- --8<-- [end:calc_logdice] -->

</div>

<div class="metric-card" markdown>

### Log-likelihood { #log_likelihood }

`log_likelihood` · Dunning (1993)
{ .metric-meta }

<!-- --8<-- [start:calc_log_likelihood] -->
``` {.python .signature}
calc_log_likelihood(freq_a, freq_b, freq_ab, n)
```

$G^2$ over the 2×2 contingency table of the two words: the observed frequencies $O$ - $f_{ab}$, $f_a - f_{ab}$, $f_b - f_{ab}$ and $N - f_a - f_b + f_{ab}$ - against the expected ones $E$ under independence. A word that fills the whole text, or a negative cell, as of a word paired with itself in a window above one, gives `nan`.

$$
G^2 = 2 \sum O \ln \frac{O}{E}
$$
<!-- --8<-- [end:calc_log_likelihood] -->

</div>

<div class="metric-card" markdown>

### NPMI { #npmi }

`npmi` · Bouma (2009)
{ .metric-meta }

<!-- --8<-- [start:calc_npmi] -->
``` {.python .signature}
calc_npmi(freq_a, freq_b, freq_ab, n)
```

The mutual information normalized by the information of the pair: one means the words occur only together. A pair as frequent as the text is long gives `nan`.

$$
\frac{MI}{-\log_2 (f_{ab} / N)}
$$
<!-- --8<-- [end:calc_npmi] -->

</div>

<div class="metric-card" markdown>

### Minimum sensitivity { #min_sensitivity }

`min_sensitivity` · Pedersen (1998)
{ .metric-meta }

<!-- --8<-- [start:calc_min_sensitivity] -->
``` {.python .signature}
calc_min_sensitivity(freq_a, freq_b, freq_ab, n)
```

The smaller of the shares of the pair in the occurrences of each word.

$$
\min\left(\frac{f_{ab}}{f_a}, \frac{f_{ab}}{f_b}\right)
$$
<!-- --8<-- [end:calc_min_sensitivity] -->

</div>
