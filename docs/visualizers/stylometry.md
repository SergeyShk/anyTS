# Stylometric plots

Plots for [stylometry](../corpus/stylometry.md): a dendrogram, the multidimensional scaling and the histograms within and between authors of the matrix of distances of `delta`, the principal components of the frequencies of the most frequent words, the distances of rolling Delta along a text, the segments of corpora by the markers of Zeta and the Mendenhall curves of several texts. The functions take the axes `ax` and return `Axes`.

## Dendrogram { #dendrogram_plot }

<!-- --8<-- [start:dendrogram_plot] -->
``` {.python .signature}
dendrogram_plot(distances, method='ward', ax=None, labels=None)
```

Hierarchical clustering by `scipy.cluster.hierarchy` over the matrix of distances between texts, Ward's method by default as in [Evert et al. (2015)](https://aclanthology.org/W15-0709.pdf); the leaves are labelled by the index of the matrix. The columns are taken in the order of the rows.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `distances` | `DataFrame` | - | Symmetric matrix of distances with the names of the texts in the rows and the columns, in any order |
| `method` | `str` | `'ward'` | Method of `scipy.cluster.hierarchy.linkage` to join the clusters: `single`, `complete`, `average`, `weighted`, `centroid`, `median` or `ward` |
| `ax` | `Axes` | `None` | Axes for the plot |
| `labels` | `dict[str, str]` | `None` | Labels over the defaults: `title`, `xlabel` |

Other texts in the columns than in the rows, fewer than two texts, an infinite or negative distance, asymmetry or a distance on the diagonal raise `SourceError` before a figure is created. Distances that are not a `DataFrame` of numbers raise `SourceTypeError`; an unknown `method`, labels that `merge_labels` refuses and an `ax` that is not a matplotlib `Axes` raise `ParameterError`.
<!-- --8<-- [end:dendrogram_plot] -->

## Principal components { #pca_plot }

<!-- --8<-- [start:pca_plot] -->
``` {.python .signature}
pca_plot(corpus, n_mfw=100, culling=0.0, ax=None, labels=None)
```

Principal component analysis of the z-scores of the relative frequencies of the most frequent units (`frequency_table`, `z_scores`): the texts on the plane of the first two components with their names, the shares of the explained variance in the labels of the axes.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `corpus` | `dict[str, list[str]]` | - | Units of the texts by the names of the texts |
| `n_mfw` | `int` | `100` | Number of the most frequent units; `None` - all of them |
| `culling` | `float` | `0.0` | Smallest share of the texts a unit occurs in |
| `ax` | `Axes` | `None` | Axes for the plot |
| `labels` | `dict[str, str]` | `None` | Labels over the defaults: `title`, `xlabel` and `ylabel` (format strings with the explained `share`) |

The corpus, `n_mfw` and `culling` raise the errors of `frequency_table`, and fewer than three texts raise `SourceError`; labels that `merge_labels` refuses and an `ax` that is not a matplotlib `Axes` raise `ParameterError`.
<!-- --8<-- [end:pca_plot] -->

## Multidimensional scaling { #mds_plot }

<!-- --8<-- [start:mds_plot] -->
``` {.python .signature}
mds_plot(distances, ax=None, labels=None)
```

Classical multidimensional scaling (Torgerson 1952) of any matrix of distances: the two leading eigenvectors of the double-centred squared distances, so the distances between the points approximate those of the matrix. The columns are taken in the order of the rows.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `distances` | `DataFrame` | - | Symmetric matrix of distances with the names of the texts in the rows and the columns, in any order |
| `ax` | `Axes` | `None` | Axes for the plot |
| `labels` | `dict[str, str]` | `None` | Labels over the defaults: `title`, `xlabel`, `ylabel` |

Other texts in the columns than in the rows, fewer than two texts, an infinite or negative distance, asymmetry or a distance on the diagonal raise `SourceError` before a figure is created. Distances that are not a `DataFrame` of numbers raise `SourceTypeError`; labels that `merge_labels` refuses and an `ax` that is not a matplotlib `Axes` raise `ParameterError`.
<!-- --8<-- [end:mds_plot] -->

## Distances within and between authors { #delta_histogram_plot }

<!-- --8<-- [start:delta_histogram_plot] -->
``` {.python .signature}
delta_histogram_plot(distances, authors, bins=20, ax=None, labels=None)
```

The histograms of the distances of the pairs of texts by one author and of the pairs by different authors, as densities over common bins, so groups of different sizes are comparable. The less the histograms overlap, the better the distances tell the authors apart - a check of the number of units and of the variant of Delta on texts of known authors. The columns are taken in the order of the rows.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `distances` | `DataFrame` | - | Symmetric matrix of distances with the names of the texts in the rows and the columns, in any order |
| `authors` | `dict[str, str]` | - | Authors of the texts by the names of the texts |
| `bins` | `int` | `20` | Number of the bins |
| `ax` | `Axes` | `None` | Axes for the plot |
| `labels` | `dict[str, str]` | `None` | Labels over the defaults: `title`, `xlabel`, `ylabel` and the legend `within`, `between` |

The matrix raises the errors of `dendrogram_plot`; authors that are not a mapping raise `SourceTypeError`, and a text without an author, no two texts by one author or all of them by one author `SourceError`. A `bins` that is not an integer of at least one, labels that `merge_labels` refuses and an `ax` that is not a matplotlib `Axes` raise `ParameterError`.
<!-- --8<-- [end:delta_histogram_plot] -->

## Rolling Delta { #rolling_delta_plot }

<!-- --8<-- [start:rolling_delta_plot] -->
``` {.python .signature}
rolling_delta_plot(distances, ax=None, labels=None)
```

The distances of `rolling_delta` as a line for every reference text over the middles of the windows: the lowest line is the nearest reference of a part of the text, and where the lines cross, the style changes.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `distances` | `DataFrame` | - | Distances of `rolling_delta`: the windows by the position of their middle in the rows, the reference texts in the columns |
| `ax` | `Axes` | `None` | Axes for the plot |
| `labels` | `dict[str, str]` | `None` | Labels over the defaults: `title`, `xlabel`, `ylabel` |

Distances that are not a `DataFrame` of numbers with numbers in the index raise `SourceTypeError`; no windows or no reference texts and an infinite or negative distance raise `SourceError` before a figure is created. Labels that `merge_labels` refuses and an `ax` that is not a matplotlib `Axes` raise `ParameterError`.
<!-- --8<-- [end:rolling_delta_plot] -->

## Zeta scatter { #zeta_scatter_plot }

<!-- --8<-- [start:zeta_scatter_plot] -->
``` {.python .signature}
zeta_scatter_plot(segments, ax=None, labels=None)
```

The segments of `zeta_segments` on the plane of the shares of the avoided words (horizontal axis) and of the preferred ones (vertical axis), a colour for every corpus, as in `oppose` of stylo.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `segments` | `DataFrame` | - | Segments of `zeta_segments` with the columns `corpus`, `preferred` and `avoided` |
| `ax` | `Axes` | `None` | Axes for the plot |
| `labels` | `dict[str, str]` | `None` | Labels over the defaults: `title`, `xlabel`, `ylabel` |

Segments that are not a `DataFrame` or shares that are not numbers raise `SourceTypeError`; a missing column, no segments and a share that is not finite raise `SourceError` before a figure is created. Labels that `merge_labels` refuses and an `ax` that is not a matplotlib `Axes` raise `ParameterError`.
<!-- --8<-- [end:zeta_scatter_plot] -->

## Mendenhall curves { #mendenhall_plot }

<!-- --8<-- [start:mendenhall_plot] -->
``` {.python .signature}
mendenhall_plot(corpus, ax=None, labels=None)
```

The shares of the words by length in characters (`mendenhall_curve`) of every text on one plot; a length no word has is drawn at zero.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `corpus` | `dict[str, list[str]]` | - | Words of the texts by the names of the texts |
| `ax` | `Axes` | `None` | Axes for the plot |
| `labels` | `dict[str, str]` | `None` | Labels over the defaults: `title`, `xlabel`, `ylabel` |

A corpus that is not a mapping of lists of strings raises `SourceTypeError`, no texts or a text without words `SourceError`; labels that `merge_labels` refuses and an `ax` that is not a matplotlib `Axes` raise `ParameterError`.
<!-- --8<-- [end:mendenhall_plot] -->

``` python
import matplotlib.pyplot as plt

from anyts.corpus import delta
from anyts.visualizers import dendrogram_plot, mds_plot, mendenhall_plot, pca_plot

corpus = {
    "A": "the cat sat on the mat and the cat slept".split(),
    "B": "a dog lay on a rug and a dog barked".split(),
    "C": "the cat and a dog sat on the rug".split(),
}
distances = delta(corpus, n_mfw=5)
fig, axes = plt.subplots(2, 2, figsize=(12, 10))
dendrogram_plot(distances, ax=axes[0, 0])
mds_plot(distances, ax=axes[0, 1])
pca_plot(corpus, n_mfw=5, ax=axes[1, 0])
mendenhall_plot(corpus, ax=axes[1, 1])
```

``` python
from anyts.corpus import rolling_delta, zeta, zeta_segments
from anyts.visualizers import delta_histogram_plot, rolling_delta_plot, zeta_scatter_plot

scores = zeta(corpus["A"], corpus["B"], segment_size=3)
preferred = [score.word for score in scores if score.zeta > 0]
avoided = [score.word for score in scores if score.zeta < 0]
fig, axes = plt.subplots(1, 3, figsize=(18, 5))
delta_histogram_plot(distances, {"A": "cat", "B": "dog", "C": "cat"}, bins=5, ax=axes[0])
rolling_delta_plot(
    rolling_delta(corpus, corpus["A"] + corpus["B"], window=5, step=1, n_mfw=5), ax=axes[1]
)
zeta_scatter_plot(zeta_segments(corpus, preferred, avoided, segment_size=3), ax=axes[2])
```
