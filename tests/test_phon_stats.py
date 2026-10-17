import re
from math import isnan, log2
from typing import ClassVar

import pytest
import spacy

from anyts.constants import MESSAGES, PHON_STATS_DESC
from anyts.exceptions import ParameterError, SourceError, SourceTypeError
from anyts.extractors import WordsExtractor
from anyts.phon_stats import (
    PhonStats,
    check_params,
    consonant_clusters,
    count_hiatus,
    cv_pattern,
)
from anyts.phonetics import calc_repetition_index

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
