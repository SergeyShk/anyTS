from math import isnan, sqrt
from typing import ClassVar

import numpy as np
import pandas as pd
import pytest
import spacy

from anyts.constants import MESSAGES, STYLE_STATS_DESC
from anyts.exceptions import ParameterError, SourceError, SourceTypeError, UnknownStatError
from anyts.extractors import WordsExtractor
from anyts.style_stats import (
    StyleStats,
    calc_academic_nausea,
    calc_classic_nausea,
    calc_keyword_density,
    calc_parentheticals,
    calc_phrase_density,
    calc_spam,
    calc_water,
    calc_zipf_naturalness,
    check_params,
    find_nausea_words,
    find_parentheticals,
)

STOPWORDS = frozenset({"the", "and", "a", "of", "in", "it", "is", "to"})


def test_classic_nausea():
    assert calc_classic_nausea(["cat", "cat", "dog", "cat"]) == sqrt(3)
    assert calc_classic_nausea([]) == 0.0


def test_spam():
    assert calc_spam(["cat", "cat", "dog", "cat"]) == 50.0
    assert calc_spam([]) == 0.0


def test_nausea_words_and_academic_nausea():
    words = ["the", "cat", "and", "the", "dog", "and", "the", "cat", "ran"]
    assert find_nausea_words(words, 2) == {"the": 3, "cat": 2}
    assert find_nausea_words(words, 2, STOPWORDS) == {"cat": 2, "dog": 1}
    assert find_nausea_words(words, 2, is_stopword=STOPWORDS.__contains__) == {"cat": 2, "dog": 1}
    assert find_nausea_words(["The", "cat"], 1, ["the"]) == {"cat": 1}
    upper = find_nausea_words(["THE", "cat"], 1, ["the"], normalize=str.upper)
    assert upper == {"cat": 1}
    assert calc_academic_nausea(words, 2, STOPWORDS) == pytest.approx(100 * 3 / 9)
    assert calc_academic_nausea([], 2) == 0.0


def test_water():
    words = ["the", "cat", "and", "the", "dog"]
    assert calc_water(words, STOPWORDS) == 60.0
    assert calc_water(words, is_water_word=lambda word: word == "and") == 20.0
    assert calc_water(words) == 0.0
    assert calc_water(["The", "cat"], ["the"]) == 50.0


@pytest.mark.parametrize(
    ("words", "top_n", "expected"),
    [
        (
            ["a", "a", "a", "a", "b", "b", "c"],
            10,
            100 * (1 - (abs(2 * 2 - 4) + abs(1 * 3 - 4)) / 8),
        ),
        (["a", "a", "b"], 10, 100.0),
        (["a", "a", "a", "a", "b"], 10, 50.0),
        (["a", "b", "c"], 10, nan := float("nan")),
        (["a", "a", "a"], 10, nan),
        (["a", "a", "b", "b"], 1, nan),
        ([], 10, nan),
        (["a", "a", "a", "a", "a", "a", "b", "b", "b", "b", "b", "b"], 10, 0.0),
    ],
)
def test_zipf_naturalness(words, top_n, expected):
    value = calc_zipf_naturalness(words, top_n)
    assert (isnan(value) and isnan(expected)) or value == pytest.approx(expected)


def test_keyword_density():
    words = ["The", "cat", "and", "the", "cat", "and", "the", "dog"]
    assert calc_keyword_density(words, ["the cat", "dog", ""]) == {
        "the cat": 25.0,
        "dog": 12.5,
        "": 0.0,
    }
    assert list(calc_keyword_density(words, {"dog", "cat"})) == ["cat", "dog"]
    assert calc_keyword_density(words, ["cat and cat"]) == {"cat and cat": 0.0}
    assert calc_keyword_density(["a", "a", "a"], ["a a"]) == {"a a": pytest.approx(200 / 3)}


def test_phrase_density():
    words = ["we", "made", "a", "decision", "and", "makes", "a", "decision", "again"]
    assert calc_phrase_density(words, ["make a decision"]) == 0.0

    def expand(text, phrases):
        return {"made a decision": "make a decision", "make a decision": "make a decision"}

    assert calc_phrase_density(words, ["make a decision"], expand=expand) == pytest.approx(100 / 9)
    assert calc_phrase_density(["A", "Lot"], ["a lot"]) == 50.0


def test_check_params():
    check_params(1)
    with pytest.raises(ParameterError, match="greater than 0"):
        check_params(0)
    with pytest.raises(ParameterError, match="must be an integer"):
        check_params(2.5)


@pytest.mark.parametrize(
    ("func", "args"),
    [
        (calc_classic_nausea, ("cat",)),
        (calc_spam, (["cat", 1],)),
        (calc_water, (["cat"], "the")),
        (find_nausea_words, (["cat"], 1, "the")),
        (calc_keyword_density, (["cat"], "cat")),
        (calc_phrase_density, (["cat"], "a cat")),
    ],
)
def test_errors_of_the_words(func, args):
    with pytest.raises(SourceTypeError):
        func(*args)


class EnglishStyle(StyleStats):
    """The hooks of a language, on English words"""

    compound_prepositions_list = ("in order to", "with regard to")
    parentheticals_list = ("of course", "in fact")
    cliches_list = ("make a decision",)

    def is_stopword(self, word):
        return word in STOPWORDS

    def is_parenthetical(self, word):
        return word == "however"

    def expand_phrases(self, text, phrases):
        expanded = {phrase: phrase for phrase in phrases}
        if "make a decision" in phrases:
            expanded["made a decision"] = "make a decision"
        return expanded

    def nouns(self):
        return [(form, form.rstrip("s")) for form in self.forms if form in NOUNS]

    def is_verbal_noun(self, lemma):
        return lemma.endswith(("tion", "sion"))


NOUNS = frozenset({"decision", "decisions", "report", "organization"})
TEXT = (
    "In fact the organization made a decision in order to write the report. "
    "However the report is late, of course, and the decision is late"
)


@pytest.fixture(scope="module")
def style():
    return EnglishStyle(TEXT)


def test_metrics_of_a_subclass(style):
    words = style.words
    assert len(words) == 25 and words[0] == "in"
    assert style.forms == words
    stats = style.get_stats()
    assert list(stats) == list(STYLE_STATS_DESC)
    assert stats["classic_nausea"] == sqrt(4)
    assert stats["academic_nausea"] == pytest.approx(calc_academic_nausea(words, 10, STOPWORDS))
    assert stats["water"] == pytest.approx(calc_water(words, STOPWORDS))
    assert stats["verbal_nouns"] == pytest.approx(100 * 3 / 5)
    assert stats["compound_prepositions"] == pytest.approx(100 / 25)
    assert stats["parentheticals"] == pytest.approx(100 * 3 / 25)
    assert stats["cliches"] == pytest.approx(100 / 25)


def test_markers(style):
    assert style.markers() == {
        "verbal_nouns": ("organization", "decision", "decision"),
        "compound_prepositions": ("in order to",),
        "parentheticals": ("in fact", "however", "of course"),
        "cliches": ("made a decision",),
    }


def test_nausea_words_and_keywords(style):
    assert list(style.nausea_words())[:2] == ["decision", "report"]
    assert style.keyword_density("decision", "the report") == {
        "decision": 8.0,
        "the report": 8.0,
    }


def test_defaults_of_the_base():
    style = StyleStats("The cat and the dog")
    assert style.words == ("the", "cat", "and", "the", "dog")
    assert style.nausea_words() == {"the": 2, "cat": 1, "and": 1, "dog": 1}
    assert style.water == 0.0
    assert isnan(style.verbal_nouns)
    assert style.compound_prepositions == style.parentheticals == style.cliches == 0.0
    assert style.markers() == dict.fromkeys(
        ("verbal_nouns", "compound_prepositions", "parentheticals", "cliches"), ()
    )
    assert style.describe("water") is None
    assert not style.is_verbal_noun("organization")
    assert not style.is_parenthetical("however")


def test_source_of_a_doc_and_an_extractor():
    doc = spacy.blank("en")("The cat, the well-known cat")
    assert StyleStats(doc).words == ("the", "cat", "the", "well", "known", "cat")

    class Joined(StyleStats):
        join_hyphens = True

    assert Joined(doc).words == ("the", "cat", "the", "well-known", "cat")
    extractor = WordsExtractor(stopwords=["the"])
    style = StyleStats(doc, words_extractor=extractor)
    assert style.words == ("cat", "well", "known", "cat")
    assert style.forms == ("the", "cat", "the", "well", "known", "cat")
    assert StyleStats("The cat, the cat", words_extractor=extractor).words == ("cat", "cat")


def test_parameters():
    style = EnglishStyle(
        TEXT, stopwords=["the"], top_n=2, cliches={"the report"}, nausea_stopwords=["the", "is"]
    )
    assert style.stopwords == ("the",) and style.top_n == 2
    assert style.cliches_list == ("the report",)
    assert style.cliches == pytest.approx(100 * 2 / 25)
    assert style.water == pytest.approx(100 * 4 / 25)
    assert list(style.nausea_words()) == ["in", "decision"]
    assert EnglishStyle.cliches_list == ("make a decision",)


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"source": 5}, SourceTypeError),
        ({"source": "?!"}, SourceError),
        ({"source": TEXT, "words_extractor": 5}, SourceTypeError),
        ({"source": TEXT, "top_n": 0}, ParameterError),
        ({"source": TEXT, "stopwords": "the"}, SourceTypeError),
        ({"source": TEXT, "nausea_stopwords": [1]}, SourceTypeError),
        ({"source": TEXT, "cliches": "make"}, SourceTypeError),
    ],
)
def test_errors(kwargs, error):
    with pytest.raises(error):
        StyleStats(**kwargs)


def test_describe_by_norms():
    class Normed(StyleStats):
        level_scales: ClassVar = {"spam": ((50, "spammed"), (0, "natural"))}

    style = Normed("the cat and the cat")
    assert style.describe("spam") == "natural"
    assert style.describe("cliches") is None
    with pytest.raises(UnknownStatError):
        style.describe("unknown")


def test_own_messages():
    class Own(StyleStats):
        messages: ClassVar = {**MESSAGES, "top_n": "Own top"}

    with pytest.raises(ParameterError, match=r"^Own top$"):
        Own(TEXT, top_n=0)


@pytest.mark.parametrize(
    "name", ["compound_prepositions_list", "parentheticals_list", "cliches_list"]
)
def test_lists_checked_when_a_class_is_defined(name):
    with pytest.raises(SourceTypeError, match=name):
        type("Bad", (StyleStats,), {name: "in fact"})


class Folded(StyleStats):
    """A normalized form that folds two spellings of the same word"""

    parentheticals_list = ("in honor of",)
    cliches_list = ("best endeavor",)

    def normalize(self, word):
        return word.lower().replace("our", "or")


def test_normalize_hook():
    text = "We made our best endeavour in honour of the team and our best endeavor"
    style = Folded(text, stopwords=["colour", "we", "endeavor"], nausea_stopwords=["endeavor"])
    assert style.cliches == pytest.approx(100 * 2 / 14)
    assert style.parentheticals == pytest.approx(100 / 14)
    assert style.markers()["cliches"] == ("best endeavour", "best endeavor")
    assert style.markers()["parentheticals"] == ("in honour of",)
    assert style.water == pytest.approx(100 * 3 / 14)
    assert "endeavour" not in style.nausea_words()
    every = Folded(text, top_n=20, nausea_stopwords=["endeavor"])
    assert every.academic_nausea == pytest.approx(100 * 12 / 14)


def test_phrase_density_normalize():
    words = ["best", "endeavour"]
    assert calc_phrase_density(words, ["best endeavor"]) == 0.0
    fold = Folded("x").normalize
    assert calc_phrase_density(words, ["best endeavor"], normalize=fold) == 50.0


def test_functions_check_their_hooks():
    words = ["the", "cat", "and", "the", "dog"]
    calls = [
        lambda: calc_water(words, is_water_word=42),
        lambda: calc_water(words, ["the"], normalize=42),
        lambda: find_nausea_words(words, is_stopword=42),
        lambda: calc_academic_nausea(words, is_stopword=42),
        lambda: calc_phrase_density(words, ["the cat"], expand=42),
        lambda: calc_phrase_density(words, ["the cat"], normalize=42),
    ]
    for call in calls:
        with pytest.raises(SourceTypeError, match=r" must be callable, not int$"):
            call()


def test_classic_nausea_of_an_array():
    assert calc_classic_nausea(np.array(["a", "b", "a"])) == calc_classic_nausea(["a", "b", "a"])
    assert calc_classic_nausea(pd.Series([], dtype=object)) == 0.0


def test_keyword_density_by_a_normalization():
    words = ["Café", "and", "cafe", "café"]
    assert calc_keyword_density(words, ["café"]) == {"café": 50.0}
    plain = lambda word: word.lower().replace("é", "e")  # noqa: E731
    assert calc_keyword_density(words, ["café"], plain) == {"café": 75.0}
    with pytest.raises(SourceTypeError):
        calc_keyword_density(words, ["café"], "lower")


def test_keyword_density_of_a_class_by_its_normalization():
    class PlainStyle(StyleStats):
        def normalize(self, word):
            return word.lower().replace("é", "e")

    assert PlainStyle("Café and cafe").keyword_density("café") == {"café": pytest.approx(200 / 3)}


def test_parentheticals_of_the_module(style):
    forms = list(style.forms)
    hooks = {"is_parenthetical": style.is_parenthetical, "expand": style.expand_phrases}
    spans = find_parentheticals(forms, EnglishStyle.parentheticals_list, **hooks)
    assert [" ".join(forms[start:end]) for start, end in spans] == list(
        style.markers()["parentheticals"]
    )
    assert calc_parentheticals(forms, EnglishStyle.parentheticals_list, **hooks) == pytest.approx(
        style.parentheticals
    )
    assert find_parentheticals(forms, ["of course"]) == [
        (forms.index("of"), forms.index("of") + 2)
    ]
    assert find_parentheticals(["In", "fact"], ["in fact"], normalize=str) == []
    assert calc_parentheticals(forms) == 0.0
    for hook in ("is_parenthetical", "expand"):
        with pytest.raises(SourceTypeError):
            find_parentheticals(forms, **{hook: "no"})
