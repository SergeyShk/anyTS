from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from math import floor, isfinite, nan, sqrt
from numbers import Real
from statistics import median
from typing import TYPE_CHECKING, Any, ClassVar

from .basic_stats import BasicStats, _check_extractors
from .constants import (
    GRADE_AGE_LEVELS,
    LIX_LEVELS,
    LIX_LONG_WORD_LETTER_FACTOR,
    MESSAGES,
    POSTGRADUATE_LEVEL,
    READABILITY_GRADE_STATS,
    READABILITY_PRESETS,
    READABILITY_STATS_DESC,
    READING_EASE_GRADES,
    READING_EASE_LEVELS,
    READING_SPEED_NORMS,
    READING_SPEED_WPM,
    RIX_GRADES,
    RIX_LEVELS,
    SMOG_COMPLEX_SYL_FACTOR,
)
from .exceptions import ParameterError, SourceError, SourceTypeError
from .extractors import SentsExtractor, WordsExtractor
from .stats import Stats, _check_scale, _check_scales
from .stats import scale_level as scale_level
from .utils import check_integer, check_number, safe_divide

if TYPE_CHECKING:
    from spacy.tokens import Doc


class ReadabilityStats(Stats):
    """
    Base of the readability metrics of a text

    Description:
        Readability formulas over the basic statistics of a text; the metrics
        are properties computed on each access. A language library sets the
        class attributes, may override reading_ease_to_grade and level_scale,
        and adds its formulas as properties named in stats_desc. The defaults
        are the original English formulas
        The other methods come from Stats

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
        preset (str): Name of the coefficient preset, read-only; an object of
            another preset may reuse bs
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
        level_scale: Interpretation scale of a metric
        describe_level: Band of the interpretation scale of a metric
        describe: Reading of any metric by its scale
        reading_time_by_speed: Reading time at a given speed
        reading_time_by_norm: Reading times at the speeds of a norm

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
            of describe_level and describe by metric, as lower bounds and their bands
        preset_level_scales (dict[str, dict[str, tuple[tuple[float, str], ...]]]):
            Interpretation scales by preset and metric, in place of level_scales for
            the preset
        grade_scales (dict[str, tuple[tuple[float, float], ...]]): Scales of a metric in
            years of schooling, as lower bounds and grades, for describe when
            level_scale gives no scale of bands
        reading_ease_grades (tuple[tuple[float, float], ...]): Scale of the reading ease
            in years of schooling for the consensus grade, as lower bounds and grades;
            READING_EASE_GRADES and 13 below them by default
        preset_reading_ease_grades (dict[str, tuple[tuple[float, float], ...]]): Scales
            of reading_ease_grades by preset, in its place for the preset
        postgraduate_level (tuple[str, str]): Stage and age above the last school stage
        reading_speed (float): Reading speed of reading_time, words per minute
        reading_speed_norms (dict[str, tuple[float, ...]]): Speeds of the reading norms,
            words per minute

    Raises:
        SourceTypeError: If the source is neither a string, a Doc nor a BasicStats object,
            the basic statistics are of another class, an extractor is of another type,
            or a class without basic_stats_class is given a string or a Doc
        SourceError: If the source has no words or no sentences
        ParameterError: If the coefficient preset is not a string or is unknown; when
            a class is defined, if its scales of a preset name an unknown preset, a
            scale or a scale of grades is not one of scale_level with finite grades, its
            school stages are not ascending quadruples of two years and two strings, or
            the stage above them is not a pair of strings
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
        "rix": RIX_LEVELS,
    }
    preset_level_scales: ClassVar[Mapping[str, Mapping[str, tuple[tuple[float, str], ...]]]] = {}
    grade_scales: ClassVar[Mapping[str, tuple[tuple[float, float], ...]]] = {"rix": RIX_GRADES}
    reading_ease_grades: ClassVar[tuple[tuple[float, float], ...]] = (
        *READING_EASE_GRADES,
        (0, 13),
    )
    preset_reading_ease_grades: ClassVar[Mapping[str, tuple[tuple[float, float], ...]]] = {}
    postgraduate_level: ClassVar[tuple[str, str]] = POSTGRADUATE_LEVEL
    reading_speed: ClassVar[float] = READING_SPEED_WPM
    reading_speed_norms: ClassVar[Mapping[str, tuple[float, ...]]] = READING_SPEED_NORMS

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # The scales of the presets a class sets itself: a subclass may narrow the presets
        for attribute in ("preset_level_scales", "preset_reading_ease_grades"):
            if attribute not in vars(cls):
                continue
            unknown = [preset for preset in getattr(cls, attribute) if preset not in cls.presets]
            if unknown:
                raise ParameterError(
                    f"The {attribute} of {cls.__name__} name unknown presets: {unknown}. "
                    f"Available presets: {tuple(cls.presets)}"
                )
        name = cls.__name__
        for preset, scales in cls.preset_level_scales.items():
            _check_scales(scales, f"preset_level_scales of {name} for {preset}")
        for stat, grades in cls.grade_scales.items():
            _check_grades(grades, f"scale of {stat} in the grade_scales of {name}")
        _check_grades(cls.reading_ease_grades, f"reading_ease_grades of {name}")
        for preset, grades in cls.preset_reading_ease_grades.items():
            _check_grades(grades, f"preset_reading_ease_grades of {name} for {preset}")
        _check_levels(cls.grade_age_levels, cls.postgraduate_level, f"grade_age_levels of {name}")

    def __init__(
        self,
        source: str | Doc | BasicStats,
        sents_extractor: SentsExtractor | None = None,
        words_extractor: WordsExtractor | None = None,
        preset: str = "original",
    ):
        messages = self.messages
        if not isinstance(preset, str):
            raise ParameterError(messages["preset_type"].format(type=type(preset).__name__))
        if preset not in self.presets:
            raise ParameterError(
                messages["unknown_preset"].format(preset=preset, presets=tuple(self.presets))
            )
        self._preset = preset
        self.coefficients = dict(self.presets[preset])
        _check_extractors(sents_extractor, words_extractor, messages)
        if isinstance(source, BasicStats):
            expected = self.basic_stats_class or BasicStats
            if not isinstance(source, expected):
                raise SourceTypeError(
                    messages["basic_stats_type"].format(
                        expected=expected.__name__, type=type(source).__name__
                    )
                )
            self.bs = source
        elif self.basic_stats_class is None:
            raise SourceTypeError(messages["no_basic_stats_class"].format(cls=type(self).__name__))
        else:
            self.bs = self.basic_stats_class(source, sents_extractor, words_extractor)
        if not self.bs.n_sents:
            raise SourceError(messages["no_sentences"])

    @property
    def preset(self) -> str:
        return self._preset

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
        return calc_reading_time(self.bs.n_words, self.reading_speed, messages=self.messages)

    def reading_ease_to_grade(self, flesch_reading_easy: float) -> float:
        """
        Converting the Flesch reading ease into years of schooling

        Description:
            Used for the consensus grade; by default the band of the scale of the
            preset in preset_reading_ease_grades, else of reading_ease_grades

        Arguments:
            flesch_reading_easy (float): Value of the reading ease

        Returns:
            float: Years of schooling

        Raises:
            ParameterError: If the reading ease is not a finite number
        """
        check_number(flesch_reading_easy, "reading ease")
        grades = self.preset_reading_ease_grades.get(self.preset, self.reading_ease_grades)
        return scale_level(flesch_reading_easy, grades)

    def level_scale(self, stat: str) -> tuple[tuple[float, str], ...] | None:
        """
        Getting the interpretation scale of a metric

        Description:
            The scale of the preset in preset_level_scales, else that of level_scales

        Arguments:
            stat (str): Name of the metric

        Returns:
            tuple[tuple[float, str], ...] | None: Lower bounds and their bands, None
                for a metric without a scale
        """
        if isinstance(stat, str):
            scale = self.preset_level_scales.get(self.preset, {}).get(stat)
            if scale is not None:
                return scale
        return super().level_scale(stat)

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
        if not isinstance(stat, str) or stat not in grade_stats:
            raise ParameterError(
                self.messages["not_grade_formula"].format(stat=stat, grade_stats=grade_stats)
            )
        return grade_to_age(getattr(self, stat), self.grade_age_levels, self.postgraduate_level)

    def describe_level(self, stat: str = "flesch_reading_easy") -> str:
        """
        Getting the band of the interpretation scale of a metric

        Arguments:
            stat (str): Name of a metric with a scale (level_scale), the reading ease
                by default

        Returns:
            str: Band of the scale

        Raises:
            ParameterError: If the metric has no scale of bands or its value is not
                a finite number
        """
        scale = self.level_scale(stat) if isinstance(stat, str) else None
        if scale is None:
            raise ParameterError(self.messages["no_scale"].format(stat=stat))
        return scale_level(getattr(self, stat), scale)

    def describe(self, stat: str) -> str | None:
        """
        Getting the reading of a metric by its scale

        Description:
            The consensus grade and a grade formula give the school stage and
            reader age (describe_grade), a metric with a scale of bands
            (level_scale) its band, another metric of grade_scales the stage and
            age of the years of schooling its scale gives. A metric is a name of
            stats_desc or a public property of the class

        Arguments:
            stat (str): Name of the metric

        Returns:
            str | None: Reading of the value; None for a metric without a scale
                or an undefined value

        Raises:
            UnknownStatError: If the class has no such metric
        """
        self._check_stat(stat)
        value = getattr(self, stat)
        if isinstance(value, Real) and not isfinite(value):
            return None
        if stat in ("consensus_grade", *self.grade_stats):
            return grade_to_age(value, self.grade_age_levels, self.postgraduate_level)
        scale = self.level_scale(stat)
        if scale is not None:
            return scale_level(value, scale)
        if stat in self.grade_scales:
            grade = scale_level(value, self.grade_scales[stat])
            return grade_to_age(grade, self.grade_age_levels, self.postgraduate_level)
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
        return calc_reading_time(self.bs.n_words, wpm, messages=self.messages)

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
                self.messages["unknown_norm"].format(
                    norm=norm, norms=tuple(self.reading_speed_norms)
                )
            )
        return tuple(
            calc_reading_time(self.bs.n_words, wpm, messages=self.messages)
            for wpm in self.reading_speed_norms[norm]
        )


def _word_letters(bs: BasicStats) -> int:
    """Letters of the counted words, so that the mean word length matches the number of words"""
    return sum(letters * count for letters, count in bs.c_letters.items())


def _check_grades(grades: Iterable[tuple[float, float]], what: str) -> list[tuple[float, float]]:
    """Bands of a scale of grades, checked as a scale of scale_level with finite grades"""
    bands = _check_scale(grades, what)
    for _, grade in bands:
        check_number(grade, "grade of a band")
    return bands


def _check_levels(levels: object, above: object, what: str) -> list[tuple[int, int, str, str]]:
    """School stages checked as the first and the last year, the stage and the age in
    ascending order of the years, and the stage above them as a pair of strings"""
    try:
        stages = [(first, last, stage, age) for first, last, stage, age in levels]  # type: ignore[attr-defined]
    except (TypeError, ValueError):
        raise ParameterError(
            f"The {what} must be a list of the first and the last year, the stage and the age"
        ) from None
    previous = None
    for first, last, stage, age in stages:
        check_integer(first, "first year of a stage")
        check_integer(last, "last year of a stage")
        if not isinstance(stage, str) or not isinstance(age, str):
            raise ParameterError(f"The stage and the age of the {what} must be strings")
        if last < first or (previous is not None and first <= previous):
            raise ParameterError(f"The years of the {what} must ascend")
        previous = last
    if not (
        isinstance(above, tuple | list)
        and len(above) == 2
        and all(isinstance(x, str) for x in above)
    ):
        raise ParameterError("The stage above the last one must be a pair of strings")
    return stages


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
        mean word length in syllables. The higher the value, the easier the
        text: nominally 0 to 100, though the simplest texts go above 100 and
        the hardest below 0. The defaults are those of Flesch (1948) for English

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

    Raises:
        ParameterError: If a number of words or sentences is not an integer or is negative
    """
    for count, what in (
        (n_complex, "number of polysyllabic words"),
        (n_sents, "number of sentences"),
    ):
        check_integer(count, what)
        if count < 0:
            raise ParameterError(f"The {what} cannot be negative")
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
        The mean sentence length plus the percentage of long words, of more
        than six letters (Björnsson, 1968); no coefficients. The higher the
        value, the harder the text; the text types of Björnsson are the bands
        of LIX_LEVELS

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
        Long words, of more than six letters, per sentence (Anderson, 1983); no
        coefficients. The higher the value, the harder the text; the grades of
        Anderson are the bands of RIX_LEVELS, and RIX_GRADES gives them as
        years of schooling, 13 for college

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
        (divided by n - 1), times 100 (Muñoz Baquedano and Muñoz Urra, 2006);
        no coefficients. The higher the value, the easier the text. Words
        without letters (numbers) are left out; with fewer than two words or
        without variability the index is undefined (nan)

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
        The grade of the first band whose lower bound the value reaches;
        values above 100 belong to the first band. By default the bands of
        text_standard of textstat, after the table of Flesch (1948): 90-100 - 5,
        80-90 - 6, 70-80 - 7, 60-70 - 8.5, 50-60 - 10, 40-50 - 11, 30-40 - 12,
        below 30 - 13

    Arguments:
        flesch_reading_easy (float): Value of the reading ease
        grades (list[tuple[float, float]]): Lower bounds and their grades in
            descending order of the bounds
        below (float): Grade below the last bound

    Returns:
        float: Years of schooling

    Raises:
        ParameterError: If the reading ease or the grade below is not a finite number,
            or the grades are not a scale of finite grades (scale_level)
    """
    check_number(flesch_reading_easy, "reading ease")
    check_number(below, "grade below the last bound")
    for threshold, grade in _check_grades(grades, "scale of the grades"):
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
        SourceTypeError: If to_grade is not callable or the grades are not a list
        ParameterError: If there are no values, or a grade or the reading ease is not a
            finite number
    """
    if not callable(to_grade):
        raise SourceTypeError(f"to_grade must be callable, not {type(to_grade).__name__}")
    source: object = grades
    if not isinstance(source, Iterable) or isinstance(source, str):
        raise SourceTypeError(f"The grades must be a list of numbers, not {type(grades).__name__}")
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
        ParameterError: If the grade is not a finite number, or the stages are not
            quadruples of two whole years and two strings in ascending order of the
            years, or the stage above is not a pair of strings
    """
    check_number(grade, "grade")
    rounded = floor(grade + 0.5)
    for _, high, education, age in _check_levels(levels, above, "school stages"):
        if rounded <= high:
            return f"{education} ({age})"
    education, age = above
    return f"{education} ({age})"


def calc_reading_time(
    n_words: int, wpm: float = READING_SPEED_WPM, *, messages: Mapping[str, str] = MESSAGES
) -> float:
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
        messages (dict[str, str]): Messages of the errors by key (MESSAGES)

    Returns:
        float: Reading time in minutes

    Raises:
        ParameterError: If the number of words is not an integer or is negative, or
            the reading speed is not a positive number
    """
    check_integer(n_words, "number of words")
    if n_words < 0:
        raise ParameterError("The number of words cannot be negative")
    check_number(wpm, "reading speed")
    if not wpm > 0:
        raise ParameterError(messages["reading_speed"])
    return n_words / wpm
