import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.axes import Axes

from anyts.exceptions import ParameterError, SourceError, SourceTypeError
from anyts.visualizers import rhythm_plot

PATTERNS = ["cCcCcCcC", "cCcCcccCc", "CcCc"]


def test_rhythm_plot():
    ax = rhythm_plot(PATTERNS, "C")
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
    assert ax.figure.get_layout_engine() is not None
    _, given = plt.subplots()
    assert rhythm_plot(["-+-+"], "+", ax=given, labels={"title": "Ритм"}) is given
    assert given.get_title() == "Ритм"


def test_rhythm_plot_of_a_long_poem():
    """Every cell keeps its color, and the ticks of the lines do not crowd"""
    ax = rhythm_plot(["cC" * 4] * 300, "C")
    assert ax.get_images()[0].get_interpolation() == "nearest"
    assert len(ax.get_yticks()) < 20


@pytest.mark.parametrize(
    ("patterns", "stressed", "error"),
    [
        ([], "C", SourceError),
        ([1], "C", SourceTypeError),
        ("cC", "C", SourceTypeError),
        (["cC"], "CC", ParameterError),
        (["cC"], 1, ParameterError),
    ],
)
def test_rhythm_plot_errors(patterns, stressed, error):
    with pytest.raises(error):
        rhythm_plot(patterns, stressed)
