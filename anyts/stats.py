from collections.abc import Iterable, Mapping
from math import isfinite
from numbers import Real
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar

from .constants import MESSAGES
from .exceptions import ParameterError, UnknownStatError
from .utils import check_messages, check_number

if TYPE_CHECKING:
    from pandas import DataFrame

Band = TypeVar("Band")


class Stats:
    """
    Base of the classes of statistics of a text

    Description:
        The common interface of the statistics of a text: their dictionary,
        nested or flat, a one-row frame, a printed table with descriptions and
        the reading of a statistic by its scale. A class names its statistics
        in stats_desc, each an attribute or a property of the object; the
        values of a dictionary statistic become keys of their own in the flat
        dictionary, joined to its name with an underscore

    Methods:
        stat_names: Names of the statistics of get_stats
        get_stats: Getting the computed statistics
        to_dataframe: Getting the computed statistics as a one-row frame
        print_stats: Printing the computed statistics with descriptions
        level_scale: Interpretation scale of a statistic, level_scales by default
        describe: Reading of a statistic by its scale

    Class attributes:
        stats_desc (dict[str, str]): Statistics of get_stats and their descriptions for
            print_stats
        stats_headers (tuple[str, str]): Headers of the columns for print_stats
        level_scales (dict[str, tuple[tuple[float, str], ...]]): Interpretation scales
            of describe by statistic, as lower bounds and their bands
        messages (dict[str, str]): Messages of the errors by key (MESSAGES)

    Example:
        >>> from anyts.stats import Stats
        >>> class TextSize(Stats):
        ...     stats_desc = {"n_words": "Words", "c_lengths": "Words by length"}
        ...     level_scales = {"n_words": ((100, "long"), (0, "short"))}
        ...     def __init__(self, text):
        ...         words = text.split()
        ...         self.n_words = len(words)
        ...         self.c_lengths = {3: sum(len(word) == 3 for word in words)}
        >>> size = TextSize("The cat sat on the mat")
        >>> size.get_stats(), size.get_stats(flat=True)
        ({'n_words': 6, 'c_lengths': {3: 5}}, {'n_words': 6, 'c_lengths_3': 5})
        >>> size.describe("n_words")
        'short'
    """

    stats_desc: ClassVar[Mapping[str, str]] = {}
    stats_headers: ClassVar[tuple[str, str]] = ("Statistic", "Value")
    level_scales: ClassVar[Mapping[str, tuple[tuple[float, str], ...]]] = {}
    messages: ClassVar[Mapping[str, str]] = MESSAGES

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        check_messages(cls.messages)

    def stat_names(self) -> tuple[str, ...]:
        """
        Getting the names of the statistics of get_stats

        Returns:
            tuple[str, ...]: Names of the statistics, the keys of stats_desc by default
        """
        return tuple(self.stats_desc)

    def get_stats(self, flat: bool = False) -> dict[str, Any]:
        """
        Getting the computed statistics

        Arguments:
            flat (bool): Turn the values of the dictionary statistics into keys of
                their own, joined to the name of the statistic with an underscore

        Returns:
            dict[str, Any]: Dictionary of the statistics of stat_names - a copy,
                editing it does not change the object
        """
        stats = {stat: getattr(self, stat) for stat in self.stat_names()}
        return _flatten(stats) if flat else _copy(stats)

    def to_dataframe(self) -> "DataFrame":
        """
        Getting the computed statistics as a one-row frame

        Returns:
            pandas.DataFrame: Frame with a column for every key of the flat statistics
        """
        from pandas import DataFrame

        return DataFrame([self.get_stats(flat=True)])

    def print_stats(self) -> None:
        """Printing the computed statistics of stats_desc with descriptions"""
        stats = self.get_stats()
        rows = [(desc, _format(stats[stat])) for stat, desc in self.stats_desc.items()]
        stat_header, value_header = self.stats_headers
        left = max([len(stat_header), *(len(desc) for desc, _ in rows)]) + 1
        right = max([8, len(value_header), *(len(value) for _, value in rows)]) + 2
        print(f"{stat_header:^{left}}|{value_header:^{right}}")
        print("-" * (left + 1 + right))
        for desc, value in rows:
            print(f"{desc:{left}}|{value:^{right}}")

    def level_scale(self, stat: str) -> tuple[tuple[float, str], ...] | None:
        """
        Getting the interpretation scale of a statistic

        Description:
            By default the scale of level_scales; a class whose scale depends
            on its parameters overrides the method, and describe follows it

        Arguments:
            stat (str): Name of the statistic

        Returns:
            tuple[tuple[float, str], ...] | None: Lower bounds and their bands, None
                for a statistic without a scale
        """
        return self.level_scales.get(stat) if isinstance(stat, str) else None

    def describe(self, stat: str) -> str | None:
        """
        Getting the reading of a statistic by its scale

        Description:
            The band of the scale of the statistic (level_scale); a statistic
            without a scale and an undefined value (nan) give None. A statistic
            is a name of stat_names or a public property of the class

        Arguments:
            stat (str): Name of the statistic

        Returns:
            str | None: Band of the scale; None for a statistic without a scale
                or an undefined value

        Raises:
            UnknownStatError: If the class has no such statistic
        """
        self._check_stat(stat)
        scale = self.level_scale(stat)
        if scale is None:
            return None
        value = getattr(self, stat)
        if isinstance(value, Real) and not isfinite(value):
            return None
        return scale_level(value, scale)

    def _check_stat(self, stat: object) -> None:
        """Raising UnknownStatError for a name neither of stat_names nor a public property"""
        names = self.stat_names()
        if (
            isinstance(stat, str)
            and not stat.startswith("_")
            and (stat in names or isinstance(getattr(type(self), stat, None), property))
        ):
            return
        raise UnknownStatError(self.messages["unknown_stat"].format(stat=stat, stats=names))


def _copy(stats: Mapping[Any, Any]) -> dict[Any, Any]:
    """Copy of a dictionary with copies of its nested dictionaries"""
    return {
        key: _copy(value) if isinstance(value, Mapping) else value for key, value in stats.items()
    }


def _flatten(stats: Mapping[Any, Any], prefix: str = "") -> dict[str, Any]:
    """Flat dictionary with the keys of the nested ones joined to their names"""
    flat: dict[str, Any] = {}
    for key, value in stats.items():
        name = f"{prefix}{key}"
        if isinstance(value, Mapping):
            flat.update(_flatten(value, f"{name}_"))
        else:
            flat[name] = value
    return flat


def _format(value: Any) -> str:
    """Value for print_stats, a float with two decimals"""
    return f"{value:.2f}" if isinstance(value, float) else str(value)


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
        ParameterError: If the value is not a finite number, or the scale is empty or
            not a list of pairs of a finite lower bound and a band

    Example:
        >>> from anyts.constants import READING_EASE_LEVELS
        >>> from anyts.readability_stats import scale_level
        >>> scale_level(45, READING_EASE_LEVELS), scale_level(-40, READING_EASE_LEVELS)
        ('college', 'professional')
    """
    check_number(value, "value")
    try:
        bands = [(threshold, band) for threshold, band in scale]
    except (TypeError, ValueError):
        raise ParameterError(
            "The scale must be a list of pairs of a lower bound and a band"
        ) from None
    if not bands:
        raise ParameterError("The scale is empty")
    for threshold, _ in bands:
        check_number(threshold, "lower bound of a band")
    for threshold, band in bands:
        if value >= threshold:
            return band
    return bands[-1][1]
