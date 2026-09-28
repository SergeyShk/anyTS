# Corpus plots

!!! info ""
    **anyts.visualizers.dispersion_plot()**, **anyts.visualizers.keyness_plot()**, **anyts.visualizers.collocation_network()**

## Description

Plots for the [corpus measures](../corpus/keyness.md): the lexical dispersion - where in a text a word occurs, a chart of the keywords found by `keyness` and a network of the collocations found by `collocations`. The matplotlib functions take the axes `ax` and return `Axes`: without `ax` a new figure is created, with it the plot goes into a grid of one's own; the network of collocations is built by graphviz and returns a `Graph`, as the [word tree](word_tree.md) returns a `Digraph`.

## Lexical dispersion { #dispersion_plot }

<!-- --8<-- [start:dispersion_plot] -->
A row for every word of `targets` and a tick at the position of each of its occurrences in the text. Words are compared as they are: case and lemmatization belong to the extraction of the words.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `words` | list[str] | `-` | Words of the text in order |
| `targets` | list[str] | `-` | Words whose occurrences are shown |
| `ax` | Axes | `None` | Axes for the plot |
| `labels` | dict[str, str] | `None` | Labels over the defaults: `title`, `xlabel` |
<!-- --8<-- [end:dispersion_plot] -->

## Chart of keywords { #keyness_plot }

<!-- --8<-- [start:keyness_plot] -->
Diverging horizontal bars: the words of `positive` to the right, of `negative` - the result of `keyness` with `positive=False` - to the left, the length of a bar is the absolute value of the `field` (`score`, `g2`, `log_ratio`), so the side is set by the list and not by the sign of the measure; `top_n` words on each side, the words with an undefined or infinite value are skipped. For the odds ratio (`score` from 0 to infinity, one - equal odds) set `log=True`: the absolute $\log_2$ of the value is plotted, symmetric around one.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `positive` | list[Keyword] | `-` | Positive keywords |
| `negative` | list[Keyword] | `()` | Negative keywords |
| `top_n` | int | `20` | Number of words on each side |
| `labels` | dict[str, str]/tuple[str, str] | `None` | Labels over the defaults: `title`, `xlabel` and `xlabel_log` (format strings with `field`), `target` and `reference` (the legend); a pair of strings sets the legend alone |
| `field` | str | `score` | Field of `Keyword` whose values are plotted |
| `log` | bool | `False` | Plot $\log_2$ of the value - for the odds ratio |
| `ax` | Axes | `None` | Axes for the plot |
<!-- --8<-- [end:keyness_plot] -->

## Network of collocations { #collocation_network }

<!-- --8<-- [start:collocation_network] -->
An undirected graph: the nodes are the words with the size of the font by frequency, the edges the pairs with the width and the label by the value of the measure; the `neato` layout. A pair of a word with itself - a word repeated within the window - would be a loop and is left out before `top_n` pairs are taken. Rendering needs the executables of [Graphviz](https://graphviz.org/download/); in Jupyter the graph displays itself, and `graph.render("network")` saves a png file.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `collocations` | list[Collocation] | `-` | Collocations |
| `top_n` | int | `None` | Number of pairs from the start of the list; `None` - all of them |
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
