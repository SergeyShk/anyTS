from __future__ import annotations

from abc import ABCMeta, abstractmethod
from collections.abc import Iterable, Sequence
from functools import cached_property
from math import log2, log10, nan
from numbers import Integral
from re import Pattern
from statistics import fmean
from typing import TYPE_CHECKING, Any, ClassVar, NamedTuple, Protocol

from .constants import FREQUENCY_BANDS, LEXICAL_STATS_DESC
from .exceptions import ParameterError, SourceError, SourceTypeError
from .extractors import NUMBER_PATTERN
from .stats import Stats
from .utils import check_words, safe_divide

if TYPE_CHECKING:
    from spacy.tokens import Doc


class FrequencyEntry(Protocol):
    """Entry of a frequency dictionary: the frequency, the range and the dispersion of a lemma"""

    @property
    def ipm(self) -> float: ...

    @property
    def range(self) -> float: ...

    @property
    def dispersion(self) -> float: ...


class FrequencyDictionary(Protocol):
    """Frequency dictionary of lemmas: their entries, frequencies and the lowest frequency"""

    @property
    def min_ipm(self) -> float: ...

    def lookup(self, lemma: str) -> FrequencyEntry | None: ...

    def ipm(self, lemma: str) -> float: ...


class LexicalWord(NamedTuple):
    """
    Word of a text for the lexical sophistication

    Attributes:
        word (str): Word as the text writes it
        lemma (str): Lemma of the word, by which its rank is found
        content (bool): Whether the word is a content word
    """

    word: str
    lemma: str
    content: bool


def is_number(word: str, pattern: Pattern[str] = NUMBER_PATTERN) -> bool:
    """
    Checking whether a word is a number

    Arguments:
        word (str): Word
        pattern (Pattern): Number of a language, matched against the whole lower-cased word;
            NUMBER_PATTERN of the extractors by default

    Returns:
        bool: Result of the check

    Example:
        >>> from anyts.lexical_stats import is_number
        >>> is_number("2020"), is_number("10%"), is_number("cat")
        (True, True, False)
    """
    return pattern.fullmatch(word.lower()) is not None


def _mean(values: Sequence[float]) -> float:
    return fmean(values) if values else nan


def calc_surprisal(lemmas: Sequence[str], freq_dict: FrequencyDictionary) -> float:
    """
    Computing the mean surprisal of the words by the unigram model of a frequency dictionary

    Description:
        The mean over the words of -log2 P(w), where P(w) = ipm / 10^6; a word
        out of the dictionary gets its lowest frequency (min_ipm), so every
        word has a surprisal. The perplexity is 2 to the power of the surprisal

    Arguments:
        lemmas (list[str]): Keys of the words in the dictionary
        freq_dict (FrequencyDictionary): Frequency dictionary with ipm and min_ipm

    Returns:
        float: Mean surprisal in bits, nan for no words

    Raises:
        SourceTypeError: If the lemmas are not a list of strings or the dictionary has
            no ipm and min_ipm
    """
    check_words(lemmas)
    if not callable(getattr(freq_dict, "ipm", None)) or not hasattr(freq_dict, "min_ipm"):
        raise SourceTypeError(
            f"The frequency dictionary must have ipm and min_ipm, not {type(freq_dict).__name__}"
        )
    floor = freq_dict.min_ipm
    return _mean([-log2(max(freq_dict.ipm(lemma), floor) / 1_000_000) for lemma in lemmas])


class LexicalStats(Stats, metaclass=ABCMeta):
    """
    Base of the lexical sophistication statistics of a text

    Description:
        Lexical sophistication in the manner of TAALES - how rare the words of a
        text are in the language: the mean frequency, range and dispersion of
        the words by a frequency dictionary, the surprisal and the perplexity by
        its unigram model, the shares of the frequency bands of a list of the
        most frequent lemmas and the lexical density. A language library
        subclasses the class and implements analyze - the words of a source
        with their lemmas and whether they are content words - and sets the
        dictionary, the keys of the words in it and the ranks of the lemmas.
        The statistics by the dictionary are computed when first read.
        get_stats, to_dataframe, print_stats and describe come from Stats

    Arguments:
        source (str|Doc): Data source (a string or a Doc object)
        freq_dict (FrequencyDictionary): Frequency dictionary; freq_dict_class() by
            default

    Attributes:
        freq_dict (FrequencyDictionary): Frequency dictionary
        words (tuple[str]): Words
        lemmas (tuple[str]): Lemmas of the words; the bands are counted by them
        keys (tuple[str]): Keys of the words in the frequency dictionary
        entries (tuple[FrequencyEntry|None]): Entries of the dictionary, None for a
            word out of it
        ranks (tuple[int|None]): Ranks of the lemmas, None out of the list
        n_words (int): Number of words
        n_content_words (int): Number of content words
        n_found (int): Number of words found in the frequency dictionary
        coverage (float): Share of words found in the frequency dictionary
        mean_ipm (float): Mean frequency of the words found
        mean_ipm_content (float): Mean frequency of the content words found
        mean_log_ipm (float): Mean decimal logarithm of the frequency of the words found
        mean_log_ipm_content (float): The same over the content words
        mean_range (float): Mean range of the words found
        mean_dispersion (float): Mean dispersion of the words found
        surprisal (float): Mean surprisal of the words, in bits
        perplexity (float): Unigram perplexity - 2 to the power of the surprisal
        p_top1000 (float): Share of words with a lemma of the top 1000
        p_top2000 (float): Share of words with a lemma of the top 2000
        p_top5000 (float): Share of words with a lemma of the top 5000
        p_top10000 (float): Share of words with a lemma of the top 10000
        p_beyond_top10000 (float): Share of words with a lemma beyond the top 10000
        lexical_density (float): Share of content words

    Methods:
        analyze: Words of a source with their lemmas and their kind
        dictionary_keys: Keys of the words in the frequency dictionary
        rank: Rank of a lemma in the list of the most frequent lemmas
        top_size: Size of the list of the most frequent lemmas
        band_coverage: Shares of the words or of the lemmas by frequency bands

    Class attributes:
        freq_dict_class (type): Class of the frequency dictionary, made without
            arguments when none is given; its instances are the only ones taken
        stats_desc (dict[str, str]): Statistics of get_stats and their descriptions for
            print_stats

    Raises:
        SourceTypeError: If the dictionary is not of freq_dict_class, or the class has
            none and no dictionary is given
        SourceError: If the source has no words
    """

    freq_dict_class: ClassVar[type[Any] | None] = None
    stats_desc: ClassVar[dict[str, str]] = LEXICAL_STATS_DESC

    def __init__(self, source: str | Doc, freq_dict: FrequencyDictionary | None = None):
        messages = self.messages
        expected = self.freq_dict_class
        if freq_dict is not None and expected is not None and not isinstance(freq_dict, expected):
            raise SourceTypeError(messages["freq_dict_type"].format(expected=expected.__name__))
        words = tuple(self.analyze(source))
        if not words:
            raise SourceError(messages["no_words"])
        if freq_dict is None:
            if expected is None:
                raise SourceTypeError(
                    messages["no_freq_dict_class"].format(cls=type(self).__name__)
                )
            freq_dict = expected()
        self.freq_dict = freq_dict
        self.words = tuple(word.word for word in words)
        self.lemmas = tuple(word.lemma for word in words)
        self._content = tuple(word.content for word in words)
        self.n_words = len(self.words)
        self.n_content_words = sum(self._content)
        self.ranks = tuple(self.rank(lemma) for lemma in self.lemmas)
        self.lexical_density = self.n_content_words / self.n_words
        bands = self.band_coverage(FREQUENCY_BANDS)
        self.p_top1000 = bands[1000]
        self.p_top2000 = bands[2000]
        self.p_top5000 = bands[5000]
        self.p_top10000 = bands[10000]
        self.p_beyond_top10000 = 1 - bands[10000]

    @abstractmethod
    def analyze(self, source: str | Doc) -> Iterable[LexicalWord]:
        """
        Getting the words of a source with their lemmas and their kind

        Description:
            The lemmas and the parts of speech depend on the language, so a
            language library implements the method; the numbers (is_number) are
            not words. A source of another type raises SourceTypeError

        Arguments:
            source (str|Doc): Data source

        Returns:
            iterable[LexicalWord]: Word, lemma and whether it is a content word
        """
        raise NotImplementedError

    def dictionary_keys(self) -> tuple[str, ...]:
        """
        Getting the keys of the words in the frequency dictionary

        Description:
            The lemmas by default; a library looks a word up otherwise, such as
            a proper noun by its form

        Returns:
            tuple[str]: Key of every word
        """
        return self.lemmas

    def rank(self, lemma: str) -> int | None:
        """
        Getting the rank of a lemma in the list of the most frequent lemmas

        Arguments:
            lemma (str): Lemma

        Returns:
            int|None: Rank from 1, None out of the list; without a list None
        """
        return None

    def top_size(self) -> int:
        """
        Getting the size of the list of the most frequent lemmas

        Returns:
            int: The last rank of the list, the bound of the largest band by default
        """
        return max(FREQUENCY_BANDS)

    @cached_property
    def keys(self) -> tuple[str, ...]:
        return self.dictionary_keys()

    @cached_property
    def entries(self) -> tuple[FrequencyEntry | None, ...]:
        return tuple(self.freq_dict.lookup(key) for key in self.keys)

    @property
    def n_found(self) -> int:
        return sum(1 for entry in self.entries if entry)

    @property
    def coverage(self) -> float:
        return self.n_found / self.n_words

    @property
    def mean_ipm(self) -> float:
        return _mean([entry.ipm for entry in self.entries if entry])

    @property
    def mean_ipm_content(self) -> float:
        return _mean([entry.ipm for entry in self._content_entries()])

    @property
    def mean_log_ipm(self) -> float:
        return _mean([log10(entry.ipm) for entry in self.entries if entry])

    @property
    def mean_log_ipm_content(self) -> float:
        return _mean([log10(entry.ipm) for entry in self._content_entries()])

    @property
    def mean_range(self) -> float:
        return _mean([entry.range for entry in self.entries if entry])

    @property
    def mean_dispersion(self) -> float:
        return _mean([entry.dispersion for entry in self.entries if entry])

    @cached_property
    def surprisal(self) -> float:
        return calc_surprisal(self.keys, self.freq_dict)

    @property
    def perplexity(self) -> float:
        return float(2**self.surprisal)

    def _content_entries(self) -> list[FrequencyEntry]:
        """Entries of the content words found in the dictionary"""
        return [
            entry
            for entry, content in zip(self.entries, self._content, strict=True)
            if entry and content
        ]

    def band_coverage(
        self, bands: Iterable[int] = FREQUENCY_BANDS, unique: bool = False
    ) -> dict[int, float]:
        """
        Getting the shares of the words by the frequency bands of the list

        Arguments:
            bands (list[int]): Bounds of the bands - the sizes of the top lists
            unique (bool): Count the distinct lemmas instead of the words

        Returns:
            dict[int, float]: Share of the words with a lemma of the top N for every bound N

        Raises:
            ParameterError: If the bounds are not a list of integers, or a bound is out
                of 1 and top_size
        """
        messages = self.messages
        if isinstance(bands, str | bytes) or not isinstance(bands, Iterable):
            raise ParameterError(messages["bands_type"].format(type=type(bands).__name__))
        bands = tuple(bands)
        size = self.top_size()
        for band in bands:
            value: object = band
            if isinstance(value, bool) or not isinstance(value, Integral) or not 1 <= band <= size:
                raise ParameterError(messages["band_bound"].format(size=size, band=repr(band)))
        ranks = [self.rank(lemma) for lemma in set(self.lemmas)] if unique else list(self.ranks)
        return {
            band: safe_divide(sum(1 for rank in ranks if rank and rank <= band), len(ranks))
            for band in bands
        }
