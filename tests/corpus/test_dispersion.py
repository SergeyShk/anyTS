from math import isnan, log2, sqrt

import numpy as np
import pytest
import spacy

from anyts.constants import DISPERSION_STATS_DESC
from anyts.corpus import Dispersion, dispersion
from anyts.corpus.dispersion import (
    calc_carroll_d2,
    calc_dp,
    calc_dp_norm,
    calc_juilland_d,
    calc_kl_divergence,
    calc_rosengren_s,
)
from anyts.exceptions import ParameterError, SourceError, SourceTypeError

words = [
    "kitty", "is", "in", "window",
    "kitty", "is", "in", "rug",
    "kitty", "dozed", "in", "window",
]  # fmt: skip
sizes = [10, 10, 10, 10, 10]


def test_measures_even():
    assert calc_dp([2, 2, 2, 2, 2], sizes) == 0
    assert calc_dp_norm([2, 2, 2, 2, 2], sizes) == 0
    assert calc_juilland_d([2, 2, 2, 2, 2], sizes) == 1
    assert calc_carroll_d2([2, 2, 2, 2, 2], sizes) == pytest.approx(1)
    assert calc_rosengren_s([2, 2, 2, 2, 2], sizes) == pytest.approx(1)
    assert calc_kl_divergence([2, 2, 2, 2, 2], sizes) == 0


def test_measures_clumped():
    assert calc_dp([10, 0, 0, 0, 0], sizes) == pytest.approx(0.8)
    assert calc_dp_norm([10, 0, 0, 0, 0], sizes) == pytest.approx(1)
    assert calc_juilland_d([10, 0, 0, 0, 0], sizes) == pytest.approx(1 - 2 / sqrt(4))
    assert calc_carroll_d2([10, 0, 0, 0, 0], sizes) == 0
    assert calc_rosengren_s([10, 0, 0, 0, 0], sizes) == pytest.approx(0.2)
    assert calc_kl_divergence([10, 0, 0, 0, 0], sizes) == pytest.approx(log2(5))


def test_measures_gries():
    frequencies = [1, 2, 3, 4, 5]
    assert calc_dp(frequencies, sizes) == pytest.approx(
        0.5 * (2 / 15 + 1 / 15 + 0 + 1 / 15 + 2 / 15)
    )
    assert calc_dp_norm(frequencies, sizes) == pytest.approx(0.25)
    assert calc_juilland_d(frequencies, sizes) == pytest.approx(1 - (sqrt(2) / 3) / 2)
    entropy = -sum(p / 15 * log2(p / 15) for p in frequencies)
    assert calc_carroll_d2(frequencies, sizes) == pytest.approx(entropy / log2(5))
    assert calc_rosengren_s(frequencies, sizes) == pytest.approx(
        sum(sqrt(0.2 * f) for f in frequencies) ** 2 / 15
    )
    assert calc_kl_divergence(frequencies, sizes) == pytest.approx(
        sum(f / 15 * log2(f / 15 / 0.2) for f in frequencies)
    )


def test_measures_unequal():
    frequencies = [3, 1]
    parts = [30, 10]
    assert calc_dp(frequencies, parts) == 0
    assert calc_dp_norm(frequencies, parts) == 0
    assert calc_juilland_d(frequencies, parts) == 1
    assert calc_carroll_d2(frequencies, parts) == pytest.approx(1)
    assert calc_rosengren_s(frequencies, parts) == pytest.approx(1)
    assert calc_kl_divergence(frequencies, parts) == 0
    assert calc_dp([0, 4], parts) == pytest.approx(0.75)
    assert calc_dp_norm([0, 4], parts) == pytest.approx(1)
    assert calc_rosengren_s([0, 4], parts) == pytest.approx(0.25)


@pytest.mark.parametrize(
    "calc",
    [
        calc_dp,
        calc_dp_norm,
        calc_juilland_d,
        calc_carroll_d2,
        calc_rosengren_s,
        calc_kl_divergence,
    ],
)
def test_measures_of_a_missing_word(calc):
    assert isnan(calc([0, 0], [30, 10]))


def test_dispersion():
    result = dispersion(words, parts=3)
    assert [item.word for item in result] == [
        "kitty",
        "in",
        "is",
        "window",
        "rug",
        "dozed",
    ]
    assert result[0] == Dispersion("kitty", 3, 0.0, 0.0, 1.0, 1.0, pytest.approx(1.0), 0.0)
    assert result[2] == Dispersion(
        "is",
        2,
        pytest.approx(1 / 3),
        pytest.approx(0.5),
        pytest.approx(0.5),
        pytest.approx(1 / log2(3)),
        pytest.approx(2 / 3),
        pytest.approx(log2(1.5)),
    )
    assert result[-1].dp == pytest.approx(2 / 3)


def test_dispersion_matches_the_single_measures():
    result = dispersion(words, parts=3)
    frequencies = {"kitty": [1, 1, 1], "is": [1, 1, 0], "window": [1, 0, 1]}
    for item in result:
        if item.word in frequencies:
            parts = frequencies[item.word]
            assert item.dp == pytest.approx(calc_dp(parts, [4, 4, 4]))
            assert item.juilland_d == pytest.approx(calc_juilland_d(parts, [4, 4, 4]))
            assert item.carroll_d2 == pytest.approx(calc_carroll_d2(parts, [4, 4, 4]))
            assert item.rosengren_s == pytest.approx(calc_rosengren_s(parts, [4, 4, 4]))
            assert item.kl_divergence == pytest.approx(calc_kl_divergence(parts, [4, 4, 4]))


def test_dispersion_options():
    result = dispersion(words, parts=3)
    assert dispersion(words, parts=[4, 4, 4]) == result
    assert dispersion(words, parts=3, word="window") == [result[3]]
    assert dispersion(words, parts=3, min_freq=3) == result[:2]
    missing = dispersion(words, parts=3, word="pup")[0]
    assert missing.freq == 0
    assert isnan(missing.dp)
    assert set(Dispersion._fields[2:]) == set(DISPERSION_STATS_DESC)


@pytest.mark.parametrize("parts", [1, 13, [6, 5], [12, 0], [12], ["a", "b"], 2.5])
def test_dispersion_errors(parts):
    with pytest.raises(ParameterError):
        dispersion(words, parts=parts)


def test_dispersion_of_an_empty_corpus():
    with pytest.raises(SourceError, match="has no words"):
        dispersion([], parts=2)
    with pytest.raises(SourceError):
        dispersion(np.array([], dtype=str), parts=2)


def test_dispersion_of_a_string():
    with pytest.raises(SourceTypeError):
        dispersion("the cat sleeps", parts=2)


@pytest.mark.parametrize("span", [False, True])
def test_refuses_a_doc(span):
    doc = spacy.blank("xx")("The cat sleeps and the cat eats.")
    source = doc[0:3] if span else doc
    with pytest.raises(SourceTypeError, match="WordsExtractor"):
        dispersion(source, parts=2)


def test_dispersion_of_an_array():
    result = dispersion(np.array(["lamp", "quill", "lamp", "lark"]), parts=2, word="lamp")[0]
    assert type(result.word) is str
    assert result == dispersion(["lamp", "quill", "lamp", "lark"], parts=2, word="lamp")[0]
