import math
import string
import sys
import unicodedata

import pytest
import spacy
from spacy.tokens import Doc

from anyts.exceptions import SourceTypeError
from anyts.utils import (
    PUNCTUATION_CATEGORIES,
    check_sequence,
    count_letters,
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


@pytest.mark.parametrize("value", [["the", "cat"], ("the",), [], None, 42])
def test_check_sequence(value):
    assert check_sequence(value) is None


def test_check_sequence_errors(nlp):
    with pytest.raises(SourceTypeError, match=r"^A list of texts is expected, not a string$"):
        check_sequence("the cat", "texts")
    doc = nlp("The cat")
    with pytest.raises(SourceTypeError, match="not a Doc: extract the words"):
        check_sequence(doc)
    with pytest.raises(SourceTypeError, match="not a Span"):
        check_sequence(doc[:1])


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


@pytest.mark.parametrize(
    ("text", "expected"),
    [("Hello \u200b world", ["Hello", "world"]), ("I \u2764\ufe0f it", ["I", "it"])],
)
def test_iter_doc_words_skips_invisible(nlp, text, expected):
    assert [word for _, _, word in iter_doc_words(nlp(text))] == expected
