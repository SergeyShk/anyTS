import re
from collections import Counter
from math import isnan, sqrt
from typing import ClassVar

import pytest
import spacy

from anyts.basic_stats import BasicStats
from anyts.constants import READABILITY_PRESETS, READABILITY_STATS_DESC
from anyts.exceptions import ParameterError, SourceError, SourceTypeError
from anyts.extractors import SentsExtractor, WordsExtractor
from anyts.readability_stats import (
    ReadabilityStats,
    calc_automated_readability_index,
    calc_coleman_liau_index,
    calc_consensus_grade,
    calc_flesch_kincaid_grade,
    calc_flesch_reading_easy,
    calc_gunning_fog_index,
    calc_lix,
    calc_mu_index,
    calc_reading_time,
    calc_rix,
    calc_smog_index,
    flesch_reading_easy_to_grade,
    grade_to_age,
)

# 2 sentences, 9 words, 11 syllables, 30 letters of the words, one word of three syllables
# and of seven or more letters (beautiful)
TEXT = "The cat sat on the mat. A beautiful day!"


class Stats(BasicStats):
    def count_syllables(self, word):
        return len(re.findall(r"[aeiouy]+", word, re.IGNORECASE))


class Readability(ReadabilityStats):
    basic_stats_class = Stats


@pytest.fixture(scope="module")
def rs():
    return Readability(TEXT)


def test_metrics_by_hand(rs):
    assert rs.flesch_reading_easy == pytest.approx(206.835 - 1.015 * 4.5 - 84.6 * 11 / 9)
    assert rs.flesch_kincaid_grade == pytest.approx(0.39 * 4.5 + 11.8 * 11 / 9 - 15.59)
    assert rs.coleman_liau_index == pytest.approx(0.0588 * 3000 / 9 - 0.296 * 200 / 9 - 15.8)
    assert rs.automated_readability_index == pytest.approx(4.71 * 30 / 9 + 0.5 * 4.5 - 21.43)
    assert rs.smog_index == pytest.approx(1.043 * sqrt(15) + 3.1291)
    assert rs.gunning_fog_index == pytest.approx(0.4 * (4.5 + 100 / 9))
    assert rs.lix == pytest.approx(4.5 + 100 / 9)
    assert rs.rix == 0.5
    # letters 1, 2, 3 (six words) and 9: mean 30 / 9, sample variance 40 / 8
    assert rs.mu_index == pytest.approx(30 / 9 / 5 * 100)
    # grades 1, -3, -3, 7, 6 and the reading ease 98.9 - grade 5
    assert rs.consensus_grade == 3.0
    assert rs.reading_time == 9 / 238


def test_init_basic_stats(rs):
    basic = Stats(TEXT)
    reused = ReadabilityStats(basic)
    assert reused.bs is basic
    assert reused.get_stats() == rs.get_stats()
    # Ready basic statistics are taken as they are, the extractors are not used
    stopwords = WordsExtractor(stopwords=["the"])
    assert Readability(basic, words_extractor=stopwords).bs is basic
    # but are checked all the same
    with pytest.raises(SourceTypeError, match=r"^The word extractor must be a WordsExtractor$"):
        Readability(basic, words_extractor="junk")
    with pytest.raises(
        SourceTypeError, match=r"^The sentence extractor must be a SentsExtractor$"
    ):
        ReadabilityStats(basic, sents_extractor=42)


def test_init_basic_stats_of_another_class():
    class OneSyllable(BasicStats):
        def count_syllables(self, word):
            return 1

    class Words(Stats):
        pass

    message = r"^The basic statistics must be a Stats object, not OneSyllable$"
    with pytest.raises(SourceTypeError, match=message):
        Readability(OneSyllable(TEXT))
    assert Readability(Words(TEXT)).bs.n_syllables == 11
    # Without basic_stats_class any basic statistics are taken
    assert ReadabilityStats(OneSyllable(TEXT)).bs.n_syllables == 9


def test_init_doc(rs):
    assert Readability(spacy.blank("xx")(TEXT)).get_stats() == rs.get_stats()


def test_init_extractors():
    two = Readability(TEXT, words_extractor=WordsExtractor(stopwords=["the", "a", "on"]))
    assert two.bs.n_words == 5
    # The letters of the kept words - cat, sat, mat, beautiful, day - not the 30 of the text
    assert two.coleman_liau_index == pytest.approx(0.0588 * 2100 / 5 - 0.296 * 200 / 5 - 15.8)
    assert two.automated_readability_index == pytest.approx(4.71 * 21 / 5 + 0.5 * 2.5 - 21.43)
    one = Readability(TEXT, sents_extractor=SentsExtractor(min_len=20))
    assert one.bs.n_sents == 1


def test_init_without_basic_stats_class():
    with pytest.raises(SourceTypeError, match=r"^ReadabilityStats has no basic_stats_class"):
        ReadabilityStats(TEXT)


@pytest.mark.parametrize("source", [666, ["a", "b"], {"a": "b"}])
def test_init_type_error(source):
    with pytest.raises(SourceTypeError):
        Readability(source)


def test_init_no_words_error():
    with pytest.raises(SourceError, match="words"):
        Readability("+ _")


def test_init_no_sents_error():
    with pytest.raises(SourceError, match="sentences"):
        Readability("A text. Another text.", sents_extractor=SentsExtractor(min_len=1000))


@pytest.mark.parametrize(
    ("preset", "message"),
    [
        ("unknown", r"^Unknown coefficient preset: unknown\. Available presets: \('original',\)$"),
        (["original"], r"^The preset must be a string, not list$"),
    ],
)
def test_init_preset_error(preset, message):
    with pytest.raises(ParameterError, match=message):
        Readability(TEXT, preset=preset)


def test_default_preset(rs):
    assert rs.preset == "original"
    assert rs.coefficients == READABILITY_PRESETS["original"]


def test_coefficients_copy():
    rs = Readability(TEXT)
    rs.coefficients["flesch_reading_easy"] = (1.0, 62.3, 206.835)
    assert rs.flesch_reading_easy == pytest.approx(206.835 - 4.5 - 62.3 * 11 / 9)
    assert READABILITY_PRESETS["original"]["flesch_reading_easy"] == (1.015, 84.6, 206.835)
    del rs.coefficients["flesch_reading_easy"]
    assert rs.flesch_reading_easy == Readability(TEXT).flesch_reading_easy


@pytest.mark.parametrize(
    ("stat", "coefficients", "expected"),
    [
        ("flesch_reading_easy", (1.0, 62.3, 206.835), 206.835 - 4.5 - 62.3 * 11 / 9),
        ("flesch_kincaid_grade", (0.5, 8.4, 15.59), 0.5 * 4.5 + 8.4 * 11 / 9 - 15.59),
        ("coleman_liau_index", (0.055, 0.35, 20.33), 0.055 * 3000 / 9 - 0.35 * 200 / 9 - 20.33),
        ("automated_readability_index", (6.26, 0.28, 31.04), 6.26 * 30 / 9 + 0.28 * 4.5 - 31.04),
        ("smog_index", (1.1, 64.6, 0.05), 1.1 * sqrt(64.6 / 2) + 0.05),
        ("gunning_fog_index", (0.5,), 0.5 * (4.5 + 100 / 9)),
    ],
)
def test_preset_coefficients(rs, stat, coefficients, expected):
    class Preset(Readability):
        presets: ClassVar = {"one": {stat: coefficients}}

    value = getattr(Preset(TEXT, preset="one"), stat)
    assert value == pytest.approx(expected)
    assert value != pytest.approx(getattr(rs, stat))


class Custom(Readability):
    presets: ClassVar = {
        "short": {"smog_index": (1.1, 64.6, 0.05)},
        "long": {"smog_index": (1.1, 64.6, 0.05), "gunning_fog_index": (0.5,)},
    }
    grade_stats = ("smog_index", "rix_grade")
    stats_desc: ClassVar = {"rix_grade": "RIX grade", "smog_index": "SMOG index"}
    stats_headers = ("Measure", "Score")
    smog_complex_syl_factor = 1
    lix_long_word_letter_factor = 3
    grade_age_levels = ((1, 7, "lower school", "6-13 years"),)
    postgraduate_level = ("upper school", "over 13 years")
    reading_speed = 90
    reading_speed_norms: ClassVar = {"slow": (30, 45, 90)}

    def __init__(self, source, preset="short"):
        super().__init__(source, preset=preset)

    @property
    def rix_grade(self):
        return self.rix * 2

    def reading_ease_to_grade(self, flesch_reading_easy):
        return 1.5


def test_hooks():
    rs = Custom(TEXT)
    assert rs.preset == "short"
    # nine words of a syllable or more, seven of three letters or more
    assert rs.smog_index == pytest.approx(1.1 * sqrt(64.6 * 9 / 2) + 0.05)
    assert rs.gunning_fog_index == pytest.approx(0.4 * (4.5 + 100))
    assert Custom(TEXT, "long").gunning_fog_index == pytest.approx(0.5 * (4.5 + 100))
    assert rs.lix == pytest.approx(4.5 + 700 / 9)
    assert rs.rix_grade == 7.0
    # smog 18.8 and rix_grade 7 rounded, the reading ease 1.5
    assert rs.consensus_grade == 7.0
    assert rs.describe_grade() == "lower school (6-13 years)"
    assert rs.describe_grade("smog_index") == "upper school (over 13 years)"
    assert rs.reading_time == 0.1
    assert rs.reading_time_by_norm("slow") == (0.3, 0.2, 0.1)
    assert rs.get_stats() == {"rix_grade": 7.0, "smog_index": rs.smog_index}
    with pytest.raises(ParameterError, match=r"Grade formulas: \('consensus_grade', 'smog_index'"):
        rs.describe_grade("flesch_kincaid_grade")
    with pytest.raises(ParameterError, match=r"Available norms: \('slow',\)$"):
        rs.reading_time_by_norm("adult")


def test_consensus_grade_hook():
    class Hard(Custom):
        def reading_ease_to_grade(self, flesch_reading_easy):
            return 30

    # smog 19 and rix_grade 7 rounded, the reading ease 30 instead of 5 by default
    assert Hard(TEXT).consensus_grade == 19.0


def test_print_stats_hooks(capsys):
    Custom(TEXT).print_stats()
    lines = capsys.readouterr().out.split("\n")
    assert lines[0] == f"{'Measure':^45}|{'Score':^10}"
    assert lines[2] == f"{'RIX grade':45}|{7.0:^10.2f}"


def test_describe_grade(rs):
    assert rs.describe_grade() == "elementary school, grades 1-5 (6-11 years)"
    assert rs.describe_grade("smog_index") == grade_to_age(rs.smog_index)
    with pytest.raises(ParameterError, match=r"^The metric lix is not a grade formula"):
        rs.describe_grade("lix")


def test_reading_time_by_speed(rs):
    assert rs.reading_time_by_speed(238) == rs.reading_time
    assert rs.reading_time_by_speed(4.5) == 2.0
    with pytest.raises(ParameterError):
        rs.reading_time_by_speed(-1)


def test_reading_time_by_norm(rs):
    assert rs.reading_time_by_norm("adult") == (9 / 183, 9 / 238)
    assert rs.reading_time_by_norm("adult")[1] == rs.reading_time
    for norm in ("grade_1", ["adult"]):
        with pytest.raises(ParameterError, match=r"^Unknown reading speed norm"):
            rs.reading_time_by_norm(norm)


def test_get_stats(rs):
    stats = rs.get_stats()
    assert list(stats) == list(READABILITY_STATS_DESC)
    for key in READABILITY_STATS_DESC:
        assert stats[key] == getattr(rs, key)


def test_print_stats(capsys, rs):
    rs.print_stats()
    lines = capsys.readouterr().out.split("\n")
    assert lines[0] == f"{'Metric':^45}|{'Value':^10}"
    assert lines[1] == "-" * 55
    assert lines[2] == f"{'Flesch reading ease':45}|{rs.flesch_reading_easy:^10.2f}"
    assert len(lines) == len(READABILITY_STATS_DESC) + 3


def test_formulas():
    assert calc_flesch_reading_easy(15, 10, 2) == pytest.approx(74.86)
    assert calc_flesch_reading_easy(23, 10, 1, 1.0, 62.3, 206.835) == pytest.approx(53.545)
    assert calc_flesch_kincaid_grade(15, 10, 2) == pytest.approx(4.06)
    assert calc_flesch_kincaid_grade(15, 10, 2, 0.5, 8.4, 15.59) == pytest.approx(-0.49)
    assert calc_coleman_liau_index(50, 10, 2) == pytest.approx(7.68)
    assert calc_automated_readability_index(50, 10, 2) == pytest.approx(4.62)
    assert calc_smog_index(3, 10) == pytest.approx(1.043 * 3 + 3.1291)
    assert calc_smog_index(0, 1) == pytest.approx(3.1291)
    assert calc_smog_index(30, 30) == pytest.approx(8.8418, abs=0.0001)
    assert calc_smog_index(5, 10, 1.1, 64.6, 0.05) == pytest.approx(1.1 * sqrt(32.3) + 0.05)
    assert calc_gunning_fog_index(2, 10, 2) == pytest.approx(10.0)
    assert calc_gunning_fog_index(2, 10, 2, 0.5) == pytest.approx(12.5)
    assert calc_lix(3, 10, 2) == 35.0
    assert calc_rix(3, 2) == 1.5


def test_mu_index():
    # the worked example of the authors' manual: 18 words, mean 6.9444, sample variance 13.5844
    manual = Counter([4, 6, 5, 5, 8, 14, 11, 11, 6, 1, 4, 10, 9, 11, 7, 3, 9, 1])
    assert calc_mu_index(manual) == pytest.approx(51.12, abs=0.01)
    assert calc_mu_index({3: 5, 5: 5}) == pytest.approx(360.0)
    assert calc_mu_index({0: 4, 3: 5, 5: 5}) == calc_mu_index({3: 5, 5: 5})
    assert isnan(calc_mu_index({3: 1}))
    assert isnan(calc_mu_index({3: 5}))
    assert isnan(calc_mu_index({}))


@pytest.mark.parametrize(
    ("flesch_reading_easy", "grade"),
    [(120, 5), (90, 5), (89.9, 6), (65, 8.5), (50, 10), (30, 12), (29.9, 13), (-50, 13)],
)
def test_flesch_reading_easy_to_grade(flesch_reading_easy, grade):
    assert flesch_reading_easy_to_grade(flesch_reading_easy) == grade


def test_flesch_reading_easy_to_grade_bands():
    bands = ((80, 3), (65, 5), (55, 8), (40, 11))
    assert flesch_reading_easy_to_grade(70, bands) == 5
    assert flesch_reading_easy_to_grade(39.9, bands) == 13
    assert flesch_reading_easy_to_grade(39.9, bands, below=14) == 14
    assert flesch_reading_easy_to_grade(float("nan")) == 13


def test_calc_consensus_grade():
    # grades 4, 5, 8 and the reading ease 65 - grade 8.5
    assert calc_consensus_grade([4.4, 4.6, 7.5], 65.0) == 6.5
    assert calc_consensus_grade([10, 12, 14], 65.0) == 11.0
    assert calc_consensus_grade([2.5, 2.5, 3.4]) == 3.0
    assert calc_consensus_grade([8.5]) == 9.0
    assert calc_consensus_grade([], 65.0) == 8.5
    assert calc_consensus_grade(iter([7.0])) == 7.0
    assert calc_consensus_grade([12.0], 53.545) == 11.0
    assert calc_consensus_grade([12.0], 53.545, lambda value: 11) == 11.5
    with pytest.raises(ParameterError, match=r"^The list of grade formulas is empty$"):
        calc_consensus_grade([])
    with pytest.raises(SourceTypeError, match=r"^to_grade must be callable, not str$"):
        calc_consensus_grade([1.0], 50.0, "classic")


@pytest.mark.parametrize(
    ("grade", "expected"),
    [
        (-3, "elementary school, grades 1-5 (6-11 years)"),
        (5.4, "elementary school, grades 1-5 (6-11 years)"),
        (5.5, "middle school, grades 6-8 (11-14 years)"),
        (12.4, "high school, grades 9-12 (14-18 years)"),
        (16.4, "college (18-22 years)"),
        (16.5, "graduate school (over 22 years)"),
    ],
)
def test_grade_to_age(grade, expected):
    assert grade_to_age(grade) == expected


def test_grade_to_age_levels():
    levels = ((1, 3, "early", "6-9"), (4, 6, "late", "9-12"))
    assert grade_to_age(3.4, levels, ("adult", "12+")) == "early (6-9)"
    assert grade_to_age(6.5, levels, ("adult", "12+")) == "adult (12+)"


def test_calc_reading_time():
    assert calc_reading_time(476) == 2.0
    assert calc_reading_time(278, 139) == 2.0
    for wpm in (0, -1, float("nan"), "238", True, None):
        with pytest.raises(ParameterError):
            calc_reading_time(100, wpm)


@pytest.mark.parametrize("grade", [float("nan"), float("inf"), "5", None])
def test_grades_must_be_finite_numbers(grade):
    with pytest.raises(ParameterError, match="grade must be"):
        calc_consensus_grade([grade, 3.0])
    with pytest.raises(ParameterError, match="grade must be"):
        grade_to_age(grade)


def test_reading_speed_must_be_finite():
    with pytest.raises(ParameterError, match="finite"):
        calc_reading_time(100, float("inf"))


@pytest.mark.parametrize(
    "value",
    [
        lambda: calc_flesch_reading_easy(10, 0, 0),
        lambda: calc_flesch_kincaid_grade(10, 5, 0),
        lambda: calc_coleman_liau_index(10, 0, 1),
        lambda: calc_automated_readability_index(10, 5, 0),
        lambda: calc_smog_index(3, 0),
        lambda: calc_gunning_fog_index(3, 0, 1),
        lambda: calc_lix(3, 0, 2),
        lambda: calc_rix(3, 0),
    ],
)
def test_formulas_without_words_or_sentences(value):
    assert isnan(value())


def test_calc_mu_index_of_no_mapping():
    with pytest.raises(
        SourceTypeError, match=r"^A mapping of word lengths to counts is expected, not NoneType$"
    ):
        calc_mu_index(None)
