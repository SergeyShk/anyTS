from collections.abc import Mapping, Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import squareform

from ..constants import VISUALIZER_LABELS
from ..corpus.stylometry import frequency_table, mendenhall_curve, z_scores
from ..exceptions import SourceError, SourceTypeError
from ..utils import merge_labels


def dendrogram_plot(
    distances: pd.DataFrame,
    method: str = "ward",
    ax: Axes | None = None,
    labels: Mapping[str, str] | None = None,
) -> Axes:
    """
    Plotting a dendrogram from the matrix of distances between texts

    Description:
        Hierarchical clustering of scipy over the matrix of distances (delta);
        the labels of the leaves are the names of the texts of the index

    Arguments:
        distances (DataFrame): Symmetric matrix of distances with the names of the texts
        method (str): Method of scipy.cluster.hierarchy.linkage to join the clusters
        ax (Axes): Axes for the plot; if not given, a new figure is created
        labels (dict[str, str]): Labels over VISUALIZER_LABELS["dendrogram_plot"]

    Returns:
        Axes: Axes with the dendrogram

    Raises:
        SourceError: If the matrix is not square, has fewer than two texts or
            an infinite distance
        ParameterError: If the labels are set incorrectly (merge_labels)
    """
    captions = merge_labels(VISUALIZER_LABELS["dendrogram_plot"], labels)
    values = _distance_matrix(distances, "a dendrogram")
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 0.4 * len(distances) + 1.5))
    condensed = squareform(values, checks=False)
    dendrogram(
        linkage(condensed, method=method), labels=list(distances.index), orientation="right", ax=ax
    )
    ax.set_xlabel(captions["xlabel"])
    ax.set_title(captions["title"])
    return ax


def pca_plot(
    corpus: Mapping[str, Sequence[str]],
    n_mfw: int | None = 100,
    culling: float = 0.0,
    ax: Axes | None = None,
    labels: Mapping[str, str] | None = None,
) -> Axes:
    """
    Plotting the principal components of the frequencies of the most frequent units

    Description:
        Principal component analysis of the z-scores of the relative
        frequencies (frequency_table, z_scores): the texts on the plane of the
        first two components, the shares of the explained variance in the
        labels of the axes

    Arguments:
        corpus (dict[str, list[str]]): Units of the texts by the names of the texts
        n_mfw (int): Number of the most frequent units; None - all of them
        culling (float): Smallest share of the texts a unit occurs in
        ax (Axes): Axes for the plot; if not given, a new figure is created
        labels (dict[str, str]): Labels over VISUALIZER_LABELS["pca_plot"]

    Returns:
        Axes: Axes with the plot

    Raises:
        SourceError: If there are fewer than three texts
        ParameterError: If the labels are set incorrectly (merge_labels)
    """
    captions = merge_labels(VISUALIZER_LABELS["pca_plot"], labels)
    if len(corpus) < 3:
        raise SourceError("The principal components need at least three texts")
    scores = z_scores(frequency_table(corpus, n_mfw, culling))
    values = scores.to_numpy(dtype=float)
    left, singular, _ = np.linalg.svd(values, full_matrices=False)
    components = left[:, :2] * singular[:2]
    if components.shape[1] < 2:
        components = np.hstack([components, np.zeros((len(components), 1))])
    variance = singular**2 / (singular**2).sum() if singular.any() else np.zeros(2)
    explained = list(variance[:2]) + [0.0] * (2 - min(len(variance), 2))
    if ax is None:
        _, ax = plt.subplots(figsize=(7, 6))
    ax.scatter(components[:, 0], components[:, 1], color="tab:blue")
    for name, (x, y) in zip(scores.index, components, strict=True):
        ax.annotate(str(name), (x, y), xytext=(4, 4), textcoords="offset points")
    ax.axhline(0, color="gray", linewidth=0.5)
    ax.axvline(0, color="gray", linewidth=0.5)
    ax.set_xlabel(captions["xlabel"].format(share=explained[0]))
    ax.set_ylabel(captions["ylabel"].format(share=explained[1]))
    ax.set_title(captions["title"])
    return ax


def mds_plot(
    distances: pd.DataFrame, ax: Axes | None = None, labels: Mapping[str, str] | None = None
) -> Axes:
    """
    Plotting the multidimensional scaling of a matrix of distances

    Description:
        Classical multidimensional scaling (Torgerson 1952): the texts on the
        plane, the distances between the points approximate the distances of
        the matrix (delta)

    Arguments:
        distances (DataFrame): Symmetric matrix of distances with the names of the texts
        ax (Axes): Axes for the plot; if not given, a new figure is created
        labels (dict[str, str]): Labels over VISUALIZER_LABELS["mds_plot"]

    Returns:
        Axes: Axes with the plot

    Raises:
        SourceError: If the matrix is not square, has fewer than two texts or
            an infinite distance
        ParameterError: If the labels are set incorrectly (merge_labels)
    """
    captions = merge_labels(VISUALIZER_LABELS["mds_plot"], labels)
    squared = _distance_matrix(distances, "the scaling") ** 2
    n_texts = len(squared)
    centering = np.eye(n_texts) - np.ones((n_texts, n_texts)) / n_texts
    gram = -0.5 * centering @ squared @ centering
    eigenvalues, eigenvectors = np.linalg.eigh(gram)
    order = np.argsort(eigenvalues)[::-1][:2]
    coordinates = eigenvectors[:, order] * np.sqrt(np.clip(eigenvalues[order], 0, None))
    if ax is None:
        _, ax = plt.subplots(figsize=(7, 6))
    ax.scatter(coordinates[:, 0], coordinates[:, 1], color="tab:blue")
    for name, (x, y) in zip(distances.index, coordinates, strict=True):
        ax.annotate(str(name), (x, y), xytext=(4, 4), textcoords="offset points")
    ax.axhline(0, color="gray", linewidth=0.5)
    ax.axvline(0, color="gray", linewidth=0.5)
    ax.set_xlabel(captions["xlabel"])
    ax.set_ylabel(captions["ylabel"])
    ax.set_title(captions["title"])
    return ax


def _distance_matrix(distances: pd.DataFrame, purpose: str) -> np.ndarray:
    """Values of a square matrix of finite distances between at least two texts"""
    values = np.asarray(distances.to_numpy(dtype=float), dtype=float)
    if values.ndim != 2 or values.shape[0] != values.shape[1] or len(values) < 2:
        raise SourceError(f"{purpose.capitalize()} needs a square matrix of at least two texts")
    if not np.isfinite(values).all():
        raise SourceError(f"{purpose.capitalize()} needs every distance to be finite")
    return values


def mendenhall_plot(
    corpus: Mapping[str, Sequence[str]],
    ax: Axes | None = None,
    labels: Mapping[str, str] | None = None,
) -> Axes:
    """
    Plotting the Mendenhall curves of several texts

    Description:
        The shares of the words by length in characters (mendenhall_curve)
        of every text on one plot; a length no word has is drawn at zero

    Arguments:
        corpus (dict[str, list[str]]): Words of the texts by the names of the texts
        ax (Axes): Axes for the plot; if not given, a new figure is created
        labels (dict[str, str]): Labels over VISUALIZER_LABELS["mendenhall_plot"]

    Returns:
        Axes: Axes with the curves

    Raises:
        SourceTypeError: If the corpus is not a mapping
        SourceError: If there are no texts or one of them has no words
        ParameterError: If the labels are set incorrectly (merge_labels)
    """
    captions = merge_labels(VISUALIZER_LABELS["mendenhall_plot"], labels)
    if not isinstance(corpus, Mapping):
        raise SourceTypeError(
            f"The corpus must be a mapping of the names of the texts to their words, "
            f"not {type(corpus).__name__}"
        )
    if not corpus:
        raise SourceError("The corpus has no texts")
    curves = {name: mendenhall_curve(words) for name, words in corpus.items()}
    if ax is None:
        _, ax = plt.subplots()
    for name, curve in curves.items():
        lengths = range(1, max(curve) + 1)
        shares = [curve.get(length, 0.0) for length in lengths]
        ax.plot(list(lengths), shares, marker=".", label=str(name))
    ax.set_xlabel(captions["xlabel"])
    ax.set_ylabel(captions["ylabel"])
    ax.set_title(captions["title"])
    ax.legend()
    return ax
