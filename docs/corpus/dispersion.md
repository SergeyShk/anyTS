# Word dispersion

!!! info ""
    **anyts.corpus.dispersion()**, **anyts.corpus.Dispersion**

## Description

<!-- --8<-- [start:dispersion] -->
The dispersion of a word is how evenly it is spread over the parts of a text or of a corpus. Frequency does not tell a word that occurs once in every chapter from a word gathered in one of them; the measures of dispersion ([Gries 2008](https://www.stgries.info/research/2008_STG_Dispersion_IJCL.pdf), [2020](https://www.stgries.info/research/2020_STG_Dispersion_PHCL.pdf)) complement frequency.

The text is split into parts: `parts` is the number of parts of about equal size or the sizes of the parts in order (sentences, paragraphs, chapters, documents of a corpus), which add up to the number of words. For every word its frequencies by part and six measures are computed; Gries recommends DP as the main one.

Words are compared as they are: case and lemmatization belong to the word extractor.
<!-- --8<-- [end:dispersion] -->

## Measures

<!-- --8<-- [start:dispersion-measures] -->
For $n$ parts of shares $s_i$ of the text, frequencies of the word by part $v_i$ and a total frequency $f = \sum v_i$; $p_i = v_i / n_i$ is the relative frequency in a part of size $n_i$:

| Measure | Field | Formula | Values |
| :------ | :---- | :------ | :----- |
| Deviation of proportions DP | `dp` | $\frac{1}{2} \sum \left\lvert \frac{v_i}{f} - s_i \right\rvert$ | 0 - in proportion to the sizes of the parts, tends to 1 - in one part; Gries (2008) |
| Normalized DP | `dp_norm` | $\frac{DP}{1 - \min s_i}$ | the maximum is one whatever the split; Lijffijt and Gries (2012) |
| Juilland's D | `juilland_d` | $1 - \frac{V}{\sqrt{n - 1}}$, $V = \frac{\sigma(p)}{\mu(p)}$ | 1 - even, 0 - in one part; Juilland and Chang-Rodríguez (1964) |
| Carroll's D2 | `carroll_d2` | $\frac{H(p)}{\log_2 n}$ | entropy of the distribution $p_i$; 1 - even, 0 - in one part; Carroll (1970) |
| Rosengren's S | `rosengren_s` | $\frac{(\sum \sqrt{s_i v_i})^2}{f}$ | 1 - in proportion, tends to $1/n$ when gathered in one of equal parts; Rosengren (1971) |
| Kullback-Leibler divergence | `kl_divergence` | $\sum \frac{v_i}{f} \log_2 \frac{v_i / f}{s_i}$ | in bits; 0 - in proportion, grows when gathered in small parts; Gries (2020) |

The measures are available as the functions `calc_dp`, `calc_dp_norm`, `calc_juilland_d`, `calc_carroll_d2`, `calc_rosengren_s` and `calc_kl_divergence` with the arguments `(frequencies, sizes)` - the frequencies of the word by part and the sizes of the parts - of the module `anyts.corpus.dispersion`; their names are in `anyts.constants.DISPERSION_STATS_DESC`. For a word of zero frequency every measure is `nan`.
<!-- --8<-- [end:dispersion-measures] -->

## Parameters

<!-- --8<-- [start:dispersion-parameters] -->
| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `words` | list[str] | `-` | Words of the text in order |
| `parts` | int/list[int] | `10` | Number of parts (from 2 to the number of words) or sizes of the parts |
| `word` | str | `None` | Word whose dispersion is needed; `None` - every word |
| `min_freq` | int | `1` | Minimum frequency of a word |
<!-- --8<-- [end:dispersion-parameters] -->

## Result

<!-- --8<-- [start:Dispersion] -->
A list of `Dispersion` named tuples by descending frequency: `word`, `freq` and the six measures of the table; `pd.DataFrame(result)` gives a table.
<!-- --8<-- [end:Dispersion] -->

## Example

!!! example "Example"

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
    # [10, 12, 12]

    dispersion(words, parts=sizes, word="cat")
    # [Dispersion(word='cat', freq=3, dp=0.039215686274509776, dp_norm=0.05555555555555552,
    #  juilland_d=0.9374999999999999, carroll_d2=0.9965119062478288,
    #  rosengren_s=0.998213770592287, kl_divergence=0.005215975085958165)]

    # Three equal parts: birds are gathered at the edges of the text
    [(d.word, round(d.dp, 2)) for d in dispersion(words, parts=3, min_freq=3)]
    # [('the', 0.1), ('cat', 0.02), ('at', 0.02), ('window', 0.02), ('and', 0.02), ('birds', 0.32)]
    ```
