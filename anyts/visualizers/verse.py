from collections.abc import Mapping, Sequence
from numbers import Integral

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch

from ..constants import VISUALIZER_LABELS
from ..exceptions import SourceError, SourceTypeError
from ..utils import check_sequence, merge_labels
from ._axes import check_axes

# Colors of an unstressed and of a stressed syllable
_COLORS = ("#d9d9d9", "#2f5d8a")


def rhythm_plot(
    stresses: Sequence[Sequence[int]],
    lengths: Sequence[int],
    ax: Axes | None = None,
    labels: Mapping[str, str] | None = None,
) -> Axes:
    """
    Plotting the rhythm of the lines of a verse

    Description:
        A row per line and a cell per syllable: the stressed syllables in
        one color, the unstressed in another, nothing past the end of a line,
        so that the columns of a meter and its deviations show at a glance

    Arguments:
        stresses (list[list[int]]): Indices of the stressed syllables of every line, from 0
        lengths (list[int]): Number of the syllables of every line
        ax (Axes): Axes for the plot; if not given, a new figure is created
        labels (dict[str, str]): Labels over VISUALIZER_LABELS["rhythm_plot"]

    Returns:
        Axes: Axes with the plot

    Raises:
        SourceTypeError: If the stresses or the lengths are not lists of integers
        SourceError: If there are no lines, the stresses and the lengths differ in
            number, a length is negative or a stress lies outside its line
        ParameterError: If the labels are set incorrectly (merge_labels) or ax is not a matplotlib
            Axes (check_axes)

    Example:
        >>> from anyts.visualizers import rhythm_plot
        >>> ax = rhythm_plot([(1, 3, 5, 7), (1, 3, 7)], [8, 9])
        >>> ax.get_images()[0].get_array().shape
        (2, 9)
    """
    captions = merge_labels(VISUALIZER_LABELS["rhythm_plot"], labels)
    check_sequence(stresses, "stresses of the lines")
    check_sequence(lengths, "lengths of the lines")
    lines = [list(line) for line in stresses]
    if not lines:
        raise SourceError("The rhythm needs at least one line")
    if len(lines) != len(lengths):
        raise SourceError(
            f"The stresses and the lengths must be one per line: {len(lines)} and {len(lengths)}"
        )
    values: list[object] = [*lengths, *(index for line in lines for index in line)]
    for value in values:
        if isinstance(value, bool) or not isinstance(value, Integral):
            raise SourceTypeError("The stresses and the lengths must be integers")
    for line, length in zip(lines, lengths, strict=True):
        if length < 0 or any(not 0 <= index < length for index in line):
            raise SourceError("Every stress must lie within its line of a non-negative length")
    check_axes(ax)
    if ax is None:
        _, ax = plt.subplots()
    grid = np.full((len(lines), max(max(lengths), 1)), np.nan)
    for row, (line, length) in enumerate(zip(lines, lengths, strict=True)):
        grid[row, :length] = 0
        grid[row, line] = 1
    ax.imshow(grid, cmap=ListedColormap(_COLORS), vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(grid.shape[1]), [str(number) for number in range(1, grid.shape[1] + 1)])
    ax.set_yticks(range(len(lines)), [str(number) for number in range(1, len(lines) + 1)])
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
