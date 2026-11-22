from collections.abc import Mapping, Sequence

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
from matplotlib.ticker import MaxNLocator

from ..constants import VISUALIZER_LABELS
from ..exceptions import ParameterError, SourceError, SourceTypeError
from ..utils import check_sequence, merge_labels
from ._axes import check_axes

# Colors of an unstressed and of a stressed syllable
_COLORS = ("#d9d9d9", "#2f5d8a")


def rhythm_plot(
    patterns: Sequence[str],
    stressed: str,
    ax: Axes | None = None,
    labels: Mapping[str, str] | None = None,
) -> Axes:
    """
    Plotting the rhythm of the lines of a verse

    Description:
        A row per line and a cell per syllable of its pattern: the stressed
        syllables in one color, the others in another, nothing past the end of
        a line, so that the columns of a meter and its deviations show at a
        glance

    Arguments:
        patterns (list[str]): Patterns of the lines, a character per syllable
        stressed (str): Character of a stressed syllable in the patterns
        ax (Axes): Axes for the plot; if not given, a new figure is created
        labels (dict[str, str]): Labels over VISUALIZER_LABELS["rhythm_plot"]

    Returns:
        Axes: Axes with the plot

    Raises:
        SourceTypeError: If the patterns are not a list of strings
        SourceError: If there are no lines
        ParameterError: If stressed is not one character, the labels are set incorrectly
            (merge_labels) or ax is not a matplotlib Axes (check_axes)

    Example:
        >>> from anyts.visualizers import rhythm_plot
        >>> ax = rhythm_plot(["cCcCcCcC", "cCcCcccCc"], "C")
        >>> ax.get_images()[0].get_array().shape
        (2, 9)
    """
    captions = merge_labels(VISUALIZER_LABELS["rhythm_plot"], labels)
    check_sequence(patterns, "patterns of the lines")
    if not all(isinstance(pattern, str) for pattern in patterns):
        raise SourceTypeError("The patterns of the lines must be strings")
    if not patterns:
        raise SourceError("The rhythm needs at least one line")
    if not isinstance(stressed, str) or len(stressed) != 1:
        raise ParameterError(f"The stressed syllable must be one character, not {stressed!r}")
    check_axes(ax)
    if ax is None:
        _, ax = plt.subplots(layout="constrained")
    rows, columns = len(patterns), max(max(map(len, patterns)), 1)
    grid = np.full((rows, columns), np.nan)
    for row, pattern in enumerate(patterns):
        grid[row, : len(pattern)] = [syllable == stressed for syllable in pattern]
    ax.imshow(
        grid,
        cmap=ListedColormap(_COLORS),
        vmin=0,
        vmax=1,
        aspect="auto",
        interpolation="nearest",
        extent=(0.5, columns + 0.5, rows + 0.5, 0.5),
    )
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_xlabel(captions["xlabel"])
    ax.set_ylabel(captions["ylabel"])
    ax.set_title(captions["title"])
    ax.legend(
        handles=[
            Patch(color=_COLORS[1], label=captions["stressed"]),
            Patch(color=_COLORS[0], label=captions["unstressed"]),
        ],
        loc="upper left",
        bbox_to_anchor=(1, 1),
    )
    return ax
