from math import inf, log2, nan

import matplotlib.pyplot as plt
import pytest
import spacy
from matplotlib.axes import Axes

from anyts.corpus import Collocation, Keyword, collocations, keyness
from anyts.exceptions import ParameterError, SourceError, SourceTypeError
from anyts.visualizers import collocation_network, dispersion_plot, keyness_plot

words = [
    "kitty", "is", "in", "window",
    "kitty", "is", "in", "rug",
    "kitty", "dozed", "in", "window",
]  # fmt: skip
target = ["kitty", "is", "in", "window", "with", "looked", "in", "peacocks", "kitty", "dozed"]
reference = ["pal", "yawned", "in", "rug", "with", "basked", "pal", "ate"]


def test_dispersion_plot():
    ax = dispersion_plot(words, ["kitty", "window", "pal"])
    assert isinstance(ax, Axes)
    assert [label.get_text() for label in ax.get_yticklabels()] == ["kitty", "window", "pal"]
    positions = [list(collection.get_positions()) for collection in ax.collections]
    assert positions == [[0, 4, 8], [3, 11], []]
    assert ax.get_xlim() == (0.0, 12.0)
    assert ax.get_ylim()[0] > ax.get_ylim()[1]
    assert ax.get_title() == "Lexical dispersion"
    _, given = plt.subplots()
    assert dispersion_plot(words, ["kitty"], ax=given) is given
    with pytest.raises(SourceError):
        dispersion_plot([], ["kitty"])
    with pytest.raises(SourceError):
        dispersion_plot(words, [])
    with pytest.raises(SourceTypeError):
        dispersion_plot("kitty is in window", ["kitty"])
    with pytest.raises(SourceTypeError):
        dispersion_plot(spacy.blank("xx")("kitty is in"), ["kitty"])
    with pytest.raises(SourceTypeError):
        dispersion_plot(words, "kitty")
    plt.close("all")


def test_keyness_plot():
    positive = keyness(target, reference)
    negative = keyness(target, reference, positive=False)
    ax = keyness_plot(positive, negative, top_n=3, labels=("kitty", "pal"))
    assert isinstance(ax, Axes)
    labels = [label.get_text() for label in ax.get_yticklabels()]
    assert labels[:3] == [keyword.word for keyword in positive[:3]]
    assert labels[3:] == [keyword.word for keyword in negative[:3]][::-1]
    widths = [patch.get_width() for patch in ax.patches]
    assert widths[:3] == [keyword.score for keyword in positive[:3]]
    assert widths[3:] == [keyword.score for keyword in negative[:3]][::-1]
    assert all(width < 0 for width in widths[3:])
    assert [text.get_text() for text in ax.get_legend().get_texts()] == ["kitty", "pal"]
    assert ax.get_title() == "Keywords"
    assert ax.get_xlabel() == "|score|"
    ax = keyness_plot(positive)
    assert len(ax.patches) == len(positive)
    assert [text.get_text() for text in ax.get_legend().get_texts()] == ["target corpus"]
    _, given = plt.subplots()
    assert keyness_plot(positive, ax=given) is given
    ax = keyness_plot([], negative, top_n=2)
    assert len(ax.patches) == 2
    assert [text.get_text() for text in ax.get_legend().get_texts()] == ["reference corpus"]
    plt.close("all")
    for top_n in (0, -1):
        with pytest.raises(ParameterError):
            keyness_plot(positive, negative, top_n=top_n)
    assert plt.get_fignums() == []
    undefined = [Keyword("a", 1, 0, 1.0, 0.0, 1.0, 0.5, 1.0, nan)]
    infinite = [Keyword("b", 1, 0, 1.0, 0.0, 1.0, 0.5, 1.0, inf)]
    assert len(keyness_plot(positive + undefined + infinite).patches) == len(positive)
    with pytest.raises(SourceError, match="no words"):
        keyness_plot([])
    with pytest.raises(SourceError, match="undefined"):
        keyness_plot(undefined)
    for kwargs in ({"field": "word"}, {"field": ["score"]}, {"top_n": 1.5}, {"labels": ("a",)}):
        with pytest.raises(ParameterError):
            keyness_plot(positive, **kwargs)
    plt.close("all")


def test_keyness_plot_sides():
    positive = keyness(target, reference, measure="odds_ratio")
    negative = keyness(target, reference, measure="odds_ratio", positive=False)
    ax = keyness_plot(positive, negative, top_n=2, log=True)
    widths = [patch.get_width() for patch in ax.patches]
    assert widths[:2] == [pytest.approx(abs(log2(keyword.score))) for keyword in positive[:2]]
    assert (
        widths[2:] == [pytest.approx(-abs(log2(keyword.score))) for keyword in negative[:2]][::-1]
    )
    assert ax.get_xlabel() == "|log2(score)|"
    ax = keyness_plot(positive, negative, top_n=2, field="log_ratio")
    widths = [patch.get_width() for patch in ax.patches]
    assert widths[:2] == [abs(keyword.log_ratio) for keyword in positive[:2]]
    assert all(width < 0 for width in widths[2:])
    weak = [Keyword("a", 1, 0, 1.0, 0.0, 1.0, 0.5, 1.0, -2.0)]
    assert keyness_plot(weak, weak).patches[0].get_width() == 2.0
    assert keyness_plot(weak, weak).patches[1].get_width() == -2.0
    zero = [Keyword("a", 1, 0, 1.0, 0.0, 1.0, 0.5, 1.0, 0.0)]
    with pytest.raises(SourceError):
        keyness_plot(zero, log=True)
    plt.close("all")


def test_collocation_network():
    found = collocations(words, window=2)
    graph = collocation_network(found, top_n=3)
    assert graph.engine == "neato"
    assert graph.source.count("--") == 3
    assert "\tn0 [label=kitty fontsize=24]" in graph.source
    assert "\tn3 [label=is fontsize=10]" in graph.source
    assert "n0 -- n1 [label=13.00 penwidth=4.00]" in graph.source
    assert graph.source.count("penwidth=0.50") == 2
    assert collocation_network(found).source.count("--") == len(found)
    single = collocation_network([Collocation("a", "b", 1, 1, 1, nan)])
    assert "label=0.00 penwidth=2.25" in single.source
    assert "\tn0 [label=a fontsize=17]" in single.source
    with pytest.raises(SourceError):
        collocation_network([])
    html_like = collocation_network([Collocation("<b>", "kitty", 2, 2, 2, 1.0)])
    assert '\tn0 [label="<b>" fontsize=17]' in html_like.source
    assert "n0 -- n1" in html_like.source
    backslash = collocation_network([Collocation("a\\", "\\G", 2, 2, 2, 1.0)])
    assert '\tn0 [label="a\\\\" fontsize=17]' in backslash.source
    assert '\tn1 [label="\\\\G" fontsize=17]' in backslash.source
    for top_n in (0, -1, 1.5):
        with pytest.raises(ParameterError):
            collocation_network(found, top_n=top_n)


def test_collocation_network_ports():
    # A colon in a word would read as a port of graphviz
    graph = collocation_network([Collocation("10:30", "at", 2, 3, 2, 5.0)])
    assert '\tn0 [label="10:30" fontsize=10]' in graph.source
    assert "\tn0 -- n1 [label=5.00 penwidth=2.25]" in graph.source
    assert "10:30 --" not in graph.source


def test_collocation_network_pairs_of_a_word_with_itself():
    # A pair of a word with itself is left out before top_n
    pairs = [
        Collocation("bye", "bye", 5, 5, 5, 11.9),
        Collocation("very", "very", 7, 7, 7, 11.4),
        Collocation("wine", "red", 2, 3, 2, 5.0),
        Collocation("wine", "white", 2, 3, 1, 4.0),
    ]
    graph = collocation_network(pairs, top_n=1)
    assert graph.source.count("--") == 1
    assert "red" in graph.source and "bye" not in graph.source and "very" not in graph.source
    assert graph.format == "png"
    with pytest.raises(SourceError):
        collocation_network(pairs[:2])
