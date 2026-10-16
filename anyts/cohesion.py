from collections import Counter
from collections.abc import Collection, Iterable, Mapping, Sequence
from itertools import pairwise
from math import fsum, nan
from typing import Any, ClassVar, NamedTuple

import numpy as np

from .constants import CONNECTOR_CLASSES, CONNECTOR_KINDS, CONNECTOR_POS, MESSAGES
from .exceptions import ParameterError, SourceTypeError
from .utils import check_integer, check_messages, check_sequence, check_words, safe_divide


def _check_sents(sents: Iterable[Iterable[object]], what: str, ordered: bool = True) -> None:
    """Checking a list of sentences given as collections of their elements"""
    check_sequence(sents, "sentences")
    for sent in sents:
        check_words(sent, what, ordered)


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


def calc_overlap(sets: Sequence[Collection[str]], adjacent: bool = True) -> float:
    """
    Computing the share of pairs of sentences with a shared element

    Description:
        The binary overlap of Coh-Metrix (CRFNO1, CRFAO1, CRFSO1 over the
        adjacent pairs, CRFNOa, CRFAOa, CRFSOa over all): a pair of sentences is
        cohesive when they share at least one element; all the pairs are counted
        over bit masks of the sentences, without going through them

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


def calc_proportional_overlap(sets: Sequence[Collection[str]], adjacent: bool = True) -> float:
    """
    Computing the mean share of shared elements in pairs of sentences

    Description:
        The proportional overlap of Coh-Metrix (CRFCWO1, CRFCWOa): the Dice
        coefficient of a pair of sentences (dice) averaged over the pairs; over all
        the pairs the sum comes from the histograms of the lengths of the sentences
        holding every element (see calc_overlaps), without going through them

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
        Gives the values of calc_overlap and calc_proportional_overlap over the
        adjacent and all the pairs at once

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
        The repetition of the tense and of the mood of Coh-Metrix (SMTEMP): a
        pair of adjacent sentences is cohesive when the dominant values of the
        feature of their verbs are equal; a pair where one of the sentences has
        no verb with the feature is skipped

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
        A connector is matched by the normalized forms of its words (normalize,
        the lower case by default), the longest one at every position, without
        overlaps; a period or a hyphen inside a connector may be split off by
        the tokenizer (e.g.). The words are those of one sentence without
        punctuation, the first one its start. The context rules of a language
        are class attributes: a connector followed by a word of blocked_after,
        preceded by one of blocked_before or followed by a part of speech of
        blocked_after_pos is no connector, nor is one of not_at_start opening
        the sentence or one of only_after inside it after another word than
        those listed. With the parts of speech given, a one-word connector
        counts only with a part of speech of pos_tags or of pos_extra for its
        form, never after a part of speech of not_after_pos, and with one of
        start_only_pos only at the start of the sentence; without them the
        rules that read a part of speech are skipped. The rules are empty by
        default

    Arguments:
        connectors (dict[str, tuple[str, str]]): Class and kind by connector

    Methods:
        normalize: Normalized form of a word or a connector
        find: Finding the connectors of a sentence

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
        messages (dict[str, str]): Messages of the errors by key (MESSAGES)

    Raises:
        SourceTypeError: If the connectors are not a dictionary of a phrase and a pair
            of strings
        ParameterError: If a connector has an unknown class or kind

    Example:
        >>> from anyts.cohesion import ConnectorMatcher
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
    messages: ClassVar[Mapping[str, str]] = MESSAGES

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        check_messages(cls.messages)

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
    ) -> list[Connector]:
        """
        Finding the connectors of a sentence

        Arguments:
            words (list[str]): Words of the sentence without punctuation
            sent_index (int): Number of the sentence, written into the occurrences
            pos (list[str]): Parts of speech of the words, None for a word without one;
                without them the rules that read a part of speech are skipped

        Returns:
            list[Connector]: Occurrences of the connectors in the order of the words

        Raises:
            SourceTypeError: If the words are not a list of strings or the parts of
                speech are not a list of strings and None
            ParameterError: If the number of the sentence is not an integer or the parts
                of speech are not as many as the words
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
        normalized = [self.normalize(word) for word in words]
        found = []
        position = 0
        while position < len(normalized):
            for pattern in self._by_first.get(normalized[position], ()):
                end = position + len(pattern)
                if tuple(normalized[position:end]) != pattern:
                    continue
                text, cls, kind = self._entries[" ".join(pattern)]
                if self._is_blocked(text, normalized, position, end, pos):
                    continue
                if (
                    len(pattern) == 1
                    and pos is not None
                    and not self._is_pos(pattern[0], pos, position)
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
    ) -> bool:
        """Whether the context of the words of a connector makes them no connector"""
        following = words[end] if end < len(words) else ""
        previous = words[position - 1] if position else ""
        if following in self.blocked_after.get(text, ()):
            return True
        if previous in self.blocked_before.get(text, ()):
            return True
        if position == 0 and text in self.not_at_start:
            return True
        if position and text in self.only_after and previous not in self.only_after[text]:
            return True
        if pos is None or end >= len(pos):
            return False
        return pos[end] in self.blocked_after_pos.get(text, ())

    def _is_pos(self, word: str, pos: Sequence[str | None], position: int) -> bool:
        """Whether the part of speech of a one-word connector lets it count"""
        tag = pos[position]
        if tag is None:
            return True
        if position and pos[position - 1] in self.not_after_pos:
            return False
        if tag in self.start_only_pos:
            return position == 0
        return tag in self.pos_tags or tag in self.pos_extra.get(word, ())
