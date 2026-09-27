from collections import Counter
from collections.abc import Mapping, Sequence
from math import floor, fsum, log2
from typing import NamedTuple

import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist, jensenshannon, pdist, squareform

from ..constants import DELTA_VARIANTS
from ..exceptions import ParameterError, SourceError
from ..utils import check_integer, check_sequence, check_words

ZERO_SEGMENTS = 0.5


class ZetaScore(NamedTuple):
    """
    Zeta score of a word - the difference of the shares of the segments of two corpora with it

    Attributes:
        word (str): Word
        dp_target (float): Share of the segments of the target corpus with the word
        dp_comparison (float): Share of the segments of the comparison corpus with the word
        zeta (float): Zeta - the difference of the shares, from −1 to 1
        log_zeta (float): Logarithmic Zeta - the binary logarithm of the ratio of the shares
    """

    word: str
    dp_target: float
    dp_comparison: float
    zeta: float
    log_zeta: float


def frequency_table(
    corpus: Mapping[str, Sequence[str]], n_mfw: int | None = 100, culling: float = 0.0
) -> pd.DataFrame:
    """
    Building the table of relative frequencies of the most frequent units of a corpus

    Description:
        Rows are the texts, columns the units (words or character N-grams) by
        descending mean relative frequency over the texts, alphabetically when
        equal; a value is the frequency of the unit in the text divided by the
        length of the text. Culling keeps the units that occur in at least the
        given share of the texts, as in stylo

    Arguments:
        corpus (dict[str, list[str]]): Units of the texts by the names of the texts
        n_mfw (int): Number of the most frequent units; None - all of them
        culling (float): Smallest share of the texts a unit occurs in

    Returns:
        DataFrame: Table of relative frequencies

    Raises:
        SourceTypeError: If the units of a text are not a list of strings (check_words)
        SourceError: If the corpus is empty, holds a text without units or no
            unit is left after culling
        ParameterError: If n_mfw is below one or culling outside [0, 1]

    Example:
        >>> from anyts.corpus import frequency_table
        >>> corpus = {"A": "the cat and the dog".split(), "B": "a house and the garden".split()}
        >>> frequency_table(corpus, n_mfw=2)
           the  and
        A  0.4  0.2
        B  0.2  0.2
    """
    if not corpus:
        raise SourceError("The corpus has no texts")
    for units in corpus.values():
        check_words(units, "units of a text")
    if any(len(units) == 0 for units in corpus.values()):
        raise SourceError("The corpus holds a text without units")
    if not 0 <= culling <= 1:
        raise ParameterError("The share of texts for culling must lie between 0 and 1")
    if n_mfw is not None:
        check_integer(n_mfw, "number of the most frequent units")
    if n_mfw is not None and n_mfw < 1:
        raise ParameterError("The number of the most frequent units must be greater than 0")
    rows = {
        name: {unit: count / len(units) for unit, count in Counter(units).items()}
        for name, units in corpus.items()
    }
    shares: dict[str, list[float]] = {}
    for row in rows.values():
        for unit, share in row.items():
            shares.setdefault(unit, []).append(share)
    n_texts = len(rows)
    # fsum keeps the mean free of the order of the texts, and 12 significant digits
    # let equal rational means tie, so that they go alphabetically
    means = {unit: float(f"{fsum(values) / n_texts:.12g}") for unit, values in shares.items()}
    selected = sorted(
        (unit for unit in means if len(shares[unit]) / n_texts >= culling),
        key=lambda unit: (-means[unit], unit),
    )
    if n_mfw:
        selected = selected[:n_mfw]
    if not selected:
        raise SourceError("No unit is left after culling")
    columns = {unit: [row.get(unit, 0.0) for row in rows.values()] for unit in selected}
    return pd.DataFrame(columns, index=list(rows))


def z_scores(table: pd.DataFrame) -> pd.DataFrame:
    """
    Standardizing a table of frequencies by column

    Description:
        z = (x − mean) / sd with the sample standard deviation; a column with
        the same frequency in every text gives zeros

    Arguments:
        table (DataFrame): Table of relative frequencies

    Returns:
        DataFrame: Table of z-scores

    Example:
        >>> from anyts.corpus import frequency_table, z_scores
        >>> corpus = {"A": "the cat and the dog".split(), "B": "a house and the garden".split()}
        >>> z_scores(frequency_table(corpus, n_mfw=2)).round(3)
             the  and
        A  0.707  0.0
        B -0.707  0.0
    """
    constant = _constant_columns(table)
    scaled = (table - table.mean(axis=0)) / table.std(axis=0, ddof=1).where(~constant, 1.0)
    scaled.loc[:, constant] = 0.0
    return scaled


def _constant_columns(table: pd.DataFrame) -> pd.Series:
    """Columns with the same value in every row: equal relative frequencies are equal floats"""
    return table.max(axis=0) == table.min(axis=0)


def delta(
    corpus: Mapping[str, Sequence[str]],
    n_mfw: int | None = 100,
    variant: str = "burrows",
    culling: float = 0.0,
) -> pd.DataFrame:
    """
    Computing the distances between texts by Burrows's Delta and its variants

    Description:
        Over the z-scores of the relative frequencies of the n most frequent
        units (frequency_table, z_scores), as in stylo: burrows - the Manhattan
        distance divided by n (Burrows 2002); quadratic - the Euclidean one
        divided by n (Argamon 2008); eder - the Manhattan one with the weights
        (n − rank + 2) / n by the rank of the unit; cosine - 1 − cos (Smith and
        Aldridge 2011, Evert et al. 2015). The units are word forms or
        character N-grams (CharNgramsExtractor). At least three texts are
        needed: with two, the z-scores degenerate to ±1/√2

    References:
        https://aclanthology.org/W15-0709.pdf
        https://github.com/computationalstylistics/stylo

    Arguments:
        corpus (dict[str, list[str]]): Units of the texts by the names of the texts
        n_mfw (int): Number of the most frequent units; None - all of them
        variant (str): Variant of Delta of DELTA_VARIANTS
        culling (float): Smallest share of the texts a unit occurs in

    Returns:
        DataFrame: Symmetric matrix of distances with the names of the texts

    Raises:
        ParameterError: If the variant is unknown or n_mfw is below one
        SourceError: If there are fewer than three texts
        SourceTypeError: If the units of a text are not a list of strings (check_words)

    Example:
        >>> from anyts.corpus import delta
        >>> corpus = {
        ...     "A": "the cat and the dog".split(),
        ...     "B": "a house and the garden".split(),
        ...     "C": "the cat in a house".split(),
        ... }
        >>> delta(corpus, n_mfw=4).round(3)
               A      B      C
        A  0.000  1.299  1.299
        B  1.299  0.000  0.866
        C  1.299  0.866  0.000
    """
    if variant not in DELTA_VARIANTS:
        raise ParameterError(f"Unknown variant of Delta: {variant}")
    if len(corpus) < 3:
        raise SourceError("The distances need at least three texts")
    scores = z_scores(frequency_table(corpus, n_mfw, culling))
    distances = squareform(_delta_distances(scores.to_numpy(), None, variant))
    return pd.DataFrame(distances, index=scores.index, columns=scores.index)


def delta_profiles(
    reference: Mapping[str, Sequence[str]],
    samples: Mapping[str, Sequence[str]],
    n_mfw: int | None = 100,
    variant: str = "burrows",
    culling: float = 0.0,
    statistics: Mapping[str, Sequence[str]] | None = None,
) -> pd.DataFrame:
    """
    Computing the distances by Delta from texts to reference texts

    Description:
        Authorship attribution: the most frequent units and the mean and
        deviation of the z-scores come from the reference texts or from a
        separate set statistics (the training windows, when the references are
        too few); the samples are scaled by the same statistics and compared
        by the variant of Delta, as in delta. The nearest reference in a row is
        the presumed author; the result for a sample does not depend on the
        other samples

    Arguments:
        reference (dict[str, list[str]]): Units of the reference texts by name
        samples (dict[str, list[str]]): Units of the texts under test by name
        n_mfw (int): Number of the most frequent units; None - all of them
        variant (str): Variant of Delta of DELTA_VARIANTS
        culling (float): Smallest share of the texts a unit occurs in
        statistics (dict[str, list[str]]): Texts for the list of units and the
            statistics of the scaling; None - the reference texts

    Returns:
        DataFrame: Distances, rows - the texts under test, columns - the reference texts

    Raises:
        ParameterError: If the variant is unknown or n_mfw is below one
        SourceError: If there are fewer than three texts for the statistics, no
            reference texts or texts under test, or one of them has no units
        SourceTypeError: If the units of a text are not a list of strings (check_words)

    Example:
        >>> from anyts.corpus import delta_profiles
        >>> reference = {
        ...     "A": "the cat and the dog".split(),
        ...     "B": "a house and the garden".split(),
        ...     "C": "the cat in a house".split(),
        ... }
        >>> delta_profiles(reference, {"?": "the dog and the cat".split()}, n_mfw=4).round(3)
             A      B      C
        ?  0.0  1.299  1.299
    """
    if variant not in DELTA_VARIANTS:
        raise ParameterError(f"Unknown variant of Delta: {variant}")
    basis = reference if statistics is None else statistics
    if len(basis) < 3:
        raise SourceError("The statistics of the scaling need at least three texts")
    _check_corpus(reference, "reference")
    _check_corpus(samples, "tested")
    table = frequency_table(basis, n_mfw, culling)
    mean = table.mean(axis=0)
    constant = _constant_columns(table)
    scale = table.std(axis=0, ddof=1).where(~constant, 1.0)
    scores = []
    for corpus in (reference, samples):
        frequencies = _relative_frequencies(corpus, table.columns)
        scaled = np.array((frequencies - mean) / scale)
        scaled[:, constant.to_numpy()] = 0.0
        scores.append(scaled)
    distances = _delta_distances(scores[1], scores[0], variant)
    return pd.DataFrame(distances, index=list(samples), columns=list(reference))


def _check_corpus(corpus: Mapping[str, Sequence[str]], what: str) -> None:
    """Checking that a corpus has texts, all of them sequences with units"""
    if not corpus:
        raise SourceError(f"There are no {what} texts")
    for units in corpus.values():
        check_words(units, "units of a text")
    if any(len(units) == 0 for units in corpus.values()):
        raise SourceError(f"One of the {what} texts has no units")


def _relative_frequencies(corpus: Mapping[str, Sequence[str]], columns: pd.Index) -> pd.DataFrame:
    """Relative frequencies of the given units in the texts of a corpus"""
    rows = []
    for units in corpus.values():
        counts = Counter(units)
        rows.append([counts.get(unit, 0) / len(units) for unit in columns])
    return pd.DataFrame(rows, index=list(corpus), columns=columns)


def _delta_distances(values: np.ndarray, others: np.ndarray | None, variant: str) -> np.ndarray:
    """
    Distances by a variant of Delta between rows of z-scores

    Arguments:
        values (ndarray): Z-scores of the texts, rows - the texts
        others (ndarray): Z-scores of the second texts; None - pairwise within
            values (the condensed form of pdist)
        variant (str): Variant of Delta of DELTA_VARIANTS

    Returns:
        ndarray: Distances
    """
    n_units = values.shape[1]
    if variant == "eder":
        weights = (n_units - np.arange(1, n_units + 1) + 2) / n_units
        values = values * weights
        others = None if others is None else others * weights
    metric = {"burrows": "cityblock", "quadratic": "euclidean", "eder": "cityblock"}.get(
        variant, "cosine"
    )
    distances = pdist(values, metric) if others is None else cdist(values, others, metric)
    if variant in ("burrows", "quadratic"):
        return np.asarray(distances / n_units)
    if variant == "cosine":
        return np.asarray(np.nan_to_num(distances, nan=0.0))
    return np.asarray(distances)


def zeta(
    target: Sequence[str] | Sequence[Sequence[str]],
    comparison: Sequence[str] | Sequence[Sequence[str]],
    segment_size: int = 2000,
    top_n: int | None = None,
) -> list[ZetaScore]:
    """
    Computing Zeta - the markers of preferred and avoided words

    Description:
        Every text is split into equal segments of about segment_size words,
        and DP is the share of the segments of a corpus where a word occurs.
        Zeta = DP_target − DP_comparison from −1 to 1 (Burrows 2007, Craig and
        Kinney 2009, as in stylo; the classic Zeta of Craig is greater by one),
        the logarithmic Zeta = log2(DP_target / DP_comparison) (Schöch et al.
        2018), a zero share replaced by half a segment. The list starts with
        the words the target corpus prefers and ends with the avoided ones

    References:
        https://dh2010.cch.kcl.ac.uk/academic-programme/abstracts/papers/html/ab-659.html
        https://github.com/computationalstylistics/stylo

    Arguments:
        target (list[str]|list[list[str]]): Words of the target corpus - one
            text or a list of texts
        comparison (list[str]|list[list[str]]): Words of the comparison corpus
        segment_size (int): Size of a segment in words
        top_n (int): Number of words from the start of the list; None - all of them

    Returns:
        list[ZetaScore]: Words by descending Zeta, by descending logarithmic Zeta
            and alphabetically when equal

    Raises:
        SourceTypeError: If the words, or the words of a text, are not a list of strings
        ParameterError: If the size of a segment or top_n is below one
        SourceError: If one of the corpora is empty

    Example:
        >>> from anyts.corpus import zeta
        >>> target = "the cat eats and the cat sleeps".split()
        >>> comparison = "the dog eats and the dog barks".split()
        >>> [(score.word, score.zeta) for score in zeta(target, comparison, segment_size=3, top_n=2)]
        [('cat', 1.0), ('sleeps', 0.5)]
    """
    check_integer(segment_size, "size of a segment")
    if segment_size < 1:
        raise ParameterError("The size of a segment must be greater than 0")
    if top_n is not None:
        check_integer(top_n, "number of words")
    if top_n is not None and top_n < 1:
        raise ParameterError("The number of words must be greater than 0")
    check_sequence(target)
    check_sequence(comparison)
    presence_target, n_target = _segment_presence(target, segment_size)
    presence_comparison, n_comparison = _segment_presence(comparison, segment_size)
    if not n_target or not n_comparison:
        raise SourceError("The data source has no words")
    scores = []
    for word in set(presence_target) | set(presence_comparison):
        dp_target = presence_target.get(word, 0) / n_target
        dp_comparison = presence_comparison.get(word, 0) / n_comparison
        log_zeta = log2(
            (dp_target or ZERO_SEGMENTS / n_target)
            / (dp_comparison or ZERO_SEGMENTS / n_comparison)
        )
        scores.append(
            ZetaScore(word, dp_target, dp_comparison, dp_target - dp_comparison, log_zeta)
        )
    scores.sort(key=lambda score: (-score.zeta, -score.log_zeta, score.word))
    return scores[:top_n] if top_n else scores


def _segment_presence(
    texts: Sequence[str] | Sequence[Sequence[str]], segment_size: int
) -> tuple[Counter[str], int]:
    """Number of the segments every word occurs in and the number of the segments"""
    if len(texts) and all(isinstance(text, str) for text in texts):
        texts = [texts]  # type: ignore[list-item]
    presence: Counter[str] = Counter()
    n_segments = 0
    for text in texts:
        check_words(text, "words of a text")
        if not len(text):
            continue
        for segment in np.array_split(
            np.asarray(text, dtype=object), max(1, floor(len(text) / segment_size + 0.5))
        ):
            presence.update(set(segment.tolist()))
            n_segments += 1
    return presence, n_segments


def kilgarriff_chi2(words_a: Sequence[str], words_b: Sequence[str], n_mfw: int = 500) -> float:
    """
    Computing Kilgarriff's chi-square distance between two corpora

    Description:
        Over the n most frequent words of the joint corpus (Kilgarriff 2001):
        for every word the expected frequencies in the corpora are proportional
        to their sizes, χ² = Σ (O − E)² / E over the words and both corpora.
        The value grows with the size of the corpora, so pairs of corpora are
        comparable with each other at equal sizes

    References:
        https://www.sketchengine.eu/wp-content/uploads/comparing_corpora_2001.pdf

    Arguments:
        words_a (list[str]): Words of the first corpus
        words_b (list[str]): Words of the second corpus
        n_mfw (int): Number of the most frequent words of the joint corpus

    Returns:
        float: Value of the chi-square

    Raises:
        SourceTypeError: If the words are not a list of strings (check_words)
        ParameterError: If n_mfw is below one
        SourceError: If one of the corpora is empty

    Example:
        >>> from anyts.corpus import kilgarriff_chi2
        >>> round(kilgarriff_chi2(["the", "cat", "the"], ["the", "dog", "a"], n_mfw=1), 3)
        0.333
    """
    check_integer(n_mfw, "number of the most frequent words")
    if n_mfw < 1:
        raise ParameterError("The number of the most frequent words must be greater than 0")
    check_words(words_a)
    check_words(words_b)
    counts_a = Counter(words_a)
    counts_b = Counter(words_b)
    size_a = sum(counts_a.values())
    size_b = sum(counts_b.values())
    if not size_a or not size_b:
        raise SourceError("The data source has no words")
    joint = counts_a + counts_b
    words = sorted(joint, key=lambda word: (-joint[word], word))[:n_mfw]
    total = size_a + size_b
    chi2 = 0.0
    for word in words:
        expected_a = size_a * joint[word] / total
        expected_b = size_b * joint[word] / total
        chi2 += (counts_a[word] - expected_a) ** 2 / expected_a
        chi2 += (counts_b[word] - expected_b) ** 2 / expected_b
    return chi2


def mendenhall_curve(words: Sequence[str]) -> dict[int, float]:
    """
    Computing the Mendenhall curve - the distribution of the words by length

    Description:
        The share of the words of every length in characters (Mendenhall 1887)

    Arguments:
        words (list[str]): Words of the text

    Returns:
        dict[int, float]: Shares of the words by length, by ascending length

    Raises:
        SourceTypeError: If the words are not a list of strings (check_words)
        SourceError: If there are no words

    Example:
        >>> from anyts.corpus import mendenhall_curve
        >>> mendenhall_curve(["an", "idea", "a", "an", "image"])
        {1: 0.2, 2: 0.4, 4: 0.2, 5: 0.2}
    """
    check_words(words)
    if not len(words):
        raise SourceError("The data source has no words")
    counts = Counter(len(word) for word in words)
    return {length: counts[length] / len(words) for length in sorted(counts)}


def mendenhall_distance(words_a: Sequence[str], words_b: Sequence[str]) -> float:
    """
    Computing the distance between the Mendenhall curves of two texts

    Description:
        The Jensen-Shannon distance with base 2 between the distributions of
        the words by length - from 0 (the distributions coincide) to 1

    Arguments:
        words_a (list[str]): Words of the first text
        words_b (list[str]): Words of the second text

    Returns:
        float: Jensen-Shannon distance

    Raises:
        SourceTypeError: If the words are not a list of strings (check_words)
        SourceError: If one of the texts has no words

    Example:
        >>> from anyts.corpus import mendenhall_distance
        >>> mendenhall_distance(["the", "cat"], ["a", "house"])
        1.0
    """
    curve_a = mendenhall_curve(words_a)
    curve_b = mendenhall_curve(words_b)
    lengths = sorted(set(curve_a) | set(curve_b))
    return float(
        jensenshannon(
            [curve_a.get(length, 0.0) for length in lengths],
            [curve_b.get(length, 0.0) for length in lengths],
            base=2,
        )
    )
