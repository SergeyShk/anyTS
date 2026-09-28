"""The labels of the plots: defaults, one label changed alone, errors"""

from collections import Counter

import matplotlib.pyplot as plt
import pytest

from anyts.constants import VISUALIZER_LABELS
from anyts.corpus import keyness
from anyts.exceptions import ParameterError
from anyts.utils import merge_labels
from anyts.visualizers import (
    dispersion_plot,
    frequency_spectrum_plot,
    heaps_plot,
    keyness_plot,
    mendenhall_plot,
    sentence_lengths_plot,
    zipf,
    zipf_theory,
)

words = ["kitty", "is", "in", "window", "kitty", "is", "in", "rug"]


def test_merge_labels():
    defaults = {"title": "Plot", "xlabel": "x"}
    assert merge_labels(defaults, None) == defaults
    assert merge_labels(defaults, None) is not defaults
    assert merge_labels(defaults, {"title": "Gráfico"}) == {"title": "Gráfico", "xlabel": "x"}
    with pytest.raises(ParameterError, match=r"^The labels must be a mapping, not list$"):
        merge_labels(defaults, ["Gráfico"])
    with pytest.raises(ParameterError, match=r"^Unknown labels: \['ylabel'\]"):
        merge_labels(defaults, {"ylabel": "y"})
    with pytest.raises(ParameterError, match=r"^The labels must be strings$"):
        merge_labels(defaults, {"title": 1})


def test_merge_labels_format_strings():
    defaults = {"title": "Plot", "fit": "q={q:.2f}, s={s:.2f}"}
    assert merge_labels(defaults, {"fit": "s={s:.1f}"})["fit"] == "s={s:.1f}"
    assert merge_labels(defaults, {"fit": "{{q}}"})["fit"] == "{{q}}"
    assert merge_labels(defaults, {"fit": "{q!r:>{s}}"})["fit"] == "{q!r:>{s}}"
    assert merge_labels(defaults, {"title": "f(r) = {C}"})["title"] == "f(r) = {C}"
    for label, message in (
        (
            "q={q} {x}",
            r"^The label 'fit' has unknown fields \['x'\]; available fields: \['q', 's'\]$",
        ),
        ("K={0}", r"unknown fields \['0'\]"),
        ("|{}|", r"unknown fields \[''\]"),
        ("q={q} {", r"^The label 'fit' is not a format string"),
        ("{q:{x}}", r"unknown fields \['x'\]"),
        ("{q!z}", r"^The label 'fit' is not a format string: Unknown conversion specifier z$"),
    ):
        with pytest.raises(ParameterError, match=message):
            merge_labels(defaults, {"fit": label})


def test_labels_are_the_names_of_the_visualizers():
    import anyts.visualizers as visualizers

    assert set(VISUALIZER_LABELS) <= set(visualizers.__all__)


def test_labels_replace_the_defaults():
    ax = zipf(
        Counter(words),
        show_theory=True,
        show_fit=True,
        labels={"title": "Ley de Zipf", "theoretical": "Ley teórica", "fit": "q={q:.1f}"},
    )
    assert ax.get_title() == "Ley de Zipf"
    assert ax.get_xlabel() == "Rank of the word"
    assert [line.get_label() for line in ax.get_lines()][:2] == ["Experimental law", "Ley teórica"]
    assert zipf_theory(10, 5, labels={"theoretical": "T"}).get_lines()[0].get_label() == "T"
    ax = heaps_plot(words, labels={"fit": "β={beta:.1f}", "ylabel": "V"})
    assert ax.get_lines()[1].get_label().startswith("β=")
    assert ax.get_ylabel() == "V"
    assert frequency_spectrum_plot(words, labels={"xlabel": "m"}).get_xlabel() == "m"
    ax = sentence_lengths_plot([3, 5, 2], window=2, labels={"average": "Media ({window})"})
    assert ax.get_lines()[1].get_label() == "Media (2)"
    assert dispersion_plot(words, ["kitty"], labels={"title": "T"}).get_title() == "T"
    assert mendenhall_plot({"A": words}, labels={"ylabel": "S"}).get_ylabel() == "S"
    positive = keyness(words, ["pal", "is", "in", "rug"])
    ax = keyness_plot(positive, labels={"xlabel": "{field}!", "target": "Cervantes"})
    assert ax.get_xlabel() == "score!"
    assert [text.get_text() for text in ax.get_legend().get_texts()] == ["Cervantes"]


@pytest.mark.parametrize("labels", [{"unknown": "x"}, ["x"], {"title": 1}, {"fit": "{x}"}])
def test_labels_checked_before_plotting(labels):
    plt.close("all")
    with pytest.raises(ParameterError):
        zipf(Counter(words), labels=labels)
    with pytest.raises(ParameterError):
        heaps_plot(words, labels=labels)
    with pytest.raises(ParameterError):
        sentence_lengths_plot([3, 5, 2], labels={"average": "avg {w}"})
    assert plt.get_fignums() == []
