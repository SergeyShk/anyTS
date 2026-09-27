from collections import Counter
from collections.abc import Iterable, Sequence
from math import log2, nan, sqrt
from numbers import Integral
from typing import NamedTuple

import numpy as np

from ..exceptions import ParameterError, SourceError
from ..utils import check_integer, check_words


class Dispersion(NamedTuple):
    """
    Dispersion of a word over the parts of a text

    Attributes:
        word (str): Word
        freq (int): Frequency of the word
        dp (float): Deviation of proportions DP of Gries: 0 - even, 1 − s_i - all in
            part i of share s_i, at most 1 − min(s_i)
        dp_norm (float): DP normalized to its greatest possible value: 1 - all in the
            smallest part
        juilland_d (float): Juilland's D: 1 - even, 0 - in one part
        carroll_d2 (float): Carroll's D2: 1 - even, 0 - in one part
        rosengren_s (float): Rosengren's S: 1 - even, tends to 0 when concentrated
        kl_divergence (float): Kullback-Leibler divergence in bits: 0 - even
    """

    word: str
    freq: int
    dp: float
    dp_norm: float
    juilland_d: float
    carroll_d2: float
    rosengren_s: float
    kl_divergence: float


def dispersion(
    words: Sequence[str],
    parts: int | Sequence[int] = 10,
    word: str | None = None,
    min_freq: int = 1,
) -> list[Dispersion]:
    """
    Computing the dispersion of words over the parts of a text

    Description:
        The text is split into parts: parts is either the number of parts of
        about equal size or the sizes of the parts in order (sentences,
        paragraphs, chapters), which add up to the number of words. For every
        word its frequencies by part are taken and the measures of dispersion
        of Gries (2008, 2020) computed: DP and normalized DP, Juilland's D,
        Carroll's D2, Rosengren's S and the Kullback-Leibler divergence; Gries
        recommends DP
        Words are compared as they are: case and lemmatization belong to the
        extraction

    References:
        https://www.stgries.info/research/2020_STG_Dispersion_PHCL.pdf
        https://www.stgries.info/research/2008_STG_Dispersion_IJCL.pdf

    Arguments:
        words (list[str]): Words of the text in order
        parts (int|list[int]): Number of parts or sizes of the parts
        word (str): Word whose dispersion is needed; None - every word
        min_freq (int): Minimum frequency of a word

    Returns:
        list[Dispersion]: Dispersion of the words by descending frequency; for a
            word absent from the text - a zero frequency and nan

    Raises:
        SourceTypeError: If the words are not a list of strings (check_words)
        SourceError: If there are no words
        ParameterError: If there are fewer than two parts or more parts than
            words, the number of parts is not an integer, or the sizes of the
            parts do not match the text

    Example:
        >>> from anyts.corpus import dispersion
        >>> words = "the cat eats and the cat sleeps but the dog barks".split()
        >>> result = dispersion(words, parts=2, word="cat")[0]
        >>> result.freq, round(result.dp, 3)
        (2, 0.455)
    """
    check_words(words)
    if not len(words):
        raise SourceError("The data source has no words")
    sizes = _sizes(len(words), parts)
    total = Counter(words)
    targets = [word] if word is not None else [w for w, f in total.most_common() if f >= min_freq]
    vocabulary = {target: index for index, target in enumerate(targets)}
    ids = np.fromiter((vocabulary.get(w, -1) for w in words), dtype=np.int64, count=len(words))
    part_ids = np.repeat(np.arange(len(sizes), dtype=np.int64), sizes)
    known = ids >= 0
    cells, counts = np.unique(ids[known] * len(sizes) + part_ids[known], return_counts=True)
    measures = _cell_measures(
        cells // len(sizes),
        cells % len(sizes),
        counts.astype(float),
        len(targets),
        np.asarray(sizes, dtype=float),
    )
    return [
        Dispersion(str(target), int(total[target]), *(float(column[index]) for column in measures))
        for index, target in enumerate(targets)
    ]


def _sizes(n_words: int, parts: int | Sequence[int]) -> list[int]:
    if isinstance(parts, Integral):
        n_parts = int(parts)
        if not 2 <= n_parts <= n_words:
            raise ParameterError("There must be at least two parts and no more parts than words")
        return [len(part) for part in np.array_split(np.arange(n_words), n_parts)]
    if not isinstance(parts, Iterable):
        raise ParameterError(
            "The number of parts must be an integer and the sizes of the parts a list of integers"
        )
    sizes = list(parts)
    for size in sizes:
        check_integer(size, "size of a part")
    if len(sizes) < 2 or sum(sizes) != n_words or min(sizes) < 1:
        raise ParameterError("The sizes of the parts must be positive and add up to the words")
    return sizes


def _cell_measures(
    rows: np.ndarray, cols: np.ndarray, values: np.ndarray, n_words: int, sizes: np.ndarray
) -> tuple[np.ndarray, ...]:
    """
    Measures of dispersion of every word over the non-zero cells of the word × part matrix

    Description:
        The measures of calc_dp, calc_dp_norm, calc_juilland_d,
        calc_carroll_d2, calc_rosengren_s and calc_kl_divergence over a sparse
        matrix: rows and cols are the word and the part of a non-zero cell,
        values its frequency; words of zero frequency give nan

    Arguments:
        rows (ndarray): Words of the non-zero cells
        cols (ndarray): Parts of the non-zero cells
        values (ndarray): Frequencies in the cells
        n_words (int): Number of words
        sizes (ndarray): Sizes of the parts

    Returns:
        tuple[ndarray, ...]: Arrays of DP, DP_norm, D, D2, S and the divergence by word
    """
    shares = sizes / sizes.sum()
    n_parts = len(sizes)
    cell_shares = shares[cols]

    def by_word(weights: np.ndarray) -> np.ndarray:
        return np.bincount(rows, weights=weights, minlength=n_words)

    totals = by_word(values)
    proportions = values / totals[rows]
    dp = 0.5 * (1 + by_word(np.abs(proportions - cell_shares) - cell_shares))
    dp_norm = dp / (1 - shares.min())
    relative = values / sizes[cols]
    mean = by_word(relative) / n_parts
    variance = np.maximum(by_word(relative**2) / n_parts - mean**2, 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        juilland = 1 - np.sqrt(variance) / mean / sqrt(n_parts - 1)
        probabilities = relative / (mean * n_parts)[rows]
        carroll = -by_word(probabilities * np.log2(probabilities)) / log2(n_parts)
        rosengren = by_word(np.sqrt(cell_shares * values)) ** 2 / totals
        kl = by_word(proportions * np.log2(proportions / cell_shares))
    empty = totals == 0
    return tuple(
        np.where(empty, nan, measure)
        for measure in (dp, dp_norm, juilland, carroll, rosengren, kl)
    )


def _proportions(
    frequencies: Sequence[int], sizes: Sequence[int]
) -> tuple[np.ndarray, np.ndarray]:
    counts = np.asarray(frequencies, dtype=float)
    shares = np.asarray(sizes, dtype=float)
    shares = shares / shares.sum()
    return counts, shares


def calc_dp(frequencies: Sequence[int], sizes: Sequence[int]) -> float:
    """
    Computing the deviation of proportions DP

    Description:
        By Gries (2008): 0.5 · Σ |v_i / f − s_i|, where v_i is the frequency of
        the word in part i, f the frequency of the word and s_i the share of
        part i in the text; 0 - the word is spread in proportion to the sizes
        of the parts, 1 − s_i - it is all in part i, so at most 1 − min(s_i)

    Arguments:
        frequencies (list[int]): Frequencies of the word by part
        sizes (list[int]): Sizes of the parts

    Returns:
        float: DP, nan for a word of zero frequency

    Example:
        >>> from anyts.corpus.dispersion import calc_dp
        >>> calc_dp([3, 1], [10, 10])
        0.25
    """
    counts, shares = _proportions(frequencies, sizes)
    total = counts.sum()
    if not total:
        return nan
    return float(0.5 * np.abs(counts / total - shares).sum())


def calc_dp_norm(frequencies: Sequence[int], sizes: Sequence[int]) -> float:
    """
    Computing the normalized deviation of proportions DP_norm

    Description:
        By Lijffijt and Gries (2012): DP / (1 − min(s_i)), so that the greatest
        value is one whatever the split into parts

    Arguments:
        frequencies (list[int]): Frequencies of the word by part
        sizes (list[int]): Sizes of the parts

    Returns:
        float: DP_norm, nan for a word of zero frequency
    """
    _, shares = _proportions(frequencies, sizes)
    return calc_dp(frequencies, sizes) / (1 - float(shares.min()))


def calc_juilland_d(frequencies: Sequence[int], sizes: Sequence[int]) -> float:
    """
    Computing Juilland's D

    Description:
        By Juilland and Chang-Rodríguez (1964) as written by Gries (2020):
        1 − V / sqrt(n − 1), where V is the coefficient of variation (the ratio
        of the population standard deviation to the mean; Gries (2008) takes
        the sample one) of the relative frequencies of
        the word by part v_i / n_i and n the number of parts; 1 - even,
        0 - in one part

    Arguments:
        frequencies (list[int]): Frequencies of the word by part
        sizes (list[int]): Sizes of the parts

    Returns:
        float: D, nan for a word of zero frequency
    """
    counts, _ = _proportions(frequencies, sizes)
    if not counts.sum():
        return nan
    relative = counts / np.asarray(sizes, dtype=float)
    variation = relative.std() / relative.mean()
    return float(1 - variation / sqrt(len(sizes) - 1))


def calc_carroll_d2(frequencies: Sequence[int], sizes: Sequence[int]) -> float:
    """
    Computing Carroll's D2

    Description:
        By Carroll (1970): the entropy of the distribution of the relative
        frequencies of the word by part p_i = v_i / n_i divided by log2 of the
        number of parts; 1 - even, 0 - in one part

    Arguments:
        frequencies (list[int]): Frequencies of the word by part
        sizes (list[int]): Sizes of the parts

    Returns:
        float: D2, nan for a word of zero frequency
    """
    counts, _ = _proportions(frequencies, sizes)
    if not counts.sum():
        return nan
    relative = counts / np.asarray(sizes, dtype=float)
    probabilities = relative[relative > 0] / relative.sum()
    entropy = -float((probabilities * np.log2(probabilities)).sum())
    return entropy / log2(len(sizes))


def calc_rosengren_s(frequencies: Sequence[int], sizes: Sequence[int]) -> float:
    """
    Computing Rosengren's S

    Description:
        By Rosengren (1971) as written by Gries (2008): (Σ sqrt(s_i · v_i))² / f;
        1 - the word is spread in proportion to the sizes of the parts, tends to
        1/n when it is concentrated in one of n equal parts

    Arguments:
        frequencies (list[int]): Frequencies of the word by part
        sizes (list[int]): Sizes of the parts

    Returns:
        float: S, nan for a word of zero frequency
    """
    counts, shares = _proportions(frequencies, sizes)
    total = counts.sum()
    if not total:
        return nan
    return float(np.sqrt(shares * counts).sum() ** 2 / total)


def calc_kl_divergence(frequencies: Sequence[int], sizes: Sequence[int]) -> float:
    """
    Computing the Kullback-Leibler divergence of the distribution of a word over the parts

    Description:
        By Gries (2020): Σ (v_i / f) · log2((v_i / f) / s_i) - the divergence of
        the shares of the occurrences of the word by part from the shares of
        the parts in the text; 0 - in proportion, grows when the word is
        concentrated in small parts

    Arguments:
        frequencies (list[int]): Frequencies of the word by part
        sizes (list[int]): Sizes of the parts

    Returns:
        float: Divergence in bits, nan for a word of zero frequency
    """
    counts, shares = _proportions(frequencies, sizes)
    total = counts.sum()
    if not total:
        return nan
    mask = counts > 0
    observed = counts[mask] / total
    return float((observed * np.log2(observed / shares[mask])).sum())
