from collections.abc import Callable, Mapping, Sequence
from math import ceil

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
from mpl_toolkits.axes_grid1 import make_axes_locatable

from ..constants import VISUALIZER_LABELS
from ..diversity_stats import calc_ttr
from ..exceptions import ParameterError, SourceError, SourceTypeError
from ..utils import check_integer, check_sequence, check_words, merge_labels

# Size of a square and the margin between blocks, in the units of the drawing area
SQUARE = 15
MARGIN = 25
# Colour of the empty cells of a block and of the undefined measure
MISSING_COLOR = "lightgray"


def fingerprinting(
    texts: list[list[str]],
    segment_len: int = 10,
    metric: Callable[[Sequence[str]], float] | None = None,
    x_size: int = 800,
    y_size: int = 600,
    cmap: str = "viridis",
    ax: Axes | None = None,
    labels: Mapping[str, str] | None = None,
) -> Axes:
    """
    Visualizing literature fingerprinting

    Description:
        Every text is cut into segments of segment_len words with a sliding
        step of a tenth of a segment, the last one ending with the text, and
        the measure is computed for every segment. A text is a block of squares in the order of its segments,
        row by row, 8 rows high, or a single column when it has at most 8
        segments. The blocks are laid out left to right in an area 2 · x_size
        wide, which grows downwards from 2 · y_size when they need more height.
        The colour scale runs from the smallest to the greatest finite value
        over all the texts; undefined values (nan) and the empty cells of a
        block are light grey

    References:
        https://www.uni-konstanz.de/mmsp/pubsys/publishedFiles/KeOe07.pdf

    Arguments:
        texts (list[list[str]]): List of lists of words
        segment_len (int): Size of a segment
        metric (callable): Function of a measure of lexical diversity; calc_ttr by default
        x_size (int): Half the width of the drawing area, greater than MARGIN (25)
        y_size (int): Half the height of the drawing area, which grows when the blocks need more
        cmap (str): Colour map
        ax (Axes): Axes for the plot; if not given, a 15×10 figure is created
        labels (dict[str, str]): Labels over VISUALIZER_LABELS["fingerprinting"]

    Returns:
        Axes: Axes with the fingerprinting

    Raises:
        SourceTypeError: If the texts are not a list of lists of words or the
            measure is not callable
        SourceError: If there are no texts or a text has no words
        ParameterError: If the size of a segment is not an integer or is below one,
            the half width is not an integer above MARGIN, the half height not an
            integer above zero, or the labels are set incorrectly (merge_labels)
    """
    title = merge_labels(VISUALIZER_LABELS["fingerprinting"], labels)["title"]
    check_sequence(texts, "lists of words")
    if not all(isinstance(text, (list, tuple)) for text in texts):
        raise SourceTypeError("The texts must be a list of lists of words")
    for text in texts:
        check_words(text)
    if not texts or any(not text for text in texts):
        raise SourceError("The data source has no words")
    if metric is not None and not callable(metric):
        raise SourceTypeError("The measure must be callable")
    check_integer(segment_len, "size of a segment")
    if segment_len < 1:
        raise ParameterError("The size of a segment must be greater than 0")
    check_integer(x_size, "half width of the drawing area")
    check_integer(y_size, "half height of the drawing area")
    if x_size <= MARGIN or y_size < 1:
        raise ParameterError(
            f"The half width of the drawing area must be greater than {MARGIN} "
            "and the half height greater than 0"
        )
    measure = metric if metric is not None else calc_ttr
    values = [_segment_values(text, segment_len, measure) for text in texts]
    finite = [value for segments in values for value in segments if np.isfinite(value)]
    norm = Normalize(min(finite), max(finite)) if finite else Normalize(0, 1)
    colormap = plt.get_cmap(cmap).with_extremes(bad=MISSING_COLOR)
    if ax is None:
        _, ax = plt.subplots(figsize=(15, 10))
    left = -x_size + MARGIN
    width = 2 * x_size - 2 * MARGIN
    max_cols = max(1, width // SQUARE)
    x, top, row_height = left, y_size - MARGIN, 0
    for segments in values:
        grid = _block(segments, max_cols)
        n_rows, n_cols = grid.shape
        if x > left and x + n_cols * SQUARE > left + width:
            x, top, row_height = left, top - row_height - MARGIN, 0
        ax.pcolormesh(
            x + SQUARE * np.arange(n_cols + 1),
            top - SQUARE * np.arange(n_rows + 1),
            np.ma.masked_invalid(grid),
            cmap=colormap,
            norm=norm,
        )
        x += n_cols * SQUARE + MARGIN
        row_height = max(row_height, n_rows * SQUARE)
    ax.set_xlim(-x_size, x_size)
    ax.set_ylim(min(-y_size, top - row_height - MARGIN), y_size)
    ax.set_aspect("equal")
    # The colorbar follows the box of the axes that the equal aspect shrinks
    colorbar_ax = make_axes_locatable(ax).append_axes("right", size="3%", pad=0.1)
    colorbar_ax.set_label("<colorbar>")
    ax.figure.colorbar(ScalarMappable(norm=norm, cmap=colormap), cax=colorbar_ax)
    ax.get_xaxis().set_visible(False)
    ax.get_yaxis().set_visible(False)
    ax.set_title(title)
    return ax


def _segment_values(
    text: Sequence[str], segment_len: int, measure: Callable[[Sequence[str]], float]
) -> list[float]:
    """
    Values of the measure over the sliding segments of a text

    Description:
        Every segment is segment_len words long, so the values are comparable:
        when the step leaves words after the last segment, one more ends with
        the text; a text not longer than a segment is one segment
    """
    if len(text) <= segment_len:
        return [float(measure(text))]
    step = max(1, int(0.1 * segment_len))
    starts = list(range(0, len(text) - segment_len + 1, step))
    if starts[-1] + segment_len < len(text):
        starts.append(len(text) - segment_len)
    return [float(measure(text[start : start + segment_len])) for start in starts]


def _block(values: Sequence[float], max_cols: int) -> np.ndarray:
    """Block of a text: its values row by row, 8 rows or one column, empty cells nan"""
    n_values = len(values)
    n_cols = ceil(n_values / 8)
    n_rows = 8 if n_cols > 1 else n_values
    if n_cols > max_cols:
        n_cols, n_rows = max_cols, ceil(n_values / max_cols)
    grid = np.full(n_rows * n_cols, np.nan)
    grid[:n_values] = values
    return grid.reshape(n_rows, n_cols)
