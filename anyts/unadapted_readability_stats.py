from __future__ import annotations

from collections.abc import Mapping
from math import log, nan
from typing import TYPE_CHECKING, Any, ClassVar

from .basic_stats import BasicStats
from .constants import (
    EFLAW_MINI_WORD_LETTERS,
    LIX_LONG_WORD_LETTER_FACTOR,
    SMOG_COMPLEX_SYL_FACTOR,
    UNADAPTED_READABILITY_STATS_DESC,
)
from .exceptions import ParameterError
from .readability_stats import _read_basic_stats, _word_letters
from .stats import Stats
from .utils import check_integer, safe_divide

if TYPE_CHECKING:
    from spacy.tokens import Doc

    from .extractors import SentsExtractor, WordsExtractor

# Coefficients of the four Wiener Sachtextformeln over the shares of the words of three
# syllables or more, the sentence length, the shares of the long and the monosyllabic words
_WIENER_COEFFICIENTS = {
    1: (0.1935, 0.1672, 0.1297, -0.0327, -0.875),
    2: (0.2007, 0.1682, 0.1373, 0.0, -2.779),
    3: (0.2963, 0.1905, 0.0, 0.0, -1.1144),
    4: (0.2744, 0.2656, 0.0, 0.0, -1.693),
}


class UnadaptedReadabilityStats(Stats):
    """
    Readability formulas of other languages with their original coefficients

    Description:
        Formulas made for English, German or Italian, computed from the basic
        statistics of a text as they were published (Linsear Write as textstat
        computes it), without a calibration for its language: their values compare texts of one language, not grade
        levels of another. A language library subclasses the class and sets
        basic_stats_class.
        get_stats, to_dataframe, print_stats and describe come from Stats

    Arguments:
        source (str|Doc|BasicStats): Data source - a string, a Doc object or
            a ready object of basic_stats_class to reuse
        sents_extractor (SentsExtractor): Sentence extraction tool, not used for
            ready basic statistics
        words_extractor (WordsExtractor): Word extraction tool, not used for ready
            basic statistics

    Attributes:
        bs (BasicStats): Basic statistics of the text
        forcast (float): FORCAST grade
        linsear_write (float): Linsear Write grade
        powers_sumner_kearl (float): Powers-Sumner-Kearl grade
        eflaw (float): McAlpine EFLAW score
        wiener_sachtextformel_1, ..., wiener_sachtextformel_4 (float): The four Wiener
            Sachtextformeln
        dickes_steiwer (float): Dickes-Steiwer index
        gulpease (float): Gulpease index
        fucks (float): Fucks index
        strain_index (float): Strain index
        elf (float): Easy listening formula
        wheeler_smith (float): Wheeler-Smith index

    Class attributes:
        basic_stats_class (type[BasicStats]): Basic statistics of a string or a Doc;
            without it the source must be a BasicStats object
        complex_syl_factor (int): Minimum number of syllables of a hard word
            (SMOG_COMPLEX_SYL_FACTOR)
        long_word_letter_factor (int): Minimum number of letters of a long word of the
            Wiener Sachtextformeln (LIX_LONG_WORD_LETTER_FACTOR)
        mini_word_letters (int): Largest number of letters of a mini word of EFLAW
            (EFLAW_MINI_WORD_LETTERS)
        stats_desc (dict[str, str]): Metrics of get_stats and their descriptions for
            print_stats
        stats_headers (tuple[str, str]): Headers of the columns for print_stats

    Raises:
        SourceTypeError: If the source is neither a string, a Doc nor a BasicStats object,
            the basic statistics are of another class, an extractor is of another type,
            or a class without basic_stats_class is given a string or a Doc
        SourceError: If the source has no words or no sentences
    """

    basic_stats_class: ClassVar[type[BasicStats] | None] = None
    complex_syl_factor: ClassVar[int] = SMOG_COMPLEX_SYL_FACTOR
    long_word_letter_factor: ClassVar[int] = LIX_LONG_WORD_LETTER_FACTOR
    mini_word_letters: ClassVar[int] = EFLAW_MINI_WORD_LETTERS
    stats_desc: ClassVar[Mapping[str, str]] = UNADAPTED_READABILITY_STATS_DESC
    stats_headers: ClassVar[tuple[str, str]] = ("Metric", "Value")

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        for attribute in ("complex_syl_factor", "long_word_letter_factor", "mini_word_letters"):
            value = getattr(cls, attribute)
            check_integer(value, f"{attribute} of {cls.__name__}")
            if value < 1:
                raise ParameterError(
                    f"The {attribute} of {cls.__name__} must be greater than 0, not {value}"
                )
        basic = cls.basic_stats_class
        if basic is not None and not (isinstance(basic, type) and issubclass(basic, BasicStats)):
            raise ParameterError(
                f"The basic_stats_class of {cls.__name__} must be a subclass of BasicStats "
                f"or None, not {basic!r}"
            )

    def __init__(
        self,
        source: str | Doc | BasicStats,
        sents_extractor: SentsExtractor | None = None,
        words_extractor: WordsExtractor | None = None,
    ):
        self.bs = _read_basic_stats(
            self, source, self.basic_stats_class, sents_extractor, words_extractor
        )

    @property
    def forcast(self) -> float:
        return calc_forcast(self.bs.n_monosyllable_words, self.bs.n_words)

    @property
    def linsear_write(self) -> float:
        n_hard = self.bs.count_words_by_syllables(self.complex_syl_factor)
        n_easy = self.bs.count_words_by_syllables(1) - n_hard
        return calc_linsear_write(n_easy, n_hard, self.bs.n_sents)

    @property
    def powers_sumner_kearl(self) -> float:
        return calc_powers_sumner_kearl(self.bs.n_syllables, self.bs.n_words, self.bs.n_sents)

    @property
    def eflaw(self) -> float:
        n_mini = sum(
            count
            for letters, count in self.bs.c_letters.items()
            if 0 < letters <= self.mini_word_letters
        )
        return calc_eflaw(n_mini, self.bs.n_words, self.bs.n_sents)

    def _wiener(self, variant: int) -> float:
        return calc_wiener_sachtextformel(
            self.bs.count_words_by_syllables(self.complex_syl_factor),
            self.bs.count_words_by_letters(self.long_word_letter_factor),
            self.bs.n_monosyllable_words,
            self.bs.n_words,
            self.bs.n_sents,
            variant,
        )

    @property
    def wiener_sachtextformel_1(self) -> float:
        return self._wiener(1)

    @property
    def wiener_sachtextformel_2(self) -> float:
        return self._wiener(2)

    @property
    def wiener_sachtextformel_3(self) -> float:
        return self._wiener(3)

    @property
    def wiener_sachtextformel_4(self) -> float:
        return self._wiener(4)

    @property
    def dickes_steiwer(self) -> float:
        return calc_dickes_steiwer(
            _word_letters(self.bs), self.bs.n_words, self.bs.n_sents, self.bs.n_unique_words
        )

    @property
    def gulpease(self) -> float:
        return calc_gulpease(_word_letters(self.bs), self.bs.n_words, self.bs.n_sents)

    @property
    def fucks(self) -> float:
        return calc_fucks(self.bs.n_syllables, self.bs.n_sents)

    @property
    def strain_index(self) -> float:
        return calc_strain_index(self.bs.n_syllables, self.bs.n_sents)

    @property
    def elf(self) -> float:
        return calc_elf(self.bs.n_syllables, self.bs.count_words_by_syllables(1), self.bs.n_sents)

    @property
    def wheeler_smith(self) -> float:
        return calc_wheeler_smith(self.bs.count_words_by_syllables(2), self.bs.n_sents)


def calc_forcast(n_monosyllable_words: int, n_words: int) -> float:
    """
    Computing the FORCAST grade

    Description:
        Caylor et al. (1973), for technical texts: 20 minus a tenth of the
        monosyllabic words per 150 words, from 5 (every word monosyllabic) to 20

    Arguments:
        n_monosyllable_words (int): Number of monosyllabic words
        n_words (int): Number of words

    Returns:
        float: Grade level, nan without words

    Raises:
        ParameterError: If a count is not an integer or is negative, or there
            are more monosyllabic words than words

    Example:
        >>> from anyts.unadapted_readability_stats import calc_forcast
        >>> calc_forcast(100, 150)
        10.0
    """
    _check_counts(
        (n_monosyllable_words, "number of monosyllabic words"),
        (n_words, "number of words"),
    )
    if n_monosyllable_words > n_words:
        raise ParameterError("The monosyllabic words cannot outnumber the words")
    return safe_divide(20 * n_words - 15 * n_monosyllable_words, n_words, nan)


def _check_counts(*counts: tuple[int, str]) -> None:
    """Checking that the counts of a formula are integers, not negative"""
    for count, what in counts:
        check_integer(count, what)
        if count < 0:
            raise ParameterError(f"The {what} cannot be negative")


def calc_linsear_write(n_easy_words: int, n_hard_words: int, n_sents: int) -> float:
    """
    Computing the Linsear Write grade

    Description:
        In the form of textstat, not the Lensear Write Formula of O'Hayre (1966)
        of the monosyllabic words and the sentences: an easy word, of one or two
        syllables, weighs 1, a hard one of three syllables or more weighs 3;
        their sum over the sentences, halved above 20, else less 2 and halved.
        Over the whole text, not over a sample of 100 words

    Arguments:
        n_easy_words (int): Number of the words of one or two syllables
        n_hard_words (int): Number of the words of three syllables or more
        n_sents (int): Number of sentences

    Returns:
        float: Grade level, nan without sentences

    Raises:
        ParameterError: If a count is not an integer or is negative

    Example:
        >>> from anyts.unadapted_readability_stats import calc_linsear_write
        >>> calc_linsear_write(80, 20, 5)
        14.0
    """
    _check_counts(
        (n_easy_words, "number of easy words"),
        (n_hard_words, "number of hard words"),
        (n_sents, "number of sentences"),
    )
    score = safe_divide(n_easy_words + 3 * n_hard_words, n_sents, nan)
    return score / 2 if score > 20 else (score - 2) / 2


def calc_powers_sumner_kearl(n_syllables: int, n_words: int, n_sents: int) -> float:
    """
    Computing the Powers-Sumner-Kearl grade

    Description:
        The recalculation of the Flesch formula by Powers, Sumner and Kearl
        (1958) as a grade level, for primary school texts

    Arguments:
        n_syllables (int): Number of syllables
        n_words (int): Number of words
        n_sents (int): Number of sentences

    Returns:
        float: Grade level, nan without words or sentences

    Raises:
        ParameterError: If a count is not an integer or is negative

    Example:
        >>> from anyts.unadapted_readability_stats import calc_powers_sumner_kearl
        >>> round(calc_powers_sumner_kearl(130, 100, 10), 4)
        4.4901
    """
    _check_counts(
        (n_syllables, "number of syllables"),
        (n_words, "number of words"),
        (n_sents, "number of sentences"),
    )
    if not n_words or not n_sents:
        return nan
    return 0.0778 * n_words / n_sents + 4.55 * n_syllables / n_words - 2.2029


def calc_eflaw(n_mini_words: int, n_words: int, n_sents: int) -> float:
    """
    Computing the McAlpine EFLAW score

    Description:
        McAlpine (2005), for readers of English as a foreign language: the words
        and the mini words, of one to three letters, per sentence; 20 and below
        is very easy, 30 and above confusing

    Arguments:
        n_mini_words (int): Number of the words of one to three letters
        n_words (int): Number of words
        n_sents (int): Number of sentences

    Returns:
        float: Score, nan without sentences

    Raises:
        ParameterError: If a count is not an integer or is negative

    Example:
        >>> from anyts.unadapted_readability_stats import calc_eflaw
        >>> calc_eflaw(40, 100, 5)
        28.0
    """
    _check_counts(
        (n_mini_words, "number of mini words"),
        (n_words, "number of words"),
        (n_sents, "number of sentences"),
    )
    return safe_divide(n_words + n_mini_words, n_sents, nan)


def calc_wiener_sachtextformel(
    n_complex: int,
    n_long_words: int,
    n_monosyllable_words: int,
    n_words: int,
    n_sents: int,
    variant: int = 1,
) -> float:
    """
    Computing a Wiener Sachtextformel

    Description:
        Bamberger and Vanecek (1984), for German non-fiction, a grade from 4 to
        15: over the percentages of the words of three syllables or more (MS),
        of more than six letters (IW) and of one syllable (ES) and the mean
        sentence length (SL), in four variants
        1: 0.1935·MS + 0.1672·SL + 0.1297·IW − 0.0327·ES − 0.875
        2: 0.2007·MS + 0.1682·SL + 0.1373·IW − 2.779
        3: 0.2963·MS + 0.1905·SL − 1.1144
        4: 0.2744·MS + 0.2656·SL − 1.693

    Arguments:
        n_complex (int): Number of the words of three syllables or more
        n_long_words (int): Number of the words of more than six letters
        n_monosyllable_words (int): Number of monosyllabic words
        n_words (int): Number of words
        n_sents (int): Number of sentences
        variant (int): Variant of the formula, from 1 to 4

    Returns:
        float: Grade, nan without words or sentences

    Raises:
        ParameterError: If a count is not an integer or is negative, or the variant is
            not an integer from 1 to 4

    Example:
        >>> from anyts.unadapted_readability_stats import calc_wiener_sachtextformel
        >>> round(calc_wiener_sachtextformel(20, 30, 50, 100, 8), 4)
        7.341
    """
    check_integer(variant, "variant of the Wiener Sachtextformel")
    if variant not in _WIENER_COEFFICIENTS:
        raise ParameterError(
            f"The variant of the Wiener Sachtextformel must be from 1 to 4, not {variant}"
        )
    _check_counts(
        (n_complex, "number of complex words"),
        (n_long_words, "number of long words"),
        (n_monosyllable_words, "number of monosyllabic words"),
        (n_words, "number of words"),
        (n_sents, "number of sentences"),
    )
    if not n_words or not n_sents:
        return nan
    ms, sl, iw, es, constant = _WIENER_COEFFICIENTS[variant]
    return (
        ms * 100 * n_complex / n_words
        + sl * n_words / n_sents
        + iw * 100 * n_long_words / n_words
        + es * 100 * n_monosyllable_words / n_words
        + constant
    )


def calc_dickes_steiwer(n_letters: int, n_words: int, n_sents: int, n_types: int) -> float:
    """
    Computing the Dickes-Steiwer index

    Description:
        The short formula of Dickes and Steiwer (1977) for German, as Bamberger
        and Vanecek (1984) give it, over the letters per word, the words per
        sentence and the type-token ratio, without syllables; higher is easier
        235.95993 − 73.021·ln(letters / words + 1) − 12.56438·ln(words / sentences + 1)
        − 50.03293·types / words

    Arguments:
        n_letters (int): Number of the letters of the words
        n_words (int): Number of words
        n_sents (int): Number of sentences
        n_types (int): Number of the distinct words

    Returns:
        float: Index, nan without words or sentences

    Raises:
        ParameterError: If a count is not an integer or is negative

    Example:
        >>> from anyts.unadapted_readability_stats import calc_dickes_steiwer
        >>> round(calc_dickes_steiwer(500, 100, 8, 60), 2)
        42.4
    """
    _check_counts(
        (n_letters, "number of letters"),
        (n_words, "number of words"),
        (n_sents, "number of sentences"),
        (n_types, "number of distinct words"),
    )
    if not n_words or not n_sents:
        return nan
    return (
        235.95993
        - 73.021 * log(n_letters / n_words + 1)
        - 12.56438 * log(n_words / n_sents + 1)
        - 50.03293 * n_types / n_words
    )


def calc_gulpease(n_letters: int, n_words: int, n_sents: int) -> float:
    """
    Computing the Gulpease index

    Description:
        Lucisano and Piemontese (1988), for Italian: by letters, not syllables,
        about 0 for the hardest texts and 100 for the easiest; below 80 is hard
        for a reader of primary school, below 40 for a reader with a secondary
        education

    Arguments:
        n_letters (int): Number of the letters of the words
        n_words (int): Number of words
        n_sents (int): Number of sentences

    Returns:
        float: Index, nan without words

    Raises:
        ParameterError: If a count is not an integer or is negative

    Example:
        >>> from anyts.unadapted_readability_stats import calc_gulpease
        >>> calc_gulpease(500, 100, 8)
        63.0
    """
    _check_counts(
        (n_letters, "number of letters"),
        (n_words, "number of words"),
        (n_sents, "number of sentences"),
    )
    return safe_divide(89 * n_words + 300 * n_sents - 10 * n_letters, n_words, nan)


def calc_fucks(n_syllables: int, n_sents: int) -> float:
    """
    Computing the Fucks index

    Description:
        The style characteristic of Fucks (1955): the mean word length in
        syllables times the mean sentence length in words, the syllables per
        sentence

    Arguments:
        n_syllables (int): Number of syllables
        n_sents (int): Number of sentences

    Returns:
        float: Index, nan without sentences

    Raises:
        ParameterError: If a count is not an integer or is negative

    Example:
        >>> from anyts.unadapted_readability_stats import calc_fucks
        >>> calc_fucks(150, 10)
        15.0
    """
    _check_counts(
        (n_syllables, "number of syllables"),
        (n_sents, "number of sentences"),
    )
    return safe_divide(n_syllables, n_sents, nan)


def calc_strain_index(n_syllables: int, n_sents: int) -> float:
    """
    Computing the Strain index

    Description:
        Nathaniel (2009): the syllables of three sentences over 10, here the
        syllables of three sentences on average over the text

    Arguments:
        n_syllables (int): Number of syllables
        n_sents (int): Number of sentences

    Returns:
        float: Index, nan without sentences

    Raises:
        ParameterError: If a count is not an integer or is negative

    Example:
        >>> from anyts.unadapted_readability_stats import calc_strain_index
        >>> calc_strain_index(150, 10)
        4.5
    """
    _check_counts(
        (n_syllables, "number of syllables"),
        (n_sents, "number of sentences"),
    )
    return safe_divide(3 * n_syllables, 10 * n_sents, nan)


def calc_elf(n_syllables: int, n_syllabic_words: int, n_sents: int) -> float:
    """
    Computing the easy listening formula (ELF)

    Description:
        Fang (1966), for texts read aloud: the syllables above one per word, per
        sentence; a word without syllables (a number) adds none. 12 and below is
        easy to listen to

    Arguments:
        n_syllables (int): Number of syllables
        n_syllabic_words (int): Number of the words of one syllable or more
        n_sents (int): Number of sentences

    Returns:
        float: Score, nan without sentences

    Raises:
        ParameterError: If a count is not an integer or is negative

    Example:
        >>> from anyts.unadapted_readability_stats import calc_elf
        >>> calc_elf(150, 100, 10)
        5.0
    """
    _check_counts(
        (n_syllables, "number of syllables"),
        (n_syllabic_words, "number of words with syllables"),
        (n_sents, "number of sentences"),
    )
    return safe_divide(n_syllables - n_syllabic_words, n_sents, nan)


def calc_wheeler_smith(n_polysyllable_words: int, n_sents: int) -> float:
    """
    Computing the Wheeler-Smith index

    Description:
        Wheeler and Smith (1954), for primary school texts: the mean sentence
        length times the share of the words of two syllables or more, times 10,
        that is 10 such words per sentence

    Arguments:
        n_polysyllable_words (int): Number of the words of two syllables or more
        n_sents (int): Number of sentences

    Returns:
        float: Index, nan without sentences

    Raises:
        ParameterError: If a count is not an integer or is negative

    Example:
        >>> from anyts.unadapted_readability_stats import calc_wheeler_smith
        >>> calc_wheeler_smith(40, 10)
        40.0
    """
    _check_counts(
        (n_polysyllable_words, "number of polysyllabic words"),
        (n_sents, "number of sentences"),
    )
    return safe_divide(10 * n_polysyllable_words, n_sents, nan)
