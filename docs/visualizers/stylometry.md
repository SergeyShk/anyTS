# Stylometric plots

!!! info ""
    **anyts.visualizers.dendrogram_plot()**, **anyts.visualizers.pca_plot()**, **anyts.visualizers.mds_plot()**, **anyts.visualizers.mendenhall_plot()**

## Description

Plots for [stylometry](../corpus/stylometry.md): a dendrogram and the multidimensional scaling of the matrix of distances of `delta`, the principal components of the frequencies of the most frequent words and the Mendenhall curves of several texts. The functions take the axes `ax` and return `Axes`.

## Dendrogram { #dendrogram_plot }

<!-- --8<-- [start:dendrogram_plot] -->
Hierarchical clustering by `scipy.cluster.hierarchy` over the matrix of distances between texts; Ward's method by default, as in [Evert et al. (2015)](https://aclanthology.org/W15-0709.pdf); the labels of the leaves are the names of the texts of the index of the matrix.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `distances` | DataFrame | `-` | Symmetric matrix of distances with the names of the texts |
| `method` | str | `ward` | Method of `scipy.cluster.hierarchy.linkage` to join the clusters |
| `ax` | Axes | `None` | Axes for the plot |
| `labels` | dict[str, str] | `None` | Labels over the defaults: `title`, `xlabel` |
<!-- --8<-- [end:dendrogram_plot] -->

## Principal components { #pca_plot }

<!-- --8<-- [start:pca_plot] -->
Principal component analysis of the z-scores of the relative frequencies of the most frequent units (`frequency_table`, `z_scores`): the texts on the plane of the first two components with their names, the shares of the explained variance in the labels of the axes.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `corpus` | dict[str, list[str]] | `-` | Units of the texts by the names of the texts |
| `n_mfw` | int | `100` | Number of the most frequent units; `None` - all of them |
| `culling` | float | `0.0` | Smallest share of the texts a unit occurs in |
| `ax` | Axes | `None` | Axes for the plot |
| `labels` | dict[str, str] | `None` | Labels over the defaults: `title`, `xlabel` and `ylabel` (format strings with the explained `share`) |
<!-- --8<-- [end:pca_plot] -->

## Multidimensional scaling { #mds_plot }

<!-- --8<-- [start:mds_plot] -->
Classical multidimensional scaling (Torgerson 1952) of any matrix of distances: the double centering of the matrix of squared distances and the two leading eigenvectors; the distances between the points approximate the distances of the matrix.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `distances` | DataFrame | `-` | Symmetric matrix of distances with the names of the texts |
| `ax` | Axes | `None` | Axes for the plot |
| `labels` | dict[str, str] | `None` | Labels over the defaults: `title`, `xlabel`, `ylabel` |
<!-- --8<-- [end:mds_plot] -->

## Mendenhall curves { #mendenhall_plot }

<!-- --8<-- [start:mendenhall_plot] -->
The shares of the words by length in characters (`mendenhall_curve`) of every text on one plot; a length no word has is drawn at zero.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `corpus` | dict[str, list[str]] | `-` | Words of the texts by the names of the texts |
| `ax` | Axes | `None` | Axes for the plot |
| `labels` | dict[str, str] | `None` | Labels over the defaults: `title`, `xlabel`, `ylabel` |
<!-- --8<-- [end:mendenhall_plot] -->

## Usage example

!!! example "Example"

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
