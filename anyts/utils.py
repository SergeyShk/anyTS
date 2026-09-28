import math
import unicodedata
from collections.abc import Iterable, Iterator, Mapping, Sequence, Set
from functools import lru_cache
from itertools import repeat
from numbers import Integral, Real
from string import Formatter

from spacy.tokens import Doc, Span, Token

from .exceptions import ParameterError, SourceError, SourceTypeError

# Punctuation, symbols, combining marks and invisible format characters
PUNCTUATION_CATEGORIES = frozenset(
    ("Pc", "Pd", "Ps", "Pe", "Pi", "Pf", "Po", "Sm", "Sc", "Sk", "So", "Mn", "Mc", "Me", "Cf")
)


def is_punctuation(token: str) -> bool:
    """
    Checking whether a token consists only of punctuation marks and symbols

    Description:
        Characters of the Unicode categories P (punctuation), S (symbols),
        M (combining marks) and Cf (invisible format characters: the zero-width
        space, the byte order mark, the zero-width joiner), so "?!", "--", "«",
        "€", "№" and a lone zero-width space are punctuation too, while a token
        with a letter or a digit is not; an empty token is punctuation as well

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
    if isinstance(value, Doc | Span):
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


def iter_doc_tokens(source: Doc | Span) -> Iterator[Token]:
    """
    Extracting the tokens of the words from a Doc or Span object

    Description:
        Whitespace tokens and the tokens of is_punctuation (symbols like %
        and € included) are skipped

    Arguments:
        source (Doc|Span): Doc or Span object

    Returns:
        generator[Token]: Token of each word
    """
    for token in source:
        if not token.is_space and not is_punctuation(token.text):
            yield token


def iter_doc_units(source: Doc | Span, join_hyphens: bool = False) -> Iterator[list[Token]]:
    """
    Extracting words from a Doc or Span object as lists of tokens

    Description:
        The words of iter_doc_tokens, one token each; with join_hyphens, a word
        the tokenizer split at its hyphens (well-known into well, -, known) is
        joined back when no whitespace separates its parts

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
        if token.is_space or is_punctuation(token.text):
            index += 1
            continue
        last = index
        while (
            join_hyphens
            and last + 2 < len(tokens)
            and tokens[last + 1].text == "-"
            and not tokens[last].whitespace_
            and not tokens[last + 1].whitespace_
            and not tokens[last + 2].is_space
            and not is_punctuation(tokens[last + 2].text)
        ):
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
