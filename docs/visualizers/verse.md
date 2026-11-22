# Rhythm of the lines

A plot of the stressed and the unstressed syllables of the lines of a verse, from the patterns of the lines that the statistics of verse of a language library give. The function takes the axes `ax` and returns `Axes`.

## Rhythm of the lines { #rhythm_plot }

<!-- --8<-- [start:rhythm_plot] -->
``` {.python .signature}
rhythm_plot(patterns, stressed, ax=None, labels=None)
```

A row per line and a cell per syllable of its pattern, numbered from 1: the stressed syllables in one color, the others in another, nothing past the end of a line, so that the columns of a meter and the lines that break it show at a glance.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `patterns` | `list[str]` | - | Patterns of the lines, a character per syllable |
| `stressed` | `str` | - | Character of a stressed syllable in the patterns |
| `ax` | `Axes` | `None` | Axes for the plot |
| `labels` | `dict[str, str]` | `None` | Labels over the defaults: `title`, `xlabel`, `ylabel`, `stressed`, `unstressed` (the legend) |

Patterns that are not a list of strings raise `SourceTypeError`, no lines `SourceError`; a `stressed` that is not one character, labels that `merge_labels` refuses and an `ax` that is not a matplotlib `Axes` raise `ParameterError`.
<!-- --8<-- [end:rhythm_plot] -->

``` python
from anyts.visualizers import rhythm_plot

# Iambic tetrameter: stresses on the even syllables, one skipped in the second and the fourth lines
rhythm_plot(["cCcCcCcC", "cCcCcccCc", "cCcCcCcC", "cCcccCcCc"], "C")
```
