from __future__ import annotations

import math
import re
import sys
import threading
import unicodedata
from collections.abc import Callable, Collection, Iterable, Iterator, Mapping, Sequence, Set, Sized
from contextlib import contextmanager
from functools import lru_cache
from importlib import import_module
from itertools import repeat
from numbers import Integral, Real
from re import Pattern
from statistics import StatisticsError, fmean
from string import Formatter
from types import FrameType, ModuleType
from typing import TYPE_CHECKING, Any, TypeGuard

from .constants import MESSAGES
from .exceptions import ParameterError, SourceError, SourceTypeError

if TYPE_CHECKING:
    from anyseg import Document
    from spacy.language import Language
    from spacy.tokens import Doc, Span, Token

    from .document import TreeWord

# Punctuation, symbols, combining marks and invisible format characters
_PUNCTUATION_CATEGORIES = frozenset(
    ("Pc", "Pd", "Ps", "Pe", "Pi", "Pf", "Po", "Sm", "Sc", "Sk", "So", "Mn", "Mc", "Me", "Cf")
)

# A signed number with separators and an optional percent sign: -5, 1990-1995, 1,500.50, 10%,
# its thousands apart by a space, a no-break or a narrow no-break space as in a token of
# anySeg: 3 500, 1 000 000
NUMBER_PATTERN = re.compile(r"[+\-−]?(?:\d{1,3}(?:[ \u00a0\u202f]\d{3})+|\d+)(?:[.,:/-]\d+)*%?")
# A line break of Unicode, the vertical tab and the form feed among them, as in anySeg
_BREAK = r"\r\n|[\n\r\x0b\x0c\x85\u2028]"
# What a blank line may hold besides its breaks: whitespace, control characters and the
# invisible separators of anySeg (the soft hyphen, zero-width characters, the byte order mark)
_BLANK = r"[^\S\n\r\x0b\x0c\x85\u2028\u2029]|[\x00-\x08\x0e-\x1f\x7f-\x84\x86-\x9f\u00ad\u200b-\u200d\u2060\ufeff]"
# Blank lines: a line break and the breaks after it with nothing but blank characters
# between them, or a paragraph separator - a paragraph break of anySeg
BLANK_LINE = re.compile(rf"(?>{_BREAK}|\u2029)(?:(?:{_BLANK})*(?>{_BREAK}|\u2029))+|\u2029")
# A line break of Unicode, the paragraph separator among them
LINE_BREAK = re.compile(rf"{_BREAK}|\u2029")
# One import of a name of a lazy package at a time, a nested one in the same thread included
_LAZY_IMPORT = threading.RLock()


@lru_cache(maxsize=1)
def _separators() -> str:
    """Characters between the tokens of anySeg: whitespace, control and invisible characters"""
    return (
        "".join(
            char
            for char in map(chr, range(0x3001))
            if char.isspace() or unicodedata.category(char) == "Cc"
        )
        + "\u00ad\u200b\u200c\u200d\u2060\ufeff"
    )


@lru_cache(maxsize=1 << 16)
def is_punctuation(token: str) -> bool:
    """
    Checking whether a token consists only of punctuation marks and symbols

    Description:
        Characters of the Unicode categories P (punctuation), S (symbols),
        M (combining marks) and Cf (invisible format characters such as the
        zero-width space), so "?!", "€", "№" and an empty token are punctuation,
        and a token with a letter or a digit is not. The results are cached, so
        the function is meant for tokens, not whole texts

    Arguments:
        token (str): Token

    Returns:
        bool: Result of the check

    Example:
        >>> from anyts.utils import is_punctuation
        >>> is_punctuation("?!"), is_punctuation("€"), is_punctuation("no.")
        (True, True, False)
    """
    return all(unicodedata.category(char) in _PUNCTUATION_CATEGORIES for char in token)


def is_number(word: str, pattern: Pattern[str] = NUMBER_PATTERN) -> bool:
    """
    Checking whether a word is a number

    Arguments:
        word (str): Word
        pattern (Pattern): Number of a language, matched against the whole lower-cased word;
            NUMBER_PATTERN by default

    Returns:
        bool: Result of the check

    Example:
        >>> from anyts.utils import is_number
        >>> is_number("2020"), is_number("10%"), is_number("cat")
        (True, True, False)
    """
    return _is_number(word, pattern.pattern, pattern.flags)


@lru_cache(maxsize=1 << 16)
def _is_number(word: str, pattern: str, flags: int) -> bool:
    """is_number by the text of the pattern: a compiled pattern hashes its code on every call"""
    return re.fullmatch(pattern, word.lower(), flags) is not None


@lru_cache(maxsize=1 << 16)
def count_letters(word: str) -> int:
    """
    Counting the letters of a string

    Description:
        Letters of any alphabet (str.isalpha), not digits, hyphens or marks; the
        results are cached, so the function is meant for words, not whole texts

    Arguments:
        word (str): Word form

    Returns:
        int: Number of letters

    Example:
        >>> from anyts.utils import count_letters
        >>> count_letters("well-known"), count_letters("3rd")
        (9, 2)
    """
    return sum(map(str.isalpha, word))


def has_words(source: str | Doc | Span) -> bool:
    """
    Checking whether a text holds a word

    Description:
        A word holds a letter or a digit (str.isalnum): a text of whitespace,
        punctuation marks, symbols and characters of no class alone (?!, ..., a
        zero-width space, a bullet of private use) holds none

    Arguments:
        source (str|Doc|Span): Text, Doc or Span object

    Returns:
        bool: Result of the check

    Example:
        >>> from anyts.utils import has_words
        >>> has_words("The cat sleeps"), has_words("?!"), has_words("\\uf0b7"), has_words("")
        (True, False, False, False)
    """
    text = source if isinstance(source, str) else source.text
    return any(map(str.isalnum, text))


def find_marks(text: str, words: Sequence[str]) -> frozenset[int]:
    """
    Finding the punctuation marks between the words of a text

    Description:
        The words are found in the text in their order, apart from the letters
        and digits around them unless glued to the word before or after; a word
        with an is_punctuation character between it and the word before gets
        its position, except a quote, an apostrophe, an invisible separator (the
        soft hyphen, zero-width characters, the byte order mark) and the hyphen
        that joins two parts of a word. A word the text does not hold is passed
        over

    Arguments:
        text (str): Text
        words (list[str]): Words of the text in their order

    Returns:
        frozenset[int]: Positions of the words a punctuation mark stands before

    Raises:
        SourceTypeError: If the text is not a string or the words are not a list
            of strings

    Example:
        >>> from anyts.utils import find_marks
        >>> sorted(find_marks("So, it is late - very late", ["So", "it", "is", "late", "very", "late"]))
        [1, 4]
    """
    check_word(text, "text")
    check_words(words)
    return frozenset(
        position
        for position, start, end in _word_gaps(text, words)
        if _is_mark_gap(text[start:end])
    )


def _word_gaps(text: str, words: Sequence[str]) -> Iterator[tuple[int, int, int]]:
    """Position of every word found in a text after the first one, with the bounds of the text
    between it and the word found before it"""
    cursor = 0
    for position, word in enumerate(words):
        following = words[position + 1] if position + 1 < len(words) else ""
        start = text.find(word, cursor)
        # A word inside a longer one (here in Therefore) is no occurrence of it
        while start != -1 and not _stands_apart(text, start, start + len(word), cursor, following):
            start = text.find(word, start + 1)
        if start == -1:
            continue
        if position:
            yield position, cursor, start
        cursor = start + len(word)


def _stands_apart(text: str, start: int, end: int, cursor: int, following: str) -> bool:
    """Whether a word found in a text is no part of a longer word, but glued to the word
    found before it (cursor) or to the next one"""
    before = start == cursor or not text[start - 1].isalnum()
    after = (
        end == len(text)
        or not text[end].isalnum()
        or (bool(following) and text.startswith(following, end))
    )
    return before and after


def _is_mark_gap(gap: str) -> bool:
    """Whether the text between two words holds a punctuation mark, the quotes, the hyphen
    that joins two parts of a word and the invisible separators aside"""
    separators = _separators()
    return gap != "-" and any(
        is_punctuation(char) and not _is_quote(char) and char not in separators for char in gap
    )


def _is_quote(char: str) -> bool:
    """Whether a character is a quote or an apostrophe: an initial or a final quote of
    Unicode, a straight or a low one"""
    return unicodedata.category(char) in ("Pi", "Pf") or char in "\"'„‚"


def find_paragraph_starts(
    text: str, words: Sequence[str], blank_lines: bool = False
) -> frozenset[int]:
    """
    Finding the words of a text that start a paragraph

    Description:
        The words are found in the text in their order, as in find_marks; a word
        that a line break (LINE_BREAK) separates from the word before gets its
        position, or a blank line (BLANK_LINE) with blank_lines, for a text whose
        lines are wrapped inside its paragraphs. A word the text does not hold
        is passed over

    Arguments:
        text (str): Text
        words (list[str]): Words of the text in their order
        blank_lines (bool): Start the paragraphs after the blank lines alone

    Returns:
        frozenset[int]: Positions of the words a paragraph starts at

    Raises:
        SourceTypeError: If the text is not a string or the words are not a list
            of strings
        ParameterError: If blank_lines is not a bool

    Example:
        >>> from anyts.utils import find_paragraph_starts
        >>> text = "It rains.\\nWe stay\\nhome.\\n\\nIt stops."
        >>> words = ["It", "rains", "We", "stay", "home", "It", "stops"]
        >>> sorted(find_paragraph_starts(text, words)), sorted(find_paragraph_starts(text, words, True))
        ([2, 4, 5], [5])
    """
    check_word(text, "text")
    check_words(words)
    check_bool(blank_lines, "blank_lines")
    pattern = BLANK_LINE if blank_lines else LINE_BREAK
    return frozenset(
        position
        for position, start, end in _word_gaps(text, words)
        if pattern.search(text, start, end)
    )


def in_order(words: Collection[str]) -> tuple[str, ...]:
    """
    Putting a collection of words in a fixed order

    Arguments:
        words (list[str]|set[str]): Words; a set or a mapping is sorted, a list keeps
            its order

    Returns:
        tuple[str]: Words in order

    Example:
        >>> from anyts.utils import in_order
        >>> in_order({"dog", "cat"}), in_order(["dog", "cat"])
        (('cat', 'dog'), ('dog', 'cat'))
    """
    return tuple(sorted(words)) if isinstance(words, Set | Mapping) else tuple(words)


def find_phrases(
    words: Sequence[str], phrases: Collection[str], normalize: Callable[[str], str] = str.lower
) -> list[tuple[int, int]]:
    """
    Finding phrases in a sequence of words

    Description:
        The words and the phrases are compared by their normalized forms; at
        every position the longest phrase is taken, and the phrases found do not
        overlap

    Arguments:
        words (list[str]): Words of the text
        phrases (list[str]): Phrases, words separated by spaces
        normalize (callable): Normalized form of a word and of a phrase, the lower
            case by default

    Returns:
        list[tuple[int, int]]: Bounds of the phrases found as slices of words; empty
            phrases are skipped

    Raises:
        SourceTypeError: If the words or the phrases are not a list of strings, or
            normalize is not callable

    Example:
        >>> from anyts.utils import find_phrases
        >>> find_phrases(["In", "fact", "it", "rains"], ["in fact", "in"])
        [(0, 2)]
    """
    check_words(words)
    check_words(phrases, "phrases", ordered=False)
    check_callable(normalize, "normalization")
    by_first: dict[str, list[list[str]]] = {}
    for pattern in sorted(
        {pattern for phrase in phrases if (pattern := tuple(normalize(phrase).split()))},
        key=len,
        reverse=True,
    ):
        by_first.setdefault(pattern[0], []).append(list(pattern))
    normalized = list(map(normalize, words))
    spans: list[tuple[int, int]] = []
    end = 0
    for position, word in enumerate(normalized):
        if position < end or word not in by_first:
            continue
        for phrase_words in by_first[word]:
            if normalized[position : position + len(phrase_words)] == phrase_words:
                end = position + len(phrase_words)
                spans.append((position, end))
                break
    return spans


def count_words_by_spans(starts: Sequence[int], spans: Sequence[tuple[int, int]]) -> list[int]:
    """
    Counting the words in every span of a text by the positions of the words and the spans

    Description:
        A word belongs to the span of its first character, and a span without
        words is skipped

    Arguments:
        starts (list[int]): Positions of the first characters of the words in order
        spans (list[tuple[int, int]]): Spans in order - the start and the position
            after the end

    Returns:
        list[int]: Number of words in every span with words

    Raises:
        SourceTypeError: If the positions or the spans are not a sequence

    Example:
        >>> from anyts.utils import count_words_by_spans
        >>> count_words_by_spans([0, 4, 10, 14, 20], [(0, 9), (9, 10), (10, 19), (20, 24)])
        [2, 2, 1]
    """
    check_sequence(starts, "positions of the words")
    check_sequence(spans, "spans")
    positions = list(starts)
    lengths = []
    index = 0
    for start, stop in spans:
        count = 0
        while index < len(positions) and positions[index] < stop:
            count += int(positions[index] >= start)
            index += 1
        lengths.append(count)
    return [length for length in lengths if length]


def is_doc(value: object) -> TypeGuard[Doc]:
    """
    Checking whether a value is a Doc object of spaCy

    Description:
        The check does not import spaCy: a Doc exists only once spaCy is
        loaded, so before that every value gives False

    Arguments:
        value (object): Value to check

    Returns:
        bool: Result of the check

    Example:
        >>> import spacy
        >>> from anyts.utils import is_doc
        >>> doc = spacy.blank("en")("The cat sleeps")
        >>> is_doc(doc), is_doc(doc[:2]), is_doc("The cat sleeps")
        (True, False, False)
    """
    tokens = sys.modules.get("spacy.tokens")
    return tokens is not None and isinstance(value, tokens.Doc)


def is_span(value: object) -> TypeGuard[Span]:
    """
    Checking whether a value is a Span object of spaCy

    Description:
        The check does not import spaCy, as is_doc

    Arguments:
        value (object): Value to check

    Returns:
        bool: Result of the check

    Example:
        >>> import spacy
        >>> from anyts.utils import is_span
        >>> doc = spacy.blank("en")("The cat sleeps")
        >>> is_span(doc[:2]), is_span(doc)
        (True, False)
    """
    tokens = sys.modules.get("spacy.tokens")
    return tokens is not None and isinstance(value, tokens.Span)


def is_token(value: object) -> TypeGuard[Token]:
    """
    Checking whether a value is a Token object of spaCy

    Description:
        The check does not import spaCy, as is_doc

    Arguments:
        value (object): Value to check

    Returns:
        bool: Result of the check

    Example:
        >>> import spacy
        >>> from anyts.utils import is_token
        >>> doc = spacy.blank("en")("The cat sleeps")
        >>> is_token(doc[0]), is_token(doc[:1])
        (True, False)
    """
    tokens = sys.modules.get("spacy.tokens")
    return tokens is not None and isinstance(value, tokens.Token)


def is_language(value: object) -> TypeGuard[Language]:
    """
    Checking whether a value is a Language pipeline of spaCy

    Description:
        The check does not import spaCy, as is_doc: a pipeline exists only once
        spaCy is loaded, so before that every value gives False

    Arguments:
        value (object): Value to check

    Returns:
        bool: Result of the check

    Example:
        >>> import spacy
        >>> from anyts.utils import is_language
        >>> is_language(spacy.blank("en")), is_language("en_core_web_sm")
        (True, False)
    """
    language = getattr(sys.modules.get("spacy.language"), "Language", None)
    return language is not None and isinstance(value, language)


def is_document(value: object) -> TypeGuard[Document]:
    """
    Checking whether a value is a Document object of anySeg

    Description:
        The check does not import anySeg, as is_doc: a Document exists only
        once anySeg is loaded, so before that every value gives False

    Arguments:
        value (object): Value to check

    Returns:
        bool: Result of the check

    Example:
        >>> from anyseg import Document
        >>> from anyts.utils import is_document
        >>> document = Document.from_tokens("The cat", [0, 4], [3, 7])
        >>> is_document(document), is_document("The cat")
        (True, False)
    """
    document = getattr(sys.modules.get("anyseg"), "Document", None)
    return document is not None and isinstance(value, document)


def has_feature(word: TreeWord, field: str, value: str) -> bool:
    """
    Checking whether a word carries a morphological feature with a given value

    Arguments:
        word (TreeWord): Word of the tree of a document
        field (str): Name of the feature of Universal Dependencies (VerbForm, Mood)
        value (str): Value of the feature (Part, Ger, Fin), one of several (Int of Int,Rel)

    Returns:
        bool: Result of the check
    """
    values = word.feats.get(field)
    return values is not None and value in values.split(",")


def is_finite_verb(word: TreeWord) -> bool:
    """
    Checking whether a word is a finite form of a verb

    Arguments:
        word (TreeWord): Word of the tree of a document

    Returns:
        bool: Result of the check
    """
    return word.upos == "VERB" and has_feature(word, "VerbForm", "Fin")


def is_infinitive(word: TreeWord) -> bool:
    """
    Checking whether a word is an infinitive

    Arguments:
        word (TreeWord): Word of the tree of a document

    Returns:
        bool: Result of the check
    """
    return has_feature(word, "VerbForm", "Inf")


def safe_divide(num: float | int, den: float | int, default: float | int = 0) -> float:
    """
    Dividing two numbers safely

    Arguments:
        num (float|int): Numerator
        den (float|int): Denominator
        default (float|int): Value returned for a zero denominator

    Returns:
        float: Result of the division
    """
    if not den:
        return default
    return num / den


def safe_mean(values: Iterable[float], default: float = math.nan) -> float:
    """
    Computing the mean of numbers safely

    Arguments:
        values (iterable[float]): Numbers
        default (float): Value returned for no numbers

    Returns:
        float: Arithmetic mean
    """
    try:
        return fmean(values)
    except StatisticsError:
        return default


def shannon_entropy(counts: Mapping[Any, int]) -> float:
    """
    Computing the Shannon entropy of a distribution by its counts

    Arguments:
        counts (dict[object, int]): Count of every value, such as a Counter

    Returns:
        float: Entropy in bits, 0 for one value and nan for no counts; a zero count is
            left out

    Raises:
        SourceError: If a count is negative, nan or infinite

    Example:
        >>> from anyts.utils import shannon_entropy
        >>> shannon_entropy({"a": 2, "b": 2})
        1.0
    """
    for count in counts.values():
        if not math.isfinite(count) or count < 0:
            raise SourceError(f"The counts must be finite and not negative, not {count}")
    total = sum(counts.values())
    if not total:
        return math.nan
    return (
        -sum(count / total * math.log2(count / total) for count in counts.values() if count) or 0.0
    )


def check_sequence(
    value: object, what: str = "words", ordered: bool = True, *, message: str | None = None
) -> None:
    """
    Checking that an argument is a sequence and not a text or an iterator

    Description:
        A set or a mapping holds every item once, in no order of the text, so it
        passes only with ordered=False, for a collection such as stop words

    Arguments:
        value (object): Value to check
        what (str): What is expected, for the message of the error
        ordered (bool): Whether the order and the repeats of the items matter
        message (str): Message of the error with the fields {type}, the type of the value,
            and {param}, what, in place of the English one

    Raises:
        SourceTypeError: If a string (of characters or bytes), a Doc, a Span, an
            iterator, an object without iteration or without a length, a table
            (a two-dimensional array or a DataFrame) or, with ordered, a set or a
            mapping is passed

    Example:
        >>> from anyts.utils import check_sequence
        >>> check_sequence(["the", "cat"])
        >>> check_sequence({"the", "cat"}, "stop words", ordered=False)
        >>> check_sequence("the cat")
        Traceback (most recent call last):
        ...
        anyts.exceptions.SourceTypeError: A list of words is expected, not a string
    """
    problem = _sequence_problem(value, what, ordered)
    if problem is not None:
        raise SourceTypeError(
            problem if message is None else message.format(type=type(value).__name__, param=what)
        )


def _sequence_problem(value: object, what: str, ordered: bool) -> str | None:
    """Why a value is no sequence of check_sequence, None for a sequence"""
    if isinstance(value, str | bytes | bytearray):
        return f"A list of {what} is expected, not a string"
    if is_doc(value) or is_span(value):
        return (
            f"A list of {what} is expected, not a {type(value).__name__}: "
            "extract the words with WordsExtractor"
        )
    if isinstance(value, Iterator):
        return f"A list of {what} is expected, not an iterator"
    sized: object = value
    if not isinstance(value, Iterable) or not isinstance(sized, Sized):
        return f"A list of {what} is expected, not {type(value).__name__}"
    ndim = getattr(value, "ndim", 1)
    if ndim != 1:
        return f"A list of {what} is expected, not a {ndim}-dimensional {type(value).__name__}"
    if ordered and isinstance(value, Set | Mapping):
        return f"A list of {what} is expected, not {type(value).__name__}"
    return None


def _sliceable(values: Any) -> Any:
    """The values if they can be sliced, else a list of them (a deque, the values of a dict)"""
    try:
        values[:0]
    except (TypeError, KeyError, IndexError):
        return list(values)
    return values


def check_words(
    value: Iterable[object],
    what: str = "words",
    ordered: bool = True,
    *,
    message: str | None = None,
) -> None:
    """
    Checking that an argument is a list of words: a sequence of strings

    Arguments:
        value (object): Value to check
        what (str): What is expected, for the message of the error
        ordered (bool): Whether the order and the repeats of the words matter (check_sequence)
        message (str): Message of the error with the fields {type}, the type of the value or
            of the item that is not a string, and {param}, what, in place of the English one

    Raises:
        SourceTypeError: If the value fails check_sequence or holds an item
            that is not a string, such as a spaCy token

    Example:
        >>> import spacy
        >>> from anyts.utils import check_words
        >>> check_words(["the", "cat"])
        >>> check_words(list(spacy.blank("xx")("the cat")))
        Traceback (most recent call last):
        ...
        anyts.exceptions.SourceTypeError: The words must be strings, not Token
    """
    check_sequence(value, what, ordered, message=message)
    if not all(map(isinstance, value, repeat(str))):
        kind = type(next(item for item in value if not isinstance(item, str))).__name__
        raise SourceTypeError(
            f"The {what} must be strings, not {kind}"
            if message is None
            else message.format(type=kind, param=what)
        )


def check_word(value: object, what: str = "word") -> None:
    """
    Checking that an argument is a word: a string

    Arguments:
        value (object): Value to check
        what (str): What is expected, for the message of the error

    Raises:
        SourceTypeError: If the value is not a string

    Example:
        >>> from anyts.utils import check_word
        >>> check_word("cat")
        >>> check_word(["cat"])
        Traceback (most recent call last):
        ...
        anyts.exceptions.SourceTypeError: The word must be a string, not list
    """
    if not isinstance(value, str):
        raise SourceTypeError(f"The {what} must be a string, not {type(value).__name__}")


def check_counts(value: object) -> None:
    """
    Checking that an argument is a counter: a mapping of words to their frequencies

    Arguments:
        value (object): Value to check

    Raises:
        SourceTypeError: If the value is not a mapping, a word is not a string
            or a frequency is not a number
        SourceError: If a frequency is negative, nan or infinite

    Example:
        >>> from collections import Counter
        >>> from anyts.utils import check_counts
        >>> check_counts(Counter(["the", "cat", "the"]))
        >>> check_counts({"the": "2"})
        Traceback (most recent call last):
        ...
        anyts.exceptions.SourceTypeError: The frequencies must be numbers, not str
    """
    if not isinstance(value, Mapping):
        raise SourceTypeError(f"A mapping of frequencies is expected, not {type(value).__name__}")
    for word, count in value.items():
        if not isinstance(word, str):
            raise SourceTypeError(f"The words must be strings, not {type(word).__name__}")
        if isinstance(count, bool) or not isinstance(count, Real):
            raise SourceTypeError(f"The frequencies must be numbers, not {type(count).__name__}")
        if not math.isfinite(count) or count < 0:
            raise SourceError(f"The frequencies must be finite and not negative, not {count}")


def check_integer(value: object, what: str, *, message: str | None = None) -> None:
    """
    Checking that a parameter is an integer

    Description:
        A bool or a float, even a whole one, is not taken for an integer

    Arguments:
        value (object): Value to check
        what (str): Name of the parameter, for the message of the error
        message (str): Message of the error with the fields {type}, the type of the value,
            and {param}, what, in place of the English one

    Raises:
        ParameterError: If the value is not an integer

    Example:
        >>> from anyts.utils import check_integer
        >>> check_integer(5, "window size")
        >>> check_integer(5.0, "window size")
        Traceback (most recent call last):
        ...
        anyts.exceptions.ParameterError: The window size must be an integer, not float
    """
    if isinstance(value, bool) or not isinstance(value, Integral):
        kind = type(value).__name__
        raise ParameterError(
            f"The {what} must be an integer, not {kind}"
            if message is None
            else message.format(type=kind, param=what)
        )


def check_bool(value: object, what: str, *, message: str | None = None) -> None:
    """
    Checking that a parameter is a bool, a numpy bool included

    Arguments:
        value (object): Value to check
        what (str): Name of the parameter, for the message of the error
        message (str): Message of the error with the fields {type}, the type of the value,
            and {param}, what, in place of the English one

    Raises:
        ParameterError: If the value is not a bool

    Example:
        >>> from anyts.utils import check_bool
        >>> check_bool(True, "normalization")
        >>> check_bool("yes", "normalization")
        Traceback (most recent call last):
        ...
        anyts.exceptions.ParameterError: The normalization must be a bool, not str
    """
    numpy = sys.modules.get("numpy")
    if not (isinstance(value, bool) or (numpy is not None and isinstance(value, numpy.bool_))):
        kind = type(value).__name__
        raise ParameterError(
            f"The {what} must be a bool, not {kind}"
            if message is None
            else message.format(type=kind, param=what)
        )


def check_number(value: object, what: str, *, message: str | None = None) -> None:
    """
    Checking that a parameter is a finite real number

    Description:
        A bool is not taken for a number, nor are nan and infinity

    Arguments:
        value (object): Value to check
        what (str): Name of the parameter, for the message of the error
        message (str): Message of the error with the fields {type}, the type of the value or
            the value that is not finite, and {param}, what, in place of the English one

    Raises:
        ParameterError: If the value is not a finite real number

    Example:
        >>> from anyts.utils import check_number
        >>> check_number(0.95, "confidence level")
        >>> check_number("0.95", "confidence level")
        Traceback (most recent call last):
        ...
        anyts.exceptions.ParameterError: The confidence level must be a number, not str
    """
    if isinstance(value, bool) or not isinstance(value, Real):
        kind = type(value).__name__
        raise ParameterError(
            f"The {what} must be a number, not {kind}"
            if message is None
            else message.format(type=kind, param=what)
        )
    if not math.isfinite(value):
        raise ParameterError(
            f"The {what} must be a finite number, not {value}"
            if message is None
            else message.format(type=value, param=what)
        )


def check_callable(value: object, what: str) -> None:
    """
    Checking that an argument is a function, such as a hook passed as a parameter

    Arguments:
        value (object): Value to check
        what (str): Name of the argument, for the message of the error

    Raises:
        SourceTypeError: If the value cannot be called

    Example:
        >>> from anyts.utils import check_callable
        >>> check_callable(str.lower, "normalization")
        >>> check_callable("lower", "normalization")
        Traceback (most recent call last):
        ...
        anyts.exceptions.SourceTypeError: The normalization must be callable, not str
    """
    if not callable(value):
        raise SourceTypeError(f"The {what} must be callable, not {type(value).__name__}")


def merge_labels(
    defaults: Mapping[str, str], labels: Mapping[str, str] | None, **samples: object
) -> dict[str, str]:
    """
    Merging the labels given for a plot over its default ones

    Description:
        A label not given keeps its default. A default with fields in braces is
        a format string: a label given for it may use only those fields, with a
        literal brace doubled ({{), and is tried on the samples of its fields,
        so that a wrong format spec fails before the plot. The other labels are
        taken as they are

    Arguments:
        defaults (dict[str, str]): Default labels by key
        labels (dict[str, str]): Labels given; None - the default ones
        samples (object): Values of the fields of the format labels, of the types
            the plot gives them

    Returns:
        dict[str, str]: Labels by key

    Raises:
        ParameterError: If the labels are not a mapping of strings, have an
            unknown key, or a format label is not a format string of the fields
            of its default or does not format their values

    Example:
        >>> from anyts.utils import merge_labels
        >>> merge_labels({"title": "Plot", "xlabel": "x"}, {"title": "My plot"})
        {'title': 'My plot', 'xlabel': 'x'}
    """
    if labels is None:
        return dict(defaults)
    if not isinstance(labels, Mapping):
        raise ParameterError(f"The labels must be a mapping, not {type(labels).__name__}")
    unknown = [key for key in labels if key not in defaults]
    if unknown:
        raise ParameterError(f"Unknown labels: {unknown}. Available labels: {tuple(defaults)}")
    if not all(isinstance(label, str) for label in labels.values()):
        raise ParameterError("The labels must be strings")
    for key, label in labels.items():
        fields = _format_fields(defaults[key])
        if not fields:
            continue
        try:
            extra = _format_fields(label) - fields
        except ValueError as error:
            raise ParameterError(f"The label {key!r} is not a format string: {error}") from None
        if extra:
            raise ParameterError(
                f"The label {key!r} has unknown fields {sorted(extra)}; "
                f"available fields: {sorted(fields)}"
            )
        if fields <= samples.keys():
            try:
                label.format(**samples)
            except (ValueError, TypeError, IndexError, KeyError, AttributeError) as error:
                raise ParameterError(
                    f"The label {key!r} does not format its fields: {error}"
                ) from None
    return {**defaults, **labels}


def _format_fields(label: str) -> set[str]:
    """
    Names of the fields of a format string, those in the format specs included

    Raises:
        ValueError: If the string is not a format string or has an unknown conversion
    """
    fields = set()
    for _, name, spec, conversion in Formatter().parse(label):
        if name is None:
            continue
        if conversion not in (None, "r", "s", "a"):
            raise ValueError(f"Unknown conversion specifier {conversion}")
        fields.add(name)
        if spec:
            fields |= _format_fields(spec)
    return fields


def check_messages(messages: object, defaults: Mapping[str, str] = MESSAGES) -> None:
    """
    Checking the messages of the errors a class of statistics raises

    Description:
        The messages must be complete, a string for every key of the defaults,
        so that an error never turns into a KeyError; a library merges its own
        over the defaults ({**MESSAGES, **own}). A message whose default has
        fields in braces may use only those fields, with a literal brace doubled
        ({{); the others are taken as they are

    Arguments:
        messages (dict[str, str]): Messages by key
        defaults (dict[str, str]): Default messages by key

    Raises:
        ParameterError: If the messages are not a mapping of strings, lack a key
            of the defaults or have another, or a format message has a field its
            default lacks or is not a format string

    Example:
        >>> from anyts.constants import MESSAGES
        >>> from anyts.utils import check_messages
        >>> check_messages({**MESSAGES, "no_words": "Il testo non contiene parole"})
    """
    if not isinstance(messages, Mapping):
        raise ParameterError(f"The messages must be a mapping, not {type(messages).__name__}")
    missing = [key for key in defaults if key not in messages]
    if missing:
        raise ParameterError(f"The messages lack the keys {missing}")
    unknown = [key for key in messages if key not in defaults]
    if unknown:
        raise ParameterError(f"Unknown messages: {unknown}. Available messages: {tuple(defaults)}")
    if not all(isinstance(message, str) for message in messages.values()):
        raise ParameterError("The messages must be strings")
    for key, default in defaults.items():
        fields = _format_fields(default)
        if not fields:
            continue
        try:
            extra = _format_fields(messages[key]) - fields
        except ValueError as error:
            raise ParameterError(f"The message {key!r} is not a format string: {error}") from None
        if extra:
            raise ParameterError(
                f"The message {key!r} has unknown fields {sorted(extra)}; "
                f"available fields: {sorted(fields)}"
            )


def source_type_error(messages: Mapping[str, str], source: object) -> SourceTypeError:
    """
    Getting the error of a data source of a wrong type

    Description:
        The message source_span for a Span, which as_doc turns into a Doc, and
        source_type with the name of the type for any other source

    Arguments:
        messages (dict[str, str]): Messages by key (MESSAGES)
        source (object): Data source

    Returns:
        SourceTypeError: Error to raise

    Example:
        >>> from anyts.constants import MESSAGES
        >>> from anyts.utils import source_type_error
        >>> source_type_error(MESSAGES, 5)
        SourceTypeError('The data source cannot be of type int')
    """
    if is_span(source):
        return SourceTypeError(messages["source_span"])
    return SourceTypeError(messages["source_type"].format(type=type(source).__name__))


class LazyPackage(ModuleType):
    """
    Package whose names are imported from their modules on first use

    Description:
        The class make_lazy gives a package. A name of its mapping is imported
        from its module when it is first read, so importing the package does
        not load the dependencies of every module; a module of the package is
        imported as its attribute too. A module named as one of its functions
        (zipf, kwic) leaves the function under that name in the package, as an
        eager import would. dir() lists the names of the mapping that __all__
        holds, all of them for a package without __all__, so that help() and
        inspect.getmembers() import only the public names. The imports of the
        names of every lazy package go one at a time, so that threads reading
        names first at once do not meet in a module half loaded by another; a
        thread that runs the body of a module it imports goes on without waiting,
        as a thread that imports may wait for that module
    """

    def __getattr__(self, name: str) -> Any:
        modules = self.__dict__["_MODULES"]
        if name in modules:
            module = f"{self.__name__}.{modules[name]}"
            with _lazy_import_lock():
                if name in self.__dict__:
                    return self.__dict__[name]
                # Python would take an AttributeError of the import for a missing name
                try:
                    value = getattr(import_module(module), name)
                except AttributeError as error:
                    raise ImportError(f"cannot import {name} from {module}: {error}") from error
                super().__setattr__(name, value)
            return value
        if name.isidentifier() and not name.startswith("__"):
            try:
                with _lazy_import_lock():
                    return import_module(f".{name}", self.__name__)
            except ModuleNotFoundError as error:
                if error.name != f"{self.__name__}.{name}":
                    raise
            except AttributeError as error:
                raise ImportError(f"cannot import {self.__name__}.{name}: {error}") from error
        raise AttributeError(f"module {self.__name__!r} has no attribute {name!r}")

    def __setattr__(self, name: str, value: Any) -> None:
        if isinstance(value, ModuleType) and name in self.__dict__.get("_MODULES", ()):
            return
        super().__setattr__(name, value)

    def __dir__(self) -> list[str]:
        names = self.__dict__["_MODULES"]
        if (public := self.__dict__.get("__all__")) is not None:
            names = [name for name in names if name in public]
        return sorted({*super().__dir__(), *names})


@contextmanager
def _lazy_import_lock() -> Iterator[None]:
    """The lock of the lazy imports; a thread that runs the body of a module it imports takes it
    only when it is free, since a thread that holds it may wait for the lock of that module"""
    acquired = _LAZY_IMPORT.acquire(blocking=not _imports_a_module())
    try:
        yield
    finally:
        if acquired:
            _LAZY_IMPORT.release()


def _imports_a_module() -> bool:
    """Whether the calling thread runs the body of a module it imports or reloads: a frame of
    _load_unlocked or _exec of the import system is on its stack, which from pkg import name at
    the top level does not put there"""
    frame: FrameType | None = sys._getframe(1)
    while frame is not None:
        code = frame.f_code
        if code.co_name in ("_load_unlocked", "_exec") and code.co_filename.startswith(
            "<frozen importlib._bootstrap"
        ):
            return True
        frame = frame.f_back
    return False


def make_lazy(name: str, modules: Mapping[str, str]) -> None:
    """
    Making a package import its names on first use

    Description:
        The package turns into a LazyPackage: every name of modules is imported
        from its module of the package when it is first read, so a light name
        does not load the dependencies of a heavy one (spaCy, matplotlib). A
        package calls it at the end of its __init__ with its __name__; the names
        it imports itself stay as they are

    Arguments:
        name (str): Name of the package, imported
        modules (dict[str, str]): Module of the package by name

    Raises:
        SourceTypeError: If the name is not a string or modules is not a mapping of
            strings to strings
        ParameterError: If the name is not that of an imported package, a name of
            modules is not an identifier or a module is not a dotted name of them

    Example:
        >>> import anyts.visualizers
        >>> type(anyts.visualizers).__name__
        'LazyPackage'
    """
    check_word(name, "name of a lazy package")
    package = sys.modules.get(name)
    if package is None or not hasattr(package, "__path__"):
        raise ParameterError(f"{name!r} is not the name of an imported package")
    if not isinstance(modules, Mapping):
        raise SourceTypeError(
            f"The modules of a lazy package must be a mapping, not {type(modules).__name__}"
        )
    check_words(list(modules), "names of a lazy package")
    check_words(list(modules.values()), "modules of a lazy package")
    for key, module in modules.items():
        if not key.isidentifier() or not all(part.isidentifier() for part in module.split(".")):
            raise ParameterError(
                f"The lazy name {key!r} must be an identifier from a module of the package, "
                f"not {module!r}"
            )
    vars(package)["_MODULES"] = dict(modules)
    package.__class__ = LazyPackage
