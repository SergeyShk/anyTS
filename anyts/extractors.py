import re
from abc import ABCMeta, abstractmethod
from collections import Counter
from collections.abc import Callable, Collection, Iterable, Iterator
from re import Pattern
from typing import Any, ClassVar

from .exceptions import ParameterError, SourceTypeError
from .utils import check_sequence, is_punctuation

Tokenizer = Pattern[str] | Callable[[str], Iterable[str]]
SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?…])\s+|(?<=[.!?…][\"'»”’)\]])\s+")
WORD_PATTERN = re.compile(r"\w+")
NUMBER_PATTERN = re.compile(r"[+\-−]?\d+(?:[.,:/-]\d+)*%?")


def _check_length_bounds(min_len: int, max_len: int, unit: str) -> None:
    """
    Checking the bounds of the length of an extracted unit

    Arguments:
        min_len (int): Minimum length, 0 for no bound
        max_len (int): Maximum length, 0 for no bound
        unit (str): Name of the unit, for the message of the error

    Raises:
        ParameterError: If a bound is negative or the minimum is greater than the maximum
    """
    if min_len < 0 or max_len < 0:
        raise ParameterError(f"The {unit} length bounds cannot be negative")
    if min_len and max_len and min_len > max_len:
        raise ParameterError(f"The minimum {unit} length is greater than the maximum")


def _check_text(text: object) -> None:
    """
    Checking that the source of an extractor is a string

    Arguments:
        text (object): Value to check

    Raises:
        SourceTypeError: If the value is not a string
    """
    if not isinstance(text, str):
        raise SourceTypeError(f"A text string is expected, not {type(text).__name__}")


class Extractor(metaclass=ABCMeta):
    """
    Abstract class for extracting units from a text

    Arguments:
        tokenizer (pattern|callable): Tokenizer or regular expression
        min_len (int): Minimum length of an extracted unit
        max_len (int): Maximum length of an extracted unit

    Methods:
        extract: Extracting units from a text
    """

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

    def _tokenize(self, text: str) -> Iterator[str]:
        """
        Splitting a text with the tokenizer

        Arguments:
            text (str): Text string

        Returns:
            iterator[str]: Iterator of tokens

        Raises:
            SourceTypeError: If the text is not a string, the tokenizer is not callable
                or returns a non-iterable object; the tokenizer's own errors are not caught
        """
        _check_text(text)
        if isinstance(self.tokenizer, Pattern):
            return iter(re.split(self.tokenizer, text))
        if not callable(self.tokenizer):
            raise SourceTypeError("The tokenizer is set incorrectly")
        tokens = self.tokenizer(text)
        try:
            return iter(tokens)
        except TypeError as e:
            raise SourceTypeError("The tokenizer must return an iterable object") from e


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
        overrides; here it splits the text at whitespace after ., !, ? or …,
        optionally followed by a closing quote or bracket

    Arguments:
        tokenizer (pattern|callable): Tokenizer or regular expression
        min_len (int): Minimum length of an extracted sentence
        max_len (int): Maximum length of an extracted sentence

    Methods:
        sentenize: Default tokenizer
        extract: Extracting sentences from a text

    Raises:
        ParameterError: If a length bound is negative or the minimum is greater than the maximum
    """

    def __init__(
        self,
        tokenizer: Tokenizer | None = None,
        min_len: int = 0,
        max_len: int = 0,
    ) -> None:
        super().__init__(tokenizer, min_len, max_len)
        _check_length_bounds(min_len, max_len, "sentence")
        self.sents: tuple[str, ...] = ()
        if not self.tokenizer:
            self.tokenizer = self.sentenize

    def sentenize(self, text: str) -> Iterable[str]:
        """
        Splitting a text into sentences by default

        Arguments:
            text (str): Text string

        Returns:
            iterable[str]: Sentences
        """
        return SENTENCE_BOUNDARY.split(text)

    def extract(self, text: str) -> tuple[str, ...]:
        """
        Extracting sentences from a text

        Arguments:
            text (str): Text string

        Returns:
            sents (tuple[str]): Tuple of extracted sentences without empty
                and whitespace-only ones

        Raises:
            SourceTypeError: If the text is not a string or the tokenizer is set incorrectly
        """
        sents = (sent for sent in self._tokenize(text) if sent.strip())
        if self.min_len > 0:
            sents = (sent for sent in sents if len(sent) >= self.min_len)
        if self.max_len > 0:
            sents = (sent for sent in sents if len(sent) <= self.max_len)
        self.sents = tuple(sents)
        return self.sents


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
        The language comes through three hooks a language library overrides:
        the method tokenize (by default the runs of word characters \\w+), the
        method lemmatize (by default the word itself) and the class attribute
        number_pattern (by default signed numbers with separators and an optional
        percent sign: -5, 1990-1995, 1,500.50, 12/03/2020, 3:30, 10%). The filters
        are applied in order: punctuation, numbers, lemmatization, lower case,
        stop words, word length

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
        get_most_common: Getting a counter of the top words

    Raises:
        ParameterError: If the lower N-gram bound is less than one or greater than the upper
        ParameterError: If a length bound is negative or the minimum is greater than the maximum
        SourceTypeError: If the stop words are a string
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
        check_sequence(stopwords, "stopwords")
        self.stopwords = frozenset(word.lower() for word in stopwords) if stopwords else None
        self.lowercase = lowercase
        self.ngram_range = ngram_range
        if self.ngram_range[0] < 1:
            raise ParameterError("The lower N-gram bound must be greater than 0")
        if self.ngram_range[0] > self.ngram_range[1]:
            raise ParameterError("The lower N-gram bound is greater than the upper")
        _check_length_bounds(min_len, max_len, "word")
        self.words: tuple[str, ...] = ()
        if not self.tokenizer:
            self.tokenizer = self.tokenize

    def tokenize(self, text: str) -> Iterable[str]:
        """
        Splitting a text into words by default

        Arguments:
            text (str): Text string

        Returns:
            iterable[str]: Words
        """
        return WORD_PATTERN.findall(text)

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
            words (tuple[str]): Tuple of extracted words without empty ones

        Raises:
            SourceTypeError: If the text is not a string or the tokenizer is set incorrectly
        """
        # re.split leaves an empty string after a final separator
        words = (word for word in self._tokenize(text) if word)
        if self.filter_punct:
            words = (word for word in words if not is_punctuation(word))
        if self.filter_nums:
            words = (word for word in words if not self.number_pattern.fullmatch(word.lower()))
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

    def get_most_common(self, n: int = 10) -> list[tuple[Any, int]]:
        """
        Getting a counter of the top words

        Arguments:
            n (int): Number of words

        Returns:
            list: List of the top words

        Raises:
            ParameterError: If the number of words is less than 1
        """
        if n < 1:
            raise ParameterError("The number of words must be greater than 0")
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
        which a language library overrides; here it takes the runs of word
        characters \\w+

    Arguments:
        n (int): N-gram length in characters
        lowercase (bool): Convert the text to lower case
        within_words (bool): Take N-grams only inside words
        tokenizer (pattern|callable): Word tokenizer for within_words
            or a regular expression

    Methods:
        tokenize: Default word tokenizer
        extract: Extracting N-grams from a text
        get_most_common: Getting a counter of the top N-grams

    Raises:
        ParameterError: If the N-gram length is less than one
    """

    def __init__(
        self,
        n: int = 2,
        lowercase: bool = False,
        within_words: bool = False,
        tokenizer: Tokenizer | None = None,
    ) -> None:
        super().__init__(tokenizer)
        if n < 1:
            raise ParameterError("The N-gram length must be greater than 0")
        self.n = n
        self.lowercase = lowercase
        self.within_words = within_words
        self.ngrams: tuple[str, ...] = ()
        if not self.tokenizer:
            self.tokenizer = self.tokenize

    def tokenize(self, text: str) -> Iterable[str]:
        """
        Splitting a text into words by default

        Arguments:
            text (str): Text string

        Returns:
            iterable[str]: Words
        """
        return WORD_PATTERN.findall(text)

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
        _check_text(text)
        if self.lowercase:
            text = text.lower()
        if self.within_words:
            units = [word for word in self._tokenize(text) if not is_punctuation(word)]
        else:
            units = [" ".join(text.split())]
        self.ngrams = tuple(
            unit[index : index + self.n]
            for unit in units
            for index in range(len(unit) - self.n + 1)
        )
        return self.ngrams

    def get_most_common(self, n: int = 10) -> list[tuple[Any, int]]:
        """
        Getting a counter of the top N-grams

        Arguments:
            n (int): Number of N-grams

        Returns:
            list: List of the top N-grams

        Raises:
            ParameterError: If the number of N-grams is less than 1
        """
        if n < 1:
            raise ParameterError("The number of N-grams must be greater than 0")
        return Counter(self.ngrams).most_common(n)
