from collections import Counter

import matplotlib.pyplot as plt
import pytest

from anyts import WordsExtractor
from anyts.corpus import Keyword, delta
from anyts.exceptions import ParameterError
from anyts.visualizers import (
    dendrogram_plot,
    dispersion_plot,
    fingerprinting,
    frequency_spectrum_plot,
    heaps_plot,
    keyness_plot,
    mds_plot,
    mendenhall_plot,
    pca_plot,
    sentence_lengths_plot,
    zipf,
    zipf_theory,
)

WORDS = [
    "the",
    "cat",
    "and",
    "the",
    "dog",
    "saw",
    "the",
    "cat",
    "on",
    "the",
    "mat",
    "and",
    "the",
    "dog",
    "ran",
]
TEXTS = {
    "A": "The cat sat on the mat. The dog saw the cat and ran away from it.",
    "B": "A dog ran in the park. The cat slept on the warm mat all day long.",
    "C": "The bird sang in the tree. A cat and a dog watched the bird sing.",
}
CORPUS = {name: WordsExtractor(lowercase=True).extract(text) for name, text in TEXTS.items()}
KEYWORD = Keyword("cat", 5, 1.0, 5000.0, 1000.0, 10.0, 0.001, 2.0, 10.0)

PLOTS = {
    "sentence_lengths_plot": lambda ax: sentence_lengths_plot([5, 8, 3, 12], ax=ax),
    "fingerprinting": lambda ax: fingerprinting([WORDS, WORDS[::-1]], ax=ax),
    "dispersion_plot": lambda ax: dispersion_plot(WORDS, ["cat"], ax=ax),
    "keyness_plot": lambda ax: keyness_plot([KEYWORD], ax=ax),
    "dendrogram_plot": lambda ax: dendrogram_plot(delta(CORPUS, n_mfw=5), ax=ax),
    "pca_plot": lambda ax: pca_plot(CORPUS, n_mfw=5, ax=ax),
    "mds_plot": lambda ax: mds_plot(delta(CORPUS, n_mfw=5), ax=ax),
    "mendenhall_plot": lambda ax: mendenhall_plot(CORPUS, ax=ax),
    "heaps_plot": lambda ax: heaps_plot(WORDS, ax=ax),
    "frequency_spectrum_plot": lambda ax: frequency_spectrum_plot(WORDS, ax=ax),
    "zipf": lambda ax: zipf(Counter(WORDS), ax=ax),
    "zipf_theory": lambda ax: zipf_theory(10, 5, ax=ax),
}


@pytest.mark.parametrize("plot", PLOTS.values(), ids=PLOTS)
def test_plot_on_other_axes(plot):
    plt.close("all")
    with pytest.raises(ParameterError, match=r"^The axes must be a matplotlib Axes, not str$"):
        plot("x")
    assert plt.get_fignums() == []


@pytest.mark.parametrize("plot", PLOTS.values(), ids=PLOTS)
def test_plot_on_given_axes(plot):
    _, ax = plt.subplots()
    assert plot(ax) is ax
    plt.close("all")
