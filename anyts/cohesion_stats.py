from __future__ import annotations

from collections import Counter
from collections.abc import Collection, Iterable, Mapping, Sequence
from itertools import pairwise
from math import fsum, nan
from statistics import fmean
from typing import TYPE_CHECKING, Any, ClassVar, NamedTuple

import numpy as np

from .constants import (
    COHESION_STATS_DESC,
    CONNECTOR_CLASSES,
    CONNECTOR_KINDS,
    CONNECTOR_PLACES,
    CONNECTOR_POS,
    CONTENT_UD_POS,
    MESSAGES,
    TEMPORAL_FEATURES,
)
from .exceptions import ParameterError, SourceError, SourceTypeError
from .extractors import SentsExtractor
from .stats import Stats
from .utils import (
    check_integer,
    check_messages,
    check_sequence,
    check_words,
    find_unit_marks,
    has_sents,
    is_doc,
    iter_doc_units,
    safe_divide,
    split_doc_units,
)

if TYPE_CHECKING:
    from spacy.tokens import Doc, Token


class Overlap(NamedTuple):
    """
    Overlaps of the sentences of a text

    Attributes:
        adjacent (float): Share of adjacent pairs of sentences with a shared element
        all (float): Share of all pairs of sentences with a shared element
        prop_adjacent (float): Mean share of shared elements in adjacent pairs
        prop_all (float): Mean share of shared elements in all pairs
    """

    adjacent: float
    all: float
    prop_adjacent: float
    prop_all: float


class Connector(NamedTuple):
    """
    Occurrence of a connector in a sentence

    Attributes:
        sent (int): Number of the sentence
        start (int): Position of the first word of the connector in the sentence
        end (int): Position after the last word of the connector
        text (str): Connector as the dictionary writes it
        cls (str): Class of the connector
        kind (str): Kind of the connector
    """

    sent: int
    start: int
    end: int
    text: str
    cls: str
    kind: str


class ConnectorMatcher:
    """
    Search of the connectors of a dictionary in the sentences of a text

    Description:
        A connector is matched by the normalized forms of its words (normalize),
        the longest one at every position, without overlaps; a period or a
        hyphen inside a connector may be split off by the tokenizer (e.g.).
        The context rules of a language are class attributes, empty by default
        apart from the parts of speech of a one-word connector (pos_tags)

    Arguments:
        connectors (dict[str, tuple[str, str]]): Class and kind by connector

    Methods:
        normalize: Normalized form of a word or a connector
        find: Finding the connectors of a sentence
        is_subordinator: Whether a connector is a subordinating conjunction

    Class attributes:
        classes (tuple[str, ...]): Classes of the connectors (CONNECTOR_CLASSES)
        kinds (tuple[str, ...]): Kinds of the connectors (CONNECTOR_KINDS)
        pos_tags (frozenset[str]): Parts of speech of a one-word connector (CONNECTOR_POS)
        pos_extra (dict[str, frozenset[str]]): Parts of speech of a one-word connector
            on top of pos_tags by its normalized form
        not_after_pos (frozenset[str]): Parts of speech of the previous word that make
            a one-word connector no connector
        start_only_pos (frozenset[str]): Parts of speech of a one-word connector that
            counts only at the start of a sentence
        blocked_after (dict[str, frozenset[str]]): Words after a connector, by its text,
            that make it no connector
        blocked_before (dict[str, frozenset[str]]): Words before a connector, by its text,
            that make it no connector
        blocked_after_pos (dict[str, frozenset[str]]): Parts of speech of the word after
            a connector, by its text, that make it no connector
        not_at_start (frozenset[str]): Connectors, by their text, that do not count at the
            start of a sentence
        only_after (dict[str, frozenset[str]]): Connectors, by their text, that count
            inside a sentence only after these words
        subordinators (frozenset[str]): Connectors, by their text, that are
            subordinating conjunctions besides the one-word ones tagged SCONJ
        messages (dict[str, str]): Messages of the errors by key (MESSAGES)

    Raises:
        SourceTypeError: If the connectors are not a dictionary of a phrase and a pair
            of strings; when a class is defined, if its rules are not collections of
            strings or mappings of strings to them
        ParameterError: If a connector has an unknown class or kind; when a class is
            defined, if a class or a kind takes the name inter or intra of the
            densities by place (CohesionStats)

    Example:
        >>> from anyts.cohesion_stats import ConnectorMatcher
        >>> class Matcher(ConnectorMatcher):
        ...     blocked_after = {"before": frozenset({"the"})}
        >>> matcher = Matcher({
        ...     "however": ("adversative", "secondary"),
        ...     "before": ("temporal", "primary"),
        ...     "on the other hand": ("adversative", "secondary"),
        ... })
        >>> [c.text for c in matcher.find("On the other hand he left before".split())]
        ['on the other hand', 'before']
        >>> matcher.find("He left before the end".split())
        []
    """

    classes: ClassVar[tuple[str, ...]] = CONNECTOR_CLASSES
    kinds: ClassVar[tuple[str, ...]] = CONNECTOR_KINDS
    pos_tags: ClassVar[frozenset[str]] = CONNECTOR_POS
    pos_extra: ClassVar[Mapping[str, frozenset[str]]] = {}
    not_after_pos: ClassVar[frozenset[str]] = frozenset()
    start_only_pos: ClassVar[frozenset[str]] = frozenset()
    blocked_after: ClassVar[Mapping[str, frozenset[str]]] = {}
    blocked_before: ClassVar[Mapping[str, frozenset[str]]] = {}
    blocked_after_pos: ClassVar[Mapping[str, frozenset[str]]] = {}
    not_at_start: ClassVar[frozenset[str]] = frozenset()
    only_after: ClassVar[Mapping[str, frozenset[str]]] = {}
    subordinators: ClassVar[frozenset[str]] = frozenset()
    messages: ClassVar[Mapping[str, str]] = MESSAGES

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        check_messages(cls.messages)
        for name in ("classes", "kinds"):
            check_words(getattr(cls, name), name)
            if reserved := [place for place in CONNECTOR_PLACES if place in getattr(cls, name)]:
                raise ParameterError(
                    f"The {name} of {cls.__name__} cannot be named {', '.join(reserved)}, "
                    "the names of the connectors by place"
                )
        for name in (
            "pos_tags",
            "not_after_pos",
            "start_only_pos",
            "not_at_start",
            "subordinators",
        ):
            check_words(getattr(cls, name), name, ordered=False)
        for name in (
            "pos_extra",
            "blocked_after",
            "blocked_before",
            "blocked_after_pos",
            "only_after",
        ):
            rules = getattr(cls, name)
            if not isinstance(rules, Mapping):
                raise SourceTypeError(
                    f"The {name} of {cls.__name__} must be a mapping, not {type(rules).__name__}"
                )
            check_words(list(rules), f"connectors of {name}")
            for words in rules.values():
                check_words(words, name, ordered=False)

    def __init__(self, connectors: Mapping[str, tuple[str, str]]):
        if not isinstance(connectors, Mapping):
            raise SourceTypeError(self.messages["connector_dict"])
        self._entries: dict[str, tuple[str, str, str]] = {}
        patterns: dict[str, set[tuple[str, ...]]] = {}
        for connector, value in connectors.items():
            if not (
                isinstance(connector, str)
                and isinstance(value, tuple | list)
                and len(value) == 2
                and all(isinstance(item, str) for item in value)
            ):
                raise SourceTypeError(
                    self.messages["connector_entry"].format(connector=repr(connector))
                )
            cls, kind = value
            if cls not in self.classes or kind not in self.kinds:
                raise ParameterError(self.messages["connector_class"].format(cls=cls, kind=kind))
            key = " ".join(self.normalize(connector).split())
            split = " ".join(key.replace("-", " ").replace(".", " ").split())
            for variant in (key, split):
                if variant:
                    self._entries[variant] = (connector, cls, kind)
                    pattern = tuple(variant.split())
                    patterns.setdefault(pattern[0], set()).add(pattern)
        self._by_first = {
            first: tuple(sorted(group, key=lambda pattern: (-len(pattern), pattern)))
            for first, group in patterns.items()
        }

    def normalize(self, text: str) -> str:
        """
        Getting the normalized form of a word or a connector

        Description:
            The lower case by default; a library overrides the method for the
            letters its texts write in two ways

        Arguments:
            text (str): Word or connector

        Returns:
            str: Normalized form
        """
        return text.lower()

    def find(
        self,
        words: Sequence[str],
        sent_index: int = 0,
        pos: Sequence[str | None] | None = None,
        breaks: Collection[int] | None = None,
    ) -> list[Connector]:
        """
        Finding the connectors of a sentence

        Description:
            The rules read the neighbours of a connector through no punctuation
            mark: with the positions of the marks, a word after a comma neither
            blocks nor lets the connector before it count (so, it is late)

        Arguments:
            words (list[str]): Words of the sentence without punctuation, the first
                one its start
            sent_index (int): Number of the sentence, written into the occurrences
            pos (list[str]): Parts of speech of the words, None for a word without one;
                without them the rules that read a part of speech are skipped
            breaks (set[int]): Positions of the words a punctuation mark stands
                before; without them the words are read as adjacent

        Returns:
            list[Connector]: Occurrences of the connectors in the order of the words

        Raises:
            SourceTypeError: If the words are not a list of strings, the parts of
                speech are not a list of strings and None, or the positions of the
                marks are not a collection
            ParameterError: If the number of the sentence or a position of a mark is
                not an integer, or the parts of speech are not as many as the words
        """
        check_words(words)
        check_integer(sent_index, "number of the sentence")
        if pos is not None:
            check_sequence(pos, "parts of speech")
            for tag in pos:
                if tag is not None and not isinstance(tag, str):
                    raise SourceTypeError(
                        self.messages["connector_pos_type"].format(type=type(tag).__name__)
                    )
            if len(pos) != len(words):
                raise ParameterError(self.messages["connector_pos"])
        marks: frozenset[int] = frozenset()
        if breaks is not None:
            check_sequence(breaks, "positions of the marks", ordered=False)
            for position in breaks:
                check_integer(position, "position of a mark")
            marks = frozenset(breaks)
        return self._find(words, sent_index, pos, marks)

    def is_subordinator(self, connector: Connector, pos: str | None = None) -> bool:
        """
        Checking whether a connector is a subordinating conjunction

        Description:
            A connector of subordinators, or a one-word connector whose part of
            speech is SCONJ; its clause belongs to the sentence of the connector,
            wherever it stands

        Arguments:
            connector (Connector): Occurrence of a connector
            pos (str): Part of speech of its first word, None when unknown

        Returns:
            bool: Result of the check
        """
        return connector.text in self.subordinators or (
            connector.end - connector.start == 1 and pos == "SCONJ"
        )

    def _find(
        self,
        words: Sequence[str],
        sent_index: int,
        pos: Sequence[str | None] | None,
        breaks: frozenset[int] = frozenset(),
    ) -> list[Connector]:
        """Connectors of a sentence whose words, parts of speech and marks are checked"""
        normalized = [self.normalize(word) for word in words]
        found = []
        position = 0
        while position < len(normalized):
            for pattern in self._by_first.get(normalized[position], ()):
                end = position + len(pattern)
                if tuple(normalized[position:end]) != pattern:
                    continue
                text, cls, kind = self._entries[" ".join(pattern)]
                if self._is_blocked(text, normalized, position, end, pos, breaks):
                    continue
                if (
                    len(pattern) == 1
                    and pos is not None
                    and not self._is_pos(pattern[0], pos, position, breaks)
                ):
                    continue
                found.append(Connector(sent_index, position, end, text, cls, kind))
                position = end
                break
            else:
                position += 1
        return found

    def _is_blocked(
        self,
        text: str,
        words: Sequence[str],
        position: int,
        end: int,
        pos: Sequence[str | None] | None,
        breaks: frozenset[int],
    ) -> bool:
        """Whether the context of the words of a connector makes them no connector"""
        # A punctuation mark cuts the connector off its neighbour on that side
        after = end < len(words) and end not in breaks
        before = position > 0 and position not in breaks
        if after and words[end] in self.blocked_after.get(text, ()):
            return True
        if before and words[position - 1] in self.blocked_before.get(text, ()):
            return True
        if position == 0 and text in self.not_at_start:
            return True
        if before and text in self.only_after and words[position - 1] not in self.only_after[text]:
            return True
        if not after or pos is None:
            return False
        return pos[end] in self.blocked_after_pos.get(text, ())

    def _is_pos(
        self, word: str, pos: Sequence[str | None], position: int, breaks: frozenset[int]
    ) -> bool:
        """Whether the part of speech of a one-word connector lets it count"""
        tag = pos[position]
        if tag is None:
            return True
        if position and position not in breaks and pos[position - 1] in self.not_after_pos:
            return False
        if tag in self.start_only_pos:
            return position == 0
        return tag in self.pos_tags or tag in self.pos_extra.get(word, ())


class CohesionWord(NamedTuple):
    """
    Word of a text for the cohesion statistics

    Attributes:
        word (str): Word as the text writes it
        lemma (str): Lemma by which the sentences are compared
        pos (str|None): Part of speech of Universal Dependencies for the rules of the
            connectors, None when unknown
        noun (bool): Whether the word is a noun
        pronoun (bool): Whether the word is a pronoun
        demonstrative (bool): Whether the word is a demonstrative
        argument (bool): Whether the word is an argument - a noun or a pronoun
        content (bool): Whether the word is a content word
        tense (str|None): Tense of a verb form
        mood (str|None): Mood of a verb form
        aspect (str|None): Aspect of a verb form
        break_before (bool): Whether a punctuation mark stands between the word and
            the one before it, which the rules of the connectors do not read through
    """

    word: str
    lemma: str
    pos: str | None
    noun: bool
    pronoun: bool
    demonstrative: bool
    argument: bool
    content: bool
    tense: str | None = None
    mood: str | None = None
    aspect: str | None = None
    break_before: bool = False


class CohesionStats(Stats):
    """
    Base of the cohesion statistics of a text

    Description:
        Cohesion in the manner of Coh-Metrix: the overlap of the nouns, of the
        arguments and of the content words between sentences, the givenness,
        the temporal cohesion and the connectors of a dictionary per 1000
        words. The sentences are compared by lemmas.
        A language library subclasses the class and sets its hooks; by default
        the source is a Doc with the parts of speech and the lemmas, read by
        Universal Dependencies, and there are no connectors.
        get_stats, to_dataframe, print_stats and describe come from Stats

    References:
        https://doi.org/10.1017/CBO9780511894664 (McNamara et al. 2014, Coh-Metrix)
        https://doi.org/10.3758/s13428-015-0651-7 (Crossley et al. 2016, TAACO)

    Arguments:
        source (Doc): Data source (a Doc object, or what analyze reads)
        sents_extractor (SentsExtractor): Sentence extraction tool; given, it splits a
            Doc by its text whatever its boundaries, and without it a Doc with no
            boundaries is split by sents_extractor_class()
        connectors (dict[str, tuple[str, str]]): Class and kind by connector;
            load_connectors() by default

    Attributes:
        sents_extractor (SentsExtractor|None): Sentence extraction tool given
        words (tuple[tuple[str, ...], ...]): Words of every sentence with words
        lemmas (tuple[tuple[str, ...], ...]): Lemmas of every sentence with words
        n_sents (int): Number of sentences with words
        n_words (int): Number of words
        n_nouns (int): Number of nouns
        n_pronouns (int): Number of pronouns
        n_demonstratives (int): Number of demonstratives
        n_content_words (int): Number of content words
        n_given (int): Number of content words whose lemma was used before
        n_connectors (int): Number of connectors
        n_inter_connectors (int): Number of the connectors linking a sentence to the
            ones before
        connector_spans (tuple[Connector]): Occurrences of the connectors
        c_connectors (dict[str, int]): Number of the occurrences by connector
        noun_overlap_adjacent (float): Share of adjacent pairs of sentences sharing a noun
        noun_overlap_all (float): Share of all pairs of sentences sharing a noun
        argument_overlap_adjacent (float): Share of adjacent pairs sharing a noun or a pronoun
        argument_overlap_all (float): Share of all pairs sharing a noun or a pronoun
        content_overlap_adjacent (float): Share of adjacent pairs sharing a content word
        content_overlap_all (float): Share of all pairs sharing a content word
        content_overlap_prop_adjacent (float): Mean share of shared content words in
            adjacent pairs of sentences
        content_overlap_prop_all (float): Mean share of shared content words in all pairs
        p_pronouns (float): Share of pronouns among the words
        pronoun_noun_ratio (float): Ratio of the pronouns to the nouns
        p_demonstratives (float): Share of demonstratives among the words
        p_given (float): Share of content words whose lemma was used before in the text
        tense_repetition (float): Share of adjacent pairs of sentences with the same
            dominant tense
        mood_repetition (float): The same for the mood
        aspect_repetition (float): The same for the aspect
        temporal_cohesion (float): Mean of the repetitions of temporal_features
        connectors (float): Connectors per 1000 words
        connectors_inter (float): Inter-sentential connectors per 1000 words: those
            opening a sentence, unless a subordinating conjunction by is_subordinator
            of the matcher, whose clause belongs to the same sentence
        connectors_intra (float): Intra-sentential connectors per 1000 words, the
            others
        connectors_<class>, connectors_<kind> (float): Connectors of every class and
            kind of the matcher per 1000 words: connectors_causal, ...,
            connectors_primary, connectors_secondary by default; a matcher with
            other classes or kinds needs a stats_desc of its own

    Methods:
        analyze: Words of the sentences of a source with their features
        doc_units: Words of the sentences of a Doc as lists of tokens
        word_info: Features of a word of a Doc
        load_connectors: Dictionary of the connectors of the language
        connector_matcher: Matcher of the dictionary of the class, built once

    Class attributes:
        sents_extractor_class (type): Sentence extractor of a Doc with no boundaries
        connector_matcher_class (type): Class that finds the connectors (ConnectorMatcher)
        join_hyphens (bool): Take a word the tokenizer split at its hyphens for one word
        temporal_features (tuple[str, ...]): Features of the verbs whose repetitions
            make the temporal cohesion: one or more of tense, mood, aspect
        stats_desc (dict[str, str]): Statistics of get_stats and their descriptions for
            print_stats

    Raises:
        SourceTypeError: If the extractor is of another type, the source is not a Doc
            (analyze), analyze does not give sentences of CohesionWord objects, or the
            connectors are not a dictionary of phrases and pairs of strings
        SourceError: If the source has no parts of speech or no lemmas (analyze), or no
            words
        ParameterError: If a connector has an unknown class or kind; when a class is
            defined, if its temporal features are not one or more distinct known ones
    """

    sents_extractor_class: ClassVar[type[SentsExtractor]] = SentsExtractor
    connector_matcher_class: ClassVar[type[ConnectorMatcher]] = ConnectorMatcher
    join_hyphens: ClassVar[bool] = False
    temporal_features: ClassVar[tuple[str, ...]] = ("tense", "aspect")
    stats_desc: ClassVar[Mapping[str, str]] = COHESION_STATS_DESC
    _connector_matcher: ClassVar[ConnectorMatcher | None] = None
    # The densities of the default classes and kinds, set by name with those of the matcher
    connectors_causal: float
    connectors_adversative: float
    connectors_concessive: float
    connectors_temporal: float
    connectors_additive: float
    connectors_conditional: float
    connectors_reformulative: float
    connectors_primary: float
    connectors_secondary: float

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        features = cls.temporal_features
        if (
            not isinstance(features, tuple)
            or not features
            or not all(isinstance(name, str) and name in TEMPORAL_FEATURES for name in features)
            or len(set(features)) != len(features)
        ):
            raise ParameterError(
                cls.messages["temporal_features"].format(
                    cls=cls.__name__, features=TEMPORAL_FEATURES, value=repr(features)
                )
            )

    def __init__(
        self,
        source: Doc,
        sents_extractor: SentsExtractor | None = None,
        connectors: Mapping[str, tuple[str, str]] | None = None,
    ):
        messages = self.messages
        if sents_extractor is not None and not isinstance(sents_extractor, SentsExtractor):
            raise SourceTypeError(messages["sents_extractor_type"])
        self.sents_extractor = sents_extractor
        matcher = (
            self.connector_matcher()
            if connectors is None
            else self.connector_matcher_class(connectors)
        )
        found = self.analyze(source)
        found_sents = [
            tuple(sent) if isinstance(sent, Iterable) else (sent,)
            for sent in (found if isinstance(found, Iterable) else [found])
        ]
        for item in (word for sent in found_sents for word in sent):
            if not isinstance(item, CohesionWord):
                raise SourceTypeError(
                    messages["hook_result"].format(
                        hook="analyze",
                        cls=type(self).__name__,
                        expected="sentences of CohesionWord objects",
                        type=type(item).__name__,
                    )
                )
        sents = [sent for sent in found_sents if sent]
        if not sents:
            raise SourceError(messages["no_words"])
        self.words = tuple(tuple(word.word for word in sent) for sent in sents)
        self.lemmas = tuple(tuple(word.lemma for word in sent) for sent in sents)
        self.n_sents = len(sents)
        self.n_words = sum(len(sent) for sent in sents)

        nouns = [frozenset(word.lemma for word in sent if word.noun) for sent in sents]
        arguments = [frozenset(word.lemma for word in sent if word.argument) for sent in sents]
        content = [[word.lemma for word in sent if word.content] for sent in sents]
        self.n_nouns = sum(1 for sent in sents for word in sent if word.noun)
        self.n_pronouns = sum(1 for sent in sents for word in sent if word.pronoun)
        self.n_demonstratives = sum(1 for sent in sents for word in sent if word.demonstrative)
        self.n_content_words = sum(len(sent) for sent in content)
        self.n_given = count_given(content)

        noun_overlap = calc_overlaps(nouns, proportional=False)
        argument_overlap = calc_overlaps(arguments, proportional=False)
        content_overlap = calc_overlaps([frozenset(sent) for sent in content])
        self.noun_overlap_adjacent = noun_overlap.adjacent
        self.noun_overlap_all = noun_overlap.all
        self.argument_overlap_adjacent = argument_overlap.adjacent
        self.argument_overlap_all = argument_overlap.all
        self.content_overlap_adjacent = content_overlap.adjacent
        self.content_overlap_all = content_overlap.all
        self.content_overlap_prop_adjacent = content_overlap.prop_adjacent
        self.content_overlap_prop_all = content_overlap.prop_all
        self.p_pronouns = self.n_pronouns / self.n_words
        self.pronoun_noun_ratio = safe_divide(self.n_pronouns, self.n_nouns, nan)
        self.p_demonstratives = self.n_demonstratives / self.n_words
        self.p_given = safe_divide(self.n_given, self.n_content_words, nan)
        self.tense_repetition = calc_repetition(
            [[word.tense for word in sent if word.tense] for sent in sents]
        )
        self.mood_repetition = calc_repetition(
            [[word.mood for word in sent if word.mood] for sent in sents]
        )
        self.aspect_repetition = calc_repetition(
            [[word.aspect for word in sent if word.aspect] for sent in sents]
        )
        self.temporal_cohesion = fmean(
            getattr(self, f"{feature}_repetition") for feature in self.temporal_features
        )

        self.connector_spans = tuple(
            connector
            for index, (words, sent) in enumerate(zip(self.words, sents, strict=True))
            for connector in matcher._find(
                words,
                index,
                [word.pos for word in sent],
                frozenset(i for i, word in enumerate(sent) if word.break_before),
            )
        )
        self.n_connectors = len(self.connector_spans)
        self.n_inter_connectors = sum(
            1
            for connector in self.connector_spans
            if connector.start == 0
            and not matcher.is_subordinator(connector, sents[connector.sent][0].pos)
        )
        self.c_connectors = dict(
            sorted(Counter(connector.text for connector in self.connector_spans).items())
        )
        per_1000 = 1000 / self.n_words
        classes = Counter(connector.cls for connector in self.connector_spans)
        kinds = Counter(connector.kind for connector in self.connector_spans)
        self.connectors = self.n_connectors * per_1000
        self.connectors_inter = self.n_inter_connectors * per_1000
        self.connectors_intra = (self.n_connectors - self.n_inter_connectors) * per_1000
        for name in matcher.classes:
            setattr(self, f"connectors_{name}", classes[name] * per_1000)
        for name in matcher.kinds:
            setattr(self, f"connectors_{name}", kinds[name] * per_1000)

    def analyze(self, source: Doc) -> Iterable[Sequence[CohesionWord]]:
        """
        Getting the words of the sentences of a source with their features

        Description:
            The words of a Doc with the parts of speech and the lemmas, sentence
            by sentence (doc_units), with the features of word_info; a library
            that reads a string or a Doc without these annotations overrides it

        Arguments:
            source (Doc): Data source

        Returns:
            iterable[list[CohesionWord]]: Words of every sentence

        Raises:
            SourceTypeError: If the source is not a Doc object
            SourceError: If the source has no parts of speech or no lemmas
        """
        messages = self.messages
        if not is_doc(source):
            raise SourceTypeError(messages["source_type"])
        if not source.has_annotation("POS"):
            raise SourceError(messages["no_pos"])
        if not source.has_annotation("LEMMA"):
            raise SourceError(messages["no_lemmas"])
        return [
            [
                self.word_info(unit)._replace(break_before=position in marks)
                for position, unit in enumerate(sent)
            ]
            for sent in self.doc_units(source)
            for marks in (find_unit_marks(sent),)
        ]

    def doc_units(self, doc: Doc) -> list[list[list[Token]]]:
        """
        Getting the words of the sentences of a Doc as lists of tokens

        Description:
            By the boundaries of the Doc, or by the sentences of the extractor
            over its text when one is given or the Doc has no boundaries
            (split_doc_units); with join_hyphens, the parts of a hyphenated
            word are one word (iter_doc_units)

        Arguments:
            doc (Doc): Doc object

        Returns:
            list[list[list[Token]]]: Tokens of every word of every sentence
        """
        if self.sents_extractor is not None or not has_sents(doc):
            return split_doc_units(
                doc, self.sents_extractor or self.sents_extractor_class(), self.join_hyphens
            )
        return [list(iter_doc_units(sent, self.join_hyphens)) for sent in doc.sents]

    def word_info(self, unit: Sequence[Token]) -> CohesionWord:
        """
        Getting the features of a word of a Doc by Universal Dependencies

        Description:
            A noun is NOUN or PROPN; a pronoun is PRON or a possessive,
            demonstrative or personal determiner (my book, this book, but not
            the book); a demonstrative carries PronType=Dem; an argument is
            NOUN, PROPN or PRON; a content word is one of CONTENT_UD_POS and no
            demonstrative; the tense, the mood and the aspect are the features
            Tense, Mood and Aspect. A word of several tokens (join_hyphens) is
            written and lemmatized by its joined text, with the other features
            of its first token

        Arguments:
            unit (list[Token]): Tokens of the word

        Returns:
            CohesionWord: Word with its features
        """
        token = unit[0]
        if len(unit) == 1:
            text, lemma = token.text, token.lemma_.lower()
        else:
            text = "".join(part.text for part in unit)
            lemma = text.lower()
        features = token.morph.to_dict()
        pron_type = features.get("PronType", "").split(",")
        demonstrative = "Dem" in pron_type
        pos = token.pos_
        return CohesionWord(
            word=text,
            lemma=lemma,
            pos=pos or None,
            noun=pos in ("NOUN", "PROPN"),
            pronoun=pos == "PRON" or (pos == "DET" and _is_pronominal_det(features, pron_type)),
            demonstrative=demonstrative,
            argument=pos in ("NOUN", "PROPN", "PRON"),
            content=not demonstrative and pos in CONTENT_UD_POS,
            tense=_first_value(features, "Tense"),
            mood=_first_value(features, "Mood"),
            aspect=_first_value(features, "Aspect"),
        )

    @classmethod
    def load_connectors(cls) -> Mapping[str, tuple[str, str]]:
        """
        Getting the dictionary of the connectors of the language

        Description:
            Read once for a class and shared by its instances; empty by default

        Returns:
            dict[str, tuple[str, str]]: Class and kind by connector
        """
        return {}

    @classmethod
    def connector_matcher(cls) -> ConnectorMatcher:
        """
        Getting the matcher of the dictionary of the connectors of the class

        Description:
            connector_matcher_class over load_connectors, built once for a class
            and shared by its instances and by searches outside the statistics

        Returns:
            ConnectorMatcher: Matcher of the dictionary
        """
        matcher = cls.__dict__.get("_connector_matcher")
        if matcher is None:
            matcher = cls.connector_matcher_class(cls.load_connectors())
            cls._connector_matcher = matcher
        return matcher


def _is_pronominal_det(features: Mapping[str, str], pron_type: list[str]) -> bool:
    """Whether a determiner points at something: my book, this book"""
    if "Yes" in features.get("Poss", "").split(","):
        return True
    return bool({"Dem", "Prs"} & set(pron_type))


def _first_value(features: Mapping[str, str], field: str) -> str | None:
    """First value of a morphological feature, None without it"""
    value = features.get(field)
    return value.split(",")[0] if value else None


def calc_overlap(sets: Sequence[Collection[str]], adjacent: bool = True) -> float:
    """
    Computing the share of pairs of sentences with a shared element

    Description:
        The binary overlap of Coh-Metrix (CRFNO1, CRFAO1, CRFSO1 over the
        adjacent pairs, CRFNOa, CRFAOa, CRFSOa over all): a pair of sentences is
        cohesive when they share at least one element; all the pairs are counted
        without going through them

    Arguments:
        sets (list[set[str]]): Elements of every sentence
        adjacent (bool): Count the adjacent pairs only, otherwise all the pairs

    Returns:
        float: Share of the pairs with a shared element, nan for a text shorter
            than two sentences

    Raises:
        SourceTypeError: If the sentences are a string, a Doc or an iterator, or a sentence
            is not a list of strings (check_words)
    """
    _check_sents(sets, "elements of a sentence", ordered=False)
    frozen = [frozenset(elements) for elements in sets]
    n_sents = len(frozen)
    if n_sents < 2:
        return nan
    if adjacent:
        return sum(1 for first, second in pairwise(frozen) if not first.isdisjoint(second)) / (
            n_sents - 1
        )
    return _count_sharing_pairs(frozen) / (n_sents * (n_sents - 1) // 2)


def _check_sents(sents: Iterable[Iterable[object]], what: str, ordered: bool = True) -> None:
    """Checking a list of sentences given as collections of their elements"""
    check_sequence(sents, "sentences")
    for sent in sents:
        check_words(sent, what, ordered)


def _count_sharing_pairs(sets: Sequence[frozenset[str]], block_size: int = 4096) -> int:
    """
    Number of pairs of sentences with a shared element, over bit masks of the occurrences

    Description:
        Every element gets a mask of the sentences of a block it occurs in; the
        union of the masks of sentence i gives the sentences it shares an
        element with, and the bits after i are counted
    """
    total = 0
    for start in range(0, len(sets), block_size):
        end = min(start + block_size, len(sets))
        masks: dict[str, int] = {}
        for j in range(start, end):
            bit = 1 << (j - start)
            for element in sets[j]:
                masks[element] = masks.get(element, 0) | bit
        for i in range(end):
            union = 0
            for element in sets[i]:
                union |= masks.get(element, 0)
            if i >= start:
                union >>= i - start + 1
            total += union.bit_count()
    return total


def calc_proportional_overlap(sets: Sequence[Collection[str]], adjacent: bool = True) -> float:
    """
    Computing the mean share of shared elements in pairs of sentences

    Description:
        The proportional overlap of Coh-Metrix (CRFCWO1, CRFCWOa): the Dice
        coefficient of a pair of sentences (dice) averaged over the pairs; over all
        the pairs the sum is computed without going through them

    Arguments:
        sets (list[set[str]]): Elements of every sentence
        adjacent (bool): Count the adjacent pairs only, otherwise all the pairs

    Returns:
        float: Mean share of shared elements, nan for a text shorter than two sentences

    Raises:
        SourceTypeError: If the sentences are a string, a Doc or an iterator, or a sentence
            is not a list of strings (check_words)
    """
    _check_sents(sets, "elements of a sentence", ordered=False)
    frozen = [frozenset(elements) for elements in sets]
    n_sents = len(frozen)
    if n_sents < 2:
        return nan
    if adjacent:
        return sum(dice(first, second) for first, second in pairwise(frozen)) / (n_sents - 1)
    return _sum_dice(frozen) / (n_sents * (n_sents - 1) // 2)


def _sum_dice(sets: Sequence[frozenset[str]]) -> float:
    """
    Sum of the Dice coefficients over all the pairs, over histograms of the lengths

    Description:
        A pair of sentences of lengths k and l gives 2/(k + l) for every shared
        element, so the sum over the pairs holding an element is
        (h·W·h - h·diag(W)) / 2, where h is the histogram of the lengths of its
        sentences and W[k, l] = 2/(k + l); the sums of the elements are added
        by fsum, so the result does not depend on their order
    """
    sizes = sorted({len(elements) for elements in sets if elements})
    columns = {size: column for column, size in enumerate(sizes)}
    postings: dict[str, list[int]] = {}
    for elements in sets:
        if not elements:
            continue
        column = columns[len(elements)]
        for element in elements:
            postings.setdefault(element, []).append(column)
    rows = [row for row in postings.values() if len(row) > 1]
    if not rows:
        return 0.0
    histograms = np.zeros((len(rows), len(sizes)))
    for index, row in enumerate(rows):
        np.add.at(histograms[index], row, 1)
    lengths = np.array(sizes, dtype=float)
    weights = 2 / (lengths[:, None] + lengths[None, :])
    full = np.einsum("ik,kl,il->i", histograms, weights, histograms)
    diagonal = (histograms * np.diag(weights)).sum(axis=1)
    return fsum(full - diagonal) / 2


def dice(first: frozenset[str], second: frozenset[str]) -> float:
    """
    Computing the Dice coefficient of two sets

    Arguments:
        first (frozenset[str]): First set
        second (frozenset[str]): Second set

    Returns:
        float: The coefficient 2·|A ∩ B| / (|A| + |B|), 0 for two empty sets
    """
    return safe_divide(2 * len(first & second), len(first) + len(second))


def calc_overlaps(sets: Sequence[Collection[str]], proportional: bool = True) -> Overlap:
    """
    Computing the binary and the proportional overlap over adjacent and all pairs

    Description:
        calc_overlap and calc_proportional_overlap in one call

    Arguments:
        sets (list[set[str]]): Elements of every sentence
        proportional (bool): Compute the proportional overlap as well; without it
            prop_adjacent and prop_all are nan

    Returns:
        Overlap: Shares of the pairs with a shared element and the mean Dice
            coefficients, nan for a text shorter than two sentences

    Raises:
        SourceTypeError: If the sentences are a string, a Doc or an iterator, or a sentence
            is not a list of strings (check_words)
    """
    _check_sents(sets, "elements of a sentence", ordered=False)
    frozen = [frozenset(elements) for elements in sets]
    n_sents = len(frozen)
    if n_sents < 2:
        return Overlap(nan, nan, nan, nan)
    n_all = n_sents * (n_sents - 1) // 2
    return Overlap(
        sum(1 for first, second in pairwise(frozen) if not first.isdisjoint(second))
        / (n_sents - 1),
        _count_sharing_pairs(frozen) / n_all,
        sum(dice(first, second) for first, second in pairwise(frozen)) / (n_sents - 1)
        if proportional
        else nan,
        _sum_dice(frozen) / n_all if proportional else nan,
    )


def count_given(sents: Sequence[Sequence[str]]) -> int:
    """
    Counting the given elements - the ones used before in the text

    Description:
        An element is given when the same lemma was used earlier in any sentence,
        the current one included; the first occurrence is new

    Arguments:
        sents (list[list[str]]): Lemmas of every sentence in the order of the text

    Returns:
        int: Number of given elements

    Raises:
        SourceTypeError: If the sentences are a string, a Doc or an iterator, or a sentence
            is not a list of strings (check_words)
    """
    _check_sents(sents, "lemmas of a sentence")
    seen: set[str] = set()
    given = 0
    for sent in sents:
        for lemma in sent:
            if lemma in seen:
                given += 1
            seen.add(lemma)
    return given


def dominant(values: Sequence[str]) -> str | None:
    """
    Getting the dominant value

    Description:
        The most frequent value, the first one of the equally frequent

    Arguments:
        values (list[str]): Values

    Returns:
        str|None: Dominant value, None for an empty list

    Raises:
        SourceTypeError: If the values are not a list of strings (check_words)
    """
    check_words(values, "values")
    if not len(values):
        return None
    return Counter(values).most_common(1)[0][0]


def calc_repetition(sents: Sequence[Sequence[str]]) -> float:
    """
    Computing the share of adjacent pairs of sentences with the same dominant value

    Description:
        The repetition of the tense and of the aspect of Coh-Metrix (SMTEMP): a
        pair of adjacent sentences is cohesive when the dominant values of the
        feature of their verbs are equal; a pair with a sentence without such a
        verb is skipped

    Arguments:
        sents (list[list[str]]): Values of the feature of the verbs of every sentence

    Returns:
        float: Share of the cohesive pairs, nan without a single pair with the feature

    Raises:
        SourceTypeError: If the sentences are a string, a Doc or an iterator, or a sentence
            is not a list of strings (check_words)
    """
    _check_sents(sents, "values of a sentence")
    pairs = [
        (first, second)
        for first, second in pairwise(dominant(sent) for sent in sents)
        if first and second
    ]
    if not pairs:
        return nan
    return sum(1 for first, second in pairs if first == second) / len(pairs)
