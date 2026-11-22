# Rhythm of the lines

A plot of the stressed and the unstressed syllables of the lines of a verse, from the statistics of verse of a language library. The function takes the axes `ax` and returns `Axes`.

## Rhythm of the lines { #rhythm_plot }

<!-- --8<-- [start:rhythm_plot] -->
``` {.python .signature}
rhythm_plot(stresses, lengths, ax=None, labels=None)
```

A row per line and a cell per syllable, numbered from 1: the stressed syllables in one color, the unstressed in another, nothing past the end of a line, so that the columns of a meter and the lines that break it show at a glance.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `stresses` | `list[list[int]]` | - | Indices of the stressed syllables of every line, from 0 |
| `lengths` | `list[int]` | - | Number of the syllables of every line |
| `ax` | `Axes` | `None` | Axes for the plot |
| `labels` | `dict[str, str]` | `None` | Labels over the defaults: `title`, `xlabel`, `ylabel`, `stressed`, `unstressed` (the legend) |

Stresses or lengths that are not lists of integers raise `SourceTypeError`; no lines, stresses and lengths that differ in number, a negative length or a stress outside its line raise `SourceError`; labels that `merge_labels` refuses and an `ax` that is not a matplotlib `Axes` raise `ParameterError`.
<!-- --8<-- [end:rhythm_plot] -->

``` python
from anyts.visualizers import rhythm_plot

# Iambic tetrameter: stresses on the even syllables, one of them skipped in the second line
rhythm_plot([(1, 3, 5, 7), (1, 3, 7), (1, 3, 5, 7), (1, 5, 7)], [8, 9, 8, 9])
```
