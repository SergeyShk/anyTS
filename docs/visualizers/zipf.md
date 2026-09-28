# Zipf's law

!!! info ""
    **anyts.visualizers.zipf()**, **anyts.visualizers.zipf_theory()**

## Description

<!-- --8<-- [start:zipf] -->
Plotting [Zipf's law](https://en.wikipedia.org/wiki/Zipf%27s_law) from a counter of the frequencies of words.

!!! quote "Definition"

    Zipf's law (the rank-frequency law) is an empirical regularity of the distribution of the frequencies of words in a natural language: if all the words of a language, or of a long enough text, are ordered by descending frequency, the frequency of the n-th word of the list is roughly inversely proportional to its number n, the rank of the word. The second most frequent word occurs about half as often as the first, the third a third as often, and so on.
<!-- --8<-- [end:zipf] -->

## Parameters

<!-- --8<-- [start:zipf-parameters] -->
| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `counter` | Counter | `-` | Counter of the frequencies of words |
| `num_words` | int | `None` | Number of the most frequent words |
| `num_labels` | int | `10` | Number of the words labelled on the plot |
| `log` | bool | `True` | Use a logarithmic scale |
| `show_theory` | bool | `False` | Plot the theoretical Zipf's law |
| `alpha` | float | `1.5` | Exponent α of the theoretical Zipf's law, greater than zero |
| `show_fit` | bool | `False` | Plot the Zipf-Mandelbrot fit $f(r) = C / (r + q)^s$ of `fit_zipf_mandelbrot` |
| `ax` | Axes | `None` | Axes of matplotlib for the plot; if not given, a new figure is created |
| `labels` | dict[str, str] | `None` | Labels of the plot over the defaults: `title`, `xlabel`, `ylabel`, `experimental` and `theoretical` (the curves), `fit` (a format string with `q` and `s`) |

The function returns the `Axes` with the plot; a `num_words` greater than the number of word types does not extend the curves beyond the data, an empty counter raises `SourceError`, and a `num_words` below one raises `ParameterError`.
<!-- --8<-- [end:zipf-parameters] -->

<!-- --8<-- [start:zipf_theory] -->
`zipf_theory(size, num_ranks, alpha=1.5, ax=None, labels=None)` plots the theoretical curve alone, $f(r) = size \cdot r^{-\alpha}$ for the ranks from 1 to `num_ranks`; its label is the key `theoretical`.
<!-- --8<-- [end:zipf_theory] -->

## Usage example

!!! example "Example"

    ``` python
    from collections import Counter

    from anyts import WordsExtractor
    from anyts.visualizers import zipf

    text = "The cat sat on the mat and the dog sat on the rug, and the cat saw the dog."
    counts = Counter(WordsExtractor(lowercase=True).extract(text))
    ax = zipf(counts, num_labels=5, show_fit=True, labels={"title": "Zipf's law of a sentence"})
    ax.figure.savefig("zipf.png")
    ```
