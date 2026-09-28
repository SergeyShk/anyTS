# Word tree

!!! info ""
    **anyts.visualizers.wordtree()**

## Description

<!-- --8<-- [start:wordtree] -->
Building a [word tree](https://www.weblyzard.com/word-tree/) that shows the contexts of a keyword in a text: the N-grams of up to `max_n` words that start or end with the keyword are counted in every list of words - a sentence, for instance. Every level of the tree keeps the `max_per_n` most frequent N-grams that continue a kept shorter one, alphabetically when equal. The kept N-grams are joined into two trees, the words after the keyword and before it, with the size of the font by frequency ([Wattenberg and Viégas 2008](https://www.cg.tuwien.ac.at/courses/InfoVis/HallOfFame/2011/Gruppe05/Homepage/Paper/wordtree-paper-wattenberg.pdf)). Rendering needs the executables of [Graphviz](https://graphviz.org/download/).
<!-- --8<-- [end:wordtree] -->

## Parameters

<!-- --8<-- [start:wordtree-parameters] -->
| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `texts` | list[list[str]] | `-` | List of lists of words |
| `keyword` | str | `-` | Keyword whose contexts are shown |
| `max_n` | int | `5` | Largest size of the context |
| `max_per_n` | int | `8` | Largest number of examples for every size of the context |
| `**kwargs` | - | `-` | Drawing parameters: `max_font_size` (default `30`), `min_font_size` (`12`), `font_interp` - a function interpolating the size of the font from the frequency |

The function returns a `Digraph` of graphviz.
<!-- --8<-- [end:wordtree-parameters] -->

## Usage example

!!! example "Example"

    ``` python
    from anyts.visualizers import wordtree

    sentences = [
        ["the", "cat", "sleeps"],
        ["the", "cat", "eats", "fish"],
        ["a", "black", "cat", "sleeps"],
    ]
    tree = wordtree(sentences, "cat", max_n=3)
    tree.render("wordtree")
    ```
