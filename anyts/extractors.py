import re
import sys
import unicodedata
from abc import ABCMeta, abstractmethod
from collections import Counter
from collections.abc import Callable, Collection, Iterable, Iterator, Mapping, Sequence
from functools import cache
from numbers import Integral
from re import Pattern
from typing import Any, ClassVar

from .constants import MESSAGES
from .exceptions import ParameterError, SourceTypeError
from .utils import NUMBER_PATTERN as NUMBER_PATTERN
from .utils import (
    check_callable,
    check_integer,
    check_messages,
    check_words,
    has_words,
    is_number,
    is_punctuation,
)

Tokenizer = Pattern[str] | Callable[[str], Iterable[str]]
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?…])\s+|(?<=[.!?…][\"'»”’)\]])\s+")
BLANK_LINE = re.compile(r"\n\s*\n")


def _iter_words(text: str) -> Iterator[tuple[int, int, str]]:
    """Words of the default tokenizer of WordsExtractor with their positions"""
    return (
        (match.start(), match.end(), match.group()) for match in _word_pattern().finditer(text)
    )


@cache
def _word_pattern() -> Pattern[str]:
    """
    Pattern of a word of the default tokenizers

    Description:
        A word character \\w followed by word characters, combining marks, the
        zero-width non-joiner and joiner and the soft hyphen. Built on first use,
        not on import, since reading the combining marks takes tens of
        milliseconds

    Returns:
        Pattern: Compiled regular expression
    """
    continuation = _char_class(
        char
        for char in map(chr, range(sys.maxunicode + 1))
        if unicodedata.category(char)[0] == "M" or char in "\u00ad\u200c\u200d"
    )
    return re.compile(rf"\w[\w{continuation}]*")


def _char_class(chars: Iterable[str]) -> str:
    """
    Building the body of a regular expression class from characters

    Arguments:
        chars (iterable[str]): Characters in ascending order

    Returns:
        str: Ranges of consecutive characters, escaped
    """
    ranges: list[list[int]] = []
    for code in map(ord, chars):
        if ranges and ranges[-1][1] == code - 1:
            ranges[-1][1] = code
        else:
            ranges.append([code, code])
    return "".join(
        re.escape(chr(first)) + ("-" + re.escape(chr(last)) if last > first else "")
        for first, last in ranges
    )


class Extractor(metaclass=ABCMeta):
    """
    Abstract class for extracting units from a text

    Arguments:
        tokenizer (pattern|callable): Tokenizer or regular expression
        min_len (int): Minimum length of an extracted unit
        max_len (int): Maximum length of an extracted unit

    Methods:
        extract: Extracting units from a text

    Class attributes:
        messages (dict[str, str]): Messages of the errors by key (MESSAGES)
    """

    messages: ClassVar[Mapping[str, str]] = MESSAGES

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        check_messages(cls.messages)

    @abstractmethod
    def __init__(
        self, tokenizer: Tokenizer | None = None, min_len: int = 0, max_len: int = 0
    ) -> None:
        self.tokenizer = tokenizer
        self.min_len = min_len
        self.max_len = max_len

    @abstractmethod
    def extract(self, text: str) -> tuple[str, ...]:
        raise NotImplementedError

    def _tokenize(self, text: str, default: Callable[[str], Iterable[str]]) -> Iterator[str]:
        """
        Splitting a text with the tokenizer

        Description:
            The default tokenizer is resolved at the call, so the extractor keeps
            no reference to its own bound method

        Arguments:
            text (str): Text string
            default (callable): Tokenizer used when none is given

        Returns:
            iterator[str]: Iterator of tokens

        Raises:
            SourceTypeError: If the text is not a string, the tokenizer is not callable
                or returns something other than strings; the tokenizer's own errors
                are not caught
        """
        messages = self.messages
        _check_text(text, messages)
        tokenizer = self.tokenizer or default
        if isinstance(tokenizer, Pattern):
            # re.split gives None for a group that took no part in the match
            return (token for token in tokenizer.split(text) if token is not None)
        if not callable(tokenizer):
            raise SourceTypeError(messages["tokenizer"])
        tokens = tokenizer(text)
        try:
            return _check_tokens(iter(tokens), messages)
        except TypeError as e:
            raise SourceTypeError(messages["tokenizer_iterable"]) from e


def _check_text(text: object, messages: Mapping[str, str] = MESSAGES) -> None:
    """
    Checking that the source of an extractor is a string

    Arguments:
        text (object): Value to check
        messages (dict[str, str]): Messages of the errors by key (MESSAGES)

    Raises:
        SourceTypeError: If the value is not a string
    """
    if not isinstance(text, str):
        raise SourceTypeError(messages["text_type"].format(type=type(text).__name__))


def _check_tokens(
    tokens: Iterator[object], messages: Mapping[str, str] = MESSAGES
) -> Iterator[str]:
    """
    Checking that the tokenizer gives strings

    Arguments:
        tokens (iterator[object]): Tokens of the tokenizer
        messages (dict[str, str]): Messages of the errors by key (MESSAGES)

    Returns:
        iterator[str]: The same tokens

    Raises:
        SourceTypeError: If a token is not a string, such as a spaCy token
    """
    for token in tokens:
        if not isinstance(token, str):
            raise SourceTypeError(messages["tokenizer_strings"].format(type=type(token).__name__))
        yield token


class SentsExtractor(Extractor):
    """
    Class for extracting sentences from a text

    Example:
        >>> import re
        >>> from anyts import SentsExtractor
        >>> SentsExtractor().extract("It rains. Does it? Yes!")
        ('It rains.', 'Does it?', 'Yes!')
        >>> SentsExtractor(tokenizer=re.compile(r", ")).extract("Rain today, sun tomorrow")
        ('Rain today', 'sun tomorrow')

    Description:
        The default tokenizer is the method sentenize, which a language library
        overrides; here it splits at whitespace after ., !, ? or …, optionally
        followed by a closing quote or bracket. The text is split at blank lines
        first and every part goes to the tokenizer, so a blank line ends a
        sentence and a part without words is a sentence of its own

    Arguments:
        tokenizer (pattern|callable): Tokenizer or regular expression
        min_len (int): Minimum length of an extracted sentence
        max_len (int): Maximum length of an extracted sentence

    Methods:
        sentenize: Default tokenizer
        extract: Extracting sentences from a text

    Raises:
        ParameterError: If a length bound is not an integer, is negative or the minimum
            is greater than the maximum
    """

    def __init__(
        self,
        tokenizer: Tokenizer | None = None,
        min_len: int = 0,
        max_len: int = 0,
    ) -> None:
        super().__init__(tokenizer, min_len, max_len)
        messages = self.messages
        _check_length_bounds(
            min_len, max_len, "sentence", messages["sent_len_bounds"], messages["sent_len_order"]
        )
        self.sents: tuple[str, ...] = ()

    def sentenize(self, text: str) -> Iterable[str]:
        """
        Splitting a text into sentences by default

        Description:
            A piece without words, such as the dots of a spaced ellipsis or a lone
            "!", stays with the sentence before it, or with the one after it at
            the start of the text

        Arguments:
            text (str): Text string

        Returns:
            iterable[str]: Sentences
        """
        pieces = _SENTENCE_BOUNDARY.split(text)
        sents = pieces[:1]
        for separator, piece in zip(_SENTENCE_BOUNDARY.findall(text), pieces[1:], strict=True):
            if has_words(piece) and has_words(sents[-1]):
                sents.append(piece)
            else:
                sents[-1] += separator + piece
        return sents

    def extract(self, text: str) -> tuple[str, ...]:
        """
        Extracting sentences from a text

        Arguments:
            text (str): Text string

        Returns:
            sents (tuple[str]): Tuple of extracted sentences, stripped, without empty ones

        Raises:
            SourceTypeError: If the text is not a string or the tokenizer is set incorrectly
        """
        _check_text(text, self.messages)
        sents = (
            sent
            for part in BLANK_LINE.split(text)
            for sent in map(str.strip, self._tokenize(part, self.sentenize))
            if sent
        )
        if self.min_len > 0:
            sents = (sent for sent in sents if len(sent) >= self.min_len)
        if self.max_len > 0:
            sents = (sent for sent in sents if len(sent) <= self.max_len)
        self.sents = tuple(sents)
        return self.sents


def _check_length_bounds(
    min_len: int, max_len: int, unit: str, negative: str, reversed_bounds: str
) -> None:
    """
    Checking the bounds of the length of an extracted unit

    Arguments:
        min_len (int): Minimum length, 0 for no bound
        max_len (int): Maximum length, 0 for no bound
        unit (str): Name of the unit, for the message of a bound that is not an integer
        negative (str): Message of a negative bound
        reversed_bounds (str): Message of a minimum greater than the maximum

    Raises:
        ParameterError: If a bound is not an integer, is negative or the minimum
            is greater than the maximum
    """
    check_integer(min_len, f"minimum {unit} length")
    check_integer(max_len, f"maximum {unit} length")
    if min_len < 0 or max_len < 0:
        raise ParameterError(negative)
    if min_len and max_len and min_len > max_len:
        raise ParameterError(reversed_bounds)


def iter_part_sents(
    iter_sents: Callable[[str], Iterable[tuple[int, int, str]]], text: str
) -> Iterator[tuple[int, int, str]]:
    """
    Extracting the sentences of every part of a text between blank lines

    Description:
        Every part between blank lines (BLANK_LINE) goes to iter_sents, so that
        a blank line ends a sentence whatever the splitter; the positions are
        those in the whole text

    Arguments:
        iter_sents (Callable[[str], Iterable[tuple[int, int, str]]]): Sentences of a
            string with their positions
        text (str): Text string

    Returns:
        iterator[tuple[int, int, str]]: Position of the first character, position
            after the last character and text of each sentence

    Raises:
        SourceTypeError: If iter_sents is not callable, the text is not a string,
            or iter_sents does not give the sentences of a part in order, as ascending
            integer bounds inside the part with the text of each

    Example:
        >>> import re
        >>> from anyts.extractors import iter_part_sents
        >>> def periods(text):
        ...     return [(m.start(), m.end(), m.group()) for m in re.finditer(r"[^.\\s][^.]*\\.?", text)]
        >>> list(iter_part_sents(periods, "One. Two\\n\\nThree."))
        [(0, 4, 'One.'), (5, 8, 'Two'), (10, 16, 'Three.')]
    """
    check_callable(iter_sents, "sentence splitter")
    if not isinstance(text, str):
        raise SourceTypeError(MESSAGES["text_type"].format(type=type(text).__name__))
    return _iter_part_sents(iter_sents, text)


def _iter_part_sents(
    iter_sents: Callable[[str], Iterable[tuple[int, int, str]]], text: str
) -> Iterator[tuple[int, int, str]]:
    """iter_part_sents of checked arguments"""
    bounds = [0, *(bound for match in BLANK_LINE.finditer(text) for bound in match.span())]
    for start, end in zip(bounds[::2], [*bounds[1::2], len(text)], strict=True):
        part = text[start:end]
        for first, last, sent in _check_spans(iter_sents(part), part, "sentence splitter"):
            yield start + first, start + last, sent


def _check_spans(
    spans: object, text: str, what: str, ordered: bool = True
) -> list[tuple[int, int, str]]:
    """
    Checking the spans a hook gives for a string: triples of the start, the end and
    the text of every item inside the string, in order unless not ordered
    """
    if not isinstance(spans, Iterable):
        raise SourceTypeError(f"The {what} must return an iterable object")
    checked = []
    previous = 0
    size = len(text)
    for span in spans:
        if not (isinstance(span, tuple | list) and len(span) == 3):
            raise SourceTypeError(
                f"The {what} must give triples of the start, the end and the text, not {span!r}"
            )
        start, end, item = span
        integers = (type(start) is int and type(end) is int) or all(
            isinstance(bound, Integral) and not isinstance(bound, bool) for bound in (start, end)
        )
        if not (integers and isinstance(item, str) and previous <= start < end <= size):
            order = "ascending " if ordered else ""
            raise SourceTypeError(
                f"The {what} must give {order}integer bounds inside the string and the text "
                f"of every item, not {tuple(span)!r}"
            )
        checked.append((start, end, item))
        if ordered:
            previous = end
    return checked


class WordsExtractor(Extractor):
    """
    Class for extracting words from a text

    Example:
        >>> from anyts import WordsExtractor
        >>> text = "Better 100 friends than 100 dollars"
        >>> we = WordsExtractor(lowercase=True, stopwords=["than"],
        ...                     filter_nums=True, ngram_range=(1, 2))
        >>> we.extract(text)
        ('better', 'friends', 'dollars', 'better_friends', 'friends_dollars')

    Description:
        A language library overrides the methods tokenize (by default a word
        character \\w followed by word characters, combining marks, zero-width
        joiners and non-joiners and soft hyphens) and lemmatize (by default the
        word itself) and sets the class attribute number_pattern (NUMBER_PATTERN
        by default: -5, 1990-1995, 1,500.50, 12/03/2020, 3:30, 10%). The
        filters are applied in order: punctuation, numbers, lemmatization, lower
        case, stop words, word length

    Arguments:
        tokenizer (pattern|callable): Tokenizer or regular expression
        filter_punct (bool): Filter punctuation marks
        filter_nums (bool): Filter numbers
        use_lexemes (bool): Use word lemmas
        stopwords (collection[str]): Stop words, compared case-insensitively
        lowercase (bool): Convert words to lower case
        ngram_range (tuple[int, int]): Lower and upper bound of the N-gram size
        min_len (int): Minimum length of an extracted word
        max_len (int): Maximum length of an extracted word

    Methods:
        tokenize: Default tokenizer
        lemmatize: Lemma of a word
        extract: Extracting words from a text
        get_most_common: Getting the top words with their frequencies

    Raises:
        ParameterError: If the N-gram range is not a pair of integers, its lower bound
            is less than one or greater than the upper
        ParameterError: If a length bound is not an integer, is negative or the minimum
            is greater than the maximum
        SourceTypeError: If the stop words are not a list of strings
    """

    number_pattern: ClassVar[Pattern[str]] = NUMBER_PATTERN

    def __init__(
        self,
        tokenizer: Tokenizer | None = None,
        filter_punct: bool = True,
        filter_nums: bool = False,
        use_lexemes: bool = False,
        stopwords: Collection[str] | None = None,
        lowercase: bool = False,
        ngram_range: tuple[int, int] = (1, 1),
        min_len: int = 0,
        max_len: int = 0,
    ) -> None:
        super().__init__(tokenizer, min_len, max_len)
        self.filter_punct = filter_punct
        self.filter_nums = filter_nums
        self.use_lexemes = use_lexemes
        if stopwords is not None:
            check_words(stopwords, "stopwords", ordered=False)
        self.stopwords = (
            frozenset(word.lower() for word in stopwords) or None
            if stopwords is not None
            else None
        )
        self.lowercase = lowercase
        messages = self.messages
        if not isinstance(ngram_range, tuple | list) or len(ngram_range) != 2:
            raise ParameterError(messages["ngram_range"])
        lower, upper = ngram_range
        check_integer(lower, "lower N-gram bound")
        check_integer(upper, "upper N-gram bound")
        if lower < 1:
            raise ParameterError(messages["ngram_lower"])
        if lower > upper:
            raise ParameterError(messages["ngram_order"])
        self.ngram_range = (lower, upper)
        _check_length_bounds(
            min_len, max_len, "word", messages["word_len_bounds"], messages["word_len_order"]
        )
        self.words: tuple[str, ...] = ()

    def tokenize(self, text: str) -> Iterable[str]:
        """
        Splitting a text into words by default

        Arguments:
            text (str): Text string

        Returns:
            iterable[str]: Words
        """
        return _word_pattern().findall(text)

    def lemmatize(self, word: str) -> str:
        """
        Getting the lemma of a word

        Arguments:
            word (str): Word form

        Returns:
            str: Lemma, by default the word itself
        """
        return word

    def extract(self, text: str) -> tuple[str, ...]:
        """
        Extracting words from a text

        Arguments:
            text (str): Text string

        Returns:
            words (tuple[str]): Tuple of extracted words without empty and whitespace ones

        Raises:
            SourceTypeError: If the text is not a string or the tokenizer is set incorrectly
        """
        words = (word for word in self._tokenize(text, self.tokenize) if word.strip())
        if self.filter_punct:
            words = (word for word in words if not is_punctuation(word))
        if self.filter_nums:
            words = (word for word in words if not is_number(word, self.number_pattern))
        if self.use_lexemes:
            words = (self.lemmatize(word) for word in words)
        if self.lowercase:
            words = (word.lower() for word in words)
        if self.stopwords:
            words = (word for word in words if word.lower() not in self.stopwords)
        if self.min_len > 0:
            words = (word for word in words if len(word) >= self.min_len)
        if self.max_len > 0:
            words = (word for word in words if len(word) <= self.max_len)
        self.words = tuple(words)
        if self.ngram_range != (1, 1):
            self.words = self.__make_ngrams()
        return self.words

    def get_most_common(self, n: int = 10) -> list[tuple[str, int]]:
        """
        Getting the top words with their frequencies

        Arguments:
            n (int): Number of words

        Returns:
            list[tuple[str, int]]: Pairs (word, frequency), the most frequent first

        Raises:
            ParameterError: If the number of words is not an integer or is less than 1
        """
        check_integer(n, "number of words")
        if n < 1:
            raise ParameterError(self.messages["top_words"])
        return Counter(self.words).most_common(n)

    def __make_ngrams(self) -> tuple[str, ...]:
        """
        Building N-grams

        Returns:
            ngrams (tuple[str]): Tuple of extracted N-grams
        """
        ngrams: tuple[str, ...] = ()
        for n in range(self.ngram_range[0], self.ngram_range[1] + 1):
            ngrams += tuple(
                "_".join(self.words[i : i + n]) for i in range(len(self.words) - n + 1)
            )
        return ngrams


class CharNgramsExtractor(Extractor):
    """
    Class for extracting character N-grams from a text

    Example:
        >>> from anyts import CharNgramsExtractor
        >>> text = "The cat slept  on the sill, and the dog - on the floor."
        >>> ce = CharNgramsExtractor(n=3, lowercase=True)
        >>> ce.extract(text)[:6]
        ('the', 'he ', 'e c', ' ca', 'cat', 'at ')
        >>> ce.get_most_common(2)
        [('the', 4), ('he ', 4)]
        >>> CharNgramsExtractor(n=4, lowercase=True, within_words=True).extract(text)
        ('slep', 'lept', 'sill', 'floo', 'loor')

    Description:
        A sliding window over the text with whitespace runs collapsed into one
        space and punctuation kept (Stamatatos 2009); with within_words, over
        each word of the tokenizer, punctuation dropped, so words shorter than
        N yield no N-grams. The default word tokenizer is the method tokenize,
        which a language library overrides; here it is that of WordsExtractor

    Arguments:
        n (int): N-gram length in characters
        lowercase (bool): Convert the text to lower case
        within_words (bool): Take N-grams only inside words
        tokenizer (pattern|callable): Word tokenizer for within_words
            or a regular expression

    Methods:
        tokenize: Default word tokenizer
        extract: Extracting N-grams from a text
        get_most_common: Getting the top N-grams with their frequencies

    Raises:
        ParameterError: If the N-gram length is not an integer or is less than one
    """

    def __init__(
        self,
        n: int = 2,
        lowercase: bool = False,
        within_words: bool = False,
        tokenizer: Tokenizer | None = None,
    ) -> None:
        super().__init__(tokenizer)
        check_integer(n, "N-gram length")
        if n < 1:
            raise ParameterError(self.messages["ngram_len"])
        self.n = n
        self.lowercase = lowercase
        self.within_words = within_words
        self.ngrams: tuple[str, ...] = ()

    def tokenize(self, text: str) -> Iterable[str]:
        """
        Splitting a text into words by default

        Arguments:
            text (str): Text string

        Returns:
            iterable[str]: Words
        """
        return _word_pattern().findall(text)

    def extract(self, text: str) -> tuple[str, ...]:
        """
        Extracting character N-grams from a text

        Arguments:
            text (str): Text string

        Returns:
            ngrams (tuple[str]): Tuple of extracted N-grams

        Raises:
            SourceTypeError: If the text is not a string or the tokenizer is set incorrectly
        """
        _check_text(text, self.messages)
        if self.lowercase:
            text = text.lower()
        if self.within_words:
            units = [
                word for word in self._tokenize(text, self.tokenize) if not is_punctuation(word)
            ]
        else:
            units = [" ".join(text.split())]
        self.ngrams = tuple(
            unit[index : index + self.n]
            for unit in units
            for index in range(len(unit) - self.n + 1)
        )
        return self.ngrams

    def get_most_common(self, n: int = 10) -> list[tuple[str, int]]:
        """
        Getting the top N-grams with their frequencies

        Arguments:
            n (int): Number of N-grams

        Returns:
            list[tuple[str, int]]: Pairs (N-gram, frequency), the most frequent first

        Raises:
            ParameterError: If the number of N-grams is not an integer or is less than 1
        """
        check_integer(n, "number of N-grams")
        if n < 1:
            raise ParameterError(self.messages["top_ngrams"])
        return Counter(self.ngrams).most_common(n)


class FixedSentsExtractor(SentsExtractor):
    """
    Sentence extractor that gives the sentences it was made with

    Description:
        Any text gives the same sentences: for a class that takes an extractor
        when the sentences are already known, so that the text is not split twice

    Arguments:
        sents (list[str]): Sentences

    Raises:
        SourceTypeError: If the sentences are not a list of strings

    Example:
        >>> from anyts.extractors import FixedSentsExtractor
        >>> FixedSentsExtractor(["It rains.", "Yes!"]).extract("any text")
        ('It rains.', 'Yes!')
    """

    def __init__(self, sents: Sequence[str]) -> None:
        super().__init__()
        check_words(sents, "sentences")
        self.sents = tuple(sents)

    def extract(self, text: str) -> tuple[str, ...]:
        return self.sents


class FixedWordsExtractor(WordsExtractor):
    """
    Word extractor that gives the words it was made with

    Description:
        Any text gives the same words: for a class that takes an extractor when
        the words are already known, so that the text is not tokenized twice

    Arguments:
        words (list[str]): Words

    Raises:
        SourceTypeError: If the words are not a list of strings

    Example:
        >>> from anyts.extractors import FixedWordsExtractor
        >>> FixedWordsExtractor(["It", "rains"]).extract("any text")
        ('It', 'rains')
    """

    def __init__(self, words: Sequence[str]) -> None:
        super().__init__()
        check_words(words)
        self.words = tuple(words)

    def extract(self, text: str) -> tuple[str, ...]:
        return self.words
