from collections import Counter
from collections.abc import Iterable, Iterator, Mapping, Sequence
from math import isfinite, isnan, log2, nan

import matplotlib.pyplot as plt
from graphviz import Graph, escape
from matplotlib.axes import Axes
from matplotlib.patches import Patch

from ..constants import VISUALIZER_LABELS
from ..corpus.collocations import Collocation
from ..corpus.keyness import Keyword
from ..exceptions import ParameterError, SourceError
from ..utils import check_integer, check_sequence, check_words, merge_labels
from ._axes import check_axes


def dispersion_plot(
    words: Sequence[str],
    targets: Sequence[str],
    ax: Axes | None = None,
    labels: Mapping[str, str] | None = None,
) -> Axes:
    """
    Plotting the lexical dispersion of words over a text

    Description:
        A row for every word of targets and a tick at the position of each of
        its occurrences in the text; words are compared as they are, so case and
        lemmatization belong to the extraction

    Arguments:
        words (list[str]): Words of the text in order
        targets (list[str]): Words whose occurrences are shown
        ax (Axes): Axes for the plot; if not given, a new figure is created
        labels (dict[str, str]): Labels over VISUALIZER_LABELS["dispersion_plot"]

    Returns:
        Axes: Axes with the plot

    Raises:
        SourceTypeError: If the words or the target words are not a list of strings
        SourceError: If there are no words or no target words
        ParameterError: If the labels are set incorrectly (merge_labels) or ax is not a matplotlib
            Axes (check_axes)
    """
    captions = merge_labels(VISUALIZER_LABELS["dispersion_plot"], labels)
    check_words(words)
    check_words(targets, "target words")
    if not words or not targets:
        raise SourceError("The data source has no words")
    positions = [
        [index for index, word in enumerate(words) if word == target] for target in targets
    ]
    check_axes(ax)
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 0.4 * len(targets) + 1.5), layout="constrained")
    ax.eventplot(
        positions,
        lineoffsets=range(len(targets)),
        linelengths=0.8,
        linewidths=0.8,
        colors="tab:blue",
    )
    ax.set_yticks(range(len(targets)), labels=list(targets))
    ax.invert_yaxis()
    ax.set_xlim(0, len(words))
    ax.set_xlabel(captions["xlabel"])
    ax.set_title(captions["title"])
    return ax


def keyness_plot(
    positive: Iterable[Keyword],
    negative: Iterable[Keyword] = (),
    top_n: int = 20,
    labels: tuple[str, str] | Mapping[str, str] | None = None,
    field: str = "score",
    log: bool = False,
    ax: Axes | None = None,
) -> Axes:
    """
    Plotting a chart of keywords

    Description:
        Diverging horizontal bars: the words of positive to the right, of
        negative to the left, the length of a bar is the absolute value of the
        field, so the side is set by the list and not by the sign of the
        measure; the words with an undefined or infinite value are skipped

    Arguments:
        positive (list[Keyword]): Positive keywords (keyness)
        negative (list[Keyword]): Negative keywords (keyness with positive=False)
        top_n (int): Number of words on each side
        labels (tuple[str, str]|dict[str, str]): Labels over VISUALIZER_LABELS["keyness_plot"],
            or a pair of the labels of the legend for the target and the reference corpus
        field (str): Field of Keyword whose values are plotted
        log (bool): Plot log2 of the value - for the odds ratio
        ax (Axes): Axes for the plot; if not given, a new figure is created

    Returns:
        Axes: Axes with the chart

    Raises:
        SourceTypeError: If the keywords are not a list (check_sequence)
        ParameterError: If the field is unknown, top_n is not an integer or is below one, the
            labels are set incorrectly (merge_labels) or ax is not a matplotlib Axes (check_axes)
        SourceError: If there are no keywords or the measure of every one is undefined
    """
    if isinstance(positive, Iterator):
        positive = list(positive)
    if isinstance(negative, Iterator):
        negative = list(negative)
    check_sequence(positive, "keywords")
    check_sequence(negative, "keywords")
    if isinstance(labels, Sequence) and not isinstance(labels, str):
        if len(labels) != 2:
            raise ParameterError("The labels of the legend must be a pair of strings")
        labels = {"target": labels[0], "reference": labels[1]}
    captions = merge_labels(VISUALIZER_LABELS["keyness_plot"], labels, field="score")
    if not isinstance(field, str) or field not in Keyword._fields[1:]:
        raise ParameterError(f"Unknown field of a keyword: {field}")
    check_integer(top_n, "number of words")
    if top_n < 1:
        raise ParameterError("The number of words must be greater than 0")
    top = _bars(positive, field, log, 1)[:top_n]
    bottom = _bars(negative, field, log, -1)[:top_n]
    keywords = top + bottom[::-1]
    if not keywords:
        raw = list(positive) + list(negative)
        raise SourceError(
            "The data source has no words" if not raw else "The measure is undefined"
        )
    check_axes(ax)
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 0.3 * len(keywords) + 1.5), layout="constrained")
    rows = range(len(keywords))
    colors = ["tab:blue"] * len(top) + ["tab:red"] * len(bottom)
    ax.barh(rows, [value for _, value in keywords], color=colors)
    ax.set_yticks(rows, labels=[keyword.word for keyword, _ in keywords])
    ax.invert_yaxis()
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel(captions["xlabel_log" if log else "xlabel"].format(field=field))
    ax.set_title(captions["title"])
    handles = []
    legend_labels = []
    if top:
        handles.append(Patch(color="tab:blue"))
        legend_labels.append(captions["target"])
    if bottom:
        handles.append(Patch(color="tab:red"))
        legend_labels.append(captions["reference"])
    ax.legend(handles, legend_labels)
    return ax


def _bars(
    keywords: Iterable[Keyword], field: str, log: bool, sign: int
) -> list[tuple[Keyword, float]]:
    """Keywords with the signed length of their bars, those with an undefined value skipped"""
    bars = []
    for keyword in keywords:
        value = float(getattr(keyword, field))
        if log:
            value = log2(value) if value > 0 else nan
        if isfinite(value):
            bars.append((keyword, sign * abs(value)))
    return bars


def collocation_network(collocations: Iterable[Collocation], top_n: int | None = None) -> Graph:
    """
    Building the network of collocations

    Description:
        An undirected graph in the neato layout: the nodes are the words with
        the size of the font by frequency, the edges the pairs with the width
        and the label by the value of the measure. The pairs of a word with
        itself are left out before top_n. The format is png; rendering needs the
        executables of Graphviz

    Arguments:
        collocations (list[Collocation]): Collocations (collocations)
        top_n (int): Number of pairs from the start of the list, the pairs of a word
            with itself left out; None - all of them

    Returns:
        Graph: Graph of graphviz

    Raises:
        SourceTypeError: If the collocations are not a list (check_sequence)
        ParameterError: If top_n is not an integer or is below one
        SourceError: If there are no collocations

    Example:
        >>> from anyts.corpus import collocations
        >>> from anyts.visualizers import collocation_network
        >>> words = "red wine and white wine but red wine".split()
        >>> print(collocation_network(collocations(words, window=1)).source)
        graph collocations {
            graph [overlap=false splines=true]
            node [fontname=Helvetica margin=0 shape=plaintext]
            edge [color=gray50 fontname=Helvetica fontsize=9]
            n0 [label=red fontsize=10]
            n1 [label=wine fontsize=24]
            n0 -- n1 [label=13.68 penwidth=2.25]
        }
        <BLANKLINE>
    """
    if isinstance(collocations, Iterator):
        collocations = list(collocations)
    check_sequence(collocations, "collocations")
    if top_n is not None:
        check_integer(top_n, "number of pairs")
        if top_n < 1:
            raise ParameterError("The number of pairs must be greater than 0")
    pairs = [pair for pair in collocations if pair.left != pair.right]
    pairs = pairs[:top_n] if top_n else pairs
    if not pairs:
        raise SourceError("The data source has no collocations")
    frequencies: Counter[str] = Counter()
    for pair in pairs:
        frequencies[pair.left] = max(frequencies[pair.left], pair.freq_left)
        frequencies[pair.right] = max(frequencies[pair.right], pair.freq_right)
    scores = [pair.score for pair in pairs if not isnan(pair.score)]
    min_score, max_score = (min(scores), max(scores)) if scores else (0.0, 0.0)
    min_freq, max_freq = min(frequencies.values()), max(frequencies.values())
    graph = Graph("collocations", engine="neato", format="png")
    graph.attr("graph", overlap="false", splines="true")
    graph.attr("node", shape="plaintext", margin="0", fontname="Helvetica")
    graph.attr("edge", color="gray50", fontsize="9", fontname="Helvetica")
    nodes = {word: f"n{index}" for index, word in enumerate(frequencies)}
    for word, frequency in frequencies.items():
        graph.node(
            nodes[word],
            label=escape(word),
            fontsize=f"{_scale(frequency, min_freq, max_freq, 10, 24):.0f}",
        )
    for pair in pairs:
        score = 0.0 if isnan(pair.score) else pair.score
        graph.edge(
            nodes[pair.left],
            nodes[pair.right],
            label=f"{score:.2f}",
            penwidth=f"{_scale(score, min_score, max_score, 0.5, 4):.2f}",
        )
    return graph


def _scale(value: float, low: float, high: float, out_low: float, out_high: float) -> float:
    """Linear map of a value from [low, high] to [out_low, out_high], the middle when low = high"""
    if high <= low:
        return (out_low + out_high) / 2
    return out_low + (value - low) / (high - low) * (out_high - out_low)
