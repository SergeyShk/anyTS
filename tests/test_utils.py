import math
import string
import sys
import unicodedata
from collections import Counter

import numpy as np
import pandas as pd
import pytest
import spacy
from spacy.tokens import Doc

from anyts.exceptions import ParameterError, SourceError, SourceTypeError
from anyts.utils import (
    PUNCTUATION_CATEGORIES,
    check_counts,
    check_integer,
    check_number,
    check_sequence,
    check_words,
    count_letters,
    count_words_by_spans,
    has_words,
    is_punctuation,
    iter_doc_tokens,
    iter_doc_units,
    iter_doc_words,
    safe_divide,
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
        PUNCTUATION_CATEGORIES
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
        ("", False),
    ],
)
def test_has_words(text, expected):
    assert has_words(text) is expected


@pytest.mark.parametrize("text", ["The cat sleeps", "?!", ""])
def test_has_words_of_a_doc(nlp, text):
    assert has_words(nlp(text)) is has_words(text)


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


def test_iter_doc_tokens(nlp):
    doc = nlp("The 50 % of books,  wow!")
    assert [token.text for token in iter_doc_tokens(doc)] == ["The", "50", "of", "books", "wow"]
    assert [token.text for token in iter_doc_tokens(doc[3:])] == ["of", "books", "wow"]


def test_iter_doc_units(nlp):
    doc = nlp("A well-known, far-off cat - dog up-to-date.")
    units = [[token.text for token in unit] for unit in iter_doc_units(doc)]
    assert units == [
        [word] for word in ["A", "well", "known", "far", "off", "cat", "dog", "up", "to", "date"]
    ]
    joined = [" ".join(token.text for token in unit) for unit in iter_doc_units(doc, True)]
    assert joined == ["A", "well - known", "far - off", "cat", "dog", "up - to - date"]


@pytest.mark.parametrize(
    ("spaces", "expected"),
    [
        ((False, False, True), ["well-known"]),
        ((True, False, True), ["well", "known"]),
        ((False, True, True), ["well", "known"]),
    ],
)
def test_iter_doc_units_whitespace(nlp, spaces, expected):
    doc = Doc(nlp.vocab, words=["well", "-", "known"], spaces=list(spaces))
    assert [word for _, _, word in iter_doc_words(doc, join_hyphens=True)] == expected


def test_iter_doc_units_stop_at_a_sentence_start(nlp):
    doc = Doc(
        nlp.vocab,
        words=["Tick", "-", "tock", "-", "tock", "came"],
        spaces=[False] * 5 + [True],
        sent_starts=[True, False, True, False, False, False],
    )
    units = [" ".join(token.text for token in unit) for unit in iter_doc_units(doc, True)]
    assert units == ["Tick", "tock - tock", "came"]
    words = [word for sent in doc.sents for _, _, word in iter_doc_words(sent, True)]
    assert words == [word for _, _, word in iter_doc_words(doc, True)]


def test_iter_doc_units_stop_at_space_and_punctuation(nlp):
    doc = Doc(nlp.vocab, words=["well", "-", "\n", "known", "-", "?"], spaces=[False] * 6)
    assert [word for _, _, word in iter_doc_words(doc, join_hyphens=True)] == ["well", "known"]


def test_iter_doc_words(nlp):
    doc = nlp("A well-known cat")
    assert list(iter_doc_words(doc)) == [
        (0, 1, "A"),
        (2, 6, "well"),
        (7, 12, "known"),
        (13, 16, "cat"),
    ]
    assert list(iter_doc_words(doc, join_hyphens=True)) == [
        (0, 1, "A"),
        (2, 12, "well-known"),
        (13, 16, "cat"),
    ]
    assert list(iter_doc_words(doc[1:4], join_hyphens=True)) == [(2, 12, "well-known")]
    assert list(iter_doc_words(nlp("- . ,"), join_hyphens=True)) == []


def test_iter_doc_words_drops_byte_order_mark(nlp):
    doc = nlp("\ufeffThe cat. \ufeff\ufeffThe dog.")
    assert doc[0].text == "\ufeffThe"
    assert list(iter_doc_words(doc)) == [
        (1, 4, "The"),
        (5, 8, "cat"),
        (12, 15, "The"),
        (16, 19, "dog"),
    ]


@pytest.mark.parametrize(
    ("text", "expected"),
    [("Hello \u200b world", ["Hello", "world"]), ("I \u2764\ufe0f it", ["I", "it"])],
)
def test_iter_doc_words_skips_invisible(nlp, text, expected):
    assert [word for _, _, word in iter_doc_words(nlp(text))] == expected


def test_count_words_by_spans():
    starts = [0, 4, 10, 14, 20]
    assert count_words_by_spans(starts, [(0, 9), (10, 19), (20, 24)]) == [2, 2, 1]
    # A span without words is skipped, a word out of the spans is not counted
    assert count_words_by_spans(starts, [(0, 9), (9, 10), (20, 24)]) == [2, 1]
    assert count_words_by_spans([], [(0, 5)]) == []
    assert count_words_by_spans(starts, []) == []


@pytest.mark.parametrize(("starts", "spans"), [(iter([0]), [(0, 5)]), ([0], "0-5"), (None, [])])
def test_count_words_by_spans_errors(starts, spans):
    with pytest.raises(SourceTypeError):
        count_words_by_spans(starts, spans)
