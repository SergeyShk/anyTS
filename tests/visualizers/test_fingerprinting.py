from functools import partial
from math import nan

import matplotlib.pyplot as plt
import pytest
from matplotlib.axes import Axes

from anyts.diversity_stats import calc_simpson_index, calc_ttr
from anyts.exceptions import ParameterError, SourceError, SourceTypeError
from anyts.visualizers import fingerprinting
from anyts.visualizers.fingerprinting import _segment_values


@pytest.fixture(scope="module")
def texts():
    return [["the", "cat", "sleeps"], ["the", "dog", "eats", "bread"]]


def test_fingerprinting_type_error(texts):
    with pytest.raises(TypeError):
        fingerprinting(1)
    with pytest.raises(SourceTypeError):
        fingerprinting(["the cat sleeps", ["the", "dog"]])
    with pytest.raises(SourceTypeError):
        fingerprinting("the cat sleeps")
    with pytest.raises(SourceTypeError):
        fingerprinting(texts, metric=42)
    for segment_len in (0, -1, 2.5):
        with pytest.raises(ParameterError):
            fingerprinting(texts, segment_len=segment_len)
    for kwargs in (
        {"x_size": 25},
        {"x_size": -100},
        {"x_size": "a"},
        {"y_size": 0},
        {"y_size": 1.5},
    ):
        with pytest.raises(ParameterError):
            fingerprinting(texts, **kwargs)
    assert plt.get_fignums() == []


def _cells(ax):
    """Values of the squares of every block, the empty and undefined ones masked"""
    return [mesh.get_array() for mesh in ax.collections]


def test_fingerprinting(texts):
    ax = fingerprinting(texts, x_size=600, y_size=500)
    assert isinstance(ax, Axes)
    assert len(ax.figure.axes) == 2
    assert ax.get_title() == "Literature fingerprinting"
    assert ax.figure.axes[1].get_label() == "<colorbar>"
    assert ax.get_xlim() == (-600.0, 600.0)
    assert ax.get_ylim() == (-500.0, 500.0)
    assert ax.get_aspect() == 1.0
    assert [cells.size for cells in _cells(ax)] == [1, 1]
    plt.close("all")


def test_fingerprinting_ax(texts):
    _, given = plt.subplots()
    ax = fingerprinting(texts, ax=given)
    assert ax is given
    assert len(ax.figure.axes) == 2
    plt.close("all")


def test_fingerprinting_metric(texts):
    ax = fingerprinting(texts, metric=calc_simpson_index)
    assert isinstance(ax, Axes)
    plt.close("all")


def test_fingerprinting_callable_metric(texts):
    # Any callable, not only a function
    by_length = partial(lambda segment, scale: scale * len(segment), scale=0.1)
    values = [float(cells[0]) for cells in _cells(fingerprinting(texts, metric=by_length))]
    plt.close("all")
    assert values == pytest.approx([0.3, 0.4])


def test_fingerprinting_layout():
    # 95 words in segments of 5 with a step of 1: 91 segments and the tail, 12 columns of 8,
    # wrapped into the 10 columns of a row; 40 words: 36 and the tail, 5 columns of 8;
    # the tails of fewer than 5 words give nan
    words = [f"word{index % 7}" for index in range(95)]

    def metric(segment):
        return nan if len(segment) < 5 else len(set(segment)) / len(segment)

    ax = fingerprinting([words, words[:40]], segment_len=5, metric=metric, x_size=100, y_size=500)
    first, second = _cells(ax)
    assert first.shape == (10, 10) and second.shape == (8, 5)
    # The empty cells and the undefined tails are masked
    assert int(first.mask.sum()) == 8 + 1 and int(second.mask.sum()) == 3 + 1
    # The second block does not fit after the first and starts the next row
    corners = [mesh.get_coordinates()[0, 0] for mesh in ax.collections]
    assert corners[0][0] == corners[1][0] == -75
    assert corners[1][1] == corners[0][1] - 10 * 15 - 25
    plt.close("all")


def test_fingerprinting_fits():
    # A block wider than a row wraps, and the area grows downwards
    words = [f"word{index % 97}" for index in range(5000)]
    ax = fingerprinting([words, words], x_size=200, y_size=100)
    (x0, x1), (y0, y1) = ax.get_xlim(), ax.get_ylim()
    for mesh in ax.collections:
        coordinates = mesh.get_coordinates()
        assert x0 <= coordinates[..., 0].min() and coordinates[..., 0].max() <= x1
        assert y0 <= coordinates[..., 1].min() and coordinates[..., 1].max() <= y1
    assert y0 < -100
    assert [cells.shape[1] for cells in _cells(ax)] == [23, 23]
    assert sum(cells.count() for cells in _cells(ax)) == 2 * 4991
    plt.close("all")


def test_fingerprinting_scale():
    # Zero is a value and not a missing square; the colorbar spans the finite values
    texts = [["the", "cat", "eats"], ["the", "the", "the"], ["the", "cat", "the"]]
    ax = fingerprinting(texts, metric=calc_simpson_index)
    values = [float(cells[0]) for cells in _cells(ax)]
    assert values == pytest.approx([0.0, 1.0, 1 / 3])
    assert not any(cells.mask.any() for cells in _cells(ax))
    colorbar = ax.figure.axes[1]
    assert colorbar.get_ylim() == pytest.approx((0.0, 1.0))
    assert ax.collections[0].norm.vmin == 0.0 and ax.collections[0].norm.vmax == 1.0
    plt.close("all")
    ax = fingerprinting([["a"], ["b", "c"]], metric=lambda segment: nan)
    assert all(cells.mask.all() for cells in _cells(ax))
    plt.close("all")


@pytest.mark.parametrize("texts", [[], [[]], [["el", "gato"], []]])
def test_fingerprinting_no_words(texts):
    with pytest.raises(SourceError):
        fingerprinting(texts)
    assert plt.get_fignums() == []


def test_segment_values_end():
    # Every segment is full; one more ends with the text when the step leaves words
    assert _segment_values(["a", "b", "c"], 1, calc_ttr) == [1.0, 1.0, 1.0]
    assert _segment_values(["a", "b", "c"], 5, calc_ttr) == [1.0]
    assert _segment_values(["a", "b", "c"], 3, calc_ttr) == [1.0]
    assert _segment_values(["a", "a", "b"], 2, calc_ttr) == [0.5, 1.0]
    assert _segment_values(list("abcdefghijkl"), 12, calc_ttr) == [1.0]
    # A step of 2 on 13 words of segments of 20: one segment; of 10: starts 0, 1, 2, 3
    assert len(_segment_values(list("abcdefghijklm"), 20, calc_ttr)) == 1
    assert len(_segment_values(list("abcdefghijklm"), 10, calc_ttr)) == 4
    words = list("aabbccddeeffgghhiijjkkl")
    segments = _segment_values(words, 20, lambda segment: len(segment))
    assert segments == [20, 20, 20]
    assert _segment_values(words, 20, lambda segment: ord(segment[-1]))[-1] == ord("l")


def test_fingerprinting_uniform_text_has_no_bright_cell():
    ax = fingerprinting([("the cat sat on the mat " * 20).split()])
    values = next(iter(_cells(ax))).compressed()
    assert len(values) == 111
    assert set(values) == {0.5}
    plt.close("all")


def test_fingerprinting_colorbar_height():
    ax = fingerprinting([["the", "cat", "eats", "bread"] * 30] * 6, x_size=1000, y_size=330)
    ax.figure.canvas.draw()
    colorbar = ax.figure.axes[1]
    assert colorbar.get_position().height == pytest.approx(ax.get_position().height)
    assert ax.get_position().height < 0.5
    plt.close("all")
