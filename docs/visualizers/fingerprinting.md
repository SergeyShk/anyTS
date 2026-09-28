# Literature fingerprinting

!!! info ""
    **anyts.visualizers.fingerprinting()**

## Description

<!-- --8<-- [start:fingerprinting] -->
Visualization of literature fingerprinting ([Keim and Oelke 2007](https://www.uni-konstanz.de/mmsp/pubsys/publishedFiles/KeOe07.pdf)).

Every text is cut into segments of `segment_len` words with a sliding step of a tenth of a segment, and a measure of lexical diversity is computed for every segment. A text is a block of squares in the order of its segments, row by row, 8 rows high, or a single column when it has at most 8 segments; a block wider than a row of the drawing area wraps into rows of that width. The blocks are laid out left to right and wrap between the rows of an area `2 · x_size` wide, which grows downwards from `2 · y_size` when they need more height. The colour of a square is the value of the measure on the scale of the colorbar, from its smallest to its greatest finite value over all the texts. Segments where the measure is undefined (`nan` on segments too short for it) and the empty cells of a block are light grey, apart from every value, zero included. Every segment is `segment_len` words long, so the values are comparable: when the step leaves words after the last segment, one more segment ends with the text, and a text not longer than a segment is one segment. A list without texts or a text without words raises `SourceError`.
<!-- --8<-- [end:fingerprinting] -->

## Parameters

<!-- --8<-- [start:fingerprinting-parameters] -->
| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `texts` | list[list[str]] | `-` | List of lists of words |
| `segment_len` | int | `10` | Size of a segment |
| `metric` | Callable | `None` | Function of a measure of lexical diversity; `calc_ttr` by default |
| `x_size` | int | `800` | Half the width of the drawing area, greater than 25 (the margin between the blocks) |
| `y_size` | int | `600` | Half the height of the drawing area, which grows when the blocks need more |
| `cmap` | str | `'viridis'` | Colour map |
| `ax` | Axes | `None` | Axes of matplotlib for the plot; if not given, a 15×10 figure is created |
| `labels` | dict[str, str] | `None` | Labels over the defaults: `title` |

The function returns the `Axes` with the visualization, set to an equal aspect so that the squares stay square; the figure is `ax.figure`.
<!-- --8<-- [end:fingerprinting-parameters] -->

## Usage example

!!! example "Example"

    ``` python
    from anyts.diversity_stats import calc_mattr
    from anyts.visualizers import fingerprinting

    texts = [
        ("the cat sat on the mat " * 20).split(),
        " ".join(f"word{index % 37}" for index in range(150)).split(),
    ]
    fingerprinting(texts, segment_len=20, metric=calc_mattr)
    ```
