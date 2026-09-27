from collections import Counter
from math import inf, isnan, log

import numpy as np
import pytest
import spacy

from anyts.constants import G2_CRITICAL_VALUES, KEYNESS_MEASURES
from anyts.corpus import FrequencyReference, Keyword, keyness
from anyts.corpus.keyness import (
    MEASURES,
    calc_bic,
    calc_chi2,
    calc_diff,
    calc_ell,
    calc_log_likelihood,
    calc_log_ratio,
    calc_odds_ratio,
    calc_p_value,
)
from anyts.exceptions import ParameterError, SourceError, SourceTypeError

target = ["kitty", "is", "in", "window", "with", "looked", "in", "peacocks", "kitty", "dozed"]
reference = ["pal", "yawned", "in", "rug", "with", "basked", "pal", "ate"]


def test_measures():
    assert set(MEASURES) == set(KEYNESS_MEASURES)
    assert calc_log_likelihood(10, 5, 1000, 2000) == pytest.approx(
        2 * (10 * log(2) + 5 * log(0.5))
    )
    assert calc_log_likelihood(5, 10, 2000, 1000) == pytest.approx(
        -calc_log_likelihood(10, 5, 1000, 2000)
    )
    assert calc_log_likelihood(0, 0, 1000, 2000) == 0
    assert calc_log_likelihood(10, 0, 1000, 2000) == pytest.approx(2 * 10 * log(3))
    assert calc_chi2(10, 5, 1000, 2000) == pytest.approx(6.105527638190955)
    assert calc_chi2(5, 10, 2000, 1000) == pytest.approx(-6.105527638190955)
    assert calc_chi2(1, 2, 1000, 2000) == 0
    assert calc_chi2(0, 0, 1000, 2000) == 0
    assert calc_diff(10, 5, 1000, 2000) == pytest.approx(300)
    assert calc_diff(10, 0, 1000, 2000) == pytest.approx((0.01 - 0.00025) / 0.00025 * 100)
    assert calc_log_ratio(10, 5, 1000, 2000) == 2
    assert calc_log_ratio(0, 5, 1000, 2000) == pytest.approx(-2.321928094887362)
    assert calc_bic(10, 5, 1000, 2000) == pytest.approx(
        calc_log_likelihood(10, 5, 1000, 2000) - log(3000)
    )
    assert calc_bic(5, 10, 2000, 1000) == pytest.approx(-calc_bic(10, 5, 1000, 2000))


def test_effect_sizes():
    assert calc_ell(10, 5, 1000, 2000) == pytest.approx(
        calc_log_likelihood(10, 5, 1000, 2000) / (3000 * log(5))
    )
    assert isnan(calc_ell(1, 0, 1000, 2000))
    assert isnan(calc_ell(5, 0, 1000, 2000))
    assert not isnan(calc_ell(9, 0, 1000, 2000))
    assert isnan(calc_ell(4, 0, 4, 2))
    assert 0 < calc_ell(30, 5, 60, 60) < 1
    assert calc_odds_ratio(10, 5, 1000, 2000) == pytest.approx((10 / 990) / (5 / 1995))
    assert calc_odds_ratio(10, 10, 10, 20) == inf
    assert calc_odds_ratio(10, 20, 20, 20) == 0
    assert isnan(calc_odds_ratio(20, 20, 20, 20))


def test_p_value():
    assert calc_p_value(3.84) == pytest.approx(0.05, abs=0.001)
    for p, critical in G2_CRITICAL_VALUES.items():
        assert calc_p_value(critical) == pytest.approx(p, rel=0.01)
        assert calc_p_value(-critical) == pytest.approx(p, rel=0.01)
    assert list(calc_p_value(np.array([3.84, -6.63]))) == [
        pytest.approx(0.05, abs=0.001),
        pytest.approx(0.01, abs=0.001),
    ]


def test_keyness():
    keywords = keyness(target, reference)
    assert [keyword.word for keyword in keywords] == [
        "kitty",
        "dozed",
        "is",
        "looked",
        "peacocks",
        "window",
        "in",
    ]
    g2 = calc_log_likelihood(2, 0, 10, 8)
    assert keywords[0] == Keyword(
        "kitty", 2, 0, 200000.0, 0.0, g2, calc_p_value(g2), calc_log_ratio(2, 0, 10, 8), g2
    )
    assert keywords[-1].freq_reference == 1
    assert {type(keyword.freq_reference) for keyword in keywords} == {float}
    assert keywords[-1].ipm_reference == 125000.0
    assert all(keyword.g2 > 0 for keyword in keywords)
    assert [keyword.p_value for keyword in keywords] == [
        pytest.approx(calc_p_value(keyword.g2)) for keyword in keywords
    ]


def test_keyness_options():
    keywords = keyness(target, reference)
    assert keyness(Counter(target), Counter(reference)) == keywords
    assert keyness(target, reference, top_n=2) == keywords[:2]
    assert [keyword.word for keyword in keyness(target, reference, min_freq=2)] == ["kitty", "in"]


def test_keyness_negative():
    keywords = keyness(target, reference, positive=False)
    assert [keyword.word for keyword in keywords] == [
        "pal",
        "ate",
        "basked",
        "rug",
        "yawned",
        "with",
    ]
    assert all(keyword.g2 < 0 and keyword.score < 0 for keyword in keywords)
    assert keywords[-1].freq_target == 1
    assert keywords[-1].log_ratio == pytest.approx(-0.32192809488736235)


def test_keyness_against_frequencies_of_a_dictionary():
    frequencies = {"kitty": 40.0, "in": 20000.0, "peacocks": 8.0, "with": 25000.0}
    keywords = keyness(target, frequencies)
    kitty = next(keyword for keyword in keywords if keyword.word == "kitty")
    size = sum(frequencies.values())
    assert kitty.freq_reference == 40.0
    assert kitty.ipm_reference == pytest.approx(40 / size * 1e6)
    assert kitty.g2 == pytest.approx(calc_log_likelihood(2, 40, 10, size))


def lower_singular(word):
    return word.lower().removesuffix("s")


REFERENCE = FrequencyReference(
    {"cat": 50.0, "the": 60_000.0, "window": 30.0},
    size=1_000_000,
    missing=0.5,
    key=lower_singular,
    keep=str.isalpha,
)


def test_keyness_against_a_frequency_reference():
    words = ["Cats", "cat", "cats", "the", "xylophone", "window", "2020"]
    keywords = keyness(words, REFERENCE)
    cat = next(keyword for keyword in keywords if keyword.word == "cat")
    # 2020 is not kept, so the target has six words
    assert cat.freq_target == 3
    assert cat.ipm_target == pytest.approx(3 / 6 * 1e6)
    assert cat.freq_reference == 50.0
    assert cat.ipm_reference == 50.0
    assert cat.g2 == pytest.approx(calc_log_likelihood(3, 50, 6, 1_000_000))
    # A key out of the reference gets the frequency of a missing one
    missing = next(keyword for keyword in keywords if keyword.word == "xylophone")
    assert missing.freq_reference == 0.5
    assert [keyword.g2 for keyword in keywords] == sorted((k.g2 for k in keywords), reverse=True)
    assert "2020" not in {keyword.word for keyword in keywords}


def test_frequency_reference_by_counts():
    by_words = keyness(["cats", "cats", "cat", "window"], REFERENCE)
    by_counts = keyness({"cats": 2, "cat": 1, "window": 1}, REFERENCE)
    assert by_counts == by_words
    assert {keyword.word for keyword in by_words} == {"cat", "window"}


def test_frequency_reference_missing_keys_are_never_negative():
    target = {"cat": 100_000_000, "xylophone": 1}
    negative = keyness(target, REFERENCE, positive=False)
    assert {keyword.word for keyword in negative} == {"the", "window"}
    positive = keyness({"cat": 10, "xylophone": 1}, REFERENCE)
    assert "xylophone" in {keyword.word for keyword in positive}


def test_frequency_reference_defaults():
    counts = FrequencyReference(Counter(reference), size=len(reference))
    assert keyness(target, counts) == keyness(target, reference)
    assert keyness(target, counts, positive=False) == keyness(target, reference, positive=False)


def test_frequency_reference_of_no_size():
    with pytest.raises(SourceError, match="has no words"):
        keyness(target, FrequencyReference({"kitty": 1.0}, size=0))


@pytest.mark.parametrize("measure", list(KEYNESS_MEASURES))
def test_keyness_measures(measure):
    keywords = keyness(target, reference, measure=measure)
    kitty = next(keyword for keyword in keywords if keyword.word == "kitty")
    assert kitty.score == MEASURES[measure](2, 0, 10, 8) or isnan(kitty.score)
    if measure != "ell":
        assert keywords[0].word == "kitty"


def test_keyness_of_small_corpora_by_the_effect_size():
    keywords = keyness(target, reference, measure="ell")
    assert all(isnan(keyword.score) for keyword in keywords)
    assert [keyword.word for keyword in keywords[:2]] == ["in", "kitty"]
    found = keyness(["a"] * 30 + ["b"] * 30, ["a"] * 5 + ["b"] * 55, measure="ell")
    assert found[0].score == pytest.approx(calc_ell(30, 5, 60, 60))


def test_keyness_by_the_odds_ratio():
    assert keyness(target, reference, measure="odds_ratio")[0].word == "kitty"
    assert keyness(["a", "b"], ["a"], positive=False, measure="odds_ratio")[0].score == 0


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"measure": "mi"}, ParameterError),
        ({"top_n": 0}, ParameterError),
        ({"top_n": -1}, ParameterError),
    ],
)
def test_keyness_errors(kwargs, error):
    with pytest.raises(error):
        keyness(target, reference, **kwargs)


@pytest.mark.parametrize(("first", "second"), [([], reference), (target, {})])
def test_keyness_of_an_empty_corpus(first, second):
    with pytest.raises(SourceError):
        keyness(first, second)


def test_keyness_of_a_string():
    with pytest.raises(SourceTypeError):
        keyness("the cat sleeps", reference)


@pytest.mark.parametrize("span", [False, True])
def test_refuses_a_doc(span):
    doc = spacy.blank("xx")("The cat sleeps and the cat eats.")
    source = doc[0:3] if span else doc
    with pytest.raises(SourceTypeError, match="WordsExtractor"):
        keyness(source, reference)
