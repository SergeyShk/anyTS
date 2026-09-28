from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from math import inf, isnan, log, log2, nan
from typing import Any, NamedTuple

import numpy as np
from scipy.stats import chi2 as chi2_distribution

from ..constants import KEYNESS_MEASURES
from ..exceptions import ParameterError, SourceError, SourceTypeError
from ..utils import check_counts, check_integer, check_words

ZERO_ADJUSTMENT = 0.5


class FrequencyReference(NamedTuple):
    """
    Reference corpus given by its frequencies, such as a frequency dictionary

    Description:
        The words of the target corpus that keep passes are counted by their key,
        and the frequency of a key missing from counts is missing: a dictionary
        gives its least frequency, an upper bound, so such a word may be a
        positive keyword but never a negative one. Negative keywords come only
        from the keys of counts that keep passes, since the words it leaves out
        are not counted in the target

    Attributes:
        counts (dict[str, float]): Frequencies of the keys in the reference corpus
        size (float): Size of the reference corpus in words
        missing (float): Frequency of a key missing from counts
        key (callable): Key of a word of the target corpus, such as its lemma;
            None - the word itself
        keep (callable): Whether a word of the target corpus is counted; None - every word
    """

    counts: Mapping[str, float]
    size: float
    missing: float = 0.0
    key: Callable[[str], str] | None = None
    keep: Callable[[str], bool] | None = None


class Keyword(NamedTuple):
    """
    Keyword - the result of comparing the frequencies of two corpora

    Attributes:
        word (str): Word
        freq_target (int): Frequency in the target corpus
        freq_reference (float): Frequency in the reference corpus
        ipm_target (float): Frequency in the target corpus per million words
        ipm_reference (float): Frequency in the reference corpus per million words
        g2 (float): Log-likelihood G² signed by its direction
        p_value (float): p-value of G² by the chi-square distribution with one
            degree of freedom
        log_ratio (float): Binary logarithm of the ratio of normalized frequencies
        score (float): Value of the chosen measure
    """

    word: str
    freq_target: int
    freq_reference: float
    ipm_target: float
    ipm_reference: float
    g2: float
    p_value: float
    log_ratio: float
    score: float


def _check_words_or_counts(words: Iterable[object]) -> None:
    """Checking the words of a corpus given as a list (check_words) or a counter (check_counts)"""
    if isinstance(words, Mapping):
        check_counts(words)
    else:
        check_words(words)


def keyness(
    target: Sequence[str] | Mapping[str, int],
    reference: Sequence[str] | Mapping[str, float] | FrequencyReference,
    measure: str = "log_likelihood",
    min_freq: int = 1,
    positive: bool = True,
    top_n: int | None = None,
) -> list[Keyword]:
    """
    Finding the keywords of a target corpus against a reference one

    Description:
        For every word the log-likelihood G² with its p-value (significance)
        and Log Ratio (effect size) are computed, as Gabrielatos and Hardie
        recommend, with the chosen measure score, which sorts the list. The
        measures of significance (G², chi-square, BIC, ELL) are negative when
        the word is more frequent in the reference. A zero frequency is
        replaced with 0.5 for %DIFF, Log Ratio and the odds ratio (Hardie 2014)
        The reference may be a list of words, their frequencies (the size is
        their sum) or a FrequencyReference with a size of its own, which a
        language library builds from its frequency dictionary
        Positive keywords are more frequent in the target corpus, negative ones
        in the reference; min_freq is the least frequency of a word in the
        corpus where it is more frequent

    References:
        https://ucrel.lancs.ac.uk/llwizard.html
        http://eprints.lancs.ac.uk/51449/4/Gabrielatos_Marchi_Keyness.pdf
        http://cass.lancs.ac.uk/log-ratio-an-informal-introduction/

    Arguments:
        target (list[str]|dict[str, int]): Words of the target corpus or their
            frequencies
        reference (list[str]|dict[str, float]|FrequencyReference): Words of the
            reference corpus, their frequencies or a reference by frequencies
        measure (str): Measure of KEYNESS_MEASURES for score and the sorting
        min_freq (int): Minimum frequency of a keyword in its own corpus
        positive (bool): Positive keywords (True) or negative ones (False)
        top_n (int): Number of keywords; None - all of them

    Returns:
        list[Keyword]: Keywords by descending keyness, then by descending
            frequency and alphabetically; words of an undefined measure last

    Raises:
        SourceTypeError: If the words are not a list of strings (check_words)
            or a counter (check_counts)
        ParameterError: If the measure is unknown, top_n is below one or
            min_freq is not an integer
        SourceError: If one of the corpora is empty

    Example:
        >>> from anyts.corpus import keyness
        >>> target = "the cat sleeps and the cat eats".split()
        >>> reference = "the dog sleeps and the dog eats".split()
        >>> [(k.word, round(k.g2, 2)) for k in keyness(target, reference)]
        [('cat', 2.77)]
    """
    if not isinstance(measure, str) or measure not in KEYNESS_MEASURES:
        raise ParameterError(f"Unknown measure of keyness: {measure}")
    check_integer(min_freq, "minimum frequency")
    if top_n is not None:
        check_integer(top_n, "number of keywords")
    if top_n is not None and top_n < 1:
        raise ParameterError("The number of keywords must be greater than 0")
    _check_words_or_counts(target)
    counts_reference: Mapping[str, float]
    keep = None
    if isinstance(reference, FrequencyReference):
        if not isinstance(reference.counts, Mapping):
            raise SourceTypeError(
                "The frequencies of the reference must be a mapping, "
                f"not {type(reference.counts).__name__}"
            )
        counts_target = _count(target, key=reference.key, keep=reference.keep)
        size_reference = float(reference.size)
        counts_reference = reference.counts
        missing = float(reference.missing)
        keep = reference.keep
    else:
        _check_words_or_counts(reference)
        counts_target = _count(target)
        counts_reference = _count(reference)
        size_reference = float(sum(counts_reference.values()))
        missing = 0.0
    size_target = float(sum(counts_target.values()))
    if not size_target or not size_reference:
        raise SourceError("The data source has no words")
    calc = MEASURES[measure]
    rows = []
    # A positive keyword occurs in the target; a negative one needs a frequency of its own
    # in the reference, since that of a missing key only bounds it from above
    candidates: Iterable[str] = counts_target
    if not positive:
        candidates = counts_reference if keep is None else filter(keep, counts_reference)
    for word in candidates:
        a = counts_target.get(word, 0)
        b = float(counts_reference.get(word, missing))
        ipm_target = a / size_target * 1e6
        ipm_reference = b / size_reference * 1e6
        if ipm_target == ipm_reference or (ipm_target > ipm_reference) != positive:
            continue
        if (a if positive else b) < min_freq:
            continue
        rows.append(
            (
                word,
                int(a),
                b,
                ipm_target,
                ipm_reference,
                calc_log_likelihood(a, b, size_target, size_reference),
                calc_log_ratio(a, b, size_target, size_reference),
                calc(a, b, size_target, size_reference),
            )
        )
    p_values = calc_p_value(np.array([row[5] for row in rows]))
    keywords = [
        Keyword(*row[:6], float(p_value), *row[6:])
        for row, p_value in zip(rows, p_values, strict=True)
    ]
    sign = -1 if positive else 1
    keywords.sort(
        key=lambda keyword: (
            isnan(keyword.score),
            sign * (0.0 if isnan(keyword.score) else keyword.score),
            -(keyword.freq_target if positive else keyword.freq_reference),
            keyword.word,
        )
    )
    return keywords[:top_n] if top_n else keywords


def _count(
    words: Sequence[str] | Mapping[str, float],
    key: Callable[[str], str] | None = None,
    keep: Callable[[str], bool] | None = None,
) -> Mapping[str, float]:
    """Frequencies of the words that keep passes, summed by key when one is given"""
    if key is None and keep is None:
        return words if isinstance(words, Mapping) else Counter(words)
    counts: dict[str, float] = {}
    pairs = words.items() if isinstance(words, Mapping) else ((word, 1) for word in words)
    for word, count in pairs:
        if keep is None or keep(word):
            word_key = word if key is None else key(word)
            counts[word_key] = counts.get(word_key, 0) + count
    return counts


def _sign(a: float, b: float, c: float, d: float) -> int:
    return 1 if a / c >= b / d else -1


def _adjust(a: float, b: float) -> tuple[float, float]:
    return a or ZERO_ADJUSTMENT, b or ZERO_ADJUSTMENT


def calc_log_likelihood(a: float, b: float, c: float, d: float) -> float:
    """
    Computing the log-likelihood G² of the frequencies of a word in two corpora

    Description:
        By Rayson and Garside (2000): the expected frequencies
        E1 = c·(a + b)/(c + d) and E2 = d·(a + b)/(c + d),
        G² = 2·(a·ln(a/E1) + b·ln(b/E2)); a term of zero frequency is zero;
        critical values in G2_CRITICAL_VALUES (3.84 for p < 0.05). The sign is
        negative when the word is more frequent in the reference

    References:
        https://ucrel.lancs.ac.uk/llwizard.html

    Arguments:
        a (float): Frequency of the word in the target corpus
        b (float): Frequency of the word in the reference corpus
        c (float): Size of the target corpus
        d (float): Size of the reference corpus

    Returns:
        float: Signed G²

    Example:
        >>> from anyts.corpus.keyness import calc_log_likelihood
        >>> round(calc_log_likelihood(10, 2, 1000, 1000), 3)
        5.822
    """
    total = a + b
    if not total:
        return 0.0
    expected_a = c * total / (c + d)
    expected_b = d * total / (c + d)
    value = 2 * (_xlog(a, expected_a) + _xlog(b, expected_b))
    return _sign(a, b, c, d) * value


def _xlog(observed: float, expected: float) -> float:
    return observed * log(observed / expected) if observed else 0.0


def calc_p_value(g2: float | np.ndarray) -> Any:
    """
    Computing the p-value of a G² or a chi-square

    Arguments:
        g2 (float|ndarray): Value of G² or of the chi-square (the sign is not
            taken into account) or an array of values

    Returns:
        float|ndarray: p-value by the chi-square distribution with one degree of freedom
    """
    p_value = chi2_distribution.sf(np.abs(g2), 1)
    return float(p_value) if np.isscalar(g2) else p_value


def calc_chi2(a: float, b: float, c: float, d: float) -> float:
    """
    Computing the chi-square with Yates's correction for the frequencies of a word in two corpora

    Description:
        Over the 2×2 contingency table of the word and the other words of each
        corpus, χ² = N·(|a·(d − b) − b·(c − a)| − N/2)² / ((a + b)·(c − a + d − b)·c·d),
        N = c + d
        The sign is negative when the word is more frequent in the reference

    Arguments:
        a (float): Frequency of the word in the target corpus
        b (float): Frequency of the word in the reference corpus
        c (float): Size of the target corpus
        d (float): Size of the reference corpus

    Returns:
        float: Signed chi-square
    """
    total = c + d
    rest_a = c - a
    rest_b = d - b
    denominator = (a + b) * (rest_a + rest_b) * c * d
    if not denominator:
        return 0.0
    difference = max(abs(a * rest_b - b * rest_a) - total / 2, 0.0)
    return _sign(a, b, c, d) * total * difference**2 / denominator


def calc_diff(a: float, b: float, c: float, d: float) -> float:
    """
    Computing the difference of normalized frequencies %DIFF

    Description:
        By Gabrielatos and Marchi (2011): (NF_a − NF_b) / NF_b · 100, where NF
        is the frequency per million words; a zero frequency is replaced with 0.5

    Arguments:
        a (float): Frequency of the word in the target corpus
        b (float): Frequency of the word in the reference corpus
        c (float): Size of the target corpus
        d (float): Size of the reference corpus

    Returns:
        float: %DIFF
    """
    a, b = _adjust(a, b)
    return (a / c - b / d) / (b / d) * 100


def calc_log_ratio(a: float, b: float, c: float, d: float) -> float:
    """
    Computing Log Ratio - the binary logarithm of the ratio of normalized frequencies

    Description:
        By Hardie (2014): log2(NF_a / NF_b); one - the word is twice as frequent
        in the target corpus; a zero frequency is replaced with 0.5

    References:
        http://cass.lancs.ac.uk/log-ratio-an-informal-introduction/

    Arguments:
        a (float): Frequency of the word in the target corpus
        b (float): Frequency of the word in the reference corpus
        c (float): Size of the target corpus
        d (float): Size of the reference corpus

    Returns:
        float: Log Ratio
    """
    a, b = _adjust(a, b)
    return log2((a / c) / (b / d))


def calc_bic(a: float, b: float, c: float, d: float) -> float:
    """
    Computing the Bayesian information criterion for G²

    Description:
        By Wilson (2013): BIC = sign(G²) · (|G²| − ln N), N = c + d; values
        above 2 in the direction of G² are positive evidence of a difference,
        above 6 strong, above 10 very strong; the sign opposite to G² means no
        evidence

    Arguments:
        a (float): Frequency of the word in the target corpus
        b (float): Frequency of the word in the reference corpus
        c (float): Size of the target corpus
        d (float): Size of the reference corpus

    Returns:
        float: Signed BIC
    """
    g2 = calc_log_likelihood(a, b, c, d)
    return _sign(a, b, c, d) * (abs(g2) - log(c + d))


def calc_ell(a: float, b: float, c: float, d: float) -> float:
    """
    Computing the effect size for the log-likelihood ELL

    Description:
        By Johnston, Berry and Mielke (2006): ELL = G² / (N · ln(min(E1, E2))),
        N = c + d; the share of the greatest possible departure from the expected
        frequencies, from 0 to 1, though it grows without bound as the least
        expected frequency nears one. Signed as G²

    Arguments:
        a (float): Frequency of the word in the target corpus
        b (float): Frequency of the word in the reference corpus
        c (float): Size of the target corpus
        d (float): Size of the reference corpus

    Returns:
        float: Signed ELL, nan when the least expected frequency is at most one
            (its logarithm is zero or negative)
    """
    total = a + b
    expected_min = min(c, d) * total / (c + d)
    if expected_min <= 1:
        return nan
    return calc_log_likelihood(a, b, c, d) / ((c + d) * log(expected_min))


def calc_odds_ratio(a: float, b: float, c: float, d: float) -> float:
    """
    Computing the odds ratio of a word in two corpora

    Description:
        (a / (c − a)) / (b / (d − b)); one - equal odds, a zero frequency is
        replaced with 0.5

    Arguments:
        a (float): Frequency of the word in the target corpus
        b (float): Frequency of the word in the reference corpus
        c (float): Size of the target corpus
        d (float): Size of the reference corpus

    Returns:
        float: Odds ratio; inf if the word fills the whole target corpus, 0 if
            it fills the whole reference, nan if both
    """
    a, b = _adjust(a, b)
    if a >= c and b >= d:
        return nan
    if a >= c:
        return inf
    if b >= d:
        return 0.0
    return (a / (c - a)) / (b / (d - b))


MEASURES = {
    "log_likelihood": calc_log_likelihood,
    "chi2": calc_chi2,
    "diff": calc_diff,
    "log_ratio": calc_log_ratio,
    "bic": calc_bic,
    "ell": calc_ell,
    "odds_ratio": calc_odds_ratio,
}
