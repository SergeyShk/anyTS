from math import isnan, log2, sqrt

import pytest
import spacy
from nltk.collocations import BigramAssocMeasures, BigramCollocationFinder

from anyts.constants import COLLOCATION_MEASURES
from anyts.corpus import Collocation, collocations
from anyts.corpus.collocations import (
    MEASURES,
    calc_dice,
    calc_log_likelihood,
    calc_logdice,
    calc_mi,
    calc_mi3,
    calc_min_sensitivity,
    calc_npmi,
    calc_t_score,
)
from anyts.exceptions import ParameterError, SourceError, SourceTypeError

words = [
    "kitty", "is", "in", "window",
    "kitty", "is", "in", "rug",
    "kitty", "dozed", "in", "window",
]  # fmt: skip
text = (
    "The cat was at the window and watched the birds. The birds flew away and the cat "
    "fell asleep at the window. Tomorrow the cat will be at the window and watch the birds."
).lower()
tokens = [word.strip(".,") for word in text.split()]


def test_measures():
    assert set(MEASURES) == set(COLLOCATION_MEASURES)
    assert calc_mi(3, 3, 3, 12) == log2(4)
    assert calc_mi3(3, 3, 3, 12) == log2(27 * 12 / 9)
    assert calc_t_score(3, 3, 3, 12) == pytest.approx((3 - 9 / 12) / sqrt(3))
    assert calc_dice(3, 2, 2, 12) == 0.8
    assert calc_logdice(3, 3, 3, 12) == 14
    assert calc_logdice(3, 2, 2, 12) == pytest.approx(14 + log2(0.8))
    assert calc_npmi(3, 3, 3, 12) == pytest.approx(1)
    assert calc_npmi(3, 3, 1, 12) == pytest.approx(log2(12 / 9) / log2(12))
    assert calc_min_sensitivity(3, 2, 2, 12) == pytest.approx(2 / 3)
    assert calc_log_likelihood(3, 3, 3, 12) == pytest.approx(
        BigramAssocMeasures.likelihood_ratio(3, (3, 3), 12), rel=1e-6
    )
    assert calc_log_likelihood(5, 5, 4, 6) == pytest.approx(0.40271027101377704)


@pytest.mark.parametrize("calc", [calc_mi, calc_mi3, calc_t_score, calc_logdice, calc_npmi])
def test_measures_of_an_absent_pair(calc):
    assert isnan(calc(3, 3, 0, 12))


def test_measures_of_a_degenerate_table():
    assert isnan(calc_npmi(12, 12, 12, 12))
    assert isnan(calc_log_likelihood(12, 12, 12, 12))
    assert isnan(calc_log_likelihood(5, 5, 4 / 2 * 3, 6))
    assert isnan(calc_log_likelihood(12, 3, 2, 12))


def test_collocations():
    found = collocations(words, window=2)
    assert found[0] == Collocation("kitty", "in", 3, 3, 3, 13.0)
    assert [(c.left, c.right) for c in found[1:4]] == [
        ("in", "window"),
        ("is", "in"),
        ("kitty", "is"),
    ]
    assert found[1].score == pytest.approx(calc_logdice(3, 2, 1, 12))
    assert all(c.freq_pair >= 2 for c in found)
    assert collocations(words, window=2, top_n=1) == found[:1]


def test_bigrams():
    assert collocations(words, window=1) == [
        Collocation("in", "window", 3, 2, 2, calc_logdice(3, 2, 2, 12)),
        Collocation("is", "in", 2, 3, 2, calc_logdice(2, 3, 2, 12)),
        Collocation("kitty", "is", 3, 2, 2, calc_logdice(3, 2, 2, 12)),
    ]


def test_collocations_of_a_node():
    assert collocations(words, window=1, measure="t_score", node="kitty") == [
        Collocation("kitty", "is", 3, 2, 2, calc_t_score(3, 2, 2, 12))
    ]
    found = collocations(words, window=1, node="in", min_freq=1)
    assert [(c.left, c.right) for c in found] == [
        ("in", "window"),
        ("is", "in"),
        ("dozed", "in"),
        ("in", "rug"),
    ]


def test_collocations_of_a_short_text():
    assert collocations(["kitty"], window=3) == []
    with pytest.raises(SourceError, match="has no words"):
        collocations([])
    found = collocations(["a"] * 5, window=1, measure="log_likelihood", min_freq=1)
    assert isnan(found[0].score)


@pytest.mark.parametrize("window", [1, 2, 5])
def test_collocations_against_nltk(window):
    finder = BigramCollocationFinder.from_words(tokens, window_size=window + 1)
    found = {
        (c.left, c.right): c
        for c in collocations(tokens, window=window, measure="log_likelihood", min_freq=1)
    }
    assert {pair: c.freq_pair for pair, c in found.items()} == dict(finder.ngram_fd)
    for (left, right), score in finder.score_ngrams(BigramAssocMeasures.likelihood_ratio):
        assert found[left, right].score == pytest.approx(score, rel=1e-6)
    mi = {
        (c.left, c.right): c.score
        for c in collocations(tokens, window=window, measure="mi", min_freq=1)
    }
    for (left, right), score in finder.score_ngrams(BigramAssocMeasures.pmi):
        assert mi[left, right] == pytest.approx(score)
    t_score = {
        (c.left, c.right): c.score
        for c in collocations(tokens, window=window, measure="t_score", min_freq=1)
    }
    for (left, right), score in finder.score_ngrams(BigramAssocMeasures.student_t):
        assert t_score[left, right] == pytest.approx(score)


@pytest.mark.parametrize("measure", list(COLLOCATION_MEASURES))
def test_collocations_measures(measure):
    found = collocations(words, window=2, measure=measure)
    assert found[0].score == MEASURES[measure](3, 3, 1.5, 12)
    scores = [c.score for c in found]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"measure": "pmi"},
        {"window": 0},
        {"window": 2.0},
        {"top_n": 0},
        {"top_n": -1},
        {"top_n": 1.5},
    ],
)
def test_collocations_errors(kwargs):
    with pytest.raises(ParameterError):
        collocations(words, **kwargs)


def test_collocations_of_a_string():
    with pytest.raises(SourceTypeError):
        collocations("the cat sleeps")


def test_pair_of_a_word_with_itself():
    scores = []
    for window in (1, 2, 3):
        found = collocations(
            ["a"] * 5 + ["b"], window=window, measure="log_likelihood", min_freq=1
        )
        scores.append(next(c.score for c in found if c.left == c.right == "a"))
    assert scores[0] == pytest.approx(0.40271027101377704)
    assert all(isnan(score) for score in scores[1:])


@pytest.mark.parametrize("span", [False, True])
def test_refuses_a_doc(span):
    doc = spacy.blank("xx")("The cat sleeps and the cat eats.")
    source = doc[0:3] if span else doc
    with pytest.raises(SourceTypeError, match="WordsExtractor"):
        collocations(source)
