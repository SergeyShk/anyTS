import unicodedata
from collections.abc import Iterator
from functools import lru_cache

from spacy.tokens import Doc, Span, Token

from .exceptions import SourceTypeError

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


def check_sequence(value: object, what: str = "words") -> None:
    """
    Checking that an argument is a sequence of strings and not a text

    Arguments:
        value (object): Value to check
        what (str): What is expected, for the message of the error

    Raises:
        SourceTypeError: If a string, a Doc or a Span is passed

    Example:
        >>> from anyts.utils import check_sequence
        >>> check_sequence(["the", "cat"])
        >>> check_sequence("the cat")
        Traceback (most recent call last):
        ...
        anyts.exceptions.SourceTypeError: A list of words is expected, not a string
    """
    if isinstance(value, str):
        raise SourceTypeError(f"A list of {what} is expected, not a string")
    if isinstance(value, Doc | Span):
        raise SourceTypeError(
            f"A list of {what} is expected, not a {type(value).__name__}: "
            "extract the words with WordsExtractor"
        )


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
        The words of iter_doc_units with the positions of their tokens

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
        yield unit[0].idx, unit[-1].idx + len(unit[-1]), "".join(token.text for token in unit)
