import math
import re
import string
import sys
import unicodedata
from collections import Counter

import numpy as np
import pandas as pd
import pytest
import spacy
from spacy.tokens import Doc

from anyts.constants import MESSAGES
from anyts.document import get_tree, to_document
from anyts.exceptions import ParameterError, SourceError, SourceTypeError
from anyts.utils import (
    _PUNCTUATION_CATEGORIES,
    check_bool,
    check_callable,
    check_counts,
    check_integer,
    check_number,
    check_sequence,
    check_word,
    check_words,
    count_letters,
    count_words_by_spans,
    find_phrases,
    has_feature,
    has_words,
    in_order,
    is_doc,
    is_finite_verb,
    is_infinitive,
    is_language,
    is_number,
    is_punctuation,
    is_span,
    is_token,
    safe_divide,
    safe_mean,
    shannon_entropy,
)


@pytest.fixture(scope="module")
def nlp():
    return spacy.blank("xx")


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        (".", True),
        ("?!", True),
        ("!..", True),
        ("--", True),
        ("…", True),
        ("¿", True),
        ("¡", True),
        ("«", True),
        ("”", True),
        ("„", True),
        ("·", True),
        ("€", True),
        ("%", True),
        ("№", True),
        ("°", True),
        ("\u200b", True),
        ("\ufeff", True),
        ("\u200d", True),
        ("\ufe0f", True),
        ("\u0301", True),
        ("\u200b\u200b", True),
        ("", True),
        ("a", False),
        ("ñ", False),
        ("3", False),
        ("º", False),
        ("ʼ", False),
        ("no.", False),
        ("well-known", False),
        ("e\u0301", False),
        ("\ufeffStart", False),
        ("٣", False),
    ],
)
def test_is_punctuation(token, expected):
    assert is_punctuation(token) is expected


def test_punctuation_categories():
    categories = {unicodedata.category(chr(code)) for code in range(sys.maxunicode + 1)}
    assert {category for category in categories if category[0] in "PSM"} | {"Cf"} == (
        _PUNCTUATION_CATEGORIES
    )


def test_is_punctuation_ascii():
    assert is_punctuation(string.punctuation)
    assert not any(is_punctuation(char) for char in string.ascii_letters + string.digits)


@pytest.mark.parametrize(
    ("word", "expected"),
    [("cat", 3), ("well-known", 9), ("3rd", 2), ("ñu", 2), ("n.º", 2), ("", 0), ("42", 0)],
)
def test_count_letters(word, expected):
    assert count_letters(word) == expected


def test_count_letters_cached():
    count_letters.cache_clear()
    assert count_letters("cats") == count_letters("cats") == 4
    assert count_letters.cache_info().hits == 1
    assert count_letters.cache_info().misses == 1


def test_safe_divide():
    assert safe_divide(1, 4) == 0.25
    assert safe_divide(1, 0) == 0
    assert safe_divide(0, 0) == 0
    assert safe_divide(1.5, 0.0, default=-1) == -1
    assert math.isnan(safe_divide(1, 0, default=math.nan))


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("The cat sleeps", True),
        ("5 %", True),
        ("?!", False),
        ("...", False),
        ("«»", False),
        ("€ + %", False),
        ("   ", False),
        ("\u200b \ufeff", False),
        ("\u200b a", True),
        # Characters of no class: a bullet of private use, a control character
        ("\uf0b7 \x07", False),
        ("\uf0b7a", True),
        ("", False),
    ],
)
def test_has_words(text, expected):
    assert has_words(text) is expected


@pytest.mark.parametrize("text", ["The cat sleeps", "?!", ""])
def test_has_words_of_a_doc(nlp, text):
    assert has_words(nlp(text)) is has_words(text)


def test_is_language(nlp):
    assert is_language(nlp) and not is_language("en_core_web_sm") and not is_language(None)
    assert not is_language(nlp("The cat"))


def test_is_doc_and_is_span(nlp):
    doc = nlp("The cat sleeps")
    assert (is_doc(doc), is_doc(doc[:2]), is_doc(doc[0]), is_doc(doc.text)) == (
        True,
        False,
        False,
        False,
    )
    assert (is_span(doc[:2]), is_span(doc), is_span(doc[0]), is_span(None)) == (
        True,
        False,
        False,
        False,
    )


def test_has_words_of_a_span(nlp):
    doc = nlp("The cat sleeps. ?!")
    assert [has_words(span) for span in (doc[0:3], doc[4:])] == [True, False]


@pytest.mark.parametrize("value", [["the", "cat"], ("the",), []])
def test_check_sequence(value):
    assert check_sequence(value) is None


@pytest.mark.parametrize(("value", "name"), [(None, "NoneType"), (42, "int")])
def test_check_sequence_not_iterable(value, name):
    with pytest.raises(SourceTypeError, match=rf"^A list of words is expected, not {name}$"):
        check_sequence(value)
    with pytest.raises(SourceTypeError, match=rf"^A list of words is expected, not {name}$"):
        check_words(value)


def test_check_sequence_errors(nlp):
    with pytest.raises(SourceTypeError, match=r"^A list of texts is expected, not a string$"):
        check_sequence("the cat", "texts")
    doc = nlp("The cat")
    with pytest.raises(SourceTypeError, match="not a Doc: extract the words"):
        check_sequence(doc)
    with pytest.raises(SourceTypeError, match="not a Span"):
        check_sequence(doc[:1])
    for value in (b"the cat", bytearray(b"the")):
        with pytest.raises(SourceTypeError, match=r"^A list of words is expected, not a string$"):
            check_sequence(value)


@pytest.mark.parametrize("value", [iter([]), (word for word in "ab"), map(str.lower, "ab")])
def test_check_sequence_iterators(value):
    with pytest.raises(
        SourceTypeError, match=r"^A list of stopwords is expected, not an iterator$"
    ):
        check_sequence(value, "stopwords")


@pytest.mark.parametrize("value", [["the", "cat"], ("the",), []])
def test_check_words(value):
    assert check_words(value) is None


@pytest.mark.parametrize(
    ("value", "name"),
    [
        ({"the", "cat"}, "set"),
        (frozenset({"the"}), "frozenset"),
        ({"the": 1}, "dict"),
        (Counter(["the"]), "Counter"),
        ({"the": 1}.keys(), "dict_keys"),
    ],
)
def test_check_sequence_unordered(value, name):
    message = rf"^A list of words is expected, not {name}$"
    with pytest.raises(SourceTypeError, match=message):
        check_sequence(value)
    with pytest.raises(SourceTypeError, match=message):
        check_words(value)
    assert check_sequence(value, ordered=False) is None
    assert check_words(value, ordered=False) is None
    with pytest.raises(SourceTypeError, match=r"^The stopwords must be strings, not int$"):
        check_words({1}, "stopwords", ordered=False)


@pytest.mark.parametrize(
    ("value", "name"),
    [
        (np.array([["the", "cat"]]), "2-dimensional ndarray"),
        (np.array("the"), "0-dimensional ndarray"),
        (pd.DataFrame({"word": ["the", "cat"]}), "2-dimensional DataFrame"),
    ],
)
def test_check_sequence_tables(value, name):
    with pytest.raises(SourceTypeError, match=rf"^A list of words is expected, not a {name}$"):
        check_sequence(value, ordered=False)
    assert check_words(np.array(["the", "cat"])) is None
    assert check_words(pd.Series(["the", "cat"])) is None


def test_check_counts():
    assert check_counts(Counter(["the", "cat", "the"])) is None
    assert check_counts({"the": 2.5, "cat": np.int64(1)}) is None
    with pytest.raises(SourceTypeError, match=r"^A mapping of frequencies is expected, not list$"):
        check_counts(["the", "cat"])
    with pytest.raises(SourceTypeError, match=r"^The words must be strings, not int$"):
        check_counts({1: 2})
    for count, name in (("2", "str"), (None, "NoneType"), (True, "bool")):
        with pytest.raises(
            SourceTypeError, match=rf"^The frequencies must be numbers, not {name}$"
        ):
            check_counts({"the": count})
    for count in (-1, float("nan"), float("inf"), np.float64("-inf")):
        with pytest.raises(SourceError, match=r"^The frequencies must be finite and not negative"):
            check_counts({"the": count})
    assert check_counts({"the": 0}) is None


@pytest.mark.parametrize("value", [0.95, 1, np.float64(0.5), -3])
def test_check_number(value):
    assert check_number(value, "confidence level") is None


@pytest.mark.parametrize(
    ("value", "name"), [("0.95", "str"), (None, "NoneType"), (True, "bool"), ([0.5], "list")]
)
def test_check_number_errors(value, name):
    with pytest.raises(
        ParameterError, match=rf"^The confidence level must be a number, not {name}$"
    ):
        check_number(value, "confidence level")


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -np.inf])
def test_check_number_not_finite(value):
    with pytest.raises(ParameterError, match=r"^The confidence level must be a finite number"):
        check_number(value, "confidence level")


def test_check_callable():
    assert check_callable(str.lower, "normalization") is None
    with pytest.raises(SourceTypeError, match=r"^The normalization must be callable, not int$"):
        check_callable(42, "normalization")


def test_check_words_errors(nlp):
    with pytest.raises(SourceTypeError, match=r"^The words must be strings, not Token$"):
        check_words(list(nlp("the cat")))
    with pytest.raises(SourceTypeError, match=r"^The texts must be strings, not int$"):
        check_words(["the", 1], "texts")
    with pytest.raises(SourceTypeError, match=r"not a string$"):
        check_words("the cat")
    with pytest.raises(SourceTypeError, match=r"not an iterator$"):
        check_words(iter(["the"]))


@pytest.mark.parametrize("value", [5, 0, -3, np.int64(5)])
def test_check_integer(value):
    assert check_integer(value, "window size") is None


@pytest.mark.parametrize(
    ("value", "name"),
    [(5.0, "float"), (True, "bool"), ("5", "str"), (None, "NoneType"), (math.nan, "float")],
)
def test_check_integer_errors(value, name):
    with pytest.raises(ParameterError, match=rf"^The window size must be an integer, not {name}$"):
        check_integer(value, "window size")


def test_checks_with_a_message():
    """A message of a class takes the place of the English one, with the type of the value"""
    message = "Own: {type}"
    with pytest.raises(SourceTypeError, match=r"^Own: str$"):
        check_sequence("the cat", message=message)
    with pytest.raises(SourceTypeError, match=r"^Own: list_iterator$"):
        check_words(iter(["the"]), message=message)
    with pytest.raises(SourceTypeError, match=r"^Own: int$"):
        check_words(["the", 1], message=message)
    with pytest.raises(ParameterError, match=r"^Own: float$"):
        check_integer(5.0, "window size", message=message)
    with pytest.raises(ParameterError, match=r"^Own: int$"):
        check_bool(1, "flag", message=message)
    assert check_words(["the"], message=message) is None


def test_count_words_by_spans():
    starts = [0, 4, 10, 14, 20]
    assert count_words_by_spans(starts, [(0, 9), (10, 19), (20, 24)]) == [2, 2, 1]
    # A span without words is skipped, a word out of the spans is not counted
    assert count_words_by_spans(starts, [(0, 9), (9, 10), (20, 24)]) == [2, 1]
    assert count_words_by_spans([], [(0, 5)]) == []
    assert count_words_by_spans(starts, []) == []


def test_count_words_by_spans_of_an_array():
    spans = [(0, 9), (10, 19), (20, 24)]
    gapped = pd.Series([-5, 0, 4, 10, 14, 20]).iloc[1:]
    for starts in (np.array([0, 4, 10, 14, 20]), gapped):
        lengths = count_words_by_spans(starts, spans)
        assert lengths == [2, 2, 1]
        assert all(type(length) is int for length in lengths)


@pytest.mark.parametrize(("starts", "spans"), [(iter([0]), [(0, 5)]), ([0], "0-5"), (None, [])])
def test_count_words_by_spans_errors(starts, spans):
    with pytest.raises(SourceTypeError):
        count_words_by_spans(starts, spans)


def test_find_phrases_of_a_string():
    with pytest.raises(SourceTypeError, match="phrases"):
        find_phrases(["in", "fact"], "in fact")


def test_numbers():
    assert is_number("2020") and is_number("-5") and is_number("10%")
    assert not is_number("cat")
    roman = re.compile(r"[ivxlcdm]+")
    assert is_number("XIV", roman) and not is_number("2020", roman)


def test_in_order():
    assert in_order({"b", "a"}) == ("a", "b")
    assert in_order(["b", "a"]) == ("b", "a")
    assert in_order({"b": 1, "a": 2}) == ("a", "b")


def test_numbers_of_two_patterns_are_cached_apart():
    roman = re.compile(r"[ivxlcdm]+")
    assert not is_number("mix")
    assert is_number("mix", roman)
    assert not is_number("mix")


def test_has_feature():
    doc = Doc(
        spacy.blank("xx").vocab,
        words=["Children", "play", "who"],
        morphs=["Number=Plur", "Mood=Ind|VerbForm=Fin", "PronType=Int,Rel"],
    )
    children, play, who = get_tree(to_document(doc)).words
    assert has_feature(play, "VerbForm", "Fin")
    assert not has_feature(play, "VerbForm", "Inf")
    assert not has_feature(children, "Mood", "Ind")
    # One value of several
    assert has_feature(who, "PronType", "Rel") and not has_feature(who, "PronType", "Re")


def test_verb_forms():
    doc = Doc(
        spacy.blank("xx").vocab,
        words=["They", "will", "go", "to", "swim"],
        morphs=["Case=Nom", "VerbForm=Fin", "VerbForm=Fin", "", "VerbForm=Inf"],
        pos=["PRON", "AUX", "VERB", "PART", "VERB"],
    )
    words = get_tree(to_document(doc)).words
    assert [is_finite_verb(word) for word in words] == [False, False, True, False, False]
    assert [is_infinitive(word) for word in words] == [False, False, False, False, True]


def test_safe_mean():
    assert safe_mean([1, 2, 4]) == 7 / 3
    assert math.isnan(safe_mean([]))
    assert safe_mean([], 0) == 0
    assert safe_mean(iter([1, 2])) == safe_mean(np.array([1.0, 2.0])) == 1.5
    assert safe_mean(iter([]), 0) == safe_mean(np.array([]), 0) == 0


def test_shannon_entropy():
    assert shannon_entropy({"a": 2, "b": 2}) == 1.0
    assert shannon_entropy(Counter("aab")) == -(
        2 / 3 * math.log2(2 / 3) + 1 / 3 * math.log2(1 / 3)
    )
    assert shannon_entropy({"a": 5}) == 0.0
    assert math.isnan(shannon_entropy({})) and math.isnan(shannon_entropy({"a": 0}))
    # A zero count is left out, as 0 log 0 = 0
    assert shannon_entropy({"a": 0, "b": 2}) == 0.0
    counts = Counter("aab")
    counts.subtract("aa")
    assert shannon_entropy(counts) == 0.0


@pytest.mark.parametrize("count", [-1, math.nan, math.inf])
def test_shannon_entropy_of_bad_counts(count):
    with pytest.raises(SourceError, match=r"^The counts must be finite and not negative, not "):
        shannon_entropy({"a": count, "b": 2})


def test_check_word():
    check_word("cat")
    with pytest.raises(SourceTypeError, match=r"^The word must be a string, not list$"):
        check_word(["cat"])
    with pytest.raises(SourceTypeError, match=r"^The syllable must be a string, not int$"):
        check_word(1, "syllable")


class OnlyIterable:
    """Iterable again and again, with no length"""

    def __iter__(self):
        return iter(["the", "cat"])


def test_check_sequence_requires_a_length():
    with pytest.raises(SourceTypeError, match=r"^A list of words is expected, not OnlyIterable$"):
        check_sequence(OnlyIterable())
    check_sequence(range(3))


def test_find_phrases_checks_the_normalization():
    with pytest.raises(SourceTypeError, match=r"^The normalization must be callable, not int$"):
        find_phrases(["in", "fact"], ["in fact"], 42)


def test_find_marks():
    from anyts.utils import find_marks

    words = ["So", "it", "is", "late", "very", "late"]
    assert find_marks("So, it is late - very late", words) == {1, 4}
    assert find_marks("So it is late very late", words) == frozenset()
    # A word the text does not hold is passed over
    assert find_marks("So, it is late", ["So", "cat", "it"]) == {2}
    # A word inside a longer one is no occurrence of it, a word glued to its neighbour is
    assert find_marks("Therefore, here we go", ["therefore", "here", "we", "go"]) == {1}
    assert find_marks("Anyway, way out", ["way", "out"]) == frozenset()
    assert find_marks("the wayside, way out", ["the", "way", "out"]) == {1}
    assert find_marks("I don't know, really", ["I", "do", "n't", "know", "really"]) == {4}
    # The hyphen of a hyphenated word is no mark, a dash is
    assert find_marks("The so-called experts", ["The", "so", "called", "experts"]) == frozenset()
    assert find_marks("The so - called experts", ["The", "so", "called", "experts"]) == {2}
    # Quotes and apostrophes are no marks, a comma beside a quote is
    title = ["after", "The", "Inspector", "a", "play"]
    assert find_marks("after «The Inspector», a play", title) == {3}
    assert find_marks('after "The Inspector" a play', title) == frozenset()
    assert find_marks("after „The Inspector“ a play", title) == frozenset()
    assert find_marks("l’homme", ["l", "homme"]) == frozenset()
    # The invisible separators are no marks
    for separator in "\u00ad\u200b\u2060\ufeff":
        assert find_marks(f"before{separator} the end", ["before", "the", "end"]) == frozenset()
    with pytest.raises(SourceTypeError):
        find_marks(5, words)
    with pytest.raises(SourceTypeError):
        find_marks("So", "So")


def test_find_paragraph_starts():
    from anyts.utils import find_paragraph_starts

    words = ["Notes", "It", "rains", "We", "stay"]
    for gap in ("\n\n", "\n \t\n", "\r\n\r\n", "\r\r", "\u2029", "\u2028\u2028", "\n\u200b\n"):
        text = f"Notes{gap}It rains.{gap}We stay"
        assert find_paragraph_starts(text, words) == {1, 3}, repr(gap)
        assert find_paragraph_starts(text, words, blank_lines=True) == {1, 3}, repr(gap)
    # A line break alone starts a paragraph unless blank_lines asks for a blank line
    for gap in ("\n", "\r\n", "\r", "\x85", "\u2028"):
        text = f"Notes{gap}It rains.{gap}We stay"
        assert find_paragraph_starts(text, words) == {1, 3}, repr(gap)
        assert find_paragraph_starts(text, words, blank_lines=True) == frozenset(), repr(gap)
    # A word the text does not hold starts no paragraph
    assert find_paragraph_starts("Notes\n\nIt rains.", ["Notes", "snows", "It"]) == {2}
    assert find_paragraph_starts("", []) == frozenset()
    with pytest.raises(SourceTypeError):
        find_paragraph_starts(5, words)
    with pytest.raises(SourceTypeError):
        find_paragraph_starts("Notes", "Notes")
    with pytest.raises(ParameterError, match=r"^The blank_lines must be a bool, not int$"):
        find_paragraph_starts("Notes", ["Notes"], 1)


def test_is_token(nlp):
    doc = nlp("The cat")
    assert is_token(doc[0]) and not is_token(doc[:1]) and not is_token("The")


@pytest.mark.parametrize("value", ["yes", 1, None])
def test_check_bool(value):
    check_bool(True, "switch")
    check_bool(np.True_, "switch")
    with pytest.raises(ParameterError, match=r"^The switch must be a bool"):
        check_bool(value, "switch")


def test_messages_are_read_only():
    with pytest.raises(TypeError):
        MESSAGES["no_words"] = "No words"  # type: ignore[index]
