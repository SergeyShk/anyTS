from collections.abc import Mapping, Sequence
from itertools import combinations
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import squareform

from ..constants import VISUALIZER_LABELS
from ..corpus.stylometry import frequency_table, mendenhall_curve, z_scores
from ..exceptions import ParameterError, SourceError, SourceTypeError
from ..utils import check_integer, merge_labels
from ._axes import check_axes

# Most bins of a histogram: matplotlib draws a patch for every one
_MAX_BINS = 1000
# Methods of scipy.cluster.hierarchy.linkage
_LINKAGE_METHODS = frozenset(
    ("average", "centroid", "complete", "median", "single", "ward", "weighted")
)


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
            in the rows and the columns, in any order
        method (str): Method of scipy.cluster.hierarchy.linkage to join the clusters
        ax (Axes): Axes for the plot; if not given, a new figure is created
        labels (dict[str, str]): Labels over VISUALIZER_LABELS["dendrogram_plot"]

    Returns:
        Axes: Axes with the dendrogram

    Raises:
        SourceTypeError: If the distances are not a DataFrame of numbers
        SourceError: If the matrix is not square, has fewer than two texts, other
            texts in the columns than in the rows, an infinite or negative distance,
            is not symmetric or has a distance on the diagonal
        ParameterError: If the method is unknown, the labels are set incorrectly (merge_labels)
            or ax is not a matplotlib Axes (check_axes)
    """
    captions = merge_labels(VISUALIZER_LABELS["dendrogram_plot"], labels)
    if not isinstance(method, str) or method not in _LINKAGE_METHODS:
        raise ParameterError(f"Unknown method of linkage: {method}")
    values = _distance_matrix(distances, "a dendrogram")
    check_axes(ax)
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 0.4 * len(distances) + 1.5), layout="constrained")
    condensed = squareform(values, checks=False)
    dendrogram(
        linkage(condensed, method=method), labels=list(distances.index), orientation="right", ax=ax
    )
    ax.set_xlabel(captions["xlabel"])
    ax.set_title(captions["title"])
    return ax


def _distance_matrix(distances: pd.DataFrame, purpose: str) -> np.ndarray:
    """
    Values of a matrix of distances between at least two texts, its columns in
    the order of its rows

    Description:
        The distances are finite and non-negative, the matrix symmetric with
        zeros on the diagonal, up to a rounding error
    """
    if not isinstance(distances, pd.DataFrame):
        raise SourceTypeError(
            f"The distances must be a DataFrame with the names of the texts, "
            f"not {type(distances).__name__}"
        )
    purpose = purpose.capitalize()
    if distances.shape[0] != distances.shape[1] or len(distances) < 2:
        raise SourceError(f"{purpose} needs a square matrix of at least two texts")
    if distances.index.has_duplicates or set(distances.columns) != set(distances.index):
        raise SourceError(f"{purpose} needs the same texts in the rows and the columns")
    try:
        values: np.ndarray = distances.loc[:, distances.index].to_numpy(dtype=float)
    except (TypeError, ValueError) as e:
        raise SourceTypeError("The distances must be numbers") from e
    if not np.isfinite(values).all():
        raise SourceError(f"{purpose} needs every distance to be finite")
    # A distance below zero by a rounding error only is zero
    if ((values < 0) & ~np.isclose(values, 0)).any():
        raise SourceError(f"{purpose} needs non-negative distances")
    if not np.allclose(values, values.T):
        raise SourceError(f"{purpose} needs a symmetric matrix of distances")
    if not np.allclose(np.diagonal(values), 0):
        raise SourceError(f"{purpose} needs zero distances on the diagonal")
    clipped: np.ndarray = np.clip(values, 0, None)
    return clipped


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
        SourceTypeError: If the corpus is not a mapping
        SourceError: If there are fewer than three texts
        ParameterError: If the labels are set incorrectly (merge_labels) or ax is not a matplotlib
            Axes (check_axes)
    """
    captions = merge_labels(VISUALIZER_LABELS["pca_plot"], labels, share=0.0)
    _check_corpus(corpus)
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
    check_axes(ax)
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


def _check_corpus(corpus: object) -> None:
    """Checking that a corpus is a mapping of the names of its texts to their units"""
    if not isinstance(corpus, Mapping):
        raise SourceTypeError(
            f"The corpus must be a mapping of the names of the texts to their units, "
            f"not {type(corpus).__name__}"
        )


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
            in the rows and the columns, in any order
        ax (Axes): Axes for the plot; if not given, a new figure is created
        labels (dict[str, str]): Labels over VISUALIZER_LABELS["mds_plot"]

    Returns:
        Axes: Axes with the plot

    Raises:
        SourceTypeError: If the distances are not a DataFrame of numbers
        SourceError: If the matrix is not square, has fewer than two texts, other
            texts in the columns than in the rows, an infinite or negative distance,
            is not symmetric or has a distance on the diagonal
        ParameterError: If the labels are set incorrectly (merge_labels) or ax is not a matplotlib
            Axes (check_axes)
    """
    captions = merge_labels(VISUALIZER_LABELS["mds_plot"], labels)
    squared = _distance_matrix(distances, "the scaling") ** 2
    n_texts = len(squared)
    centering = np.eye(n_texts) - np.ones((n_texts, n_texts)) / n_texts
    gram = -0.5 * centering @ squared @ centering
    eigenvalues, eigenvectors = np.linalg.eigh(gram)
    order = np.argsort(eigenvalues)[::-1][:2]
    coordinates = eigenvectors[:, order] * np.sqrt(np.clip(eigenvalues[order], 0, None))
    check_axes(ax)
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


def delta_histogram_plot(
    distances: pd.DataFrame,
    authors: Mapping[str, str],
    bins: int = 20,
    ax: Axes | None = None,
    labels: Mapping[str, str] | None = None,
) -> Axes:
    """
    Plotting the histograms of the distances within and between authors

    Description:
        The distances of the pairs of texts by one author against those of the
        pairs by different authors, as densities over common bins: the less the
        histograms overlap, the better the distances (delta) tell the authors apart

    Arguments:
        distances (DataFrame): Symmetric matrix of distances with the names of the texts
            in the rows and the columns, in any order
        authors (dict[str, str]): Authors of the texts by the names of the texts
        bins (int): Number of the bins, at most 1000
        ax (Axes): Axes for the plot; if not given, a new figure is created
        labels (dict[str, str]): Labels over VISUALIZER_LABELS["delta_histogram_plot"]

    Returns:
        Axes: Axes with the histograms

    Raises:
        SourceTypeError: If the distances are not a DataFrame of numbers or the
            authors are not a mapping
        SourceError: If the matrix fails the checks of dendrogram_plot, a text has
            no author, no two texts have one author or all of them have one
        ParameterError: If the number of the bins is not from 1 to 1000, the labels are set
            incorrectly (merge_labels) or ax is not a matplotlib Axes (check_axes)
    """
    captions = merge_labels(VISUALIZER_LABELS["delta_histogram_plot"], labels)
    check_integer(bins, "number of bins")
    if bins < 1:
        raise ParameterError("The number of bins must be greater than 0")
    if bins > _MAX_BINS:
        raise ParameterError(f"The number of bins must be at most {_MAX_BINS}, not {bins}")
    values = _distance_matrix(distances, "the histogram of the distances")
    if not isinstance(authors, Mapping):
        raise SourceTypeError(
            f"The authors must be a mapping of the names of the texts to their authors, "
            f"not {type(authors).__name__}"
        )
    names = list(distances.index)
    missing = [name for name in names if name not in authors]
    if missing:
        raise SourceError(f"The texts have no authors: {missing}")
    within: list[float] = []
    between: list[float] = []
    for first, second in combinations(range(len(names)), 2):
        same = authors[names[first]] == authors[names[second]]
        (within if same else between).append(values[first, second])
    if not within:
        raise SourceError("The histogram of the distances needs two texts by one author")
    if not between:
        raise SourceError("The histogram of the distances needs texts by different authors")
    check_axes(ax)
    if ax is None:
        _, ax = plt.subplots()
    edges = np.histogram_bin_edges(within + between, bins).tolist()
    ax.hist(within, edges, density=True, alpha=0.5, label=captions["within"])
    ax.hist(between, edges, density=True, alpha=0.5, label=captions["between"])
    ax.set_xlabel(captions["xlabel"])
    ax.set_ylabel(captions["ylabel"])
    ax.set_title(captions["title"])
    ax.legend()
    return ax


def rolling_delta_plot(
    distances: pd.DataFrame, ax: Axes | None = None, labels: Mapping[str, str] | None = None
) -> Axes:
    """
    Plotting the distances of rolling Delta along a text

    Description:
        A line of the distances to every reference text over the middles of the
        windows (rolling_delta): the lowest line is the nearest reference of a
        part of the text, and where the lines cross, the style changes

    Arguments:
        distances (DataFrame): Distances of rolling_delta, rows - the windows by
            the position of their middle, columns - the reference texts
        ax (Axes): Axes for the plot; if not given, a new figure is created
        labels (dict[str, str]): Labels over VISUALIZER_LABELS["rolling_delta_plot"]

    Returns:
        Axes: Axes with the lines

    Raises:
        SourceTypeError: If the distances are not a DataFrame of numbers with
            numbers in the index
        SourceError: If there are no windows or no reference texts, or a position is
            not finite or a distance is infinite or negative
        ParameterError: If the labels are set incorrectly (merge_labels) or ax is not a matplotlib
            Axes (check_axes)
    """
    captions = merge_labels(VISUALIZER_LABELS["rolling_delta_plot"], labels)
    if not isinstance(distances, pd.DataFrame):
        raise SourceTypeError(
            f"The distances must be a DataFrame with the windows in the rows, "
            f"not {type(distances).__name__}"
        )
    if distances.empty:
        raise SourceError("The rolling Delta needs a window and a reference text")
    try:
        positions = distances.index.to_numpy(dtype=float)
        values = distances.to_numpy(dtype=float)
    except (TypeError, ValueError) as e:
        raise SourceTypeError(
            "The positions of the windows and the distances must be numbers"
        ) from e
    if not np.isfinite(positions).all():
        raise SourceError("The rolling Delta needs every position of a window to be finite")
    if not np.isfinite(values).all():
        raise SourceError("The rolling Delta needs every distance to be finite")
    if ((values < 0) & ~np.isclose(values, 0)).any():
        raise SourceError("The rolling Delta needs non-negative distances")
    check_axes(ax)
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 5))
    names = [str(name) for name in distances.columns]
    lines = [
        ax.plot(positions, values[:, index], marker=".", label=name)[0]
        for index, name in enumerate(names)
    ]
    ax.set_xlabel(captions["xlabel"])
    ax.set_ylabel(captions["ylabel"])
    ax.set_title(captions["title"])
    _legend(ax, lines, names)
    return ax


def _legend(ax: Axes, handles: Sequence[Any], names: Sequence[str]) -> None:
    """A legend with the names as they are: matplotlib hides a label that starts with an
    underscore, so the legend is made with a zero-width space before it and given the name"""
    legend = ax.legend(handles, [f"\u200b{name}" for name in names])
    for text, name in zip(legend.get_texts(), names, strict=True):
        text.set_text(name)


def zeta_scatter_plot(
    segments: pd.DataFrame, ax: Axes | None = None, labels: Mapping[str, str] | None = None
) -> Axes:
    """
    Plotting the segments of corpora by the shares of the markers of Zeta

    Description:
        A point for every segment of zeta_segments, the share of the avoided
        words along the horizontal axis and of the preferred ones along the
        vertical axis, a colour for every corpus

    Arguments:
        segments (DataFrame): Segments of zeta_segments with the columns corpus,
            preferred and avoided
        ax (Axes): Axes for the plot; if not given, a new figure is created
        labels (dict[str, str]): Labels over VISUALIZER_LABELS["zeta_scatter_plot"]

    Returns:
        Axes: Axes with the points

    Raises:
        SourceTypeError: If the segments are not a DataFrame or their shares are not numbers
        SourceError: If a column is missing or repeated, there are no segments or a share
            is not finite
        ParameterError: If the labels are set incorrectly (merge_labels) or ax is not a matplotlib
            Axes (check_axes)
    """
    captions = merge_labels(VISUALIZER_LABELS["zeta_scatter_plot"], labels)
    if not isinstance(segments, pd.DataFrame):
        raise SourceTypeError(
            f"The segments must be a DataFrame of zeta_segments, not {type(segments).__name__}"
        )
    missing = [column for column in ("corpus", "preferred", "avoided") if column not in segments]
    if missing:
        raise SourceError(f"The segments have no columns {missing}")
    repeated = [
        column
        for column in ("corpus", "preferred", "avoided")
        if (segments.columns == column).sum() > 1
    ]
    if repeated:
        raise SourceError(f"The segments have repeated columns {repeated}")
    if segments.empty:
        raise SourceError("The plot needs at least one segment")
    try:
        shares = segments[["avoided", "preferred"]].to_numpy(dtype=float)
    except (TypeError, ValueError) as e:
        raise SourceTypeError("The shares of the markers must be numbers") from e
    if not np.isfinite(shares).all():
        raise SourceError("The plot needs every share to be finite")
    check_axes(ax)
    if ax is None:
        _, ax = plt.subplots(figsize=(7, 6))
    codes, corpora = pd.factorize(segments["corpus"], use_na_sentinel=False)
    names = [str(name) for name in corpora]
    points = [
        ax.scatter(shares[codes == code, 0], shares[codes == code, 1], label=name)
        for code, name in enumerate(names)
    ]
    ax.set_xlabel(captions["xlabel"])
    ax.set_ylabel(captions["ylabel"])
    ax.set_title(captions["title"])
    _legend(ax, points, names)
    return ax


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
        ParameterError: If the labels are set incorrectly (merge_labels) or ax is not a matplotlib
            Axes (check_axes)
    """
    captions = merge_labels(VISUALIZER_LABELS["mendenhall_plot"], labels)
    _check_corpus(corpus)
    if not corpus:
        raise SourceError("The corpus has no texts")
    curves = {name: mendenhall_curve(words) for name, words in corpus.items()}
    check_axes(ax)
    if ax is None:
        _, ax = plt.subplots()
    names = [str(name) for name in curves]
    lines = []
    for name, curve in zip(names, curves.values(), strict=True):
        lengths = range(1, max(curve) + 1)
        shares = [curve.get(length, 0.0) for length in lengths]
        lines.append(ax.plot(list(lengths), shares, marker=".", label=name)[0])
    ax.set_xlabel(captions["xlabel"])
    ax.set_ylabel(captions["ylabel"])
    ax.set_title(captions["title"])
    _legend(ax, lines, names)
    return ax
