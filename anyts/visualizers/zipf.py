from collections import Counter
from collections.abc import Mapping

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes

from ..constants import VISUALIZER_LABELS
from ..diversity_stats import fit_zipf_mandelbrot
from ..exceptions import ParameterError, SourceError, SourceTypeError
from ..utils import check_integer, check_number, merge_labels


def zipf(
    counter: Counter[str],
    num_words: int | None = None,
    num_labels: int = 10,
    log: bool = True,
    show_theory: bool = False,
    alpha: float = 1.5,
    show_fit: bool = False,
    ax: Axes | None = None,
    labels: Mapping[str, str] | None = None,
) -> Axes:
    """
    Plotting Zipf's law from a counter of the frequencies of words

    Description:
        The frequencies of the words by rank; show_theory adds the curve of
        zipf_theory, show_fit the Zipf-Mandelbrot law f(r) = C / (r + q)^s
        fitted by fit_zipf_mandelbrot

    Arguments:
        counter (Counter): Counter of the frequencies of words
        num_words (int): Number of the most frequent words; at most the size of the counter
        num_labels (int): Number of the words labelled on the plot
        log (bool): Use a logarithmic scale
        show_theory (bool): Show the curve of the theoretical Zipf's law
        alpha (float): Exponent α of the theoretical Zipf's law
        show_fit (bool): Show the fitted curve of the Zipf-Mandelbrot law
        ax (Axes): Axes for the plot; if not given, a new figure is created
        labels (dict[str, str]): Labels over VISUALIZER_LABELS["zipf"]

    Returns:
        Axes: Axes with the plot of Zipf's law

    Raises:
        SourceTypeError: If the value is not a Counter object
        SourceError: If the counter is empty
        ParameterError: If the number of words or of labels is not an integer, the number
            of words is below one, the exponent α of the shown theoretical law is not
            a number above zero or the labels are set incorrectly (merge_labels)
    """
    captions = merge_labels(VISUALIZER_LABELS["zipf"], labels)
    if not isinstance(counter, Counter):
        raise SourceTypeError("The counter of the frequencies of words must be a Counter object")
    if not counter:
        raise SourceError("The data source has no words")
    if num_words is not None:
        check_integer(num_words, "number of words")
        if num_words < 1:
            raise ParameterError("The number of words must be greater than 0")
    check_integer(num_labels, "number of labels")
    if show_theory:
        _check_alpha(alpha)
    if ax is None:
        _, ax = plt.subplots()
    top_frequency = counter.most_common(1)[0][1]
    num_words = min(num_words, len(counter)) if num_words else len(counter)
    frequencies_by_token = dict(counter.most_common(num_words))
    counts = np.array(tuple(frequencies_by_token.values()))
    tokens = np.array(tuple(frequencies_by_token.keys()))
    ranks = np.arange(1, counts.size + 1)
    plot = ax.loglog if log else ax.plot
    plot(ranks, counts, marker=".", label=captions["experimental"])
    if num_labels > 0:
        positions = (
            np.logspace(-0.5, np.log10(len(counts) - 1), num_labels).astype(int)
            if len(counts) > 1
            else np.zeros(1, dtype=int)
        )
        for n in np.unique(positions):
            ax.text(
                ranks[n],
                counts[n],
                " " + tokens[n],
                verticalalignment="bottom",
                horizontalalignment="left",
            )
    ax.set_title(captions["title"])
    ax.set_xlabel(captions["xlabel"])
    ax.set_ylabel(captions["ylabel"])
    ax.grid()
    if show_theory:
        zipf_theory(
            top_frequency, num_words, alpha, ax=ax, labels={"theoretical": captions["theoretical"]}
        )
    if show_fit:
        fit = fit_zipf_mandelbrot(counter)
        if not np.isnan(fit.s):
            ax.plot(
                ranks,
                fit.c / (ranks + fit.q) ** fit.s,
                linewidth=2,
                color="g",
                linestyle="--",
                label=captions["fit"].format(q=fit.q, s=fit.s),
            )
    if show_theory or show_fit:
        ax.legend()
    return ax


def zipf_theory(
    size: int,
    num_ranks: int,
    alpha: float = 1.5,
    ax: Axes | None = None,
    labels: Mapping[str, str] | None = None,
) -> Axes:
    """
    Plotting the theoretical Zipf's law with the given parameters

    Description:
        The frequency of rank r is size · r^(-α)

    Arguments:
        size (int): Frequency of the first rank
        num_ranks (int): Number of ranks
        alpha (float): Exponent α
        ax (Axes): Axes for the plot; if not given, a new figure is created
        labels (dict[str, str]): Labels over VISUALIZER_LABELS["zipf_theory"]

    Returns:
        Axes: Axes with the plot of the theoretical Zipf's law

    Raises:
        ParameterError: If the number of ranks is not an integer or is below one, the
            frequency is not a number, the exponent is not a number above zero or
            the labels are set incorrectly
    """
    captions = merge_labels(VISUALIZER_LABELS["zipf_theory"], labels)
    check_integer(num_ranks, "number of ranks")
    if num_ranks < 1:
        raise ParameterError("The number of ranks must be greater than 0")
    check_number(size, "frequency of the first rank")
    _check_alpha(alpha)
    if ax is None:
        _, ax = plt.subplots()
    x = np.arange(1, num_ranks + 1)
    ax.plot(x, size * x ** (-alpha), linewidth=2, color="r", label=captions["theoretical"])
    return ax


def _check_alpha(alpha: float) -> None:
    """Checking the exponent α of the theoretical Zipf's law"""
    check_number(alpha, "exponent α")
    if alpha <= 0:
        raise ParameterError("The exponent α must be greater than 0")
