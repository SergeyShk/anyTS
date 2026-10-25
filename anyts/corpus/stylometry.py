from collections import Counter
from collections.abc import Collection, Iterator, Mapping, Sequence
from math import floor, fsum, log2
from typing import NamedTuple

import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist, jensenshannon, pdist, squareform

from ..constants import DELTA_VARIANTS
from ..exceptions import ParameterError, SourceError, SourceTypeError
from ..utils import _sliceable, check_integer, check_number, check_sequence, check_words

_ZERO_SEGMENTS = 0.5


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
        SourceTypeError: If the corpus is not a mapping or the units of a text
            are not a list of strings (check_words)
        SourceError: If the corpus is empty, holds a text without units or no
            unit is left after culling
        ParameterError: If n_mfw is below one or culling is not a number within [0, 1]

    Example:
        >>> from anyts.corpus import frequency_table
        >>> corpus = {"A": "the cat and the dog".split(), "B": "a house and the garden".split()}
        >>> frequency_table(corpus, n_mfw=2)
           the  and
        A  0.4  0.2
        B  0.2  0.2
    """
    _check_mapping(corpus, "corpus")
    if not corpus:
        raise SourceError("The corpus has no texts")
    for units in corpus.values():
        check_words(units, "units of a text")
    if any(len(units) == 0 for units in corpus.values()):
        raise SourceError("The corpus holds a text without units")
    _check_selection(n_mfw, culling)
    rows = {
        name: {unit: count / len(units) for unit, count in Counter(units).items()}
        for name, units in corpus.items()
    }
    shares: dict[str, list[float]] = {}
    for row in rows.values():
        for unit, share in row.items():
            shares.setdefault(unit, []).append(share)
    n_texts = len(rows)
    # fsum makes the mean independent of the order of the texts; 12 significant digits let
    # equal rational means tie and go alphabetically
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


def _check_selection(n_mfw: object, culling: object) -> None:
    """Checking the number of the most frequent units and the share for culling"""
    check_number(culling, "share of texts for culling")
    if not 0 <= culling <= 1:  # type: ignore[operator]  # a number after check_number
        raise ParameterError("The share of texts for culling must lie between 0 and 1")
    if n_mfw is not None:
        check_integer(n_mfw, "number of the most frequent units")
    if n_mfw is not None and n_mfw < 1:  # type: ignore[operator]  # an integer after check_integer
        raise ParameterError("The number of the most frequent units must be greater than 0")


def _check_mapping(corpus: object, what: str) -> None:
    """Checking that a corpus is a mapping of the names of its texts to their units"""
    if not isinstance(corpus, Mapping):
        raise SourceTypeError(
            f"The {what} must be a mapping of the names of the texts to their units, "
            f"not {type(corpus).__name__}"
        )


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
        SourceTypeError: If the corpus is not a mapping or the units of a text
            are not a list of strings (check_words)

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
    if not isinstance(variant, str) or variant not in DELTA_VARIANTS:
        raise ParameterError(f"Unknown variant of Delta: {variant}")
    _check_mapping(corpus, "corpus")
    if len(corpus) < 3:
        raise SourceError("The distances need at least three texts")
    scores = z_scores(frequency_table(corpus, n_mfw, culling))
    distances = squareform(_delta_distances(scores.to_numpy(), None, variant))
    return pd.DataFrame(distances, index=scores.index, columns=scores.index)


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
        separate set statistics (such as training windows when the references
        are too few); the samples are scaled by the same statistics and
        compared by the variant of Delta, as in delta. The nearest reference in
        a row is the presumed author; the result for a sample does not depend
        on the other samples

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
        SourceTypeError: If a corpus is not a mapping or the units of a text are
            not a list of strings (check_words)

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
    if not isinstance(variant, str) or variant not in DELTA_VARIANTS:
        raise ParameterError(f"Unknown variant of Delta: {variant}")
    _check_mapping(reference, "reference corpus")
    _check_mapping(samples, "tested corpus")
    if statistics is not None:
        _check_mapping(statistics, "corpus of the statistics")
    basis = reference if statistics is None else statistics
    if len(basis) < 3:
        raise SourceError("The statistics of the scaling need at least three texts")
    _check_corpus(reference, "reference")
    _check_corpus(samples, "tested")
    table = frequency_table(basis, n_mfw, culling)
    scores = [
        _scale(_relative_frequencies(corpus, table.columns), table)
        for corpus in (reference, samples)
    ]
    distances = _delta_distances(scores[1], scores[0], variant)
    return pd.DataFrame(distances, index=list(samples), columns=list(reference))


def _check_corpus(corpus: Mapping[str, Sequence[str]], what: str) -> None:
    """Checking that a corpus has texts, all of them sequences with units"""
    _check_mapping(corpus, f"{what} corpus")
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


def _scale(frequencies: pd.DataFrame, table: pd.DataFrame) -> np.ndarray:
    """Z-scores of frequencies by the means and deviations of the columns of a table"""
    constant = _constant_columns(table)
    scale = table.std(axis=0, ddof=1).where(~constant, 1.0)
    scaled = np.array((frequencies - table.mean(axis=0)) / scale)
    scaled[:, constant.to_numpy()] = 0.0
    return scaled


def rolling_delta(
    reference: Mapping[str, Sequence[str]],
    text: Sequence[str],
    window: int = 5000,
    step: int = 1000,
    n_mfw: int | None = 100,
    variant: str = "burrows",
    culling: float = 0.0,
    statistics: Mapping[str, Sequence[str]] | None = None,
) -> pd.DataFrame:
    """
    Computing the distances by Delta from the windows of a text to reference texts

    Description:
        The reference texts and the text under test are cut into windows of
        window units every step units, the rest shorter than a window dropped,
        as in stylo rolling.delta; the most frequent units, the culling and the
        mean and deviation of the z-scores come from the windows of the
        reference texts or of a separate set statistics. The distance by the
        variant of Delta goes from every window of the text to the centroid of
        the windows of every reference text; where the nearest reference changes
        along the text, so does the style. Scaled by their own windows, the
        centroids of the references balance each other: the cosine distances of
        a window to them average 1, and with two references they add up to 2

    Arguments:
        reference (dict[str, list[str]]): Units of the reference texts by name
        text (list[str]): Units of the text under test
        window (int): Size of a window in units
        step (int): Distance between the starts of the windows in units
        n_mfw (int): Number of the most frequent units; None - all of them
        variant (str): Variant of Delta of DELTA_VARIANTS
        culling (float): Smallest share of the windows a unit occurs in
        statistics (dict[str, list[str]]): Texts whose windows give the list of
            units and the statistics of the scaling; None - the reference texts

    Returns:
        DataFrame: Distances, rows - the windows of the text by the position of
            their middle, columns - the reference texts

    Raises:
        ParameterError: If the variant is unknown, the size of a window, the step
            or n_mfw is not an integer or is below one, the step exceeds the
            window, or culling is not a number within [0, 1]
        SourceError: If there are no reference texts, or fewer than two without
            statistics, a text is shorter than a window, the texts of the
            statistics have fewer than three windows or no unit is left after
            culling
        SourceTypeError: If a corpus is not a mapping or the units of a text are
            not a list of strings (check_words)

    Example:
        >>> from anyts.corpus import rolling_delta
        >>> reference = {
        ...     "A": "the cat and the cat and a cat".split(),
        ...     "B": "a dog or a dog or the dog".split(),
        ... }
        >>> text = "the cat and the cat a dog or a dog".split()
        >>> rolling_delta(reference, text, window=4, step=2, n_mfw=4).round(3)
               A      B
        2  0.306  1.327
        4  0.408  1.021
        6  1.021  0.408
        8  1.633  0.204
    """
    if not isinstance(variant, str) or variant not in DELTA_VARIANTS:
        raise ParameterError(f"Unknown variant of Delta: {variant}")
    for value, what in ((window, "size of a window"), (step, "step")):
        check_integer(value, what)
        if value < 1:
            raise ParameterError(f"The {what} must be greater than 0")
    if step > window:
        raise ParameterError("The step must not exceed the size of a window")
    _check_selection(n_mfw, culling)
    _check_corpus(reference, "reference")
    if statistics is None and len(reference) < 2:
        raise SourceError("The rolling Delta needs at least two reference texts")
    check_words(text, "units of the text")
    if statistics is not None:
        _check_corpus(statistics, "statistics")
    for corpus, what in ((reference, "reference"), (statistics or {}, "statistics")):
        if any(len(units) < window for units in corpus.values()):
            raise SourceError(f"One of the {what} texts is shorter than a window")
    if len(text) < window:
        raise SourceError("The text is shorter than a window")
    basis = [
        _sliceable(units) for units in (reference if statistics is None else statistics).values()
    ]
    if sum(len(_window_starts(len(units), window, step)) for units in basis) < 3:
        raise SourceError("The statistics of the scaling need at least three windows")
    columns = _window_units(basis, window, step, n_mfw, culling)
    table = np.vstack([_window_frequencies(units, columns, window, step) for units in basis])
    mean = table.mean(axis=0)
    constant = table.max(axis=0) == table.min(axis=0)
    scale = np.where(constant, 1.0, table.std(axis=0, ddof=1))
    centroids = [
        _scaled(
            _window_frequencies(_sliceable(units), columns, window, step), mean, scale, constant
        ).mean(axis=0)
        for units in reference.values()
    ]
    samples = _scaled(
        _window_frequencies(_sliceable(text), columns, window, step), mean, scale, constant
    )
    distances = _delta_distances(samples, np.array(centroids), variant)
    middles = [index * step + window // 2 for index in range(len(samples))]
    return pd.DataFrame(distances, index=middles, columns=list(reference))


def _window_starts(length: int, window: int, step: int) -> range:
    """Starts of the windows of a text, without the rest shorter than a window"""
    return range(0, length - window + 1, step)


def _window_units(
    texts: Sequence[Sequence[str]], window: int, step: int, n_mfw: int | None, culling: float
) -> list[str]:
    """
    The most frequent units of the windows of texts, as frequency_table of the windows gives
    them, without counting every window: the sum of the frequencies of a unit over the windows
    is the number of its occurrences weighted by the windows that cover them, and the windows
    with a unit are the union of the windows around its occurrences
    """
    ids: dict[str, int] = {}
    weights = np.zeros(0)
    windows_with = np.zeros(0, dtype=np.int64)
    for units in texts:
        codes = np.fromiter(
            (ids.setdefault(unit, len(ids)) for unit in units), dtype=np.int64, count=len(units)
        )
        last = len(_window_starts(len(units), window, step)) - 1
        positions = np.arange(len(units))
        # The windows around a position: from the first that reaches it to the last that starts before it
        first = -(-np.maximum(positions - window + 1, 0) // step)
        final = np.minimum(positions // step, last)
        covered = np.maximum(final - first + 1, 0)
        weights = _grown(weights, len(ids)) + np.bincount(
            codes, weights=covered, minlength=len(ids)
        )
        if culling:
            order = np.lexsort((positions, codes))
            sorted_codes, lows, highs = codes[order], first[order], final[order]
            same = np.concatenate([[False], sorted_codes[1:] == sorted_codes[:-1]])
            previous = np.where(same, np.concatenate([[-1], highs[:-1]]), -1)
            fresh = np.maximum(highs - np.maximum(lows, previous + 1) + 1, 0)
            windows_with = _grown(windows_with, len(ids)) + np.bincount(
                sorted_codes, weights=fresh, minlength=len(ids)
            ).astype(np.int64)
    n_windows = sum(len(_window_starts(len(units), window, step)) for units in texts)
    names = list(ids)
    kept = [
        code
        for code in range(len(names))
        if weights[code] > 0 and (not culling or windows_with[code] / n_windows >= culling)
    ]
    # The mean frequencies share the denominator: equal weights are equal means
    kept.sort(key=lambda code: (-weights[code], names[code]))
    if n_mfw:
        kept = kept[:n_mfw]
    if not kept:
        raise SourceError("No unit is left after culling")
    return [names[code] for code in kept]


def _grown(values: np.ndarray, size: int) -> np.ndarray:
    """Values padded with zeros to a size"""
    return np.concatenate([values, np.zeros(size - values.size, dtype=values.dtype)])


def _window_frequencies(
    units: Sequence[str], columns: Sequence[str], window: int, step: int
) -> np.ndarray:
    """Relative frequencies of the given units in the windows of a text, rows - the windows"""
    positions: dict[str, list[int]] = {unit: [] for unit in columns}
    for index, unit in enumerate(units):
        found = positions.get(unit)
        if found is not None:
            found.append(index)
    starts = np.array(_window_starts(len(units), window, step))
    counts = np.empty((starts.size, len(columns)))
    for column, unit in enumerate(columns):
        occurrences = np.array(positions[unit])
        counts[:, column] = np.searchsorted(occurrences, starts + window) - np.searchsorted(
            occurrences, starts
        )
    return counts / window


def _scaled(
    frequencies: np.ndarray, mean: np.ndarray, scale: np.ndarray, constant: np.ndarray
) -> np.ndarray:
    """Z-scores of frequencies by the means and deviations of the columns, 0 in a constant one"""
    scaled: np.ndarray = (frequencies - mean) / scale
    scaled[:, constant] = 0.0
    return scaled


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
            (dp_target or _ZERO_SEGMENTS / n_target)
            / (dp_comparison or _ZERO_SEGMENTS / n_comparison)
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
    presence: Counter[str] = Counter()
    n_segments = 0
    for segment in _segments(texts, segment_size):
        presence.update(segment)
        n_segments += 1
    return presence, n_segments


def _segments(
    texts: Sequence[str] | Sequence[Sequence[str]], segment_size: int
) -> Iterator[set[str]]:
    """Words of every segment of one text or of a list of texts"""
    if len(texts) and all(isinstance(text, str) for text in texts):
        texts = [texts]  # type: ignore[list-item]
    for text in texts:
        check_words(text, "words of a text")
        if not len(text):
            continue
        for segment in np.array_split(
            np.asarray(_sliceable(text), dtype=object),
            max(1, floor(len(text) / segment_size + 0.5)),
        ):
            yield set(segment.tolist())


def zeta_segments(
    corpora: Mapping[str, Sequence[str] | Sequence[Sequence[str]]],
    preferred: Collection[str],
    avoided: Collection[str],
    segment_size: int = 2000,
) -> pd.DataFrame:
    """
    Computing the shares of the markers of Zeta in the segments of corpora

    Description:
        Every text is split into segments as in zeta; a segment gets the
        shares of the preferred and of the avoided words found in it, as stylo
        oppose places the segments. With the markers of a target corpus against
        a comparison one, the segments of the target lie high on the left of
        the plane of the two shares, those of the comparison low on the right,
        and the segments of a disputed text fall near one of the groups

    Arguments:
        corpora (dict[str, list[str]|list[list[str]]]): Words of the corpora by
            name - one text or a list of texts each
        preferred (collection[str]): Words the target corpus prefers - the start
            of the list of zeta
        avoided (collection[str]): Words the target corpus avoids - the end of the list
        segment_size (int): Size of a segment in words

    Returns:
        DataFrame: Segments in the order of the corpora and of their texts;
            columns - corpus (the name of the corpus), preferred and avoided
            (the shares of the words of the lists found in the segment)

    Raises:
        ParameterError: If the size of a segment is below one
        SourceTypeError: If the corpora are not a mapping, or the words of a
            corpus or a list of markers are not a list of strings
        SourceError: If there are no corpora or no words in a list of markers,
            or a corpus has no words

    Example:
        >>> from anyts.corpus import zeta, zeta_segments
        >>> target = "the cat eats and the cat sleeps".split()
        >>> comparison = "the dog eats and the dog barks".split()
        >>> scores = zeta(target, comparison, segment_size=3)
        >>> preferred = [score.word for score in scores if score.zeta > 0]
        >>> avoided = [score.word for score in scores if score.zeta < 0]
        >>> corpora = {"cat": target, "dog": comparison, "?": "the cat barks".split()}
        >>> zeta_segments(corpora, preferred, avoided, segment_size=3)
          corpus  preferred  avoided
        0    cat        0.5      0.0
        1    cat        1.0      0.0
        2    dog        0.0      0.5
        3    dog        0.0      1.0
        4      ?        0.5      0.5
    """
    check_integer(segment_size, "size of a segment")
    if segment_size < 1:
        raise ParameterError("The size of a segment must be greater than 0")
    if not isinstance(corpora, Mapping):
        raise SourceTypeError(
            f"The corpora must be a mapping of their names to their words, "
            f"not {type(corpora).__name__}"
        )
    if not corpora:
        raise SourceError("There are no corpora")
    markers = []
    for words, what in ((preferred, "preferred"), (avoided, "avoided")):
        check_words(words, f"{what} words", ordered=False)
        if not len(words):
            raise SourceError(f"There are no {what} words")
        markers.append(set(words))
    rows = []
    for name, texts in corpora.items():
        check_sequence(texts)
        segments = list(_segments(texts, segment_size))
        if not segments:
            raise SourceError(f"The corpus {name} has no words")
        rows += [
            (
                name,
                len(segment & markers[0]) / len(markers[0]),
                len(segment & markers[1]) / len(markers[1]),
            )
            for segment in segments
        ]
    return pd.DataFrame(rows, columns=["corpus", "preferred", "avoided"])


def kilgarriff_chi2(words_a: Sequence[str], words_b: Sequence[str], n_mfw: int = 500) -> float:
    """
    Computing Kilgarriff's chi-square distance between two corpora

    Description:
        Over the n most frequent words of the joint corpus (Kilgarriff 2001):
        for every word the expected frequencies in the corpora are proportional
        to their sizes, χ² = Σ (O − E)² / E over the words and both corpora.
        The value grows with the size of the corpora, so only pairs of equal
        sizes are comparable

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
