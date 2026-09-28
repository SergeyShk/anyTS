from collections import Counter
from collections.abc import Collection, Iterable, Sequence
from itertools import pairwise
from math import fsum, nan
from typing import NamedTuple

import numpy as np

from .utils import check_sequence, check_words, safe_divide


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
    if not values:
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
