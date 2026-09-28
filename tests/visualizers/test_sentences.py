import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
import spacy
from matplotlib.axes import Axes

from anyts import SentsExtractor, WordsExtractor
from anyts.exceptions import ParameterError, SourceError, SourceTypeError
from anyts.visualizers import sentence_lengths, sentence_lengths_plot

text = (
    "The cat was on the window. It watched the birds, but the birds left. "
    "Slept? Tomorrow it will sit on the window."
)


def test_sentence_lengths():
    assert sentence_lengths(text) == [6, 8, 1, 7]
    assert sentence_lengths(spacy.blank("xx")(text)) == [6, 8, 1, 7]
    nlp = spacy.blank("xx")
    nlp.add_pipe("sentencizer")
    assert sentence_lengths(nlp(text)) == [6, 8, 1, 7]
    assert sentence_lengths([3, 5, 2]) == [3, 5, 2]
    assert sentence_lengths(np.array([3, 5, 2])) == [3, 5, 2]
    assert sentence_lengths(pd.Series([3, 5, 2])) == [3, 5, 2]
    assert sentence_lengths((np.int64(3), np.int32(5))) == [3, 5]
    assert sentence_lengths(iter([3, 5])) == [3, 5]
    assert sentence_lengths("") == []
    assert sentence_lengths("?! ... !!") == []
    with pytest.raises(SourceTypeError):
        sentence_lengths(["cat", "sleeps"])
    with pytest.raises(SourceTypeError):
        sentence_lengths([3.5, 2])
    with pytest.raises(SourceTypeError):
        sentence_lengths(42)


@pytest.mark.parametrize(
    "lengths",
    [pd.DataFrame([3, 5, 2]), {3: "a", 5: "b"}, {3, 5}, b"Hi.", [True, False], [[3, 5]]],
)
def test_sentence_lengths_ready_lengths_checked(lengths):
    with pytest.raises(SourceTypeError):
        sentence_lengths(lengths)


def test_sentence_lengths_negative():
    with pytest.raises(SourceError, match=r"^The lengths of the sentences must not be negative$"):
        sentence_lengths([3, -5, 2])
    plt.close("all")
    with pytest.raises(SourceError):
        sentence_lengths_plot([-3, -5, -2], window=2)
    assert plt.get_fignums() == []


def test_sentence_lengths_hooks():
    # The extractors of a string and the hyphens of a Doc are the hooks of a language
    parts = SentsExtractor(tokenizer=re.compile(r"(?<=,)\s+"))
    assert sentence_lengths("The cat, the dog", sents_extractor=parts) == [2, 2]
    assert sentence_lengths(text, words_extractor=WordsExtractor(stopwords={"the"})) == [
        4,
        6,
        1,
        6,
    ]
    nlp = spacy.blank("xx")
    nlp.add_pipe("sentencizer")
    doc = nlp("A well-known cat. It sleeps.")
    assert sentence_lengths(doc) == [4, 2]
    assert sentence_lengths(doc, join_hyphens=True) == [3, 2]
    # A Doc without sentence boundaries is counted as its text, by the extractors
    bare = spacy.blank("xx")("A well-known cat. It sleeps.")
    assert sentence_lengths(bare, join_hyphens=True) == [4, 2]
    with pytest.raises(SourceTypeError, match="SentsExtractor"):
        sentence_lengths(text, sents_extractor=WordsExtractor())
    with pytest.raises(SourceTypeError, match="WordsExtractor"):
        sentence_lengths(text, words_extractor=SentsExtractor())


def test_sentence_lengths_plot():
    ax = sentence_lengths_plot(text, window=2)
    assert isinstance(ax, Axes)
    series, average = ax.get_lines()
    assert list(series.get_ydata()) == [6, 8, 1, 7]
    assert list(average.get_ydata()) == [7.0, 4.5, 4.0]
    assert list(average.get_xdata()) == [1.5, 2.5, 3.5]
    assert average.get_label() == "Moving average (2)"
    assert len(ax.child_axes) == 1
    assert ax.child_axes[0].get_title() == "Distribution"
    assert ax.get_ylim()[1] == pytest.approx(8 * 1.7)
    assert ax.get_title() == "Sentence lengths"
    ax = sentence_lengths_plot([3, 5, 2], window=10, inset=False)
    assert len(ax.get_lines()) == 1
    assert not ax.child_axes
    _, given = plt.subplots()
    assert sentence_lengths_plot([3, 5, 2], ax=given) is given
    with pytest.raises(SourceError):
        sentence_lengths_plot("")
    for window in (0, 2.5):
        with pytest.raises(ParameterError):
            sentence_lengths_plot(text, window=window)
