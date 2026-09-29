from itertools import permutations
from math import comb, fsum, isnan

import numpy as np
import pandas as pd
import pytest
import spacy

from anyts.exceptions import ParameterError, SourceTypeError
from anyts.phonetics import _count_windows, calc_repetition_index

WORDS = ["casa", "cosa", "luna", "sol", "mar", "mesa", "paz"]


@pytest.mark.parametrize("window_len", [2, 3, 4])
def test_calc_repetition_index_random_order(window_len):
    # The expectation does not depend on the order, so the index averages to 1
    values = [calc_repetition_index(list(words), window_len) for words in permutations(WORDS)]
    assert fsum(values) / len(values) == pytest.approx(1, abs=1e-12)


def test_calc_repetition_index_value():
    words = ["sal", "sol", "mes", "luz", "paz", "mar"]
    # s in 3 of 6 words: 2 of the 5 windows of 2 hold it twice, 5 * C(3, 2) / C(6, 2) expected
    assert calc_repetition_index(words, 2, {"s"}) == 2 / (5 * comb(3, 2) / comb(6, 2))
    # 2 of the 4 windows of 3, and half of the windows expected
    assert calc_repetition_index(words, 3, ["s"]) == 1.0


def test_calc_repetition_index_features():
    by_letters = calc_repetition_index(WORDS, 3)
    assert calc_repetition_index(WORDS, 3, set("acelmnopsuz")) == by_letters
    assert calc_repetition_index(WORDS, 3, {"a"}) != by_letters
    # A feature absent from the text is left out
    assert calc_repetition_index(WORDS, 3, {"a", "x"}) == calc_repetition_index(WORDS, 3, {"a"})


def test_calc_repetition_index_words():
    # A word is a string of its letters or a collection of its sounds, each counted once
    sounds = [("k", "a", "s", "a"), ("k", "o", "s", "a"), ("θ", "e", "n", "a")]
    assert calc_repetition_index(sounds, 2, {"k", "θ"}) == calc_repetition_index(
        [["k"], ["k"], ["θ"]], 2
    )
    assert calc_repetition_index([set("casa"), "cosa", ("l", "u")], 2) == calc_repetition_index(
        ["cas", "cosa", "lu"], 2
    )


def test_calc_repetition_index_every_word():
    # A feature in every word repeats in every window, as expected
    assert calc_repetition_index(["ab", "ac", "ad", "ae"], 2, {"a"}) == 1.0


def test_calc_repetition_index_single_window():
    # Every feature of two words or more repeats in the only window, as expected
    assert calc_repetition_index(["sal", "sol", "mar"], 3, {"s"}) == 1.0


@pytest.mark.parametrize(
    "features",
    [{"s"}, ["s"], pd.Series(["s"], index=[5]), np.array(["s"])],
)
def test_calc_repetition_index_features_types(features):
    words = ["sal", "sol", "mes", "luz", "paz", "mar"]
    assert calc_repetition_index(words, 2, features) == 2.0


@pytest.mark.parametrize(
    "words", [np.array(WORDS), pd.Series(WORDS, index=range(10, 10 + len(WORDS)))]
)
def test_calc_repetition_index_arrays(words):
    assert calc_repetition_index(words, 3) == calc_repetition_index(WORDS, 3)


def test_count_windows_in_blocks():
    # A large alphabet is counted over blocks of columns with the same result
    words = [chr(0x4E00 + index % 97) + chr(0x4E00 + index * 7 % 89) for index in range(500)]
    presence = np.array([[chr(0x4E00 + i) in word for i in range(97)] for word in words])
    rows = np.arange(len(words))
    assert _count_windows(presence, rows, 3, block_size=5) == _count_windows(presence, rows, 3)
    assert calc_repetition_index(words, 3) > 0


@pytest.mark.parametrize(
    ("words", "window_len", "features"),
    [
        ([], 2, None),
        (["casa"], 2, None),
        (["casa", "cosa"], 3, None),
        (["ab", "cd", "ef"], 2, None),
        (["ab", "ab", "cd"], 2, {"c", "d", "e", "f"}),
        (["casa", "cosa"], 2, {"x"}),
    ],
)
def test_calc_repetition_index_nan(words, window_len, features):
    assert isnan(calc_repetition_index(words, window_len, features))


@pytest.mark.parametrize(
    ("words", "features", "message"),
    [
        ("casa cosa", None, r"^A list of words is expected, not a string$"),
        (iter(WORDS), None, r"^A list of words is expected, not an iterator$"),
        (["casa", 1], None, r"^A list of features of a word is expected, not int$"),
        (["casa", [1]], None, r"^The features of a word must be strings, not int$"),
        (["casa", ("c", ["a"])], None, r"^The features of a word must be strings, not list$"),
        (WORDS, "a", r"^A list of features is expected, not a string$"),
        (WORDS, [1], r"^The features must be strings, not int$"),
    ],
)
def test_calc_repetition_index_source_errors(words, features, message):
    with pytest.raises(SourceTypeError, match=message):
        calc_repetition_index(words, 2, features)


def test_calc_repetition_index_tokens():
    with pytest.raises(SourceTypeError, match=r"not a Doc"):
        calc_repetition_index(spacy.blank("xx")("casa cosa"), 2)


@pytest.mark.parametrize(
    ("window_len", "message"),
    [
        (1, r"^The window must be at least 2$"),
        (2.0, r"^The window must be an integer, not float$"),
        (True, r"^The window must be an integer, not bool$"),
    ],
)
def test_calc_repetition_index_window(window_len, message):
    with pytest.raises(ParameterError, match=message):
        calc_repetition_index(WORDS, window_len)
