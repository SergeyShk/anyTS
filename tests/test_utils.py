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

from anyts.components import start_sents_after_blank_lines
from anyts.exceptions import ParameterError, SourceError, SourceTypeError
from anyts.utils import (
    _PUNCTUATION_CATEGORIES,
    add_tokenizer_rules,
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
    has_sents,
    has_words,
    in_order,
    is_doc,
    is_finite_verb,
    is_infinitive,
    is_number,
    is_punctuation,
    is_span,
    iter_doc_tokens,
    iter_doc_units,
    iter_doc_words,
    joins_previous,
    safe_divide,
    safe_mean,
    shannon_entropy,
    split_doc_units,
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
        ("", False),
    ],
)
def test_has_words(text, expected):
    assert has_words(text) is expected


@pytest.mark.parametrize("text", ["The cat sleeps", "?!", ""])
def test_has_words_of_a_doc(nlp, text):
    assert has_words(nlp(text)) is has_words(text)


def test_has_sents(nlp):
    text = "The cat sleeps. The dog eats\n\nThe bird sings. It flies."
    assert not has_sents(nlp(text))
    sentencizer = spacy.blank("xx")
    sentencizer.add_pipe("sentencizer")
    assert has_sents(sentencizer(text))
    # The starts after the blank lines alone leave the other tokens unset
    partial = start_sents_after_blank_lines(nlp(text))
    assert partial.has_annotation("SENT_START")
    assert not has_sents(partial)
    full = Doc(nlp.vocab, words=["The", "cat", "Dogs"], sent_starts=[True, False, True])
    assert has_sents(full)


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
        words=["Children", "play"],
        morphs=["Number=Plur", "Mood=Ind|VerbForm=Fin"],
    )
    assert has_feature(doc[1], "VerbForm", "Fin")
    assert not has_feature(doc[1], "VerbForm", "Inf")
    assert not has_feature(doc[0], "Mood", "Ind")


def test_joins_previous():
    vocab = spacy.blank("xx").vocab
    doc = Doc(
        vocab,
        words=["Some", "-", "one", "came", "with", "a", "well", "-", "known", "cat", "."],
        spaces=[False, False, True, True, True, True, False, False, True, False, False],
    )
    assert [token.text for token in doc if joins_previous(token)] == ["one", "known"]
    spaced = Doc(vocab, words=["Some", "-", "one"])
    assert not joins_previous(spaced[2])
    assert not joins_previous(spaced[0])


def test_verb_forms():
    doc = Doc(
        spacy.blank("xx").vocab,
        words=["They", "will", "go", "to", "swim"],
        morphs=["Case=Nom", "VerbForm=Fin", "VerbForm=Fin", "", "VerbForm=Inf"],
        pos=["PRON", "AUX", "VERB", "PART", "VERB"],
    )
    assert [is_finite_verb(token) for token in doc] == [False, False, True, False, False]
    assert [is_infinitive(token) for token in doc] == [False, False, False, False, True]


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


def test_split_doc_units():
    from anyts.extractors import SentsExtractor

    class Fixed(SentsExtractor):
        def __init__(self, sents):
            super().__init__()
            self.sents = sents

        def sentenize(self, text):
            return self.sents

    doc = Doc(
        spacy.blank("xx").vocab,
        words=["One", "well", "-", "known", ".", "Two", ".", "Three"],
        spaces=[True, False, False, False, True, False, True, False],
    )

    def texts(units):
        return [["".join(token.text for token in unit) for unit in sent] for sent in units]

    assert texts(split_doc_units(doc, Fixed(["One well-known.", "Two.", "Three"]))) == [
        ["One", "well", "known"],
        ["Two"],
        ["Three"],
    ]
    # A sentence the extractor drops leaves its words out; joined parts are one word
    assert texts(split_doc_units(doc, Fixed(["One well-known.", "Three"]), join_hyphens=True)) == [
        ["One", "well-known"],
        ["Three"],
    ]
    assert split_doc_units(doc, Fixed([])) == []
    # A Span: the sentences are found in its own text
    assert texts(split_doc_units(doc[5:], Fixed(["Two.", "Three"]))) == [["Two"], ["Three"]]
    assert split_doc_units(doc, Fixed(["Four"])) == []


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


def test_add_tokenizer_rules():
    nlp = spacy.blank("en")
    text = "--No, he said a|b ok~~"
    assert [token.text for token in nlp(text)] == ["--No", ",", "he", "said", "a|b", "ok~~"]
    add_tokenizer_rules(
        nlp, prefixes=[r"-{2,}(?=\w)"], suffixes=[r"(?<=\w)~{2,}"], infixes=[r"(?<=\w)\|(?=\w)"]
    )
    assert [token.text for token in nlp(text)] == [
        "--",
        "No",
        ",",
        "he",
        "said",
        "a",
        "|",
        "b",
        "ok",
        "~~",
    ]
    # A rule the tokenizer has is not added again
    search = nlp.tokenizer.prefix_search
    add_tokenizer_rules(nlp, prefixes=[r"-{2,}(?=\w)"])
    assert nlp.tokenizer.prefix_search is search


def test_add_tokenizer_rules_of_abbreviations():
    nlp = spacy.blank("en")
    add_tokenizer_rules(nlp, abbreviations=["a.m.", "e.g.", "xyz."])
    # A form the tokenizer keeps whole gives the others, a form it splits is left
    assert [len(nlp(form)) for form in ("a.m.", "A.m.", "A.M.")] == [1, 1, 1]
    assert [len(nlp(form)) for form in ("e.g.", "E.g.", "E.G.")] == [1, 1, 1]
    assert len(nlp("Xyz.")) == 2
    # The tokenizer keeps Q.E.D. whole by a pattern, not by a rule, so its other forms follow
    assert [len(nlp(form)) for form in ("q.e.d.", "Q.e.d.")] == [2, 2]
    add_tokenizer_rules(nlp, abbreviations=["q.e.d."])
    assert [len(nlp(form)) for form in ("q.e.d.", "Q.e.d.", "Q.E.D.")] == [1, 1, 1]


def test_add_tokenizer_rules_to_other_tokenizers():
    nlp = spacy.blank("en")
    nlp.tokenizer.prefix_search = None
    add_tokenizer_rules(nlp, prefixes=[r"-{2,}(?=\w)"])
    assert [token.text for token in nlp("--No")] == ["--", "No"]
    # A rule that is not a regular expression is left, as is a tokenizer of another class
    nlp.tokenizer.suffix_search = lambda text: None
    add_tokenizer_rules(nlp, suffixes=[r"-{2,}"])
    assert nlp.tokenizer.suffix_search("no--") is None
    nlp.tokenizer = lambda text: spacy.tokens.Doc(nlp.vocab, words=text.split())
    add_tokenizer_rules(nlp, prefixes=[r"-"])
    assert [token.text for token in nlp("--No x")] == ["--No", "x"]


def test_add_tokenizer_rules_anchor_every_branch():
    nlp = spacy.blank("en")
    add_tokenizer_rules(nlp, prefixes=[r"#|@"], suffixes=[r"~|\^"])
    assert [token.text for token in nlp("a@b c^d")] == ["a@b", "c^d"]
    assert [token.text for token in nlp("@b c^")] == ["@", "b", "c", "^"]


def test_add_tokenizer_rules_inside_a_rule_of_the_tokenizer():
    # \+ and / lie inside rules of spaCy, which are other alternatives
    nlp = spacy.blank("en")
    assert [token.text for token in nlp("+5 1/2")] == ["+5", "1/2"]
    add_tokenizer_rules(nlp, prefixes=[r"\+"], infixes=["/"])
    assert [token.text for token in nlp("+5 1/2")] == ["+", "5", "1", "/", "2"]


def test_add_tokenizer_rules_inside_a_group_of_the_tokenizer():
    # -- is an alternative inside a group of the infixes of spaCy
    nlp = spacy.blank("en")
    add_tokenizer_rules(nlp, infixes=["--"])
    infixes = nlp.tokenizer.infix_finditer
    add_tokenizer_rules(nlp, infixes=["--"])
    assert nlp.tokenizer.infix_finditer is infixes
    assert [token.text for token in nlp("no--5")] == ["no", "--", "5"]


def test_add_tokenizer_rules_without_infixes():
    nlp = spacy.blank("en")
    nlp.tokenizer.infix_finditer = None
    add_tokenizer_rules(nlp, prefixes=[r"-{2,}(?=\w)"])
    assert nlp.tokenizer.infix_finditer is None
    assert [token.text for token in nlp("ab cd")] == ["ab", "cd"]


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"prefixes": r"-{2,}"}, r"^A list of prefixes is expected, not a string$"),
        ({"infixes": [1]}, r"^The infixes must be strings, not int$"),
        ({"abbreviations": "sr."}, r"^A list of abbreviations is expected, not a string$"),
    ],
)
def test_add_tokenizer_rules_checks_the_rules(kwargs, message):
    with pytest.raises(SourceTypeError, match=message):
        add_tokenizer_rules(spacy.blank("en"), **kwargs)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        (
            {"prefixes": ["("]},
            r"^The rule '\(' of the prefixes is not a regular expression: missing",
        ),
        ({"suffixes": ["(?i)ab"]}, r"^The rule '\(\?i\)ab' of the suffixes .*: global flags"),
        ({"infixes": ["a)|(b"]}, r"^The rule 'a\)\|\(b' of the infixes .*: unbalanced"),
    ],
)
def test_add_tokenizer_rules_checks_the_expressions(kwargs, message):
    nlp = spacy.blank("en")
    prefixes = nlp.tokenizer.prefix_search
    with pytest.raises(ParameterError, match=message):
        add_tokenizer_rules(nlp, **kwargs)
    assert nlp.tokenizer.prefix_search == prefixes


def test_find_phrases_checks_the_normalization():
    with pytest.raises(SourceTypeError, match=r"^The normalization must be callable, not int$"):
        find_phrases(["in", "fact"], ["in fact"], 42)


def test_add_tokenizer_rules_of_alternatives_once():
    nlp = spacy.blank("en")
    add_tokenizer_rules(nlp, infixes=["~~|\\^\\^"], prefixes=["#|@"])
    infixes, prefixes = nlp.tokenizer.infix_finditer, nlp.tokenizer.prefix_search
    add_tokenizer_rules(nlp, infixes=["~~|\\^\\^"], prefixes=["#|@"])
    assert nlp.tokenizer.infix_finditer is infixes
    assert nlp.tokenizer.prefix_search is prefixes
