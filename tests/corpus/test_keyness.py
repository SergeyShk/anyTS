from collections import Counter
from collections.abc import Mapping
from math import copysign, inf, isnan, log, nan

import numpy as np
import pytest
import spacy

from anyts import WordsExtractor
from anyts.constants import G2_CRITICAL_VALUES, KEYNESS_MEASURES
from anyts.corpus import FrequencyReference, Keyword, check_keyness_params, keyness
from anyts.corpus.keyness import (
    _MEASURES,
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
    assert set(_MEASURES) == set(KEYNESS_MEASURES)
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
    # The least expected frequencies are 1/3 and 1: the logarithm is negative and zero
    assert isnan(calc_ell(1, 0, 1000, 2000))
    assert isnan(calc_ell(3, 0, 1000, 2000))
    assert calc_ell(5, 0, 1000, 2000) == pytest.approx(
        calc_log_likelihood(5, 0, 1000, 2000) / (3000 * log(5 / 3))
    )
    assert 0 < calc_ell(5, 0, 1000, 1000) < 0.01
    assert 0 < calc_ell(30, 5, 60, 60) < 1
    # Just above one on tiny corpora the measure exceeds one
    assert calc_ell(4, 0, 4, 2) > 1
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


def test_frequency_reference_negative_keywords_are_kept_keys():
    reference = FrequencyReference(
        {"the": 60_000.0, "cat": 50.0, "sleeps": 20.0, "and": 28_000.0},
        1_000_000,
        keep=lambda word: word not in {"the", "and"},
    )
    # "the" and "and" are not counted in the target, so they are no negative keywords
    assert keyness(["the", "cat", "sleeps", "and", "the", "cat"], reference, positive=False) == []
    negative = keyness(["cat"] * 3, reference._replace(keep=None), positive=False)
    assert [keyword.word for keyword in negative] == ["the", "and", "sleeps"]


class Lookups(Mapping):
    """Frequencies that may be looked up but not iterated"""

    def __init__(self, counts):
        self.counts = counts

    def __getitem__(self, key):
        return self.counts[key]

    def __len__(self):
        return len(self.counts)

    def __iter__(self):
        raise AssertionError("the keys of the reference are iterated")


def test_positive_keywords_do_not_iterate_the_reference():
    reference = REFERENCE._replace(counts=Lookups(REFERENCE.counts))
    words = ["cats", "window", "xylophone"]
    assert keyness(words, reference) == keyness(words, REFERENCE)
    with pytest.raises(AssertionError, match="iterated"):
        keyness(words, reference, positive=False)


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
    assert kitty.score == _MEASURES[measure](2, 0, 10, 8) or isnan(kitty.score)
    if measure != "ell":
        assert keywords[0].word == "kitty"


def test_keyness_of_small_corpora_by_the_effect_size():
    keywords = keyness(target, reference, measure="ell")
    # Only "in" is expected more than once in the smaller corpus: 8 · 3 / 18 times
    assert keywords[0].word == "in"
    assert keywords[0].score == calc_ell(2, 1, 10, 8)
    assert all(isnan(keyword.score) for keyword in keywords[1:])
    assert keywords[1].word == "kitty"
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
        ({"top_n": 2.0}, ParameterError),
        ({"measure": ["g2"]}, ParameterError),
        ({"min_freq": 1.5}, ParameterError),
        ({"min_freq": True}, ParameterError),
        ({"min_freq": "2"}, ParameterError),
    ],
)
def test_keyness_errors(kwargs, error):
    with pytest.raises(error):
        keyness(target, reference, **kwargs)


@pytest.mark.parametrize(("first", "second"), [([], reference), (target, {})])
def test_keyness_of_an_empty_corpus(first, second):
    with pytest.raises(SourceError):
        keyness(first, second)


def test_keyness_of_a_string_or_a_set():
    with pytest.raises(SourceTypeError):
        keyness("the cat sleeps", reference)
    with pytest.raises(SourceTypeError):
        keyness(set(target), reference)
    with pytest.raises(SourceTypeError):
        keyness(target, frozenset(reference))
    with pytest.raises(SourceTypeError):
        keyness(Counter({1: 2}), reference)
    with pytest.raises(SourceTypeError, match=r"^The frequencies must be numbers, not str$"):
        keyness({"a": "3"}, ["a", "b"])
    with pytest.raises(SourceTypeError, match=r"target corpus must be whole numbers$"):
        keyness({"cat": 2.5, "the": 3}, reference)
    assert keyness({"cat": 2.0, "the": 3.0}, reference) == keyness({"cat": 2, "the": 3}, reference)
    for count in (-1, float("nan"), float("inf")):
        with pytest.raises(SourceError, match="finite and not negative"):
            keyness({"cat": count, "the": 5}, reference)
    with pytest.raises(SourceTypeError, match=r"^The frequencies must be numbers, not NoneType$"):
        keyness(["a"], {"a": None, "b": 1})
    with pytest.raises(
        SourceTypeError, match=r"^The frequencies of the reference must be a mapping"
    ):
        keyness(target, FrequencyReference(["the", "dog"], 100))


@pytest.mark.parametrize("span", [False, True])
def test_refuses_a_doc(span):
    doc = spacy.blank("xx")("The cat sleeps and the cat eats.")
    source = doc[0:3] if span else doc
    with pytest.raises(SourceTypeError, match="WordsExtractor"):
        keyness(source, reference)


def test_signed_measures_give_a_positive_zero():
    assert copysign(1, calc_chi2(1, 2, 100, 100)) == 1
    assert copysign(1, calc_bic(0, 2, 8, 8)) == 1


@pytest.mark.parametrize(
    "kwargs",
    [{"measure": "tf_idf"}, {"measure": 1}, {"min_freq": 1.5}, {"top_n": 0}, {"top_n": 2.0}],
)
def test_check_keyness_params(kwargs):
    with pytest.raises(ParameterError):
        check_keyness_params(**kwargs)
    with pytest.raises(ParameterError):
        keyness(["cat"], ["dog"], **kwargs)


@pytest.mark.parametrize("target", ["cat dog", 5, {"cat": 1.5}, [1, 2]])
def test_check_keyness_params_target(target):
    with pytest.raises(SourceTypeError):
        check_keyness_params(target=target)


@pytest.mark.parametrize(
    "reference",
    [
        ["dog"],
        FrequencyReference({"dog": 1.0}, 10),
        FrequencyReference({"dog": 1.0}, 10, key=str.lower),
    ],
)
def test_keyness_none_target(reference):
    with pytest.raises(SourceTypeError):
        keyness(None, reference)


def test_check_keyness_params_valid():
    assert check_keyness_params() is None
    assert check_keyness_params("log_ratio", 2, 10) is None
    assert check_keyness_params(target={"cat": 2.0}) is None


@pytest.mark.parametrize(
    ("fields", "error", "message"),
    [
        (
            {"counts": {"cat": -5.0}},
            SourceError,
            r"^The frequencies must be finite and not negative",
        ),
        (
            {"counts": {"cat": nan}},
            SourceError,
            r"^The frequencies must be finite and not negative",
        ),
        ({"counts": {"cat": "5"}}, SourceTypeError, r"^The frequencies must be numbers, not str$"),
        ({"size": nan}, ParameterError, r"^The size of the reference must be a finite number"),
        ({"size": -14}, ParameterError, r"^The size of the reference cannot be negative$"),
        ({"size": "x"}, ParameterError, r"^The size of the reference must be a number, not str$"),
        ({"missing": nan}, ParameterError, r"^The frequency of a missing key must be a finite"),
        ({"missing": -1}, ParameterError, r"^The frequency of a missing key cannot be negative$"),
        ({"key": 1}, SourceTypeError, r"^The key of a word must be callable, not int$"),
        ({"keep": "x"}, SourceTypeError, r"^The filter of the words must be callable, not str$"),
    ],
)
def test_frequency_reference_checks_its_fields(fields, error, message):
    reference = FrequencyReference(**{"counts": {"cat": 5.0}, "size": 100, **fields})
    with pytest.raises(error, match=message):
        keyness(["cat", "dog", "cat"], reference)


def test_keyness_of_ngrams():
    target = ["the", "black", "cat", "sleeps", "and", "the", "black", "cat", "eats"]
    reference = ["the", "white", "cat", "sleeps", "and", "the", "white", "cat", "eats"]
    found = keyness(target, reference, n=2, min_freq=2)
    assert [keyword.word for keyword in found] == ["black_cat", "the_black"]
    assert keyness(target, reference, n=1) == keyness(target, reference)
    # Every n-gram of a list, the last one too, against no common n-gram
    words = ["a", "b", "c", "a", "b"]
    for n, expected in (
        (2, {"a_b": 2, "b_c": 1, "c_a": 1}),
        (3, {"a_b_c": 1, "b_c_a": 1, "c_a_b": 1}),
    ):
        found = keyness(words, ["x", "y", "z"], n=n)
        assert {keyword.word: keyword.freq_target for keyword in found} == expected
    # The reference is cut into n-grams as well
    negative = keyness(target, reference, n=2, positive=False)
    assert {keyword.word: keyword.freq_reference for keyword in negative} == {
        "the_white": 2,
        "white_cat": 2,
    }
    # A mapping is taken as it is, its keys the units already, as the n-grams of WordsExtractor
    bigrams = WordsExtractor(ngram_range=(2, 2)).extract(" ".join(reference))
    assert keyness(target, Counter(bigrams), n=2) == keyness(target, reference, n=2)
    counts = {"black_cat": 2, "the_cat": 1}
    assert [k.word for k in keyness(counts, reference, n=2)][:1] == ["black_cat"]
    for n in (0, -1):
        with pytest.raises(ParameterError, match=r"^The length of the n-grams must be at least 1"):
            keyness(target, reference, n=n)
        with pytest.raises(ParameterError, match=r"^The length of the n-grams must be at least 1"):
            check_keyness_params(n=n)
    with pytest.raises(ParameterError):
        keyness(target, reference, n=1.5)
    # A frequency dictionary holds words
    dictionary = FrequencyReference(Counter(reference), len(reference))
    assert keyness(target, dictionary, n=1) == keyness(target, reference)
    with pytest.raises(ParameterError, match=r"^A FrequencyReference holds words"):
        keyness(target, dictionary, n=2)
    # Fewer words than n leave no n-grams
    with pytest.raises(SourceError):
        keyness(["cat"], reference, n=2)
