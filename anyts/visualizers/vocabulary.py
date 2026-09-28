from collections.abc import Mapping, Sequence

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes

from ..constants import VISUALIZER_LABELS
from ..diversity_stats import calc_frequency_spectrum, fit_heaps, vocabulary_growth
from ..exceptions import SourceError
from ..utils import check_words, merge_labels


def heaps_plot(
    words: Sequence[str], ax: Axes | None = None, labels: Mapping[str, str] | None = None
) -> Axes:
    """
    Plotting Heaps' law - the growth of the vocabulary with the length of a text

    Description:
        The size of the vocabulary V after every word of the text
        (vocabulary_growth) and the fitted curve V(N) = K · N^β (fit_heaps)
        with its parameters in the legend

    Arguments:
        words (list[str]): Words of the text in order
        ax (Axes): Axes for the plot; if not given, a new figure is created
        labels (dict[str, str]): Labels over VISUALIZER_LABELS["heaps_plot"]

    Returns:
        Axes: Axes with the plot

    Raises:
        SourceTypeError: If the words are not a list of strings
        SourceError: If there are fewer than two words
        ParameterError: If the labels are set incorrectly (merge_labels)
    """
    captions = merge_labels(VISUALIZER_LABELS["heaps_plot"], labels, k=0.0, beta=0.0)
    check_words(words)
    if len(words) < 2:
        raise SourceError("The growth of the vocabulary needs at least two words")
    if ax is None:
        _, ax = plt.subplots()
    lengths = np.arange(1, len(words) + 1)
    ax.plot(lengths, vocabulary_growth(words), label=captions["growth"])
    fit = fit_heaps(words)
    ax.plot(
        lengths,
        fit.k * lengths**fit.beta,
        linestyle="--",
        color="r",
        label=captions["fit"].format(k=fit.k, beta=fit.beta),
    )
    ax.set_xlabel(captions["xlabel"])
    ax.set_ylabel(captions["ylabel"])
    ax.set_title(captions["title"])
    ax.grid()
    ax.legend()
    return ax


def frequency_spectrum_plot(
    words: Sequence[str], ax: Axes | None = None, labels: Mapping[str, str] | None = None
) -> Axes:
    """
    Plotting the frequency spectrum - the number of word types by frequency

    Description:
        The number of word types V(m) that occur exactly m times
        (calc_frequency_spectrum) in logarithmic coordinates; the left edge is
        the hapaxes

    Arguments:
        words (list[str]): Words of the text
        ax (Axes): Axes for the plot; if not given, a new figure is created
        labels (dict[str, str]): Labels over VISUALIZER_LABELS["frequency_spectrum_plot"]

    Returns:
        Axes: Axes with the plot

    Raises:
        SourceTypeError: If the words are not a list of strings
        SourceError: If there are no words
        ParameterError: If the labels are set incorrectly (merge_labels)
    """
    captions = merge_labels(VISUALIZER_LABELS["frequency_spectrum_plot"], labels)
    check_words(words)
    if not words:
        raise SourceError("The data source has no words")
    if ax is None:
        _, ax = plt.subplots()
    spectrum = calc_frequency_spectrum(words)
    frequencies = sorted(spectrum)
    ax.loglog(frequencies, [spectrum[m] for m in frequencies], marker="o", linestyle="")
    ax.set_xlabel(captions["xlabel"])
    ax.set_ylabel(captions["ylabel"])
    ax.set_title(captions["title"])
    ax.grid()
    return ax
