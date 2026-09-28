from collections import Counter
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from functools import partial, wraps
from math import inf, log, log2, nan, sqrt
from typing import Any, ClassVar, NamedTuple, TypeVar, cast

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from scipy.optimize import least_squares
from scipy.special import gammaln
from scipy.stats import t as student_t

from .constants import (
    BRUNET_W_EXPONENT,
    DIVERSITY_LOG_BASE,
    DIVERSITY_STATS_DESC,
    HDD_SAMPLE_SIZE,
    MATTR_WINDOW_LEN,
    MTLD_BLOCK_SIZE,
    MTLD_MIN_LEN,
    MTLD_TTR_THRESHOLD,
    MTLD_WINDOW_LEN,
)
from .exceptions import ParameterError, SourceError, UnknownStatError
from .utils import (
    check_counts,
    check_integer,
    check_number,
    check_sequence,
    check_words,
    safe_divide,
)

Calculator = Callable[[Sequence[str]], float]
Function = TypeVar("Function", bound=Callable[..., Any])


def _checks_words(func: Function) -> Function:
    """Checking the words of a function with check_words before calling it"""

    @wraps(func)
    def checked(text: Any, *args: Any, **kwargs: Any) -> Any:
        check_words(text)
        return func(text, *args, **kwargs)

    checked.__unchecked__ = func  # type: ignore[attr-defined]
    return cast(Function, checked)


def _unchecked(func: Function) -> Function:
    """The function without the check of its words, for words already checked"""
    if isinstance(func, partial):
        return cast(Function, partial(_unchecked(func.func), *func.args, **func.keywords))
    return cast(Function, getattr(func, "__unchecked__", func))


class WindowStats(NamedTuple):
    """
    Result of the windowed computation of a metric

    Attributes:
        mean (float): Mean of the metric over the windows
        std (float): Sample standard deviation over the windows
        lower (float): Lower bound of the confidence interval of the mean
        upper (float): Upper bound of the confidence interval of the mean
        n_windows (int): Number of windows with a defined value of the metric
    """

    mean: float
    std: float
    lower: float
    upper: float
    n_windows: int


def check_params(
    window_len: int = MATTR_WINDOW_LEN,
    mtld_threshold: float = MTLD_TTR_THRESHOLD,
    mtld_min_len: int = MTLD_MIN_LEN,
    hdd_sample_size: int = HDD_SAMPLE_SIZE,
    log_base: float = DIVERSITY_LOG_BASE,
) -> None:
    """
    Checking the parameters of the lexical diversity metrics

    Arguments:
        window_len (int): Window size for MATTR and segment size for MSTTR
        mtld_threshold (float): TTR threshold for MTLD, MA-MTLD and MTLD-W
        mtld_min_len (int): Minimum factor length for MTLD, MA-MTLD and MTLD-W
        hdd_sample_size (int): Sample size for HD-D
        log_base (float): Logarithm base for the Summer, Maas and Dugast metrics

    Raises:
        ParameterError: If a parameter is not a number of its type or is out of range
    """
    check_integer(window_len, "window size")
    if window_len < 1:
        raise ParameterError("The window size must be greater than 0")
    _check_mtld_params(mtld_threshold, mtld_min_len)
    check_integer(hdd_sample_size, "HD-D sample size")
    if hdd_sample_size < 1:
        raise ParameterError("The HD-D sample size must be greater than 0")
    _check_log_base(log_base)


def _check_log_base(base: float) -> None:
    """Checking the logarithm base of the Summer, Maas and Dugast metrics"""
    check_number(base, "logarithm base")
    if not base > 1:
        raise ParameterError("The logarithm base must be greater than 1")


class DiversityStats:
    """
    Class for computing the main lexical diversity metrics of a text

    Description:
        Lexical diversity reflects the richness of the vocabulary of a text of a given
        length. Defaults: base 10 for the logarithmic measures of Summer, Maas and
        Dugast, a 50-word MATTR window and MSTTR segment, the MTLD threshold 0.72
        (a factor closes at a TTR not above it) with a minimum factor of 10 words,
        an HD-D sample of 42 words; all of them are parameters of the class

    References:
        https://en.wikipedia.org/wiki/Lexical_diversity
        https://en.wikipedia.org/wiki/Diversity_index
        https://core.ac.uk/download/pdf/82620241.pdf

    Example:
        >>> from anyts import DiversityStats
        >>> ds = DiversityStats("a b c d e b c f g h g i g j k".split())
        >>> ds.ttr
        0.7333333333333333
        >>> ds.yule_k
        444.44444444444446
        >>> ds.windowed("ttr", window_len=5)
        WindowStats(mean=0.9333333333333332, std=0.11547005383792512, lower=0.6464898180167025, upper=1.220176848649964, n_windows=3)

    Arguments:
        words (iterable[str]): Words of the text, used as given: a language library
            extracts them from its sources and lower-cases them
        window_len (int): Window size for MATTR and segment size for MSTTR
        mtld_threshold (float): TTR threshold for MTLD, MA-MTLD and MTLD-W
        mtld_min_len (int): Minimum factor length for MTLD, MA-MTLD and MTLD-W
        hdd_sample_size (int): Sample size for HD-D
        log_base (float): Logarithm base for the Summer, Maas and Dugast metrics

    Attributes:
        words (tuple[str]): Tuple of the words
        window_len (int): Window size for MATTR and segment size for MSTTR
        mtld_threshold (float): TTR threshold for MTLD, MA-MTLD and MTLD-W
        mtld_min_len (int): Minimum factor length for MTLD, MA-MTLD and MTLD-W
        hdd_sample_size (int): Sample size for HD-D
        log_base (float): Logarithm base for the Summer, Maas and Dugast metrics;
            the five parameters can be changed on the object
        frequency_spectrum (dict[int, int]): Frequency spectrum - the number of lexemes with a given frequency
        ttr (float): Type-Token Ratio (TTR)
        rttr (float): Root Type-Token Ratio (RTTR)
        cttr (float): Corrected Type-Token Ratio (CTTR)
        httr (float): Herdan Type-Token Ratio (HTTR)
        sttr (float): Summer Type-Token Ratio (STTR)
        mttr (float): Maas Type-Token Ratio (MTTR)
        dttr (float): Dugast Type-Token Ratio (DTTR)
        mattr (float): Moving Average Type-Token Ratio (MATTR)
        msttr (float): Mean Segmental Type-Token Ratio (MSTTR)
        mtld (float): Measure of Textual Lexical Diversity (MTLD)
        mamtld (float): Moving Average Measure of Textual Lexical Diversity (MA-MTLD)
        mtldw (float): MTLD with a moving window and text wrap (MTLD-W)
        hdd (float): Hypergeometric Distribution D (HD-D)
        simpson_index (float): Simpson's index (D)
        inverse_simpson_index (float): Inverse Simpson's index (1/D)
        gini_simpson_index (float): Gini-Simpson index (1-D)
        hapax_index (float): Hapax index, a.k.a. Honoré's R
        honore_r (float): Alias for the hapax index
        yule_k (float): Yule's characteristic (Yule's K)
        yule_i (float): Inverse Yule's characteristic (Yule's I)
        herdan_vm (float): Herdan's Vm
        sichel_s (float): Sichel's S
        michea_m (float): Michéa's M
        brunet_w (float): Brunet's W
        dugast_k (float): Dugast's k
        baayen_p (float): Baayen's P
        hapax_ratio (float): Share of hapaxes among lexemes
        alpha2 (float): The α₂ exponent
        entropy (float): Shannon entropy in bits
        evenness (float): Evenness - the ratio of entropy to its maximum
        perplexity (float): Perplexity
        zipf_alpha (float): Zipf's law slope
        heaps_beta (float): Heaps' law exponent

    Methods:
        windowed: Windowed computation of a metric with the mean and a confidence interval
        get_stats: Getting the computed lexical diversity metrics of the text
        print_stats: Printing the computed lexical diversity metrics with descriptions

    Class attributes:
        stats_desc (dict[str, str]): Descriptions of the metrics for print_stats
        stats_headers (tuple[str, str]): Headers of the columns for print_stats

    Raises:
        SourceTypeError: If the words are a string, a Doc, not iterable or not strings
        SourceError: If there are no words
        ParameterError: If the parameters of the metrics are set incorrectly
    """

    stats_desc: ClassVar[Mapping[str, str]] = DIVERSITY_STATS_DESC
    stats_headers: ClassVar[tuple[str, str]] = ("Metric", "Value")

    def __init__(
        self,
        words: Iterable[str],
        window_len: int = MATTR_WINDOW_LEN,
        mtld_threshold: float = MTLD_TTR_THRESHOLD,
        mtld_min_len: int = MTLD_MIN_LEN,
        hdd_sample_size: int = HDD_SAMPLE_SIZE,
        log_base: float = DIVERSITY_LOG_BASE,
    ):
        check_params(window_len, mtld_threshold, mtld_min_len, hdd_sample_size, log_base)
        if not isinstance(words, Iterator):
            check_sequence(words)
        self.words = tuple(words)
        check_words(self.words)
        if not self.words:
            raise SourceError("The data source has no words")
        self.window_len = window_len
        self.mtld_threshold = mtld_threshold
        self.mtld_min_len = mtld_min_len
        self.hdd_sample_size = hdd_sample_size
        self.log_base = log_base

    @property
    def _calculators(self) -> dict[str, Calculator]:
        """Functions of the metrics with the current parameters of the object"""
        return {
            "ttr": calc_ttr,
            "rttr": calc_rttr,
            "cttr": calc_cttr,
            "httr": calc_httr,
            "sttr": partial(calc_sttr, base=self.log_base),
            "mttr": partial(calc_mttr, base=self.log_base),
            "dttr": partial(calc_dttr, base=self.log_base),
            "mattr": partial(calc_mattr, window_len=self.window_len),
            "msttr": partial(calc_msttr, segment_len=self.window_len),
            "mtld": partial(calc_mtld, min_len=self.mtld_min_len, threshold=self.mtld_threshold),
            "mamtld": partial(
                calc_mamtld, min_len=self.mtld_min_len, threshold=self.mtld_threshold
            ),
            "mtldw": partial(calc_mtldw, min_len=self.mtld_min_len, threshold=self.mtld_threshold),
            "hdd": partial(calc_hdd, sample_size=self.hdd_sample_size),
            "simpson_index": calc_simpson_index,
            "inverse_simpson_index": calc_inverse_simpson_index,
            "gini_simpson_index": calc_gini_simpson_index,
            "hapax_index": calc_hapax_index,
            "yule_k": calc_yule_k,
            "yule_i": calc_yule_i,
            "herdan_vm": calc_herdan_vm,
            "sichel_s": calc_sichel_s,
            "michea_m": calc_michea_m,
            "brunet_w": calc_brunet_w,
            "dugast_k": partial(calc_dugast_k, base=self.log_base),
            "baayen_p": calc_baayen_p,
            "hapax_ratio": calc_hapax_ratio,
            "alpha2": calc_alpha2,
            "entropy": calc_entropy,
            "evenness": calc_evenness,
            "perplexity": calc_perplexity,
            "zipf_alpha": calc_zipf_alpha,
            "heaps_beta": calc_heaps_beta,
        }

    def _calc(self, stat: str) -> float:
        return _unchecked(self._calculators[stat])(self.words)

    @property
    def frequency_spectrum(self) -> dict[int, int]:
        return _unchecked(calc_frequency_spectrum)(self.words)

    @property
    def ttr(self) -> float:
        return self._calc("ttr")

    @property
    def rttr(self) -> float:
        return self._calc("rttr")

    @property
    def cttr(self) -> float:
        return self._calc("cttr")

    @property
    def httr(self) -> float:
        return self._calc("httr")

    @property
    def sttr(self) -> float:
        return self._calc("sttr")

    @property
    def mttr(self) -> float:
        return self._calc("mttr")

    @property
    def dttr(self) -> float:
        return self._calc("dttr")

    @property
    def mattr(self) -> float:
        return self._calc("mattr")

    @property
    def msttr(self) -> float:
        return self._calc("msttr")

    @property
    def mtld(self) -> float:
        return self._calc("mtld")

    @property
    def mamtld(self) -> float:
        return self._calc("mamtld")

    @property
    def mtldw(self) -> float:
        return self._calc("mtldw")

    @property
    def hdd(self) -> float:
        return self._calc("hdd")

    @property
    def simpson_index(self) -> float:
        return self._calc("simpson_index")

    @property
    def inverse_simpson_index(self) -> float:
        return self._calc("inverse_simpson_index")

    @property
    def gini_simpson_index(self) -> float:
        return self._calc("gini_simpson_index")

    @property
    def hapax_index(self) -> float:
        return self._calc("hapax_index")

    @property
    def honore_r(self) -> float:
        return self._calc("hapax_index")

    @property
    def yule_k(self) -> float:
        return self._calc("yule_k")

    @property
    def yule_i(self) -> float:
        return self._calc("yule_i")

    @property
    def herdan_vm(self) -> float:
        return self._calc("herdan_vm")

    @property
    def sichel_s(self) -> float:
        return self._calc("sichel_s")

    @property
    def michea_m(self) -> float:
        return self._calc("michea_m")

    @property
    def brunet_w(self) -> float:
        return self._calc("brunet_w")

    @property
    def dugast_k(self) -> float:
        return self._calc("dugast_k")

    @property
    def baayen_p(self) -> float:
        return self._calc("baayen_p")

    @property
    def hapax_ratio(self) -> float:
        return self._calc("hapax_ratio")

    @property
    def alpha2(self) -> float:
        return self._calc("alpha2")

    @property
    def entropy(self) -> float:
        return self._calc("entropy")

    @property
    def evenness(self) -> float:
        return self._calc("evenness")

    @property
    def perplexity(self) -> float:
        return self._calc("perplexity")

    @property
    def zipf_alpha(self) -> float:
        return self._calc("zipf_alpha")

    @property
    def heaps_beta(self) -> float:
        return self._calc("heaps_beta")

    def windowed(
        self,
        stat: str,
        window_len: int = 100,
        step: int | None = None,
        confidence: float = 0.95,
    ) -> WindowStats:
        """
        Windowed computation of a metric: its value over consecutive windows
        of the text, the mean and the confidence interval of the mean

        Description:
            Computed by calc_windowed with the current parameters of the object

        Arguments:
            stat (str): Name of the metric from get_stats
            window_len (int): Window size
            step (int): Window step, by default equal to the window size (windows do not overlap)
            confidence (float): Confidence level

        Returns:
            WindowStats: Mean, standard deviation, bounds of the interval and number of windows

        Raises:
            UnknownStatError: If the metric is unknown
            ParameterError: If the window size, the step or the confidence level are set incorrectly
        """
        calculators = self._calculators
        if not isinstance(stat, str) or stat not in calculators:
            raise UnknownStatError(
                f"Unknown metric: {stat}. Available metrics: {tuple(calculators)}"
            )
        return calc_windowed(self.words, calculators[stat], window_len, step, confidence)

    def get_stats(self) -> dict[str, float]:
        """
        Getting the computed lexical diversity metrics of the text

        Returns:
            dict[str, float]: Dictionary of the computed lexical diversity metrics
        """
        return {stat: getattr(self, stat) for stat in DIVERSITY_STATS_DESC}

    def print_stats(self) -> None:
        """Printing the computed lexical diversity metrics with descriptions"""
        metric_header, value_header = self.stats_headers
        print(f"{metric_header:^75}|{value_header:^10}")
        print("-" * 85)
        for stat, value in self.get_stats().items():
            print(f"{self.stats_desc[stat]:75}|{value:^10.2f}")


@_checks_words
def calc_frequency_spectrum(text: Sequence[str]) -> dict[int, int]:
    """
    Computing the frequency spectrum

    Description:
        The number of lexemes V_i that occur in the text exactly i times

    Arguments:
        text (list[str]): List of words

    Returns:
        dict[int, int]: Number of lexemes by frequency

    Raises:
        SourceTypeError: If the words are not a list of strings (check_words)
    """
    return dict(sorted(Counter(Counter(text).values()).items()))


@_checks_words
def calc_ttr(text: Sequence[str]) -> float:
    """
    Computing the Type-Token Ratio (TTR)

    Description:
        The number of lexemes divided by the number of words; strongly depends
        on text length

    Arguments:
        text (list[str]): List of words

    Returns:
        float: Value of the metric

    Raises:
        SourceTypeError: If the words are not a list of strings (check_words)
    """
    n_words = len(text)
    n_lexemes = len(set(text))
    return safe_divide(n_lexemes, n_words)


@_checks_words
def calc_rttr(text: Sequence[str]) -> float:
    """
    Computing the Root Type-Token Ratio (RTTR)

    Description:
        A modification of TTR (Guiraud, 1960)

    Arguments:
        text (list[str]): List of words

    Returns:
        float: Value of the metric

    Raises:
        SourceTypeError: If the words are not a list of strings (check_words)
    """
    n_words = len(text)
    n_lexemes = len(set(text))
    return safe_divide(n_lexemes, sqrt(n_words))


@_checks_words
def calc_cttr(text: Sequence[str]) -> float:
    """
    Computing the Corrected Type-Token Ratio (CTTR)

    Description:
        A modification of TTR (Carroll, 1964)

    Arguments:
        text (list[str]): List of words

    Returns:
        float: Value of the metric

    Raises:
        SourceTypeError: If the words are not a list of strings (check_words)
    """
    n_words = len(text)
    n_lexemes = len(set(text))
    return safe_divide(n_lexemes, sqrt(2 * n_words))


@_checks_words
def calc_httr(text: Sequence[str]) -> float:
    """
    Computing the Herdan Type-Token Ratio (HTTR)

    Description:
        A logarithmic modification of TTR (Herdan, 1960)
        The ratio of logarithms does not depend on the base

    Arguments:
        text (list[str]): List of words

    Returns:
        float: Value of the metric, 0 for an empty text

    Raises:
        SourceTypeError: If the words are not a list of strings (check_words)
    """
    n_words = len(text)
    if not n_words:
        return 0
    n_lexemes = len(set(text))
    return safe_divide(log(n_lexemes), log(n_words))


@_checks_words
def calc_sttr(text: Sequence[str], base: float = DIVERSITY_LOG_BASE) -> float:
    """
    Computing the Summer Type-Token Ratio (STTR)

    Description:
        A logarithmic modification of TTR (Summer, 1966)
        The value depends on the logarithm base, 10 by default

    Arguments:
        text (list[str]): List of words
        base (float): Logarithm base

    Returns:
        float: Value of the metric, 0 for an empty text, nan for a text of one
            lexeme or of no more words than the logarithm base

    Raises:
        ParameterError: If the logarithm base is not greater than 1
        SourceTypeError: If the words are not a list of strings (check_words)
    """
    _check_log_base(base)
    n_words = len(text)
    if not n_words:
        return 0
    n_lexemes = len(set(text))
    if n_lexemes == 1 or log(n_words, base) <= 1:
        return nan
    return log(log(n_lexemes, base), base) / log(log(n_words, base), base)


@_checks_words
def calc_mttr(text: Sequence[str], base: float = DIVERSITY_LOG_BASE) -> float:
    """
    Computing the Maas Type-Token Ratio (MTTR)

    Description:
        A logarithmic modification of TTR (Maas, 1972)
        The value depends on the logarithm base, 10 by default

    Arguments:
        text (list[str]): List of words
        base (float): Logarithm base

    Returns:
        float: Value of the metric, 0 for an empty text

    Raises:
        ParameterError: If the logarithm base is not greater than 1
        SourceTypeError: If the words are not a list of strings (check_words)
    """
    _check_log_base(base)
    n_words = len(text)
    if not n_words:
        return 0
    n_lexemes = len(set(text))
    log_words = log(n_words, base)
    return safe_divide(log_words - log(n_lexemes, base), log_words**2)


@_checks_words
def calc_dttr(text: Sequence[str], base: float = DIVERSITY_LOG_BASE) -> float:
    """
    Computing the Dugast Type-Token Ratio (DTTR)

    Description:
        A logarithmic modification of TTR (Dugast, 1978), a.k.a. Dugast's U,
        the reciprocal of the Maas metric
        The value depends on the logarithm base, 10 by default

    Arguments:
        text (list[str]): List of words
        base (float): Logarithm base

    Returns:
        float: Value of the metric, 0 for an empty text, inf for a text without
            repeated words

    Raises:
        ParameterError: If the logarithm base is not greater than 1
        SourceTypeError: If the words are not a list of strings (check_words)
    """
    _check_log_base(base)
    n_words = len(text)
    if not n_words:
        return 0
    n_lexemes = len(set(text))
    log_words = log(n_words, base)
    return safe_divide(log_words**2, log_words - log(n_lexemes, base), inf)


@_checks_words
def calc_mattr(text: Sequence[str], window_len: int = MATTR_WINDOW_LEN) -> float:
    """
    Computing the Moving Average Type-Token Ratio (MATTR)

    Description:
        A moving-average modification of TTR (Covington & McFall, 2010)
        For texts shorter than the window the TTR of the whole text is returned

    Arguments:
        text (list[str]): List of words
        window_len (int): Window size

    Returns:
        float: Value of the metric

    Raises:
        ParameterError: If the window size is less than one
        SourceTypeError: If the words are not a list of strings (check_words)
    """
    check_integer(window_len, "window size")
    if window_len < 1:
        raise ParameterError("The window size must be greater than 0")
    n_words = len(text)
    if n_words < (window_len + 1):
        return _unchecked(calc_ttr)(text)
    counts = Counter(text[:window_len])
    window_ttr = len(counts) / window_len
    for n in range(window_len, n_words):
        counts[text[n]] += 1
        outgoing = text[n - window_len]
        counts[outgoing] -= 1
        if not counts[outgoing]:
            del counts[outgoing]
        window_ttr += len(counts) / window_len
    return window_ttr / (n_words - window_len + 1)


@_checks_words
def calc_msttr(text: Sequence[str], segment_len: int = MATTR_WINDOW_LEN) -> float:
    """
    Computing the Mean Segmental Type-Token Ratio (MSTTR)

    Description:
        A segmentation-based modification of TTR (Johnson, 1944)
        For texts shorter than the segment the TTR of the whole text is returned,
        an incomplete last segment is dropped

    Arguments:
        text (list[str]): List of words
        segment_len (int): Segment size

    Returns:
        float: Value of the metric

    Raises:
        ParameterError: If the segment size is less than one
        SourceTypeError: If the words are not a list of strings (check_words)
    """
    check_integer(segment_len, "segment size")
    if segment_len < 1:
        raise ParameterError("The segment size must be greater than 0")
    n_words = len(text)
    if n_words < (segment_len + 1):
        return _unchecked(calc_ttr)(text)
    segments = [text[start : start + segment_len] for start in range(0, n_words, segment_len)]
    segments = [segment for segment in segments if len(segment) == segment_len]
    ttr = _unchecked(calc_ttr)
    return sum(ttr(segment) for segment in segments) / len(segments)


def _check_mtld_params(threshold: float, min_len: int) -> None:
    """Checking the TTR threshold and the minimum factor length of MTLD"""
    check_number(threshold, "TTR threshold of MTLD")
    if not 0 < threshold < 1:
        raise ParameterError("The TTR threshold of MTLD must lie in the interval (0, 1)")
    check_integer(min_len, "minimum factor length of MTLD")
    if min_len < 0:
        raise ParameterError("The minimum factor length of MTLD cannot be negative")


def _count_mtld_factors(text: Sequence[str], threshold: float, min_len: int) -> float:
    """Counting the MTLD factors in one pass over the text"""
    factors = 0.0
    counts: Counter[str] = Counter()
    factor_len = 0
    for word in text:
        counts[word] += 1
        factor_len += 1
        if len(counts) / factor_len <= threshold and factor_len >= min_len:
            factors += 1
            counts.clear()
            factor_len = 0
    if factor_len:
        ttr = len(counts) / factor_len
        factors += min(1.0, (1 - ttr) / (1 - threshold))
    return factors


@_checks_words
def calc_mtld(
    text: Sequence[str], min_len: int = MTLD_MIN_LEN, threshold: float = MTLD_TTR_THRESHOLD
) -> float:
    """
    Computing the Measure of Textual Lexical Diversity (MTLD)

    Description:
        A modification of MSTTR (McCarthy, 2005): the number of words divided by
        the number of factors - stretches on which TTR drops to the threshold
        inclusive (TTR <= threshold); an incomplete factor at the end of the text
        counts partially, in proportion to how close its TTR came to the threshold
        The value is the mean of a forward and a backward pass (McCarthy & Jarvis, 2010)
        The minimum factor length is not part of the original algorithm, min_len=0 disables it
        If no factor completes and TTR never drops below 1, infinity is returned

    Arguments:
        text (list[str]): List of words
        min_len (int): Minimum factor length
        threshold (float): TTR threshold for completing a factor

    Returns:
        float: Value of the metric

    Raises:
        ParameterError: If the TTR threshold is outside the interval (0, 1)
            or the minimum factor length is negative
        SourceTypeError: If the words are not a list of strings (check_words)
    """
    _check_mtld_params(threshold, min_len)
    n_words = len(text)
    forward = safe_divide(n_words, _count_mtld_factors(text, threshold, min_len), inf)
    backward = safe_divide(n_words, _count_mtld_factors(text[::-1], threshold, min_len), inf)
    return (forward + backward) / 2


def _previous_positions(text: Sequence[str], wrap: bool) -> np.ndarray:
    """Position of the previous occurrence of the word for every position of the text (-1 without one)"""
    ids: dict[str, int] = {}
    codes = np.fromiter(
        (ids.setdefault(word, len(ids)) for word in text), dtype=np.int64, count=len(text)
    )
    if wrap:
        codes = np.concatenate([codes, codes])
    order = np.argsort(codes, kind="stable")
    previous = np.full(codes.size, -1, dtype=np.int64)
    same = codes[order[1:]] == codes[order[:-1]]
    previous[order[1:][same]] = order[:-1][same]
    return previous


def _max_types(threshold: float, max_len: int) -> np.ndarray:
    """The largest number of lexemes at which the TTR of a factor of each length is not above the threshold"""
    lengths = np.arange(1, max_len + 1)
    allowed = np.floor(threshold * lengths).astype(np.int64)
    while np.any(higher := (allowed + 1) / lengths <= threshold):
        allowed[higher] += 1
    while np.any(lower := allowed / lengths > threshold):
        allowed[lower] -= 1
    return np.concatenate([[-1], allowed])


def _mtld_factor_lengths(
    text: Sequence[str], threshold: float, min_len: int, wrap: bool
) -> list[int]:
    """
    Lengths of the first MTLD factors starting at every position of the text

    Description:
        The number of lexemes on the stretch [start, pos] is the number of its
        positions whose previous occurrence of the word lies before start; the
        starts are processed in blocks over windows of MTLD_WINDOW_LEN offsets,
        and the threshold is compared in integers through _max_types. A factor
        of length L closes only with at least L − max_types[L] repeated words,
        so the repeats after a start bound the length of its factor: those of
        the rest of the text, or of the whole text with wrap
    """
    n_words = len(text)
    if not n_words:
        return []
    previous = _previous_positions(text, wrap)
    padded = np.concatenate([previous, np.full(MTLD_WINDOW_LEN, previous.size)])
    windows = sliding_window_view(padded, MTLD_WINDOW_LEN)
    max_types = _max_types(threshold, n_words + MTLD_WINDOW_LEN)
    # Number of the factor lengths that need at most so many repeats
    fits = np.cumsum(np.bincount(np.arange(1, max_types.size) - max_types[1:]))
    if wrap:
        repeats = np.full(n_words, n_words - np.count_nonzero(previous[:n_words] < 0))
    else:
        repeated = np.bincount(previous[previous >= 0], minlength=n_words)
        repeats = np.cumsum(repeated[::-1])[::-1]
    reach = fits[np.minimum(repeats, fits.size - 1)]
    lengths = np.zeros(n_words, dtype=np.int64)
    for block_start in range(0, n_words, MTLD_BLOCK_SIZE):
        pending = np.arange(block_start, min(block_start + MTLD_BLOCK_SIZE, n_words))
        limits = np.minimum(reach[pending], n_words if wrap else n_words - pending)
        reachable = limits >= max(min_len, 1)
        pending = pending[reachable]
        limits = limits[reachable]
        counts = np.zeros(pending.size, dtype=np.int32)
        offset = 0
        while pending.size:
            types = np.cumsum(windows[pending + offset] < pending[:, None], axis=1, dtype=np.int32)
            types += counts[:, None]
            factor_lens = offset + np.arange(1, MTLD_WINDOW_LEN + 1)
            closed = types <= max_types[factor_lens]
            if min_len > offset + 1:
                closed[:, : min_len - offset - 1] = False
            if offset + MTLD_WINDOW_LEN > limits.min():
                closed &= factor_lens[None, :] <= limits[:, None]
            hit = closed.any(axis=1)
            lengths[pending[hit]] = factor_lens[closed[hit].argmax(axis=1)]
            remaining = ~hit & (offset + MTLD_WINDOW_LEN < limits)
            pending = pending[remaining]
            limits = limits[remaining]
            counts = types[remaining, -1]
            offset += MTLD_WINDOW_LEN
    return [int(length) for length in lengths[lengths > 0]]


@_checks_words
def calc_mamtld(
    text: Sequence[str], min_len: int = MTLD_MIN_LEN, threshold: float = MTLD_TTR_THRESHOLD
) -> float:
    """
    Computing the Moving Average Measure of Textual Lexical Diversity (MA-MTLD)

    Description:
        A moving-window modification of MTLD after MTLD-MA of koRpus: a factor
        starts at every position of the text, the value is the mean length of the
        completed factors over a forward and a backward pass; factors close as in
        calc_mtld, those not completed by the end of the text are ignored. koRpus
        makes the forward pass only, closes a factor at TTR strictly below the
        threshold and drops the factors shorter than the minimum length

    Arguments:
        text (list[str]): List of words
        min_len (int): Minimum factor length
        threshold (float): TTR threshold for completing a factor

    Returns:
        float: Value of the metric, nan if no factor completes

    Raises:
        ParameterError: If the TTR threshold is outside the interval (0, 1)
            or the minimum factor length is negative
        SourceTypeError: If the words are not a list of strings (check_words)
    """
    _check_mtld_params(threshold, min_len)
    lengths = _mtld_factor_lengths(text, threshold, min_len, wrap=False)
    lengths += _mtld_factor_lengths(text[::-1], threshold, min_len, wrap=False)
    return safe_divide(sum(lengths), len(lengths), nan)


@_checks_words
def calc_mtldw(
    text: Sequence[str], min_len: int = MTLD_MIN_LEN, threshold: float = MTLD_TTR_THRESHOLD
) -> float:
    """
    Computing MTLD with a moving window and text wrap (MTLD-W)

    Description:
        A modification of MA-MTLD (mtld_ma_wrap of lexical-diversity): factors not
        completed by the end of the text continue from its beginning, so all factors
        get equal weight; factors close as in calc_mtld
        Unstable on texts shorter than 100 words

    Arguments:
        text (list[str]): List of words
        min_len (int): Minimum factor length
        threshold (float): TTR threshold for completing a factor

    Returns:
        float: Value of the metric, nan if no factor completes

    Raises:
        ParameterError: If the TTR threshold is outside the interval (0, 1)
            or the minimum factor length is negative
        SourceTypeError: If the words are not a list of strings (check_words)
    """
    _check_mtld_params(threshold, min_len)
    lengths = _mtld_factor_lengths(text, threshold, min_len, wrap=True)
    return safe_divide(sum(lengths), len(lengths), nan)


@_checks_words
def calc_hdd(text: Sequence[str], sample_size: int = HDD_SAMPLE_SIZE) -> float:
    """
    Computing the Hypergeometric Distribution D (HD-D)

    Description:
        An alternative to vocd-D (McCarthy & Jarvis, 2010): the expected TTR of a
        random sample of sample_size words of the text, computed exactly from the
        hypergeometric distribution, without drawing samples

    Arguments:
        text (list[str]): List of words
        sample_size (int): Sample size in words

    Returns:
        float: Value of the metric, nan for texts shorter than 50 words or the sample size

    Raises:
        ParameterError: If the sample size is less than one
        SourceTypeError: If the words are not a list of strings (check_words)
    """
    check_integer(sample_size, "HD-D sample size")
    if sample_size < 1:
        raise ParameterError("The HD-D sample size must be greater than 0")
    n_words = len(text)
    if n_words < 50 or n_words < sample_size:
        return nan
    frequencies = np.fromiter(Counter(text).values(), dtype=np.int64)
    # probability that a lexeme is absent from the sample, in logarithms: C(N, k) overflows
    absent = np.exp(
        gammaln(n_words - frequencies + 1)
        - gammaln(np.maximum(n_words - frequencies - sample_size, 0) + 1)
        - gammaln(n_words + 1)
        + gammaln(n_words - sample_size + 1)
    )
    absent[n_words - frequencies < sample_size] = 0.0
    return float(np.sum(1.0 - absent) / sample_size)


@_checks_words
def calc_simpson_index(text: Sequence[str]) -> float:
    """
    Computing Simpson's index (D)

    Description:
        D = Σ n·(n-1) / N·(N-1), without replacement. The lower the value, the
        richer the vocabulary; undefined for texts shorter than two words

    References:
        https://en.wikipedia.org/wiki/Diversity_index#Simpson_index

    Arguments:
        text (list[str]): List of words

    Returns:
        float: Value of the index, nan for texts shorter than two words

    Raises:
        SourceTypeError: If the words are not a list of strings (check_words)
    """
    n_words = len(text)
    if n_words < 2:
        return nan
    num = sum(freq * (freq - 1) for freq in Counter(text).values())
    return num / (n_words * (n_words - 1))


@_checks_words
def calc_inverse_simpson_index(text: Sequence[str]) -> float:
    """
    Computing the inverse Simpson's index (1/D)

    Description:
        The Hill number of order two; the higher the value, the richer the vocabulary
        If all words of the text are unique, the index is infinity

    References:
        https://en.wikipedia.org/wiki/Diversity_index#Inverse_Simpson_index

    Arguments:
        text (list[str]): List of words

    Returns:
        float: Value of the index, nan for texts shorter than two words

    Raises:
        SourceTypeError: If the words are not a list of strings (check_words)
    """
    return safe_divide(1, _unchecked(calc_simpson_index)(text), inf)


@_checks_words
def calc_gini_simpson_index(text: Sequence[str]) -> float:
    """
    Computing the Gini-Simpson index (1-D)

    Description:
        The probability that two randomly chosen words of the text are different
        The higher the value, the richer the vocabulary of the text

    References:
        https://en.wikipedia.org/wiki/Diversity_index#Gini–Simpson_index

    Arguments:
        text (list[str]): List of words

    Returns:
        float: Value of the index, nan for texts shorter than two words

    Raises:
        SourceTypeError: If the words are not a list of strings (check_words)
    """
    return 1 - _unchecked(calc_simpson_index)(text)


@_checks_words
def calc_hapax_index(text: Sequence[str]) -> float:
    """
    Computing the hapax index (Honoré's R)

    Description:
        Honoré's measure (1979): R = 100 · ln N / (1 - V1/V), where N is the number
        of words, V the number of lexemes, V1 the number of hapaxes (words that occur
        once); infinity if all words of the text are hapaxes
        Available under the alias calc_honore_r

    References:
        https://en.wikipedia.org/wiki/Hapax_legomenon

    Arguments:
        text (list[str]): List of words

    Returns:
        float: Value of the index, nan for texts shorter than two words

    Raises:
        SourceTypeError: If the words are not a list of strings (check_words)
    """
    n_words = len(text)
    if n_words < 2:
        return nan
    n_lexemes = len(set(text))
    num = 100 * log(n_words)
    hapaxes = _unchecked(calc_frequency_spectrum)(text).get(1, 0)
    den = 1 - (safe_divide(hapaxes, n_lexemes))
    return safe_divide(num, den, inf)


calc_honore_r = calc_hapax_index


@_checks_words
def calc_yule_k(text: Sequence[str]) -> float:
    """
    Computing Yule's characteristic (Yule's K)

    Description:
        K = 10⁴ · (Σ i²·V_i - N) / N², where V_i is the number of lexemes with frequency i (Yule, 1944)
        Theoretically independent of text length (Tweedie & Baayen, 1998)
        The lower the value, the richer the vocabulary; K ≈ 10⁴ · D (Simpson's index)

    References:
        https://link.springer.com/content/pdf/10.1007/s10579-005-8622-8.pdf

    Arguments:
        text (list[str]): List of words

    Returns:
        float: Value of the characteristic, nan for texts shorter than two words

    Raises:
        SourceTypeError: If the words are not a list of strings (check_words)
    """
    n_words = len(text)
    if n_words < 2:
        return nan
    spectrum = _unchecked(calc_frequency_spectrum)(text)
    sum_squares = sum(freq**2 * count for freq, count in spectrum.items())
    return 1e4 * (sum_squares - n_words) / n_words**2


@_checks_words
def calc_yule_i(text: Sequence[str]) -> float:
    """
    Computing the inverse Yule's characteristic (Yule's I)

    Description:
        I = V² / (Σ i²·V_i - V), where V is the number of lexemes, V_i the number of lexemes with frequency i
        The reciprocal of the characteristic K, the higher the value, the richer the vocabulary
        If all words of the text are unique, the value is infinity

    Arguments:
        text (list[str]): List of words

    Returns:
        float: Value of the characteristic, nan for texts shorter than two words

    Raises:
        SourceTypeError: If the words are not a list of strings (check_words)
    """
    if len(text) < 2:
        return nan
    n_lexemes = len(set(text))
    spectrum = _unchecked(calc_frequency_spectrum)(text)
    sum_squares = sum(freq**2 * count for freq, count in spectrum.items())
    return safe_divide(n_lexemes**2, sum_squares - n_lexemes, inf)


@_checks_words
def calc_herdan_vm(text: Sequence[str]) -> float:
    """
    Computing Herdan's measure (Herdan's Vm)

    Description:
        Vm = sqrt(Σ V_i · (i/N)² - 1/V), where N is the number of words, V the number
        of lexemes, V_i the number of lexemes with frequency i (Herdan, 1955)
        Theoretically independent of text length, the lower the value, the richer the vocabulary

    Arguments:
        text (list[str]): List of words

    Returns:
        float: Value of the measure, nan for texts shorter than two words

    Raises:
        SourceTypeError: If the words are not a list of strings (check_words)
    """
    n_words = len(text)
    if n_words < 2:
        return nan
    n_lexemes = len(set(text))
    spectrum = _unchecked(calc_frequency_spectrum)(text)
    sum_probs = sum(count * (freq / n_words) ** 2 for freq, count in spectrum.items())
    return sqrt(max(sum_probs - 1 / n_lexemes, 0))


@_checks_words
def calc_sichel_s(text: Sequence[str]) -> float:
    """
    Computing Sichel's measure (Sichel's S)

    Description:
        S = V2 / V - the share of dis legomena, lexemes with frequency 2, among all lexemes (Sichel, 1975)
        Stable across texts of different lengths

    Arguments:
        text (list[str]): List of words

    Returns:
        float: Value of the measure

    Raises:
        SourceTypeError: If the words are not a list of strings (check_words)
    """
    spectrum = _unchecked(calc_frequency_spectrum)(text)
    return safe_divide(spectrum.get(2, 0), len(set(text)))


@_checks_words
def calc_michea_m(text: Sequence[str]) -> float:
    """
    Computing Michéa's measure (Michéa's M)

    Description:
        M = V / V2 - the reciprocal of Sichel's measure (Michéa, 1969)
        If the text has no dis legomena, the value is infinity

    Arguments:
        text (list[str]): List of words

    Returns:
        float: Value of the measure

    Raises:
        SourceTypeError: If the words are not a list of strings (check_words)
    """
    spectrum = _unchecked(calc_frequency_spectrum)(text)
    return safe_divide(len(set(text)), spectrum.get(2, 0), inf)


@_checks_words
def calc_brunet_w(text: Sequence[str], a: float = BRUNET_W_EXPONENT) -> float:
    """
    Computing Brunet's measure (Brunet's W)

    Description:
        W = N ^ (V ^ -a), where N is the number of words, V the number of lexemes, a = 0.172 (Brunet, 1978)
        Values for texts usually lie within 10-20, the lower the value, the richer the vocabulary

    Arguments:
        text (list[str]): List of words
        a (float): Exponent

    Returns:
        float: Value of the measure

    Raises:
        SourceTypeError: If the words are not a list of strings (check_words)
    """
    n_words = len(text)
    n_lexemes = len(set(text))
    if not n_words:
        return nan
    return float(n_words ** (n_lexemes**-a))


@_checks_words
def calc_dugast_k(text: Sequence[str], base: float = DIVERSITY_LOG_BASE) -> float:
    """
    Computing Dugast's measure (Dugast's k)

    Description:
        k = log V / log log N, where N is the number of words, V the number of lexemes (Dugast, 1979)
        The value depends on the logarithm base, 10 by default
        Undefined when log N is not above 1, that is, for texts no longer than the logarithm base

    Arguments:
        text (list[str]): List of words
        base (float): Logarithm base

    Returns:
        float: Value of the measure, nan for short texts

    Raises:
        ParameterError: If the logarithm base is not greater than 1
        SourceTypeError: If the words are not a list of strings (check_words)
    """
    _check_log_base(base)
    n_words = len(text)
    n_lexemes = len(set(text))
    if not n_words or log(n_words, base) <= 1:
        return nan
    return log(n_lexemes, base) / log(log(n_words, base), base)


@_checks_words
def calc_baayen_p(text: Sequence[str]) -> float:
    """
    Computing Baayen's measure (Baayen's P)

    Description:
        P = V1 / N - the share of hapaxes among all words of the text (Baayen, 1991)
        Equals the slope of the vocabulary growth curve at the end of the text:
        the probability that the next word is new

    Arguments:
        text (list[str]): List of words

    Returns:
        float: Value of the measure

    Raises:
        SourceTypeError: If the words are not a list of strings (check_words)
    """
    spectrum = _unchecked(calc_frequency_spectrum)(text)
    return safe_divide(spectrum.get(1, 0), len(text))


@_checks_words
def calc_hapax_ratio(text: Sequence[str]) -> float:
    """
    Computing the hapax ratio

    Description:
        V1 / V - the share of hapaxes among all lexemes of the text

    Arguments:
        text (list[str]): List of words

    Returns:
        float: Value of the ratio

    Raises:
        SourceTypeError: If the words are not a list of strings (check_words)
    """
    spectrum = _unchecked(calc_frequency_spectrum)(text)
    return safe_divide(spectrum.get(1, 0), len(set(text)))


@_checks_words
def calc_alpha2(text: Sequence[str]) -> float:
    """
    Computing the α₂ exponent

    Description:
        α₂ = 1 - 2·V2 / V1, where V1 is the number of hapaxes, V2 the number of dis legomena
        An estimate of the Zipf-Mandelbrot parameter from the lower part of the frequency spectrum (Evert, 2004)

    Arguments:
        text (list[str]): List of words

    Returns:
        float: Value of the exponent, nan if the text has no hapaxes

    Raises:
        SourceTypeError: If the words are not a list of strings (check_words)
    """
    spectrum = _unchecked(calc_frequency_spectrum)(text)
    hapaxes = spectrum.get(1, 0)
    if not hapaxes:
        return nan
    return 1 - 2 * spectrum.get(2, 0) / hapaxes


@_checks_words
def calc_entropy(text: Sequence[str]) -> float:
    """
    Computing the Shannon entropy

    Description:
        H = -Σ p_k · log₂ p_k, where p_k is the relative frequency of a lexeme
        Measured in bits, the higher the value, the richer the vocabulary of the text

    References:
        https://en.wikipedia.org/wiki/Diversity_index#Shannon_index

    Arguments:
        text (list[str]): List of words

    Returns:
        float: Value of the entropy

    Raises:
        SourceTypeError: If the words are not a list of strings (check_words)
    """
    n_words = len(text)
    if not n_words:
        return nan
    return -sum(freq / n_words * log2(freq / n_words) for freq in Counter(text).values()) or 0.0


@_checks_words
def calc_evenness(text: Sequence[str]) -> float:
    """
    Computing evenness

    Description:
        H / log₂ V - the ratio of the Shannon entropy to its maximum for the given
        number of lexemes (Pielou's evenness), lies between 0 and 1

    Arguments:
        text (list[str]): List of words

    Returns:
        float: Value of the evenness, nan for texts of a single lexeme

    Raises:
        SourceTypeError: If the words are not a list of strings (check_words)
    """
    n_lexemes = len(set(text))
    if n_lexemes < 2:
        return nan
    return _unchecked(calc_entropy)(text) / log2(n_lexemes)


@_checks_words
def calc_perplexity(text: Sequence[str]) -> float:
    """
    Computing perplexity

    Description:
        2^H, where H is the Shannon entropy in bits; the Hill number of order one,
        the effective number of lexemes of the text

    Arguments:
        text (list[str]): List of words

    Returns:
        float: Value of the perplexity

    Raises:
        SourceTypeError: If the words are not a list of strings (check_words)
    """
    return float(2 ** _unchecked(calc_entropy)(text))


@_checks_words
def calc_zipf_alpha(text: Sequence[str]) -> float:
    """
    Computing the slope of Zipf's law

    Description:
        The exponent α of the law f(r) ∝ r^(-α), where r is the frequency rank of a lexeme
        Estimated by linear regression of log frequency on log rank, which is biased
        For natural texts α is close to 1

    References:
        https://en.wikipedia.org/wiki/Zipf's_law

    Arguments:
        text (list[str]): List of words

    Returns:
        float: Value of the exponent, nan for texts of a single lexeme

    Raises:
        SourceTypeError: If the words are not a list of strings (check_words)
    """
    frequencies = sorted(Counter(text).values(), reverse=True)
    if len(frequencies) < 2:
        return nan
    ranks = np.arange(1, len(frequencies) + 1)
    slope = np.polyfit(np.log(ranks), np.log(frequencies), 1)[0]
    return float(-slope) or 0.0


class ZipfMandelbrot(NamedTuple):
    """
    Parameters of the Zipf-Mandelbrot law f(r) = C / (r + q)^s

    Attributes:
        c (float): Scale C
        q (float): Rank shift q
        s (float): Exponent s
        r2 (float): Coefficient of determination of the fit in logarithmic coordinates
    """

    c: float
    q: float
    s: float
    r2: float


def fit_zipf_mandelbrot(text: Sequence[str] | Mapping[str, int]) -> ZipfMandelbrot:
    """
    Fitting the Zipf-Mandelbrot law to the frequency distribution

    Description:
        The law f(r) = C / (r + q)^s, where r is the frequency rank of a lexeme; with q = 0
        it reduces to Zipf's law with exponent s, the shift q describes the flattening
        of the curve on the most frequent words
        Fitted by least squares in logarithmic coordinates with q ≥ 0 and s ≥ 0

    References:
        https://en.wikipedia.org/wiki/Zipf–Mandelbrot_law

    Arguments:
        text (list[str]|Counter): List of words or frequency counter

    Returns:
        ZipfMandelbrot: Parameters of the law, nan for texts of fewer than three lexemes,
            with identical frequencies of all lexemes or if the fit diverges

    Raises:
        SourceTypeError: If the words are not a list of strings (check_words)
            or the counter fails check_counts
    """
    if isinstance(text, Mapping):
        check_counts(text)
    else:
        check_words(text)
    frequencies = np.array(
        sorted((count for count in Counter(text).values() if count > 0), reverse=True),
        dtype=float,
    )
    if len(frequencies) < 3 or frequencies[0] == frequencies[-1]:
        return ZipfMandelbrot(nan, nan, nan, nan)
    ranks = np.arange(1, len(frequencies) + 1, dtype=float)
    log_frequencies = np.log(frequencies)

    def model(rank: np.ndarray, log_c: float, q: float, s: float) -> np.ndarray:
        return log_c - s * np.log(rank + q)

    def residuals(params: np.ndarray) -> np.ndarray:
        log_c, q, s = (float(value) for value in params)
        return np.asarray(model(ranks, log_c, q, s) - log_frequencies)

    # not curve_fit: it warns when the covariance cannot be estimated
    try:
        result = least_squares(
            residuals,
            x0=(log_frequencies[0], 1.0, 1.0),
            bounds=([-np.inf, 0.0, 0.0], [np.inf, np.inf, np.inf]),
        )
    except ValueError:
        return ZipfMandelbrot(nan, nan, nan, nan)
    if not result.success:
        return ZipfMandelbrot(nan, nan, nan, nan)
    log_c, q, s = (float(value) for value in result.x)
    residual = float(((log_frequencies - model(ranks, log_c, q, s)) ** 2).sum())
    total = float(((log_frequencies - log_frequencies.mean()) ** 2).sum())
    return ZipfMandelbrot(float(np.exp(log_c)), float(q), float(s), 1 - residual / total)


class HeapsFit(NamedTuple):
    """
    Parameters of Heaps' law V(N) = K · N^β

    Attributes:
        k (float): Coefficient K
        beta (float): Exponent β
        r2 (float): Coefficient of determination of the fit in logarithmic coordinates
    """

    k: float
    beta: float
    r2: float


@_checks_words
def fit_heaps(text: Sequence[str]) -> HeapsFit:
    """
    Fitting Heaps' law to the vocabulary growth curve

    Description:
        The law V(N) = K · N^β, where V is the vocabulary size after N words of the text;
        fitted by linear regression of log V on log N along the vocabulary growth curve
        Depends on the word order

    References:
        https://en.wikipedia.org/wiki/Heaps'_law

    Arguments:
        text (list[str]): List of words

    Returns:
        HeapsFit: Parameters of the law, nan for texts shorter than two words

    Raises:
        SourceTypeError: If the words are not a list of strings (check_words)
    """
    n_words = len(text)
    if n_words < 2:
        return HeapsFit(nan, nan, nan)
    growth = np.log(_unchecked(vocabulary_growth)(text))
    lengths = np.log(np.arange(1, n_words + 1))
    slope, intercept = np.polyfit(lengths, growth, 1)
    residual = float(((growth - (intercept + slope * lengths)) ** 2).sum())
    total = float(((growth - growth.mean()) ** 2).sum())
    r2 = 1 - residual / total if total else nan
    return HeapsFit(float(np.exp(intercept)), float(slope) or 0.0, r2)


@_checks_words
def vocabulary_growth(text: Sequence[str]) -> list[int]:
    """
    Computing the vocabulary growth curve

    Arguments:
        text (list[str]): List of words

    Returns:
        list[int]: Vocabulary size after every word of the text

    Raises:
        SourceTypeError: If the words are not a list of strings (check_words)
    """
    seen: set[str] = set()
    growth = []
    for word in text:
        seen.add(word)
        growth.append(len(seen))
    return growth


@_checks_words
def calc_heaps_beta(text: Sequence[str]) -> float:
    """
    Computing the exponent of Heaps' law

    Description:
        The exponent β of the law V(N) = K · N^β, estimated as in fit_heaps
        Needs several hundred words or more; a single text gives 0.6-0.9 (corpora of
        millions of words 0.4-0.6), so compare only texts of similar length

    References:
        https://en.wikipedia.org/wiki/Heaps'_law

    Arguments:
        text (list[str]): List of words

    Returns:
        float: Value of the exponent, nan for texts shorter than two words

    Raises:
        SourceTypeError: If the words are not a list of strings (check_words)
    """
    return _unchecked(fit_heaps)(text).beta


@_checks_words
def calc_windowed(
    text: Sequence[str],
    func: Calculator,
    window_len: int = 100,
    step: int | None = None,
    confidence: float = 0.95,
) -> WindowStats:
    """
    Windowed computation of a metric

    Description:
        The metric is computed over consecutive windows of the text of equal length,
        the values of the windows give the mean, the sample standard deviation
        and the confidence interval of the mean by Student's distribution
        A text shorter than the window is a single window
        Windows with an undefined metric (nan) are ignored; if the metric is infinite
        in any window, the mean is infinite and the deviation and the interval are nan

    Arguments:
        text (list[str]): List of words
        func (callable): Function computing the metric from a list of words
        window_len (int): Window size
        step (int): Window step, by default equal to the window size (windows do not overlap)
        confidence (float): Confidence level

    Returns:
        WindowStats: Mean, standard deviation, bounds of the interval and number of windows

    Raises:
        ParameterError: If the metric is not a function or the window size, the
            step or the confidence level are set incorrectly
        SourceTypeError: If the words are not a list of strings (check_words)
    """
    check_integer(window_len, "window size")
    if window_len < 1:
        raise ParameterError("The window size must be greater than 0")
    if step is None:
        step = window_len
    check_integer(step, "window step")
    if step < 1:
        raise ParameterError("The window step must be greater than 0")
    if not callable(func):
        raise ParameterError(f"The metric must be a function, not {type(func).__name__}")
    check_number(confidence, "confidence level")
    if not 0 < confidence < 1:
        raise ParameterError("The confidence level must lie in the interval (0, 1)")
    starts = range(0, max(len(text) - window_len, 0) + 1, step)
    # The windows are slices of words checked on the way in
    func = _unchecked(func)
    values = np.array([func(text[start : start + window_len]) for start in starts], dtype=float)
    values = values[~np.isnan(values)]
    n_windows = int(values.size)
    if not n_windows:
        return WindowStats(nan, nan, nan, nan, 0)
    with np.errstate(invalid="ignore"):
        mean = float(values.mean())
    if n_windows < 2 or not np.isfinite(mean):
        return WindowStats(mean, nan, nan, nan, n_windows)
    std = float(values.std(ddof=1))
    half_width = float(student_t.ppf((1 + confidence) / 2, n_windows - 1)) * std / sqrt(n_windows)
    return WindowStats(mean, std, mean - half_width, mean + half_width, n_windows)
