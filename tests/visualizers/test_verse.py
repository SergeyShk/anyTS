import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.axes import Axes

from anyts.exceptions import SourceError, SourceTypeError
from anyts.visualizers import rhythm_plot

STRESSES = [(1, 3, 5, 7), (1, 3, 7), (0, 2)]
LENGTHS = [8, 9, 4]


def test_rhythm_plot():
    ax = rhythm_plot(STRESSES, LENGTHS)
    assert isinstance(ax, Axes)
    grid = np.ma.filled(ax.get_images()[0].get_array().astype(float), np.nan)
    assert grid.shape == (3, 9)
    assert list(grid[0, :8]) == [0, 1, 0, 1, 0, 1, 0, 1] and np.isnan(grid[0, 8])
    assert list(np.flatnonzero(grid[1] == 1)) == [1, 3, 7]
    assert np.isnan(grid[2, 4:]).all()
    assert [label.get_text() for label in ax.get_legend().get_texts()] == [
        "Stressed syllable",
        "Unstressed syllable",
    ]
    assert ax.get_title() == "Rhythm of the lines"
    _, given = plt.subplots()
    assert rhythm_plot(STRESSES, LENGTHS, ax=given, labels={"title": "Ритм"}) is given
    assert given.get_title() == "Ритм"


@pytest.mark.parametrize(
    ("stresses", "lengths", "error"),
    [
        ([], [], SourceError),
        ([(1,)], [2, 3], SourceError),
        ([(2,)], [2], SourceError),
        ([(0,)], [-1], SourceError),
        ([(0.5,)], [2], SourceTypeError),
        ([(True,)], [2], SourceTypeError),
        ("01", [2], SourceTypeError),
    ],
)
def test_rhythm_plot_errors(stresses, lengths, error):
    with pytest.raises(error):
        rhythm_plot(stresses, lengths)
