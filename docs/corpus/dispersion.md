# Word dispersion

<!-- --8<-- [start:dispersion] -->
``` {.python .signature}
dispersion(words, parts=10, word=None, min_freq=1)
```

The dispersion of a word is how evenly it is spread over the parts of a text or of a corpus. Frequency does not tell a word occurring once in every chapter from one gathered in a single chapter; the measures of dispersion ([Gries 2008](https://www.stgries.info/research/2008_STG_Dispersion_IJCL.pdf), [2020](https://www.stgries.info/research/2020_STG_Dispersion_PHCL.pdf)) complement it.

`parts` is the number of parts of about equal size or the sizes of the parts in order (sentences, paragraphs, chapters, documents of a corpus), adding up to the number of words. Six measures are computed from the frequencies of every word by part; Gries recommends DP as the main one.

Words are compared as they are: case and lemmatization belong to the word extractor.
<!-- --8<-- [end:dispersion] -->

=== "Code"

    ``` python
    from anyts import SentsExtractor, WordsExtractor
    from anyts.corpus import dispersion

    text = (
        "The cat was at the window and watched the birds. The birds flew away and the cat "
        "fell asleep at the window. Tomorrow the cat will be at the window and watch the birds."
    )
    we = WordsExtractor(lowercase=True)
    words = we.extract(text)
    sizes = [len(we.extract(sent)) for sent in SentsExtractor().extract(text)]
    sizes
    dispersion(words, parts=sizes, word="cat")

    # Three equal parts: birds are gathered at the edges of the text
    [(d.word, round(d.dp, 2)) for d in dispersion(words, parts=3, min_freq=3)]
    ```

=== "Result"

    ```
    [10, 12, 12]
    [Dispersion(word='cat', freq=3, dp=0.039215686274509776, dp_norm=0.05555555555555552, juilland_d=0.9374999999999999, carroll_d2=0.9965119062478288, rosengren_s=0.998213770592287, kl_divergence=0.005215975085958165)]
    [('the', 0.1), ('cat', 0.02), ('at', 0.02), ('window', 0.02), ('and', 0.02), ('birds', 0.32)]
    ```

## Parameters

<!-- --8<-- [start:dispersion-parameters] -->
| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `words` | `list[str]` | - | Words of the text in order |
| `parts` | `int` / `list[int]` | `10` | Number of parts (from 2 to the number of words) or sizes of the parts |
| `word` | `str` | `None` | Word whose dispersion is needed; `None` - every word |
| `min_freq` | `int` | `1` | Minimum frequency of a word |

Words that are not a list of strings raise `SourceTypeError`, and no words `SourceError`. A `parts` that is neither an integer from 2 to the number of words nor two or more positive integers adding up to it, a `word` that is not a string and a `min_freq` that is not an integer raise `ParameterError`.
<!-- --8<-- [end:dispersion-parameters] -->

## Result

<!-- --8<-- [start:Dispersion] -->
``` {.python .signature}
Dispersion(word, freq, dp, dp_norm, juilland_d, carroll_d2, rosengren_s, kl_divergence)
```

A list of `Dispersion` named tuples by descending frequency: the word, its frequency and the measures; `pd.DataFrame(result)` gives a table.
<!-- --8<-- [end:Dispersion] -->

## Measures

<!-- --8<-- [start:dispersion-measures] -->
The measures, the fields of `Dispersion`, with their names in `anyts.constants.DISPERSION_STATS_DESC`:

| Field | Measures | Range | Higher means |
| :---- | :------- | :---- | :----------- |
| [`dp`](#dp) | Deviation of the shares of the occurrences from the shares of the parts | 0 to $1 - \min s_i$ | More uneven |
| [`dp_norm`](#dp_norm) | DP over its greatest possible value | 0-1 | More uneven |
| [`juilland_d`](#juilland_d) | Variation of the relative frequencies by part | 0-1 | More even |
| [`carroll_d2`](#carroll_d2) | Entropy of the relative frequencies by part | 0-1 | More even |
| [`rosengren_s`](#rosengren_s) | Spread of the occurrences against the sizes of the parts | $\min s_i$ to 1 | More even |
| [`kl_divergence`](#kl_divergence) | Divergence of the shares of the occurrences from the shares of the parts, in bits | 0 to $-\log_2 \min s_i$ | More uneven |

Every measure is a function of the module `anyts.corpus.dispersion` of the frequencies of the word by part and the sizes of the parts. For $n$ parts of sizes $n_i$ and shares $s_i$ of the text, frequencies of the word by part $v_i$ and a total frequency $f = \sum v_i$, $p_i = v_i / n_i$ is the relative frequency in a part:

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `frequencies` | `list[int]` | - | Frequencies of the word by part |
| `sizes` | `list[int]` | - | Sizes of the parts |

For a word of zero frequency every measure is `nan`.
<!-- --8<-- [end:dispersion-measures] -->

<div class="metric-card" markdown>

### Deviation of proportions DP { #dp }

`dp` · [Gries (2008)](https://www.stgries.info/research/2008_STG_Dispersion_IJCL.pdf)
{ .metric-meta }

<!-- --8<-- [start:calc_dp] -->
``` {.python .signature}
calc_dp(frequencies, sizes)
```

How far the shares of the occurrences of the word by part are from the shares of the parts: 0 means the word is spread in proportion to the sizes of the parts, $1 - s_i$ that it is all in part $i$.

$$
DP = \frac{1}{2} \sum \left\lvert \frac{v_i}{f} - s_i \right\rvert
$$
<!-- --8<-- [end:calc_dp] -->

</div>

<div class="metric-card" markdown>

### Normalized DP { #dp_norm }

`dp_norm` · Lijffijt and Gries (2012)
{ .metric-meta }

<!-- --8<-- [start:calc_dp_norm] -->
``` {.python .signature}
calc_dp_norm(frequencies, sizes)
```

DP divided by its greatest possible value, so the maximum is one whatever the split.

$$
\frac{DP}{1 - \min s_i}
$$
<!-- --8<-- [end:calc_dp_norm] -->

</div>

<div class="metric-card" markdown>

### Juilland's D { #juilland_d }

`juilland_d` · Juilland and Chang-Rodríguez (1964)
{ .metric-meta }

<!-- --8<-- [start:calc_juilland_d] -->
``` {.python .signature}
calc_juilland_d(frequencies, sizes)
```

One less the coefficient of variation $V$ of the relative frequencies $p_i$ over its greatest value $\sqrt{n - 1}$: 1 means even, 0 all in one part. The standard deviation $\sigma$ is that of the population, as in Gries (2020); Gries (2008) takes the sample one.

$$
1 - \frac{V}{\sqrt{n - 1}}, \quad V = \frac{\sigma(p)}{\mu(p)}
$$
<!-- --8<-- [end:calc_juilland_d] -->

</div>

<div class="metric-card" markdown>

### Carroll's D2 { #carroll_d2 }

`carroll_d2` · Carroll (1970)
{ .metric-meta }

<!-- --8<-- [start:calc_carroll_d2] -->
``` {.python .signature}
calc_carroll_d2(frequencies, sizes)
```

The entropy of the distribution of the relative frequencies $p_i$ over the parts, divided by its greatest value: 1 means even, 0 all in one part.

$$
\frac{H(p)}{\log_2 n}
$$
<!-- --8<-- [end:calc_carroll_d2] -->

</div>

<div class="metric-card" markdown>

### Rosengren's S { #rosengren_s }

`rosengren_s` · Rosengren (1971)
{ .metric-meta }

<!-- --8<-- [start:calc_rosengren_s] -->
``` {.python .signature}
calc_rosengren_s(frequencies, sizes)
```

1 means the word is spread in proportion to the sizes of the parts; all in part $i$, it gives $s_i$, so $1/n$ in one of $n$ equal parts.

$$
\frac{(\sum \sqrt{s_i v_i})^2}{f}
$$
<!-- --8<-- [end:calc_rosengren_s] -->

</div>

<div class="metric-card" markdown>

### Kullback-Leibler divergence { #kl_divergence }

`kl_divergence` · [Gries (2020)](https://www.stgries.info/research/2020_STG_Dispersion_PHCL.pdf)
{ .metric-meta }

<!-- --8<-- [start:calc_kl_divergence] -->
``` {.python .signature}
calc_kl_divergence(frequencies, sizes)
```

The divergence of the shares of the occurrences of the word by part from the shares of the parts: 0 means in proportion; it grows when the word is gathered in small parts.

$$
\sum \frac{v_i}{f} \log_2 \frac{v_i / f}{s_i}
$$
<!-- --8<-- [end:calc_kl_divergence] -->

</div>
