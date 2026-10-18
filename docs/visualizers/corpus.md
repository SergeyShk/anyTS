# Corpus plots

!!! info ""
    **anyts.visualizers.dispersion_plot()**, **anyts.visualizers.keyness_plot()**, **anyts.visualizers.collocation_network()**

## Description

Plots for the [corpus measures](../corpus/keyness.md): the lexical dispersion (where in a text a word occurs), a chart of the keywords of `keyness` and a network of the collocations of `collocations`. The matplotlib functions take the axes `ax`, a new figure without them, and return `Axes`; the network is a graphviz `Graph`, as the [word tree](word_tree.md) is a `Digraph`.

## Lexical dispersion { #dispersion_plot }

<!-- --8<-- [start:dispersion_plot] -->
A row for every word of `targets` and a tick at the position of each of its occurrences in the text. Words are compared as they are: case and lemmatization belong to the extraction of the words.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `words` | list[str] | `-` | Words of the text in order |
| `targets` | list[str] | `-` | Words whose occurrences are shown |
| `ax` | Axes | `None` | Axes for the plot |
| `labels` | dict[str, str] | `None` | Labels over the defaults: `title`, `xlabel` |

Words or targets that are not a list of strings raise `SourceTypeError`, no words or no targets `SourceError`; labels that `merge_labels` refuses and an `ax` that is not a matplotlib `Axes` raise `ParameterError`.
<!-- --8<-- [end:dispersion_plot] -->

## Chart of keywords { #keyness_plot }

<!-- --8<-- [start:keyness_plot] -->
Diverging horizontal bars: the words of `positive` to the right, of `negative` (the result of `keyness` with `positive=False`) to the left, `top_n` on each side. The length of a bar is the absolute value of the `field` (`score`, `g2`, `log_ratio`), so the side is set by the list, not by the sign of the measure; words with an undefined or infinite value are skipped. For the odds ratio (from 0 to infinity, one - equal odds) `log=True` plots the absolute $\log_2$ of the value, symmetric around one.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `positive` | list[Keyword] | `-` | Positive keywords |
| `negative` | list[Keyword] | `()` | Negative keywords |
| `top_n` | int | `20` | Number of words on each side |
| `labels` | dict[str, str]/tuple[str, str] | `None` | Labels over the defaults: `title`, `xlabel` and `xlabel_log` (format strings with `field`), `target` and `reference` (the legend); a pair of strings sets the legend alone |
| `field` | str | `score` | Field of `Keyword` whose values are plotted |
| `log` | bool | `False` | Plot $\log_2$ of the value - for the odds ratio |
| `ax` | Axes | `None` | Axes for the plot |

Keywords that are not a list raise `SourceTypeError`, and no keyword with a finite value `SourceError`. An unknown `field`, a `top_n` that is not an integer of at least one, labels that `merge_labels` refuses or a legend that is not a pair, and an `ax` that is not a matplotlib `Axes` raise `ParameterError`.
<!-- --8<-- [end:keyness_plot] -->

## Network of collocations { #collocation_network }

<!-- --8<-- [start:collocation_network] -->
An undirected graph in the `neato` layout: the nodes are the words, the size of the font by frequency, the edges the pairs, the width and the label by the measure. A pair of a word with itself (a word repeated within the window) would be a loop and is left out before `top_n`. Rendering needs the executables of [Graphviz](https://graphviz.org/download/); Jupyter displays the graph, and `graph.render("network")` saves a png file.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `collocations` | list[Collocation] | `-` | Collocations |
| `top_n` | int | `None` | Number of pairs from the start of the list; `None` - all of them |

Collocations that are not a list raise `SourceTypeError`, no pair of two different words `SourceError`, and a `top_n` that is not an integer of at least one `ParameterError`.
<!-- --8<-- [end:collocation_network] -->

## Usage example

!!! example "Example"

    ``` python
    from anyts.corpus import collocations, keyness
    from anyts.visualizers import collocation_network, dispersion_plot, keyness_plot

    target = "the cat sleeps and the cat eats and the cat purrs".split()
    reference = "the dog sleeps and the dog eats and the dog barks".split()
    dispersion_plot(target, ["cat", "eats"])
    keyness_plot(keyness(target, reference), keyness(target, reference, positive=False))
    print(collocation_network(collocations(target, window=1)).source)
    ```
