from collections.abc import Callable, Iterable, Mapping
from math import floor, nan, sqrt
from statistics import median
from typing import ClassVar, TypeVar

from spacy.tokens import Doc

from .basic_stats import BasicStats, _check_extractors
from .constants import (
    GRADE_AGE_LEVELS,
    LIX_LEVELS,
    LIX_LONG_WORD_LETTER_FACTOR,
    POSTGRADUATE_LEVEL,
    READABILITY_GRADE_STATS,
    READABILITY_PRESETS,
    READABILITY_STATS_DESC,
    READING_EASE_GRADES,
    READING_EASE_LEVELS,
    READING_SPEED_NORMS,
    READING_SPEED_WPM,
    RIX_GRADES,
    SMOG_COMPLEX_SYL_FACTOR,
)
from .exceptions import ParameterError, SourceError, SourceTypeError, UnknownStatError
from .extractors import SentsExtractor, WordsExtractor
from .utils import check_number, safe_divide

Band = TypeVar("Band")


class ReadabilityStats:
    """
    Base of the readability metrics of a text

    Description:
        The common readability formulas over the basic statistics of a text,
        the consensus grade, the school stage and age of the reader and the
        reading time; the metrics are properties, computed on each access.
        A language library subclasses the class, sets its class attributes
        and may override reading_ease_to_grade; its own formulas are
        properties named in stats_desc. The defaults are the original English
        formulas

    Arguments:
        source (str|Doc|BasicStats): Data source - a string, a Doc object or
            a ready object of basic_stats_class to reuse
        sents_extractor (SentsExtractor): Sentence extraction tool, not used for
            ready basic statistics
        words_extractor (WordsExtractor): Word extraction tool, not used for ready
            basic statistics
        preset (str): Coefficient preset

    Attributes:
        bs (BasicStats): Basic statistics of the text
        preset (str): Name of the coefficient preset
        coefficients (dict[str, tuple[float, ...]]): Coefficients of the preset by
            formula, a copy that can be changed for one object; a formula missing
            from it takes the defaults of its function
        flesch_reading_easy (float): Flesch reading ease
        flesch_kincaid_grade (float): Flesch-Kincaid grade
        coleman_liau_index (float): Coleman-Liau index
        automated_readability_index (float): Automated readability index
        smog_index (float): SMOG index
        gunning_fog_index (float): Gunning fog index
        lix (float): LIX readability index
        rix (float): RIX readability index
        mu_index (float): Legibilidad µ
        consensus_grade (float): Consensus grade over the grade formulas and the reading ease
        reading_time (float): Reading time in minutes at the reading speed

    Methods:
        reading_ease_to_grade: Years of schooling for a value of the reading ease
        describe_grade: School stage and reader age for the consensus grade or a grade formula
        describe_level: Band of the interpretation scale of a metric
        describe: Reading of any metric by its scale
        reading_time_by_speed: Reading time at a given speed
        reading_time_by_norm: Reading times at the speeds of a norm
        get_stats: Getting the computed readability metrics of the text
        print_stats: Printing the computed readability metrics with descriptions

    Class attributes:
        basic_stats_class (type[BasicStats]): Basic statistics of a string or a Doc;
            without it the source must be a BasicStats object
        presets (dict[str, dict[str, tuple[float, ...]]]): Coefficients of the formulas
            by preset
        grade_stats (tuple[str, ...]): Grade formulas of the consensus grade
        stats_desc (dict[str, str]): Metrics of get_stats and their descriptions for
            print_stats
        stats_headers (tuple[str, str]): Headers of the columns for print_stats
        smog_complex_syl_factor (int): Minimum number of syllables in a polysyllabic word
            of SMOG and Gunning fog
        lix_long_word_letter_factor (int): Minimum number of letters in a long word of
            LIX and RIX
        grade_age_levels (tuple[tuple[int, int, str, str], ...]): School stages of
            describe_grade (grade_to_age)
        level_scales (dict[str, tuple[tuple[float, str], ...]]): Interpretation scales
            of describe_level by metric, as lower bounds and their bands
        grade_scales (dict[str, tuple[tuple[float, float], ...]]): Scales that convert
            a metric into years of schooling for describe, as lower bounds and grades
        postgraduate_level (tuple[str, str]): Stage and age above the last school stage
        reading_speed (float): Reading speed of reading_time, words per minute
        reading_speed_norms (dict[str, tuple[float, ...]]): Speeds of the reading norms,
            words per minute

    Raises:
        SourceTypeError: If the source is neither a string, a Doc nor a BasicStats object,
            the basic statistics are of another class, an extractor is of another type,
            or a class without basic_stats_class is given a string or a Doc
        SourceError: If the source has no words or no sentences
        ParameterError: If the coefficient preset is not a string or is unknown
    """

    basic_stats_class: ClassVar[type[BasicStats] | None] = None
    presets: ClassVar[Mapping[str, Mapping[str, tuple[float, ...]]]] = READABILITY_PRESETS
    grade_stats: ClassVar[tuple[str, ...]] = READABILITY_GRADE_STATS
    stats_desc: ClassVar[Mapping[str, str]] = READABILITY_STATS_DESC
    stats_headers: ClassVar[tuple[str, str]] = ("Metric", "Value")
    smog_complex_syl_factor: ClassVar[int] = SMOG_COMPLEX_SYL_FACTOR
    lix_long_word_letter_factor: ClassVar[int] = LIX_LONG_WORD_LETTER_FACTOR
    grade_age_levels: ClassVar[tuple[tuple[int, int, str, str], ...]] = GRADE_AGE_LEVELS
    level_scales: ClassVar[Mapping[str, tuple[tuple[float, str], ...]]] = {
        "flesch_reading_easy": READING_EASE_LEVELS,
        "lix": LIX_LEVELS,
    }
    grade_scales: ClassVar[Mapping[str, tuple[tuple[float, float], ...]]] = {"rix": RIX_GRADES}
    postgraduate_level: ClassVar[tuple[str, str]] = POSTGRADUATE_LEVEL
    reading_speed: ClassVar[float] = READING_SPEED_WPM
    reading_speed_norms: ClassVar[Mapping[str, tuple[float, ...]]] = READING_SPEED_NORMS

    def __init__(
        self,
        source: str | Doc | BasicStats,
        sents_extractor: SentsExtractor | None = None,
        words_extractor: WordsExtractor | None = None,
        preset: str = "original",
    ):
        if not isinstance(preset, str):
            raise ParameterError(f"The preset must be a string, not {type(preset).__name__}")
        if preset not in self.presets:
            raise ParameterError(
                f"Unknown coefficient preset: {preset}. Available presets: {tuple(self.presets)}"
            )
        self.preset = preset
        self.coefficients = dict(self.presets[preset])
        _check_extractors(sents_extractor, words_extractor)
        if isinstance(source, BasicStats):
            expected = self.basic_stats_class or BasicStats
            if not isinstance(source, expected):
                raise SourceTypeError(
                    f"The basic statistics must be a {expected.__name__} object, "
                    f"not {type(source).__name__}"
                )
            self.bs = source
        elif self.basic_stats_class is None:
            raise SourceTypeError(
                f"{type(self).__name__} has no basic_stats_class, the data source must be "
                "a BasicStats object"
            )
        else:
            self.bs = self.basic_stats_class(source, sents_extractor, words_extractor)
        if not self.bs.n_sents:
            raise SourceError("The data source has no sentences")

    @property
    def flesch_reading_easy(self) -> float:
        return calc_flesch_reading_easy(
            self.bs.n_syllables,
            self.bs.n_words,
            self.bs.n_sents,
            *self.coefficients.get("flesch_reading_easy", ()),
        )

    @property
    def flesch_kincaid_grade(self) -> float:
        return calc_flesch_kincaid_grade(
            self.bs.n_syllables,
            self.bs.n_words,
            self.bs.n_sents,
            *self.coefficients.get("flesch_kincaid_grade", ()),
        )

    @property
    def coleman_liau_index(self) -> float:
        return calc_coleman_liau_index(
            _word_letters(self.bs),
            self.bs.n_words,
            self.bs.n_sents,
            *self.coefficients.get("coleman_liau_index", ()),
        )

    @property
    def automated_readability_index(self) -> float:
        return calc_automated_readability_index(
            _word_letters(self.bs),
            self.bs.n_words,
            self.bs.n_sents,
            *self.coefficients.get("automated_readability_index", ()),
        )

    @property
    def smog_index(self) -> float:
        return calc_smog_index(
            self.bs.count_words_by_syllables(self.smog_complex_syl_factor),
            self.bs.n_sents,
            *self.coefficients.get("smog_index", ()),
        )

    @property
    def gunning_fog_index(self) -> float:
        return calc_gunning_fog_index(
            self.bs.count_words_by_syllables(self.smog_complex_syl_factor),
            self.bs.n_words,
            self.bs.n_sents,
            *self.coefficients.get("gunning_fog_index", ()),
        )

    @property
    def lix(self) -> float:
        return calc_lix(
            self.bs.count_words_by_letters(self.lix_long_word_letter_factor),
            self.bs.n_words,
            self.bs.n_sents,
        )

    @property
    def rix(self) -> float:
        return calc_rix(
            self.bs.count_words_by_letters(self.lix_long_word_letter_factor), self.bs.n_sents
        )

    @property
    def mu_index(self) -> float:
        return calc_mu_index(self.bs.c_letters)

    @property
    def consensus_grade(self) -> float:
        grades = [getattr(self, stat) for stat in self.grade_stats]
        return calc_consensus_grade(grades, self.flesch_reading_easy, self.reading_ease_to_grade)

    @property
    def reading_time(self) -> float:
        return calc_reading_time(self.bs.n_words, self.reading_speed)

    def reading_ease_to_grade(self, flesch_reading_easy: float) -> float:
        """
        Converting the Flesch reading ease into years of schooling

        Description:
            Used for the consensus grade; by default flesch_reading_easy_to_grade
            with its bands

        Arguments:
            flesch_reading_easy (float): Value of the reading ease

        Returns:
            float: Years of schooling
        """
        return flesch_reading_easy_to_grade(flesch_reading_easy)

    def describe_grade(self, stat: str = "consensus_grade") -> str:
        """
        Getting the school stage and reader age by the value of a grade formula

        Arguments:
            stat (str): Name of the grade formula, the consensus grade by default

        Returns:
            str: School stage and reader age

        Raises:
            ParameterError: If the metric is not a grade formula
        """
        grade_stats = ("consensus_grade", *self.grade_stats)
        if stat not in grade_stats:
            raise ParameterError(
                f"The metric {stat} is not a grade formula. Grade formulas: {grade_stats}"
            )
        return grade_to_age(getattr(self, stat), self.grade_age_levels, self.postgraduate_level)

    def describe_level(self, stat: str = "flesch_reading_easy") -> str:
        """
        Getting the band of the interpretation scale of a metric

        Arguments:
            stat (str): Name of a metric of level_scales, the reading ease by default

        Returns:
            str: Band of the scale

        Raises:
            ParameterError: If the metric has no scale in level_scales
        """
        if stat not in self.level_scales:
            raise ParameterError(
                f"The metric {stat} has no interpretation scale. "
                f"Metrics with a scale: {tuple(self.level_scales)}"
            )
        return scale_level(getattr(self, stat), self.level_scales[stat])

    def describe(self, stat: str) -> str | None:
        """
        Getting the reading of a metric by its scale

        Description:
            The consensus grade and a grade formula give the school stage and
            reader age (describe_grade), a metric of grade_scales the stage and
            age of the years of schooling its scale gives, a metric of
            level_scales the band of its scale (describe_level); another metric
            has no scale and gives None

        Arguments:
            stat (str): Name of a metric, a property of the class

        Returns:
            str | None: Reading of the value; None for a metric without a scale

        Raises:
            UnknownStatError: If the class has no such metric
        """
        if stat in ("consensus_grade", *self.grade_stats):
            return self.describe_grade(stat)
        if stat in self.grade_scales:
            grade = scale_level(getattr(self, stat), self.grade_scales[stat])
            return grade_to_age(grade, self.grade_age_levels, self.postgraduate_level)
        if stat in self.level_scales:
            return self.describe_level(stat)
        if not isinstance(getattr(type(self), stat, None), property):
            raise UnknownStatError(
                f"Unknown metric: {stat}. Available metrics: {tuple(self.stats_desc)}"
            )
        return None

    def reading_time_by_speed(self, wpm: float) -> float:
        """
        Computing the reading time of the text at a given speed

        Arguments:
            wpm (float): Reading speed, words per minute

        Returns:
            float: Reading time in minutes

        Raises:
            ParameterError: If the reading speed is not a positive number
        """
        return calc_reading_time(self.bs.n_words, wpm)

    def reading_time_by_norm(self, norm: str) -> tuple[float, ...]:
        """
        Computing the reading times of the text at the speeds of a norm

        Arguments:
            norm (str): Name of the norm from reading_speed_norms

        Returns:
            tuple[float, ...]: Reading times in minutes in the order of the speeds of the norm

        Raises:
            ParameterError: If the norm is unknown
        """
        if not isinstance(norm, str) or norm not in self.reading_speed_norms:
            raise ParameterError(
                f"Unknown reading speed norm: {norm}. "
                f"Available norms: {tuple(self.reading_speed_norms)}"
            )
        return tuple(
            calc_reading_time(self.bs.n_words, wpm) for wpm in self.reading_speed_norms[norm]
        )

    def get_stats(self) -> dict[str, float]:
        """
        Getting the computed readability metrics of the text

        Returns:
            dict[str, float]: Dictionary of the metrics of stats_desc
        """
        return {stat: getattr(self, stat) for stat in self.stats_desc}

    def print_stats(self) -> None:
        """Printing the computed readability metrics with descriptions"""
        stat_header, value_header = self.stats_headers
        print(f"{stat_header:^45}|{value_header:^10}")
        print("-" * 55)
        stats = self.get_stats()
        for stat, value in self.stats_desc.items():
            print(f"{value:45}|{stats[stat]:^10.2f}")


def _word_letters(bs: BasicStats) -> int:
    """Letters of the counted words, so that the mean word length matches the number of words"""
    return sum(letters * count for letters, count in bs.c_letters.items())


def calc_flesch_reading_easy(
    n_syllables: int,
    n_words: int,
    n_sents: int,
    a: float = 1.015,
    b: float = 84.6,
    c: float = 206.835,
) -> float:
    """
    Computing the Flesch reading ease

    Description:
        c - a * ASL - b * ASW with the mean sentence length in words and the
        mean word length in syllables; the higher the value, the easier the
        text, nominally from 0 to 100, though the simplest texts go above 100
        and the hardest below 0. The defaults are those of Flesch (1948) for
        English

    References:
        Flesch, R. A new readability yardstick. Journal of Applied Psychology,
            32(3), 1948

    Arguments:
        n_syllables (int): Number of syllables
        n_words (int): Number of words
        n_sents (int): Number of sentences
        a (float): Coefficient a, at the mean sentence length
        b (float): Coefficient b, at the mean word length
        c (float): Coefficient c, the constant

    Returns:
        float: Value of the index, nan without words or sentences
    """
    return c - safe_divide(a * n_words, n_sents, nan) - safe_divide(b * n_syllables, n_words, nan)


def calc_flesch_kincaid_grade(
    n_syllables: int,
    n_words: int,
    n_sents: int,
    a: float = 0.39,
    b: float = 11.8,
    c: float = 15.59,
) -> float:
    """
    Computing the Flesch-Kincaid grade

    Description:
        a * ASL + b * ASW - c with the mean sentence length in words and the
        mean word length in syllables: the years of schooling needed to read
        the text; the higher the value, the harder the text. The defaults are
        those of Kincaid et al. (1975) for English

    References:
        Kincaid, J. P., Fishburne, R. P., Rogers, R. L., Chissom, B. S. Derivation
            of new readability formulas for Navy enlisted personnel. Research
            Branch Report 8-75, 1975

    Arguments:
        n_syllables (int): Number of syllables
        n_words (int): Number of words
        n_sents (int): Number of sentences
        a (float): Coefficient a, at the mean sentence length
        b (float): Coefficient b, at the mean word length
        c (float): Coefficient c, the constant

    Returns:
        float: Value of the grade, nan without words or sentences
    """
    return safe_divide(a * n_words, n_sents, nan) + safe_divide(b * n_syllables, n_words, nan) - c


def calc_coleman_liau_index(
    n_letters: int,
    n_words: int,
    n_sents: int,
    a: float = 0.0588,
    b: float = 0.296,
    c: float = 15.8,
) -> float:
    """
    Computing the Coleman-Liau index

    Description:
        a * L - b * S - c with the letters and the sentences per 100 words: the
        years of schooling needed to read the text; the higher the value, the
        harder the text. The defaults are those of Coleman and Liau (1975) for
        English

    References:
        Coleman, M., Liau, T. L. A computer readability formula designed for
            machine scoring. Journal of Applied Psychology, 60(2), 1975

    Arguments:
        n_letters (int): Number of letters of the words
        n_words (int): Number of words
        n_sents (int): Number of sentences
        a (float): Coefficient a, at the letters per 100 words
        b (float): Coefficient b, at the sentences per 100 words
        c (float): Coefficient c, the constant

    Returns:
        float: Value of the index, nan without words
    """
    return (
        safe_divide(a * n_letters, n_words, nan) * 100
        - safe_divide(b * n_sents, n_words, nan) * 100
        - c
    )


def calc_automated_readability_index(
    n_letters: int,
    n_words: int,
    n_sents: int,
    a: float = 4.71,
    b: float = 0.5,
    c: float = 21.43,
) -> float:
    """
    Computing the automated readability index

    Description:
        a * letters per word + b * ASL - c with the mean sentence length in
        words: the years of schooling needed to read the text; the higher the
        value, the harder the text. The defaults are those of Smith and Senter
        (1967) for English

    References:
        Smith, E. A., Senter, R. J. Automated readability index. AMRL-TR-66-220,
            Aerospace Medical Research Laboratories, 1967

    Arguments:
        n_letters (int): Number of letters of the words
        n_words (int): Number of words
        n_sents (int): Number of sentences
        a (float): Coefficient a, at the letters per word
        b (float): Coefficient b, at the mean sentence length
        c (float): Coefficient c, the constant

    Returns:
        float: Value of the index, nan without words or sentences
    """
    return safe_divide(a * n_letters, n_words, nan) + safe_divide(b * n_words, n_sents, nan) - c


def calc_smog_index(
    n_complex: int, n_sents: int, a: float = 1.043, b: float = 30, c: float = 3.1291
) -> float:
    """
    Computing the SMOG index

    Description:
        a * sqrt(b * polysyllables / sentences) + c: the years of schooling
        needed to read the text; the higher the value, the harder the text.
        The defaults are those of McLaughlin (1969) for English, where the
        polysyllables are the words of three or more syllables and b brings
        their count to a sample of 30 sentences

    References:
        McLaughlin, G. H. SMOG grading: a new readability formula. Journal of
            Reading, 12(8), 1969

    Arguments:
        n_complex (int): Number of polysyllabic words
        n_sents (int): Number of sentences
        a (float): Coefficient a, at the square root
        b (float): Coefficient b, the number of sentences of the sample
        c (float): Coefficient c, the constant

    Returns:
        float: Value of the index, nan without sentences
    """
    return a * sqrt(safe_divide(b * n_complex, n_sents, nan)) + c


def calc_gunning_fog_index(n_complex: int, n_words: int, n_sents: int, a: float = 0.4) -> float:
    """
    Computing the Gunning fog index

    Description:
        a * (ASL + percentage of complex words) with the mean sentence length
        in words: the years of schooling needed to read the text; the higher
        the value, the harder the text. The defaults are those of Gunning
        (1952) for English, where a complex word has three or more syllables

    References:
        Gunning, R. The technique of clear writing. McGraw-Hill, 1952

    Arguments:
        n_complex (int): Number of complex words
        n_words (int): Number of words
        n_sents (int): Number of sentences
        a (float): Coefficient a

    Returns:
        float: Value of the index, nan without words or sentences
    """
    return a * (safe_divide(n_words, n_sents, nan) + safe_divide(100 * n_complex, n_words, nan))


def calc_lix(n_long_words: int, n_words: int, n_sents: int) -> float:
    """
    Computing the LIX readability index

    Description:
        The mean sentence length plus the percentage of long words, words of
        more than six letters (Björnsson, 1968), with no coefficients to fit.
        The higher the value, the harder the text; the text types of Björnsson
        are the bands of LIX_LEVELS

    References:
        Björnsson, C. H. Läsbarhet. Liber, 1968
        https://en.wikipedia.org/wiki/Lix_(readability_test)

    Arguments:
        n_long_words (int): Number of long words
        n_words (int): Number of words
        n_sents (int): Number of sentences

    Returns:
        float: Value of the index, nan without words or sentences
    """
    return safe_divide(n_words, n_sents, nan) + safe_divide(100 * n_long_words, n_words, nan)


def calc_rix(n_long_words: int, n_sents: int) -> float:
    """
    Computing the RIX readability index

    Description:
        Long words, of more than six letters, per sentence (Anderson, 1983),
        with no coefficients to fit. The higher the value, the harder the text;
        RIX_GRADES gives the grade of Anderson for a value, 13 for college

    References:
        Anderson, J. Lix and Rix: variations on a little-known readability index.
            Journal of Reading, 26(6), 1983

    Arguments:
        n_long_words (int): Number of long words
        n_sents (int): Number of sentences

    Returns:
        float: Value of the index, nan without sentences
    """
    return safe_divide(n_long_words, n_sents, nan)


def calc_mu_index(c_letters: Mapping[int, int]) -> float:
    """
    Computing Legibilidad µ

    Description:
        The mean number of letters per word divided by its sample variance
        (divided by n - 1), times 100 (Muñoz Baquedano and Muñoz Urra, 2006),
        with no coefficients to fit; the higher the value, the easier the text.
        Words without letters (numbers) are left out; with fewer than two
        words or without variability the index is undefined (nan)

    References:
        Muñoz Baquedano, M. Legibilidad y variabilidad de los textos. Boletín de
            Investigación Educacional, 21(2), 2006

    Arguments:
        c_letters (dict[int, int]): Distribution of words by number of letters

    Returns:
        float: Value of the index

    Raises:
        SourceTypeError: If the distribution is not a mapping
    """
    if not isinstance(c_letters, Mapping):
        raise SourceTypeError(
            f"A mapping of word lengths to counts is expected, not {type(c_letters).__name__}"
        )
    counts = {letters: count for letters, count in c_letters.items() if letters > 0}
    n = sum(counts.values())
    if n < 2:
        return float("nan")
    mean = sum(letters * count for letters, count in counts.items()) / n
    variance = sum(count * (letters - mean) ** 2 for letters, count in counts.items()) / (n - 1)
    if not variance:
        return float("nan")
    return mean / variance * 100


def flesch_reading_easy_to_grade(
    flesch_reading_easy: float,
    grades: Iterable[tuple[float, float]] = READING_EASE_GRADES,
    below: float = 13,
) -> float:
    """
    Converting the Flesch reading ease into years of schooling

    Description:
        The grade of the first band whose lower bound the value reaches; by
        default the bands of text_standard of textstat, which follow the table
        of Flesch (1948) down to 60 and split his lower bands, with 8.5 for
        its grades 8 and 9: 90-100 - 5,
        80-90 - 6, 70-80 - 7, 60-70 - 8.5, 50-60 - 10, 40-50 - 11, 30-40 - 12,
        below 30 - 13. Values above 100 belong to the first band

    Arguments:
        flesch_reading_easy (float): Value of the reading ease
        grades (list[tuple[float, float]]): Lower bounds and their grades in
            descending order of the bounds
        below (float): Grade below the last bound

    Returns:
        float: Years of schooling

    Raises:
        ParameterError: If the reading ease is not a finite number
    """
    check_number(flesch_reading_easy, "reading ease")
    for threshold, grade in grades:
        if flesch_reading_easy >= threshold:
            return grade
    return below


def calc_consensus_grade(
    grades: Iterable[float],
    flesch_reading_easy: float | None = None,
    to_grade: Callable[[float], float] = flesch_reading_easy_to_grade,
) -> float:
    """
    Computing the consensus grade

    Description:
        The median of the values of the grade formulas rounded half up; the
        reading ease is converted into years of schooling by to_grade and
        added without rounding, so a band of 8.5 votes for 8.5

    Arguments:
        grades (list[float]): Values of the grade formulas
        flesch_reading_easy (float): Value of the reading ease
        to_grade (Callable): Conversion of the reading ease into years of schooling

    Returns:
        float: Consensus grade

    Raises:
        SourceTypeError: If to_grade is not callable
        ParameterError: If there are no values, or a grade or the reading ease is not a
            finite number
    """
    if not callable(to_grade):
        raise SourceTypeError(f"to_grade must be callable, not {type(to_grade).__name__}")
    values = []
    for grade in grades:
        check_number(grade, "grade")
        values.append(float(floor(grade + 0.5)))
    if flesch_reading_easy is not None:
        check_number(flesch_reading_easy, "reading ease")
        values.append(to_grade(flesch_reading_easy))
    if not values:
        raise ParameterError("The list of grade formulas is empty")
    return float(median(values))


def scale_level(value: float, scale: Iterable[tuple[float, Band]]) -> Band:
    """
    Getting the band of a scale for a value

    Description:
        The scale is given as the lower bounds of its bands in descending
        order; the value falls into the first band whose bound it reaches,
        and the lowest band is open below

    Arguments:
        value (float): Value of a metric
        scale (list[tuple[float, Any]]): Lower bounds and their bands in descending order

    Returns:
        Any: Band of the scale

    Raises:
        ParameterError: If the value is not a finite number or the scale is empty

    Example:
        >>> from anyts.constants import READING_EASE_LEVELS
        >>> from anyts.readability_stats import scale_level
        >>> scale_level(45, READING_EASE_LEVELS), scale_level(-40, READING_EASE_LEVELS)
        ('college', 'professional')
    """
    check_number(value, "value")
    bands = list(scale)
    if not bands:
        raise ParameterError("The scale is empty")
    for threshold, band in bands:
        if value >= threshold:
            return band
    return bands[-1][1]


def grade_to_age(
    grade: float,
    levels: Iterable[tuple[int, int, str, str]] = GRADE_AGE_LEVELS,
    above: tuple[str, str] = POSTGRADUATE_LEVEL,
) -> str:
    """
    Getting the school stage and reader age by the value of a grade formula

    Description:
        The value is rounded half up and falls into the first stage whose
        last year it does not exceed, values below 1 into the first stage;
        by default the stages of the United States:
            1-5 - elementary school, 6-11 years
            6-8 - middle school, 11-14 years
            9-12 - high school, 14-18 years
            13-16 - college, 18-22 years
            above 16 - graduate school, over 22 years

    Arguments:
        grade (float): Value of a grade formula
        levels (list[tuple[int, int, str, str]]): Stages as the first and the
            last year, the stage and the age, in ascending order
        above (tuple[str, str]): Stage and age above the last stage

    Returns:
        str: School stage and reader age

    Raises:
        ParameterError: If the grade is not a finite number
    """
    check_number(grade, "grade")
    rounded = floor(grade + 0.5)
    for _, high, education, age in levels:
        if rounded <= high:
            return f"{education} ({age})"
    education, age = above
    return f"{education} ({age})"


def calc_reading_time(n_words: int, wpm: float = READING_SPEED_WPM) -> float:
    """
    Computing the reading time of a text

    Description:
        The default speed is the silent reading speed of adults in English,
        238 words per minute (Brysbaert, 2019)

    References:
        Brysbaert, M. How many words do we read per minute? A review and
            meta-analysis of reading rate. Journal of Memory and Language, 109, 2019

    Arguments:
        n_words (int): Number of words
        wpm (float): Reading speed, words per minute

    Returns:
        float: Reading time in minutes

    Raises:
        ParameterError: If the reading speed is not a positive number
    """
    check_number(wpm, "reading speed")
    if not wpm > 0:
        raise ParameterError("The reading speed must be greater than 0")
    return n_words / wpm
