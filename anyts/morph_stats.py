from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING, Any, ClassVar, NamedTuple

from .constants import MORPH_FEATURES, MORPH_STATS_DESC, MORPH_VALUES_DESC
from .exceptions import ParameterError, SourceError, SourceTypeError
from .stats import Stats, _print_table
from .utils import is_doc, iter_doc_tokens, source_type_error

if TYPE_CHECKING:
    from spacy.tokens import Doc


class MorphWord(NamedTuple):
    """
    Word of a text with its morphological features

    Attributes:
        word (str): Word as the text writes it
        pos (str|None): Part of speech of Universal Dependencies, None when unknown
        features (dict[str, str]): Values of the features of Universal Dependencies by
            their names (Case: Nom), a value of several joined by commas (Int,Rel)
    """

    word: str
    pos: str | None
    features: Mapping[str, str]


class MorphStats(Stats):
    """
    Base of the morphological statistics of a text

    Description:
        The parts of speech and the features of Universal Dependencies of the
        words of a text, counted by value. A language library subclasses the
        class and sets its hooks; by default the source is a Doc with the parts
        of speech, read by token.pos_ and token.morph, and the statistics are
        the features of MORPH_FEATURES.
        to_dataframe and describe come from Stats

    Arguments:
        source (Doc): Data source (a Doc object, or what analyze reads)

    Attributes:
        words (tuple[str]): Words
        tags (tuple[str]): Features of every word in the CoNLL-U format, _ for a word
            without them
        pos (tuple[str|None]): Part of speech of every word
        animacy, aspect, ..., voice (tuple[str|None]): Value of a feature of
            feature_names for every word, None for a word without it

    Methods:
        analyze: Words of a source with their features
        get_stats: Number of the words by value of every statistic
        explain_text: Values of the statistics word by word
        print_stats: Printing the numbers with the descriptions of the values
        get_markers: Markers of the language computed from the features
        print_markers: Printing the markers with their descriptions

    Class attributes:
        feature_names (dict[str, str]): Feature of Universal Dependencies by statistic
            (MORPH_FEATURES)
        stats_desc (dict[str, str]): pos and the statistics of feature_names with their
            names, in the order of get_stats (MORPH_STATS_DESC)
        values_desc (dict[str, dict[str, str]]): Descriptions of the values by statistic
            for print_stats (MORPH_VALUES_DESC)
        unknown_value (str): Description of the words without the feature in print_stats
        markers_desc (dict[str, str]): Markers of get_markers with their descriptions,
            none by default
        markers_headers (tuple[str, str]): Headers of the columns for print_markers

    Raises:
        SourceTypeError: If the source is not a Doc (analyze) or analyze does not give
            MorphWord objects
        SourceError: If the source has no parts of speech (analyze) or no words
        ParameterError: When a class is defined, if feature_names is not a mapping of
            strings, stats_desc does not name pos and the statistics of feature_names,
            or values_desc is not a mapping of statistics to mappings of strings

    Example:
        >>> import spacy
        >>> from spacy.tokens import Doc
        >>> from anyts.morph_stats import MorphStats
        >>> doc = Doc(
        ...     spacy.blank("en").vocab,
        ...     words=["The", "cats", "sleep"],
        ...     pos=["DET", "NOUN", "VERB"],
        ...     morphs=["Definite=Def|PronType=Art", "Number=Plur", "Tense=Pres|VerbForm=Fin"],
        ... )
        >>> MorphStats(doc).get_stats("pos", "number", filter_none=True)
        {'pos': {'DET': 1, 'NOUN': 1, 'VERB': 1}, 'number': {'Plur': 1}}
    """

    feature_names: ClassVar[Mapping[str, str]] = MORPH_FEATURES
    stats_desc: ClassVar[Mapping[str, str]] = MORPH_STATS_DESC
    values_desc: ClassVar[Mapping[str, Mapping[str, str]]] = MORPH_VALUES_DESC
    unknown_value: ClassVar[str] = "Unknown"
    markers_desc: ClassVar[Mapping[str, str]] = {}
    markers_headers: ClassVar[tuple[str, str]] = ("Marker", "Value")
    # The statistics of the default features, set by name with those of feature_names
    animacy: tuple[str | None, ...]
    aspect: tuple[str | None, ...]
    case: tuple[str | None, ...]
    definite: tuple[str | None, ...]
    degree: tuple[str | None, ...]
    gender: tuple[str | None, ...]
    mood: tuple[str | None, ...]
    num_type: tuple[str | None, ...]
    number: tuple[str | None, ...]
    person: tuple[str | None, ...]
    polarity: tuple[str | None, ...]
    polite: tuple[str | None, ...]
    poss: tuple[str | None, ...]
    pron_type: tuple[str | None, ...]
    reflex: tuple[str | None, ...]
    tense: tuple[str | None, ...]
    verb_form: tuple[str | None, ...]
    voice: tuple[str | None, ...]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        names = cls.feature_names
        if not (
            isinstance(names, Mapping)
            and all(
                isinstance(stat, str) and isinstance(name, str) for stat, name in names.items()
            )
            and "pos" not in names
        ):
            raise ParameterError(
                cls.messages["morph_features"].format(cls=cls.__name__, value=repr(names))
            )
        stats = list(cls.stats_desc)
        if len(stats) != len(names) + 1 or set(stats) != {"pos", *names}:
            raise ParameterError(
                cls.messages["morph_stats_desc"].format(cls=cls.__name__, stats=stats)
            )
        values = cls.values_desc
        if not (
            isinstance(values, Mapping)
            and all(
                isinstance(descs, Mapping)
                and all(isinstance(item, str) for pair in descs.items() for item in pair)
                for descs in values.values()
            )
        ):
            raise ParameterError(
                cls.messages["morph_values_desc"].format(cls=cls.__name__, value=repr(values))
            )

    def __init__(self, source: Doc):
        messages = self.messages
        found = self.analyze(source)
        words = tuple(found) if isinstance(found, Iterable) else (found,)
        for word in words:
            if not isinstance(word, MorphWord):
                raise SourceTypeError(
                    messages["hook_morph_words"].format(
                        hook="analyze", cls=type(self).__name__, type=type(word).__name__
                    )
                )
        if not words:
            raise SourceError(messages["no_words"])
        self.words = tuple(word.word for word in words)
        self.tags = tuple(_conllu_features(word.features) for word in words)
        self.pos = tuple(word.pos for word in words)
        for stat, name in self.feature_names.items():
            setattr(self, stat, tuple(word.features.get(name) or None for word in words))

    def analyze(self, source: Doc) -> Iterable[MorphWord]:
        """
        Getting the words of a source with their features

        Description:
            The words of a Doc with the parts of speech (iter_doc_tokens), with
            token.pos_ and the features of token.morph; a library that reads a
            string or a Doc without these annotations overrides it

        Arguments:
            source (Doc): Data source

        Returns:
            iterable[MorphWord]: Words with their features

        Raises:
            SourceTypeError: If the source is not a Doc object
            SourceError: If the source has no parts of speech
        """
        messages = self.messages
        if not is_doc(source):
            raise source_type_error(messages, source)
        if not source.has_annotation("POS"):
            raise SourceError(messages["no_pos"])
        return [
            MorphWord(token.text, token.pos_ or None, token.morph.to_dict())
            for token in iter_doc_tokens(source)
        ]

    def get_stats(  # type: ignore[override]
        self, *args: str, filter_none: bool = False, flat: bool = False
    ) -> dict[str, Any]:
        """
        Getting the number of the words by value of every statistic

        Arguments:
            args (tuple[str]): Names of the selected statistics, all of them by default
            filter_none (bool): Leave out the words without the feature
            flat (bool): Keys such as pos_NOUN instead of nested dictionaries, without
                the words that lack the feature

        Returns:
            dict[str, dict[str, int]]: Number of the words by value of every statistic,
                in the order of the first occurrences; with flat, the numbers by keys
                statistic_value

        Raises:
            UnknownStatError: If a statistic is unknown
        """
        stats: dict[str, dict[str | None, int]] = {}
        for stat in self._checked_stats(args):
            counts = dict(Counter(getattr(self, stat)))
            stats[stat] = (
                {value: n for value, n in counts.items() if value} if filter_none else counts
            )
        if flat:
            return {
                f"{stat}_{value}": n
                for stat, counts in stats.items()
                for value, n in counts.items()
                if value is not None
            }
        return stats

    def explain_text(
        self, *args: str, filter_none: bool = False
    ) -> tuple[tuple[str, dict[str, str | None]], ...]:
        """
        Getting the values of the statistics word by word

        Arguments:
            args (tuple[str]): Names of the selected statistics, all of them by default
            filter_none (bool): Leave out the statistics a word lacks

        Returns:
            tuple[tuple[str, dict[str, str|None]]]: Every word with the values of its
                statistics

        Raises:
            UnknownStatError: If a statistic is unknown
        """
        stats = self._checked_stats(args)
        columns = zip(*(getattr(self, stat) for stat in stats), strict=True)
        return tuple(
            (
                word,
                {
                    stat: value
                    for stat, value in zip(stats, values, strict=True)
                    if value or not filter_none
                },
            )
            for word, values in zip(self.words, columns, strict=True)
        )

    def print_stats(self, *args: str, filter_none: bool = False) -> None:
        """
        Printing the number of the words by value with the descriptions of the values

        Description:
            A table for every statistic, its values from the most frequent; a value
            of several joins the descriptions of its parts with a slash

        Arguments:
            args (tuple[str]): Names of the selected statistics, all of them by default
            filter_none (bool): Leave out the words without the feature

        Raises:
            UnknownStatError: If a statistic is unknown
        """
        for stat, counts in self.get_stats(*args, filter_none=filter_none).items():
            print(self.stats_desc[stat].center(40, "-"))
            descs = self.values_desc.get(stat, {})
            for value, number in sorted(counts.items(), key=lambda item: item[1], reverse=True):
                print(f"{self._value_desc(descs, value):30}|{number!s:^10}")
            print()

    def _value_desc(self, descs: Mapping[str, str], value: str | None) -> str:
        """Description of a value of a statistic for print_stats"""
        if not value:
            return self.unknown_value
        if value in descs:
            return descs[value]
        return " / ".join(descs.get(part, part) for part in value.split(","))

    def get_markers(self) -> dict[str, float]:
        """
        Getting the markers of the language computed from the features

        Description:
            Shares of the grammatical forms, each of its own base, by the names
            of markers_desc; a library computes them, there are none by default

        Returns:
            dict[str, float]: Markers by name
        """
        return {}

    def print_markers(self) -> None:
        """Printing the markers of get_markers with the descriptions of markers_desc"""
        markers = self.get_markers()
        _print_table(
            [(desc, markers[marker]) for marker, desc in self.markers_desc.items()],
            self.markers_headers,
        )

    def _checked_stats(self, stats: tuple[str, ...]) -> tuple[str, ...]:
        """Selected statistics checked by their names; all of them when none is selected"""
        for stat in stats:
            self._check_stat(stat)
        return stats or self.stat_names()


def _conllu_features(features: Mapping[str, str]) -> str:
    """Features of a word in the CoNLL-U format, by the names in order; _ without them"""
    return "|".join(f"{name}={value}" for name, value in sorted(features.items()) if value) or "_"
