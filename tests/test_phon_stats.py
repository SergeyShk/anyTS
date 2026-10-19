import re
from itertools import permutations
from math import comb, fsum, isnan, log2
from typing import ClassVar

import numpy as np
import pandas as pd
import pytest
import spacy

from anyts.constants import MESSAGES, PHON_STATS_DESC
from anyts.exceptions import ParameterError, SourceError, SourceTypeError
from anyts.extractors import WordsExtractor
from anyts.phon_stats import (
    PhonStats,
    _count_windows,
    calc_repetition_index,
    check_params,
    consonant_clusters,
    count_hiatus,
    cv_pattern,
)

VOWELS = frozenset("aeiou")
SONORANTS = frozenset("lmnrwy")
VOICED = frozenset("bdgvz")
VOICELESS = frozenset("cfhkpqstx")
CONSONANTS = SONORANTS | VOICED | VOICELESS
SYLLABLE = re.compile(r"[^aeiou]*[aeiou]+(?:[^aeiou]+$)?")


class English(PhonStats):
    """Letters as sounds and a rough syllabification by the vowels"""

    vowels = VOWELS
    sonorants = SONORANTS
    voiced = VOICED
    voiceless = VOICELESS

    def syllabify(self, word):
        return SYLLABLE.findall(word) or [word]


TEXT = "The poet sat on a stone by the stream"


@pytest.fixture(scope="module")
def stats():
    return English(TEXT)


def test_helpers():
    assert cv_pattern("stream", VOWELS, CONSONANTS) == "CCCVVC"
    assert cv_pattern("a-1b", VOWELS, CONSONANTS) == "VC"
    assert consonant_clusters("stream", CONSONANTS) == (3, 1)
    assert consonant_clusters("s'tr", CONSONANTS, skipped="'") == (3,)
    assert consonant_clusters("s-tr", CONSONANTS) == (1, 2)
    assert consonant_clusters("aei", CONSONANTS) == ()
    assert count_hiatus("poet", VOWELS) == 1
    assert count_hiatus("queue", VOWELS) == 1
    assert count_hiatus("cooperation", VOWELS) == 2
    assert count_hiatus("poet", VOWELS, glides="e") == 0


def test_words_and_counts(stats):
    assert stats.words == ("the", "poet", "sat", "on", "a", "stone", "by", "the", "stream")
    assert stats.syllables[1] == ("poet",) and stats.syllables[5] == ("sto", "ne")
    assert stats.sounds == stats.words
    letters = "".join(stats.words)
    assert stats.n_vowels == sum(letter in VOWELS for letter in letters)
    assert stats.n_sonorants == sum(letter in SONORANTS for letter in letters)
    assert stats.n_voiced == sum(letter in VOICED for letter in letters)
    assert stats.n_voiceless == sum(letter in VOICELESS for letter in letters)
    assert stats.n_consonants == stats.n_sonorants + stats.n_voiced + stats.n_voiceless


def test_metrics(stats):
    n_sounds = stats.n_vowels + stats.n_consonants
    assert stats.p_vowels == stats.n_vowels / n_sounds
    assert stats.consonant_vowel_ratio == stats.n_consonants / stats.n_vowels
    assert stats.hardness == stats.n_voiceless / (stats.n_vowels + stats.n_sonorants)
    # th; p t; s t; n; st n; by (y is a sonorant); th; str m
    assert stats.c_clusters == {1: 7, 2: 4, 3: 1}
    assert stats.p_heavy_clusters == 1 / 12
    # poet and stream, one hiatus each
    assert stats.p_hiatus == 2 / 9
    patterns = ["CCV", "CVVC", "CVC", "VC", "V", "CCVCV", "CC", "CCV", "CCCVVC"]
    total = len(patterns)
    counts = {pattern: patterns.count(pattern) for pattern in dict.fromkeys(patterns)}
    entropy = -sum(c / total * log2(c / total) for c in counts.values())
    assert stats.cv_entropy == pytest.approx(entropy)
    assert stats.alliteration == calc_repetition_index(stats.words, 3, CONSONANTS)
    assert stats.assonance == calc_repetition_index(stats.words, 3, VOWELS)
    syllables = [s for word in stats.syllables for s in word]
    assert stats.mean_syllable_len == sum(map(len, syllables)) / len(syllables)
    opened = sum(cv_pattern(s, VOWELS, CONSONANTS).endswith("V") for s in syllables)
    assert stats.p_open_syllables == opened / len(syllables)
    assert stats.c_syllable_patterns["CCV"] == 3
    assert list(stats.get_stats()) == list(PHON_STATS_DESC)


class Transcribed(English):
    """Sounds of a transcription: th as one sound, a sign that keeps clusters, glides"""

    skipped = frozenset("'")
    glides = frozenset("u")

    def transcribe(self, word):
        return tuple(word.replace("th", "θ"))

    def word_hiatus(self, word):
        return 7 if word == "poet" else 0


@pytest.mark.parametrize(
    ("hook", "result", "expected"),
    [
        ("syllabify", "the", "a sequence of strings"),
        ("syllabify", ["th", 5], "a sequence of strings"),
        ("transcribe", {"t"}, "a string or strings"),
        ("transcribe", [b"t"], "a string or strings"),
    ],
)
def test_results_of_the_hooks_are_checked(hook, result, expected):
    hooked = type("Hooked", (English,), {hook: lambda self, word: result})
    with pytest.raises(SourceTypeError, match=f"must return {expected}"):
        hooked(TEXT)


def test_hooks():
    stats = Transcribed("The poet sat")
    assert stats.sounds[0] == ("θ", "e")
    assert stats.p_hiatus == 7 / 3
    assert stats.c_clusters == {1: 4}

    class Unsigned(English):
        voiceless = VOICELESS - {"h"}

    class Signed(Unsigned):
        skipped = frozenset("h")

    assert Unsigned("three").c_clusters == {1: 2}
    assert Signed("three").c_clusters == {2: 1}

    class Glided(English):
        glides = frozenset("e")

    assert Glided("poet").p_hiatus == 0
    assert English("poet").p_hiatus == 1


def test_syllable_sounds_follow_transcribe():
    stats = Transcribed("thin")
    assert stats.syllables == (("thin",),)
    assert stats.mean_syllable_len == 3


def test_source_of_a_doc_and_an_extractor():
    doc = spacy.blank("en")("The well-known poet")
    assert English(doc).words == ("the", "well", "known", "poet")

    class Joined(English):
        join_hyphens = True

    assert Joined(doc).words == ("the", "well-known", "poet")
    extractor = WordsExtractor(stopwords=["the"])
    assert English(doc, words_extractor=extractor).words == ("well", "known", "poet")
    assert English("The poet", words_extractor=extractor).words == ("poet",)


def test_text_without_sounds():
    stats = English("2020 1999")
    assert stats.n_vowels == stats.n_consonants == 0
    assert isnan(stats.p_vowels) and isnan(stats.p_hiatus) and isnan(stats.cv_entropy)
    assert stats.c_clusters == {}


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"source": 5}, SourceTypeError),
        ({"source": "?!"}, SourceError),
        ({"source": TEXT, "words_extractor": 5}, SourceTypeError),
        ({"source": TEXT, "window_len": 1}, ParameterError),
        ({"source": TEXT, "window_len": 2.5}, ParameterError),
    ],
)
def test_errors(kwargs, error):
    with pytest.raises(error):
        English(**kwargs)


def test_check_params_and_messages():
    check_params(2)
    with pytest.raises(ParameterError, match="at least 2"):
        check_params(1)

    class Own(English):
        messages: ClassVar = {**MESSAGES, "phon_window_len": "Own window"}

    with pytest.raises(ParameterError, match=r"^Own window$"):
        Own(TEXT, window_len=1)


def test_syllabify_is_required():
    with pytest.raises(TypeError, match="abstract"):
        PhonStats(TEXT)


def test_syllables_without_sounds():
    stats = English("1999 2020")
    assert isnan(stats.p_open_syllables) and isnan(stats.mean_syllable_len)
    assert stats.c_syllable_patterns == {}
    with_number = English(TEXT + " 1999")
    assert with_number.c_syllable_patterns == English(TEXT).c_syllable_patterns
    assert with_number.mean_syllable_len == English(TEXT).mean_syllable_len


@pytest.mark.parametrize(
    ("attributes", "message"),
    [
        ({"voiced": VOICED | SONORANTS}, "sonorants and voiced of Bad overlap"),
        ({"vowels": VOWELS | {"y"}}, "vowels and sonorants of Bad overlap: \\['y'\\]"),
        ({"skipped": frozenset("t")}, "voiceless and skipped of Bad overlap"),
    ],
)
def test_classes_of_sounds_are_disjoint(attributes, message):
    with pytest.raises(ParameterError, match=message):
        type("Bad", (English,), attributes)


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
    # A large alphabet is counted over blocks of columns as in one pass
    words = [chr(0x4E00 + index % 97) + chr(0x4E00 + index * 7 % 89) for index in range(500)]
    presence = np.array(
        [[chr(0x4E00 + i) in word for i in range(97)] for word in words], dtype=np.int8
    )
    rows = np.arange(len(words))
    single = _count_windows(presence, rows, 3, block_size=presence.shape[1])
    assert single[0] == 30
    assert _count_windows(presence, rows, 3) == _count_windows(presence, rows, 3, 5) == single


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
        (1, r"^The size of a window must be at least 2$"),
        (2.0, r"^The size of a window must be an integer, not float$"),
        (True, r"^The size of a window must be an integer, not bool$"),
    ],
)
def test_calc_repetition_index_window(window_len, message):
    with pytest.raises(ParameterError, match=message):
        calc_repetition_index(WORDS, window_len)


def test_sound_classes_checked_at_class_definition():
    with pytest.raises(SourceTypeError, match=r"^A list of vowels is expected, not a string$"):
        type("Sounded", (English,), {"vowels": "aeiou"})
