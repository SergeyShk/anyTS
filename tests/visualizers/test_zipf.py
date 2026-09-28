from collections import Counter

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.axes import Axes

from anyts.exceptions import ParameterError, SourceError, SourceTypeError
from anyts.visualizers import zipf, zipf_theory


@pytest.fixture(scope="module")
def tokens():
    return Counter({"the": 100, "of": 75, "and": 50, "to": 25})


def test_zipf_theory():
    ax = zipf_theory(10, 5, 1.0)
    assert isinstance(ax, Axes)
    line = ax.get_lines()[0]
    assert line.get_label() == "Theoretical law"
    assert line.get_linewidth() == 2
    assert line.get_color() == "r"
    assert list(line.get_xdata()) == [1, 2, 3, 4, 5]
    assert list(line.get_ydata()) == pytest.approx([10, 5, 10 / 3, 2.5, 2])
    assert np.isfinite(zipf_theory(10, 5, 1.5).get_lines()[0].get_ydata()).all()
    plt.close("all")
    for num_ranks, alpha in ((0, 1.0), (5, 0.0), (5, -1.0), (2.5, 1.0), (5, "1.5")):
        with pytest.raises(ParameterError):
            zipf_theory(10, num_ranks, alpha)
    assert plt.get_fignums() == []


def test_zipf_empty_and_overflow(tokens):
    with pytest.raises(SourceError):
        zipf(Counter())
    assert plt.get_fignums() == []
    ax = zipf(tokens, num_words=100, num_labels=100, show_theory=True)
    assert all(len(line.get_xdata()) == 4 for line in ax.get_lines())
    assert len(ax.texts) == 4
    single = zipf(Counter({"the": 3}), num_labels=5)
    assert len(single.texts) == 1


def test_zipf_type_error():
    with pytest.raises(SourceTypeError):
        zipf(1)
    with pytest.raises(SourceTypeError):
        zipf({"the": 1})
    for kwargs in ({"num_words": -1}, {"num_words": 0}, {"num_words": 2.5}, {"num_labels": 2.5}):
        with pytest.raises(ParameterError):
            zipf(Counter({"the": 1}), **kwargs)


def test_zipf(tokens):
    ax = zipf(tokens)
    assert isinstance(ax, Axes)
    line = ax.get_lines()[0]
    assert line.get_label() == "Experimental law"
    assert ax.get_title() == "Zipf's law"
    assert ax.get_xscale() == "log"
    assert len(ax.get_lines()) == 1


def test_zipf_num_words(tokens):
    ax = zipf(tokens, num_words=2)
    assert len(ax.get_lines()[0].get_data()[0]) == 2


def test_zipf_log(tokens):
    ax = zipf(tokens, log=False)
    assert ax.get_xscale() == "linear"
    assert ax.get_yscale() == "linear"


def test_zipf_num_labels(tokens):
    ax = zipf(tokens, num_labels=1)
    assert ax.texts[0].get_text() == " the"
    assert ax.texts[0].get_position() == (1, 100)
    assert len(ax.texts) == 1
    assert not zipf(tokens, num_labels=0).texts


def test_zipf_show_theory(tokens):
    ax = zipf(tokens, show_theory=True)
    labels = [line.get_label() for line in ax.get_lines()]
    assert labels == ["Experimental law", "Theoretical law"]
    assert ax.get_legend() is not None


def test_zipf_show_fit():
    ax = zipf(Counter({"the": 12, "of": 6, "and": 4, "to": 3}), show_fit=True, show_theory=True)
    labels = [line.get_label() for line in ax.get_lines()]
    assert labels[:2] == ["Experimental law", "Theoretical law"]
    assert labels[2] == "Zipf-Mandelbrot: q=0.00, s=1.00"
    assert ax.get_lines()[2].get_ydata()[0] == pytest.approx(12, rel=1e-3)
    assert len(zipf(Counter({"the": 2, "of": 1}), show_fit=True).get_lines()) == 1


def test_zipf_ax(tokens):
    _, (left, right) = plt.subplots(1, 2)
    assert zipf(tokens, ax=left) is left
    assert zipf_theory(10, 5, ax=right) is right
    assert len(left.get_lines()) == 1
    assert len(right.get_lines()) == 1


def test_zipf_labels_of_equal_frequencies():
    ax = zipf(Counter({"a": 2, "b": 2, "c": 2, "d": 2, "e": 1}), num_labels=5)
    assert [text.get_text() for text in ax.texts] == [" a", " b", " c", " e"]
