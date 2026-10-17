from __future__ import annotations

import math
import re
import sys
import unicodedata
from collections.abc import Callable, Collection, Iterable, Iterator, Mapping, Sequence, Set
from functools import lru_cache
from itertools import repeat
from numbers import Integral, Real
from re import Pattern
from statistics import fmean
from string import Formatter
from typing import TYPE_CHECKING, Any, TypeGuard

from .constants import MESSAGES
from .exceptions import ParameterError, SourceError, SourceTypeError

if TYPE_CHECKING:
    from spacy.tokens import Doc, Span, Token

# Punctuation, symbols, combining marks and invisible format characters
PUNCTUATION_CATEGORIES = frozenset(
    ("Pc", "Pd", "Ps", "Pe", "Pi", "Pf", "Po", "Sm", "Sc", "Sk", "So", "Mn", "Mc", "Me", "Cf")
)

# A signed number with separators and an optional percent sign: -5, 1990-1995, 1,500.50, 10%
NUMBER_PATTERN = re.compile(r"[+\-−]?\d+(?:[.,:/-]\d+)*%?")


@lru_cache(maxsize=1 << 16)
def is_punctuation(token: str) -> bool:
    """
    Checking whether a token consists only of punctuation marks and symbols

    Description:
        Characters of the Unicode categories P (punctuation), S (symbols),
        M (combining marks) and Cf (invisible format characters: the zero-width
        space, the byte order mark, the zero-width joiner), so "?!", "--", "«",
        "€", "№" and a lone zero-width space are punctuation too, while a token
        with a letter or a digit is not; an empty token is punctuation as well.
        The results are cached by token, so the function is meant for tokens,
        not whole texts

    Arguments:
        token (str): Token

    Returns:
        bool: Result of the check

    Example:
        >>> from anyts.utils import is_punctuation
        >>> is_punctuation("?!"), is_punctuation("€"), is_punctuation("no.")
        (True, True, False)
    """
    return all(unicodedata.category(char) in PUNCTUATION_CATEGORIES for char in token)


@lru_cache(maxsize=1 << 16)
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
    return pattern.fullmatch(word.lower()) is not None


@lru_cache(maxsize=1 << 16)
def count_letters(word: str) -> int:
    """
    Counting the letters of a string

    Description:
        Letters of any alphabet (str.isalpha), without digits, hyphens and marks;
        the results are cached by word form, so the function is meant for words,
        not whole texts

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
        An empty text or one of whitespace and the characters of is_punctuation
        alone (?!, ..., a zero-width space) holds no word

    Arguments:
        source (str|Doc|Span): Text, Doc or Span object

    Returns:
        bool: Result of the check

    Example:
        >>> from anyts.utils import has_words
        >>> has_words("The cat sleeps"), has_words("?!"), has_words("")
        (True, False, False)
    """
    text = source if isinstance(source, str) else source.text
    return any(not char.isspace() and not is_punctuation(char) for char in text)


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
        SourceTypeError: If the words or the phrases are not a list of strings

    Example:
        >>> from anyts.utils import find_phrases
        >>> find_phrases(["In", "fact", "it", "rains"], ["in fact", "in"])
        [(0, 2)]
    """
    check_words(words)
    check_words(phrases, "phrases", ordered=False)
    patterns = sorted(
        {pattern for phrase in phrases if (pattern := tuple(normalize(phrase).split()))},
        key=lambda pattern: (-len(pattern), pattern),
    )
    by_first: dict[str, list[tuple[str, ...]]] = {}
    for pattern in patterns:
        by_first.setdefault(pattern[0], []).append(pattern)
    normalized = [normalize(word) for word in words]
    spans = []
    position = 0
    while position < len(normalized):
        for pattern in by_first.get(normalized[position], ()):
            end = position + len(pattern)
            if tuple(normalized[position:end]) == pattern:
                spans.append((position, end))
                position = end
                break
        else:
            position += 1
    return spans


def count_words_by_spans(starts: Sequence[int], spans: Sequence[tuple[int, int]]) -> list[int]:
    """
    Counting the words in every span of a text by the positions of the words and the spans

    Description:
        The words and the spans are ordered by position; a word belongs to the
        span of its first character, and a span without words is skipped, so
        the lengths of the sentences of a text come out of the positions of its
        words and sentences

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


def has_sents(doc: Doc) -> bool:
    """
    Checking whether a Doc has its sentence boundaries

    Description:
        The boundaries count when every token has them, as the parser, senter
        and sentencizer set them; the starts of a component that leaves the
        other tokens unset, such as start_sents_after_blank_lines run without
        the parser, are partial, and the sentences of such a Doc come from its
        text, as of a Doc without boundaries

    Arguments:
        doc (Doc): Doc object

    Returns:
        bool: Result of the check

    Example:
        >>> import spacy
        >>> from spacy.tokens import Doc
        >>> from anyts.utils import has_sents
        >>> nlp = spacy.blank("xx")
        >>> has_sents(nlp("The cat sleeps. The dog eats."))
        False
        >>> _ = nlp.add_pipe("sentencizer")
        >>> has_sents(nlp("The cat sleeps. The dog eats."))
        True
        >>> has_sents(Doc(nlp.vocab, words=["Notes", "The", "cat"], sent_starts=[True, True, None]))
        False
    """
    return doc.has_annotation("SENT_START", require_complete=True)


def is_word(token: Token) -> bool:
    """
    Checking whether a token is a word - not a punctuation mark and not whitespace

    Description:
        The tokens of is_punctuation (symbols like %, €, + and invisible
        characters) are no words either

    Arguments:
        token (Token): Token

    Returns:
        bool: Result of the check
    """
    return not token.is_space and not is_punctuation(token.text)


def has_feature(token: Token, field: str, value: str) -> bool:
    """
    Checking whether a token carries a morphological feature with a given value

    Arguments:
        token (Token): Token
        field (str): Name of the feature of Universal Dependencies (VerbForm, Mood)
        value (str): Value of the feature (Part, Ger, Fin)

    Returns:
        bool: Result of the check
    """
    return value in token.morph.get(field, [])


def is_finite_verb(token: Token) -> bool:
    """
    Checking whether a token is a finite form of a verb

    Arguments:
        token (Token): Token

    Returns:
        bool: Result of the check
    """
    return token.pos_ == "VERB" and has_feature(token, "VerbForm", "Fin")


def is_infinitive(token: Token) -> bool:
    """
    Checking whether a token is an infinitive

    Arguments:
        token (Token): Token

    Returns:
        bool: Result of the check
    """
    return has_feature(token, "VerbForm", "Inf")


def joins_previous(token: Token) -> bool:
    """
    Checking whether a token continues a word the tokenizer split at its hyphens

    Description:
        The token is a word that follows a hyphen with no whitespace around it,
        and the hyphen follows a word, with no sentence starting at the hyphen
        or at the token: known in well-known; iter_doc_units joins such words

    Arguments:
        token (Token): Token

    Returns:
        bool: Result of the check
    """
    doc = token.doc
    i = token.i
    return (
        i >= 2
        and doc[i - 1].text == "-"
        and not doc[i - 2].whitespace_
        and not doc[i - 1].whitespace_
        and is_word(doc[i - 2])
        and is_word(token)
        and not doc[i - 1].is_sent_start
        and not token.is_sent_start
    )


def iter_doc_tokens(source: Doc | Span) -> Iterator[Token]:
    """
    Extracting the tokens of the words from a Doc or Span object

    Description:
        The tokens that are no words (is_word) are skipped

    Arguments:
        source (Doc|Span): Doc or Span object

    Returns:
        generator[Token]: Token of each word
    """
    for token in source:
        if is_word(token):
            yield token


def iter_doc_units(source: Doc | Span, join_hyphens: bool = False) -> Iterator[list[Token]]:
    """
    Extracting words from a Doc or Span object as lists of tokens

    Description:
        The words of iter_doc_tokens, one token each; with join_hyphens, a word
        the tokenizer split at its hyphens (well-known into well, -, known) is
        joined back by joins_previous

    Arguments:
        source (Doc|Span): Doc or Span object
        join_hyphens (bool): Join the parts of hyphenated words

    Returns:
        generator[list[Token]]: Tokens of each word
    """
    tokens = list(source)
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if not is_word(token):
            index += 1
            continue
        last = index
        while join_hyphens and last + 2 < len(tokens) and joins_previous(tokens[last + 2]):
            last += 2
        yield tokens[index : last + 1]
        index = last + 1


def iter_doc_words(
    source: Doc | Span, join_hyphens: bool = False
) -> Iterator[tuple[int, int, str]]:
    """
    Extracting words with positions from a Doc or Span object

    Description:
        The words of iter_doc_units with the positions of their tokens; a byte
        order mark glued to the start of a word, as in a file read with utf-8
        instead of utf-8-sig, is dropped

    Arguments:
        source (Doc|Span): Doc or Span object
        join_hyphens (bool): Join the parts of hyphenated words

    Returns:
        generator[tuple[int, int, str]]: Position of the first character,
            position after the last character and text of each word

    Example:
        >>> import spacy
        >>> from anyts.utils import iter_doc_words
        >>> doc = spacy.blank("xx")("A well-known cat")
        >>> [word for _, _, word in iter_doc_words(doc)]
        ['A', 'well', 'known', 'cat']
        >>> list(iter_doc_words(doc, join_hyphens=True))
        [(0, 1, 'A'), (2, 12, 'well-known'), (13, 16, 'cat')]
    """
    for unit in iter_doc_units(source, join_hyphens):
        yield _unit_word(unit)


def _unit_word(unit: Sequence[Token]) -> tuple[int, int, str]:
    """Positions and text of a word of iter_doc_units, a byte order mark at its start left out"""
    text = "".join(token.text for token in unit)
    word = text.lstrip("\ufeff")
    return unit[0].idx + len(text) - len(word), unit[-1].idx + len(unit[-1]), word


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


def safe_mean(values: Sequence[float], default: float = math.nan) -> float:
    """
    Computing the mean of numbers safely

    Arguments:
        values (list[float]): Numbers
        default (float): Value returned for no numbers

    Returns:
        float: Arithmetic mean
    """
    return fmean(values) if values else default


def shannon_entropy(counts: Mapping[Any, int]) -> float:
    """
    Computing the Shannon entropy of a distribution by its counts

    Arguments:
        counts (dict[object, int]): Count of every value, such as a Counter

    Returns:
        float: Entropy in bits, 0 for one value and nan for no counts

    Example:
        >>> from anyts.utils import shannon_entropy
        >>> shannon_entropy({"a": 2, "b": 2})
        1.0
    """
    total = sum(counts.values())
    if not total:
        return math.nan
    return -sum(count / total * math.log2(count / total) for count in counts.values()) or 0.0


def check_sequence(value: object, what: str = "words", ordered: bool = True) -> None:
    """
    Checking that an argument is a sequence and not a text or an iterator

    Description:
        A string would be iterated character by character, an iterator would
        be exhausted by the first pass over it, and a table (a two-dimensional
        array or a DataFrame) by its rows or columns. A set or a mapping holds
        every item once, in no order of the text, so it passes only with
        ordered=False - for a collection whose order and repeats do not
        matter, such as stop words

    Arguments:
        value (object): Value to check
        what (str): What is expected, for the message of the error
        ordered (bool): Whether the order and the repeats of the items matter

    Raises:
        SourceTypeError: If a string (of characters or bytes), a Doc, a Span, an
            iterator, a non-iterable object, a table or, with ordered, a set or a
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
    if isinstance(value, str | bytes | bytearray):
        raise SourceTypeError(f"A list of {what} is expected, not a string")
    if is_doc(value) or is_span(value):
        raise SourceTypeError(
            f"A list of {what} is expected, not a {type(value).__name__}: "
            "extract the words with WordsExtractor"
        )
    if isinstance(value, Iterator):
        raise SourceTypeError(f"A list of {what} is expected, not an iterator")
    if not isinstance(value, Iterable):
        raise SourceTypeError(f"A list of {what} is expected, not {type(value).__name__}")
    ndim = getattr(value, "ndim", 1)
    if ndim != 1:
        raise SourceTypeError(
            f"A list of {what} is expected, not a {ndim}-dimensional {type(value).__name__}"
        )
    if ordered and isinstance(value, Set | Mapping):
        raise SourceTypeError(f"A list of {what} is expected, not {type(value).__name__}")


def check_words(value: Iterable[object], what: str = "words", ordered: bool = True) -> None:
    """
    Checking that an argument is a list of words: a sequence of strings

    Arguments:
        value (object): Value to check
        what (str): What is expected, for the message of the error
        ordered (bool): Whether the order and the repeats of the words matter (check_sequence)

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
    check_sequence(value, what, ordered)
    if not all(map(isinstance, value, repeat(str))):
        item = next(item for item in value if not isinstance(item, str))
        raise SourceTypeError(f"The {what} must be strings, not {type(item).__name__}")


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


def check_integer(value: object, what: str) -> None:
    """
    Checking that a parameter is an integer

    Description:
        A bool or a float, even a whole one, is not taken for an integer, since it
        would fail only later, as an index or a count

    Arguments:
        value (object): Value to check
        what (str): Name of the parameter, for the message of the error

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
        raise ParameterError(f"The {what} must be an integer, not {type(value).__name__}")


def check_number(value: object, what: str) -> None:
    """
    Checking that a parameter is a finite real number

    Description:
        A bool is not taken for a number, nor are nan and infinity

    Arguments:
        value (object): Value to check
        what (str): Name of the parameter, for the message of the error

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
        raise ParameterError(f"The {what} must be a number, not {type(value).__name__}")
    if not math.isfinite(value):
        raise ParameterError(f"The {what} must be a finite number, not {value}")


def merge_labels(
    defaults: Mapping[str, str], labels: Mapping[str, str] | None, **samples: object
) -> dict[str, str]:
    """
    Merging the labels given for a plot over its default ones

    Description:
        A label that is not given keeps its default, so a single label can be
        changed alone. A default with fields in braces is a format string: a
        label given for it may use only those fields, and a literal brace in it
        is doubled ({{); it is tried on the samples of its fields, so that a
        format spec the values do not take fails before the plot. The other
        labels are taken as they are

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
        The messages are complete, a string for every key of the defaults, so
        that an error never turns into a KeyError; a library merges its own over
        the defaults ({**MESSAGES, **own}). A message whose default has fields in
        braces is a format string of those fields only, with a literal brace
        doubled ({{); the other messages are taken as they are

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
