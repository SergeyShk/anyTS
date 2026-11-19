from __future__ import annotations

from collections.abc import Hashable, Iterable, Mapping, Sequence
from itertools import pairwise
from math import isfinite
from numbers import Real
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar, cast

from .constants import MESSAGES
from .exceptions import ParameterError, SourceError, SourceTypeError, UnknownStatError
from .utils import _check_removed, _messages, check_bool, check_messages, check_number

if TYPE_CHECKING:
    from anyseg import Document
    from pandas import DataFrame
    from spacy.tokens import Doc

# Attributes of the classes of statistics of 0.4 the core no longer reads, with the hooks that
# replace them
_REMOVED_ATTRIBUTES = MappingProxyType(
    {
        "words_extractor_class": ("parse", "doc_words"),
        "sents_extractor_class": ("parse",),
        "join_hyphens": ("parse",),
        "doc_units": ("analyze",),
    }
)

Band = TypeVar("Band")


class Stats:
    """
    Base of the classes of statistics of a text

    Description:
        The common interface of the statistics of a text. A class names its
        statistics in stats_desc, each an attribute or a property of the object

    Methods:
        parse: Document of a data source
        by_parts: Statistics of every sentence or paragraph of a data source
        parts_document: Document whose parts by_parts counts
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
        part_kinds (tuple[str, ...]): Parts of by_parts the class counts, sentences
            and paragraphs by default

    Raises:
        ParameterError: When a class is defined, if its messages are incomplete,
            its scales are not pairs of a finite lower bound and a band with the
            bounds descending, or it defines an attribute of 0.4 the core no
            longer reads (words_extractor_class, sents_extractor_class,
            join_hyphens, doc_units)

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
    part_kinds: ClassVar[tuple[str, ...]] = ("sentences", "paragraphs")

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        check_messages(cls.messages)
        _check_removed(cls, _REMOVED_ATTRIBUTES, cls.messages)
        _check_scales(cls.level_scales, f"level_scales of {cls.__name__}")

    def parse(self, source: str | Doc | Document) -> Document:
        """
        Getting the document of a data source

        Description:
            to_document by default: a Document as it is, a Doc with its tokens,
            columns and sentences, a string split into words of \\w, punctuation
            marks and the sentences of SentsExtractor. A language library
            overrides it to segment and annotate a string in its language

        Arguments:
            source (str|Doc|Document): Data source

        Returns:
            Document: Document of anySeg

        Raises:
            SourceTypeError: If the source is neither a string, a Doc nor a Document
                object
            SourceError: If a token of a Doc runs over a blank line
        """
        from .document import to_document

        return to_document(source, messages=self.messages)

    def _document(self, source: str | Doc | Document) -> Document:
        """Document of parse, checked to be a Document"""
        from .document import _parsed

        return _parsed(self, source)

    @classmethod
    def by_parts(
        cls, source: str | Doc | Document, parts: str = "sentences", **params: Any
    ) -> DataFrame:
        """
        Getting the statistics of every sentence or paragraph of a data source

        Description:
            The source is parsed once (parts_document), and the class with the
            parameters counts the document of every part (document_part). The
            table has a row per part, its start and end in the text of the
            document and its flat statistics (stats_dataframe); a part without
            words, such as a line of asterisks, or one the class cannot count,
            such as a number alone on a line for a class without numbers among
            its words, has its row without statistics

        Arguments:
            source (str|Doc|Document): Data source
            parts (str): Parts, one of part_kinds of the class
            **params: Parameters of the class

        Returns:
            pandas.DataFrame: Table of the parts, indexed by their number

        Raises:
            ParameterError: If the parts are not one of part_kinds
            SourceTypeError, SourceError: As the class raises for the source, or for a
                part when it can count none

        Example:
            >>> from anyts.basic_stats import BasicStats
            >>> class Vowels(BasicStats):
            ...     def count_syllables(self, word):
            ...         return sum(char in "aeiou" for char in word.lower())
            >>> Vowels.by_parts("The cat sleeps. A dog barks loudly.")[["start", "end", "n_words"]]
                      start  end  n_words
            sentence
            0             0   15        3
            1            16   35        4
        """
        return _parts_dataframe(
            [
                (number, *part)
                for number, part in enumerate(cls._count_parts(source, parts, params))
            ],
            parts[:-1],
        )

    @classmethod
    def parts_document(cls, source: str | Doc | Document, **params: Any) -> Document:
        """
        Getting the document whose parts by_parts counts

        Description:
            parse of an object of the class made without __init__ by default, so
            a parse that reads only the class serves; a class whose parse needs
            its parameters, or that annotates a string outside parse, overrides
            it, so that the parts have the annotation of an object of the class

        Arguments:
            source (str|Doc|Document): Data source
            **params: Parameters of the class

        Returns:
            Document: Document of anySeg
        """
        return cls.__new__(cls)._document(source)

    @classmethod
    def _count_parts(
        cls, source: str | Doc | Document, parts: str, params: Mapping[str, Any]
    ) -> list[tuple[int, int, Stats | None]]:
        """Start, end and statistics of every part of a source parsed once, None for a part
        without words or one the class cannot count, such as a number alone on a line for a
        class without numbers; the error of the class when it can count no part"""
        from .document import _document_parts, document_words

        if not isinstance(parts, str) or parts not in cls.part_kinds:
            raise ParameterError(
                cls.messages["parts_kind"].format(parts=repr(parts), kinds=cls.part_kinds)
            )
        document = cls.parts_document(source, **params)
        counted: list[tuple[int, int, Stats | None]] = []
        failure: SourceError | None = None
        for start, end, part in _document_parts(document, parts):
            stats = None
            if document_words(part):
                try:
                    stats = cast(Any, cls)(part, **params)
                    # A statistic computed when it is read raises here, for its part
                    stats.get_stats()
                except SourceError as error:
                    stats = None
                    failure = failure or error
            counted.append((start, end, stats))
        if failure is not None and all(stats is None for _, _, stats in counted):
            raise failure
        return counted

    def stat_names(self) -> tuple[str, ...]:
        """
        Getting the names of the statistics of get_stats

        Returns:
            tuple[str, ...]: Names of the statistics, the keys of stats_desc by default
        """
        return tuple(self.stats_desc)

    def get_stats(self, *, flat: bool = False) -> dict[str, Any]:
        """
        Getting the computed statistics

        Arguments:
            flat (bool): Turn the values of the dictionary statistics into keys of
                their own, joined to the name of the statistic with an underscore

        Returns:
            dict[str, Any]: Copy of the statistics of stat_names

        Raises:
            ParameterError: If flat is not a bool
        """
        check_bool(flat, "flat", message=self.messages["bool_param"])
        stats = {stat: getattr(self, stat) for stat in self.stat_names()}
        return _flatten(stats) if flat else _copy(stats)

    def to_dataframe(self) -> DataFrame:
        """
        Getting the computed statistics as a one-row frame

        Description:
            A dictionary statistic gives columns only for the keys of this object:
            in a frame of several objects a count one lacks is NaN

        Returns:
            pandas.DataFrame: Frame with a column for every key of the flat statistics
        """
        from pandas import DataFrame

        return DataFrame([self.get_stats(flat=True)])

    def print_stats(self) -> None:
        """Printing the computed statistics of stats_desc with descriptions"""
        stats = self.get_stats()
        _print_table(
            [(desc, stats[stat]) for stat, desc in self.stats_desc.items()], self.stats_headers
        )

    def level_scale(self, stat: str) -> tuple[tuple[float, str], ...] | None:
        """
        Getting the interpretation scale of a statistic

        Description:
            level_scales by default; a class whose scales depend on its
            parameters overrides the method, which describe follows

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
            The band of the scale of level_scale. A statistic is a name of
            stat_names or a public property of the class; a key of the flat
            statistics (get_stats(flat=True)) has no scale, and so has a key of
            any value of a dictionary statistic, which the table of another
            text may have

        Arguments:
            stat (str): Name of the statistic

        Returns:
            str | None: Band of the scale; None for a statistic without a scale
                or an undefined value

        Raises:
            UnknownStatError: If the class has no such statistic
        """
        if self._is_flat_key(stat):
            return None
        self._check_stat(stat)
        scale = self.level_scale(stat)
        if scale is None:
            return None
        value = getattr(self, stat)
        if isinstance(value, Real) and not isfinite(value):
            return None
        return scale_level(value, scale)

    def _is_flat_key(self, stat: object) -> bool:
        """Whether a name is a key of the flat statistics that is no statistic of its own"""
        if not isinstance(stat, str):
            return False
        names = self.stat_names()
        # The statistics are computed only for a name that begins as one of them
        prefixed = [name for name in names if stat.startswith(f"{name}_")]
        if stat in names or not prefixed:
            return False
        # Any value of a dictionary statistic: another text may have it in its table
        stats = self.get_stats()
        return any(isinstance(stats.get(name), Mapping) for name in prefixed)

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


def _print_table(rows: Iterable[tuple[str, Any]], headers: tuple[str, str]) -> None:
    """Printing descriptions and their values in two columns as wide as their longest cell"""
    cells = [(desc, _format(value)) for desc, value in rows]
    stat_header, value_header = headers
    left = max([len(stat_header), *(len(desc) for desc, _ in cells)]) + 1
    right = max([8, len(value_header), *(len(value) for _, value in cells)]) + 2
    print(f"{stat_header:^{left}}|{value_header:^{right}}")
    print("-" * (left + 1 + right))
    for desc, value in cells:
        print(f"{desc:{left}}|{value:^{right}}")


def _format(value: Any) -> str:
    """Value for _print_table, a float with two decimals"""
    return f"{value:.2f}" if isinstance(value, float) else str(value)


def _check_scales(scales: object, what: str) -> None:
    """Checking the scales of the statistics of a class by their names"""
    if not isinstance(scales, Mapping):
        raise ParameterError(f"The {what} must be a mapping of a statistic to its scale")
    for stat, scale in scales.items():
        _check_scale(scale, f"scale of {stat} in the {what}")


def _check_scale(
    scale: Iterable[tuple[float, Band]], what: str = "scale"
) -> list[tuple[float, Band]]:
    """Bands of a scale, checked to be pairs of a finite lower bound and a band, bounds descending"""
    try:
        bands = [(threshold, band) for threshold, band in scale]
    except (TypeError, ValueError):
        raise ParameterError(
            f"The {what} must be a list of pairs of a lower bound and a band"
        ) from None
    if not bands:
        raise ParameterError(f"The {what} is empty")
    for threshold, _ in bands:
        check_number(threshold, "lower bound of a band")
    bounds = [threshold for threshold, _ in bands]
    if any(lower >= upper for upper, lower in pairwise(bounds)):
        raise ParameterError(f"The lower bounds of the {what} must descend, not {bounds}")
    return bands


def scale_level(value: float, scale: Iterable[tuple[float, Band]]) -> Band:
    """
    Getting the band of a scale for a value

    Description:
        The first band whose lower bound the value reaches; the lowest band
        is open below

    Arguments:
        value (float): Value of a metric
        scale (list[tuple[float, Any]]): Lower bounds and their bands in descending order

    Returns:
        Any: Band of the scale

    Raises:
        ParameterError: If the value is not a finite number, or the scale is empty,
            not a list of pairs of a finite lower bound and a band, or its bounds do
            not descend

    Example:
        >>> from anyts.constants import READING_EASE_LEVELS
        >>> from anyts.readability_stats import scale_level
        >>> scale_level(45, READING_EASE_LEVELS), scale_level(-40, READING_EASE_LEVELS)
        ('college', 'professional')
    """
    check_number(value, "value")
    bands = _check_scale(scale)
    for threshold, band in bands:
        if value >= threshold:
            return band
    return bands[-1][1]


def stats_dataframe(
    stats: Iterable[Stats],
    index: Sequence[Hashable] | None = None,
    *,
    messages: Mapping[str, str] | None = None,
) -> DataFrame:
    """
    Getting the flat statistics of several objects as one table

    Description:
        A row per object, its flat statistics (get_stats(flat=True)), and a column
        for every key of any of them. A value of a dictionary statistic an object
        lacks is 0, since its text has no such value; any other value it lacks is
        NaN. The values of a dictionary with keys of numbers, such as the words
        by their length, go in the order of the keys

    Arguments:
        stats (list[Stats]): Objects of statistics
        index (list): Labels of the rows; their numbers by default
        messages (dict[str, str]): Messages of the errors by key, in place of those of the
            library

    Returns:
        pandas.DataFrame: Table of the statistics

    Raises:
        SourceTypeError: If an object is not of a class of statistics

    Example:
        >>> from anyts.stats import Stats, stats_dataframe
        >>> class TextSize(Stats):
        ...     stats_desc = {"n_words": "Words", "c_lengths": "Words by length"}
        ...     def __init__(self, text):
        ...         words = text.split()
        ...         self.n_words = len(words)
        ...         self.c_lengths = dict(sorted(Counter(map(len, words)).items()))
        >>> from collections import Counter
        >>> stats_dataframe([TextSize("The cat sat"), TextSize("A mouse ran away")])
           n_words  c_lengths_1  c_lengths_3  c_lengths_4  c_lengths_5
        0        3            0            3            0            0
        1        4            1            1            1            1
    """
    from pandas import DataFrame

    messages = _messages(messages)
    given: object = stats
    if isinstance(given, str) or not isinstance(given, Iterable):
        raise SourceTypeError(messages["stats_objects"].format(type=type(given).__name__))
    objects = list(given)
    for item in objects:
        if not isinstance(item, Stats):
            raise SourceTypeError(messages["stats_objects"].format(type=type(item).__name__))
    nested = [item.get_stats() for item in objects]
    # The keys of every dictionary statistic over all the objects, in order
    keys: dict[str, list[Any]] = {}
    for values in nested:
        for name, value in values.items():
            if isinstance(value, Mapping):
                found = keys.setdefault(name, [])
                found.extend(key for key in value if key not in found)
    for found in keys.values():
        if all(isinstance(key, Real) and not isinstance(key, bool) for key in found):
            found.sort()
    columns: list[str] = []
    rows = []
    for values in nested:
        row: dict[str, Any] = {}
        for name, value in values.items():
            if isinstance(value, Mapping):
                full = {key: value.get(key, 0) for key in keys[name]}
                row.update(_flatten({name: full}))
            else:
                row[name] = value
        for column in row:
            if column not in columns:
                columns.append(column)
        rows.append(row)
    return DataFrame(rows, index=index, columns=columns)


def _parts_dataframe(
    parts: Sequence[tuple[Hashable, int, int, Stats | None]], name: str | Sequence[str]
) -> DataFrame:
    """Table of parts: a row per part labelled by its key, with its start, its end and the flat
    statistics of stats_dataframe, none for a part without them; name names the index, or its
    levels for keys that are tuples, such as a text and the number of its part"""
    from pandas import DataFrame, Index, MultiIndex

    names = [name] if isinstance(name, str) else list(name)

    def labels(keys: list[Hashable]) -> Index:
        if len(names) > 1:
            return MultiIndex.from_tuples(keys, names=names)
        return Index(keys, name=names[0])

    bounds = DataFrame(
        {"start": [start for _, start, _, _ in parts], "end": [end for _, _, end, _ in parts]},
        index=labels([key for key, _, _, _ in parts]),
    )
    counted = [(key, stats) for key, _, _, stats in parts if stats is not None]
    table = stats_dataframe(
        [stats for _, stats in counted], index=labels([key for key, _ in counted])
    )
    return bounds.join(table)
