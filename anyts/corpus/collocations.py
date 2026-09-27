from collections import Counter
from collections.abc import Sequence
from math import isnan, log, log2, nan, sqrt
from typing import NamedTuple

from ..constants import COLLOCATION_MEASURES
from ..exceptions import ParameterError, SourceError
from ..utils import check_integer, check_words


class Collocation(NamedTuple):
    """
    Collocation - a pair of words with a measure of association

    Attributes:
        left (str): Left word
        right (str): Right word, which occurs within the window after the left one
        freq_left (int): Frequency of the left word
        freq_right (int): Frequency of the right word
        freq_pair (int): Frequency of the co-occurrence
        score (float): Value of the chosen measure
    """

    left: str
    right: str
    freq_left: int
    freq_right: int
    freq_pair: int
    score: float


def collocations(
    words: Sequence[str],
    window: int = 5,
    measure: str = "logdice",
    min_freq: int = 2,
    node: str | None = None,
    top_n: int | None = None,
) -> list[Collocation]:
    """
    Finding the collocations of a sequence of words

    Description:
        Pairs of words are ordered: the right word occurs no more than window
        words after the left one, every pair of positions counted once;
        window = 1 gives bigrams. Inside the measure the frequency of the pair
        is divided by the window (Church and Hanks 1990, as in NLTK), while
        freq_pair keeps the undivided frequency; so with window > 1 a pair
        always side by side gets a logDice of 14 − log2(window), not 14.
        Words are compared as they are: case, lemmatization and stop words
        belong to the extraction

    References:
        https://www.sketchengine.eu/wp-content/uploads/ske-statistics.pdf
        https://www.nltk.org/api/nltk.metrics.association.html

    Arguments:
        words (list[str]): Words of the text in order
        window (int): Greatest distance between the words of a pair
        measure (str): Measure of COLLOCATION_MEASURES
        min_freq (int): Minimum frequency of a pair
        node (str): Word whose collocations are needed (left or right); None - every pair
        top_n (int): Number of collocations; None - all of them

    Returns:
        list[Collocation]: Collocations by descending measure and frequency of the
            pair, alphabetically when equal

    Raises:
        SourceTypeError: If the words are not a list of strings (check_words)
        SourceError: If there are no words
        ParameterError: If the measure is unknown or the window or top_n is below one

    Example:
        >>> from anyts.corpus import collocations
        >>> words = "red wine and white wine but red wine".split()
        >>> [(c.left, c.right, c.freq_pair) for c in collocations(words, window=1)]
        [('red', 'wine', 2)]
    """
    if measure not in COLLOCATION_MEASURES:
        raise ParameterError(f"Unknown measure of association: {measure}")
    check_integer(window, "window")
    if window < 1:
        raise ParameterError("The window must be at least one")
    if top_n is not None:
        check_integer(top_n, "number of collocations")
    if top_n is not None and top_n < 1:
        raise ParameterError("The number of collocations must be greater than 0")
    check_words(words)
    if not len(words):
        raise SourceError("The data source has no words")
    calc = MEASURES[measure]
    n_words = len(words)
    frequencies = Counter(words)
    pairs: Counter[tuple[str, str]] = Counter()
    for index, left in enumerate(words):
        for right in words[index + 1 : index + 1 + window]:
            if node is None or node in (left, right):
                pairs[left, right] += 1
    found = [
        Collocation(
            left,
            right,
            frequencies[left],
            frequencies[right],
            freq_pair,
            calc(frequencies[left], frequencies[right], freq_pair / window, n_words),
        )
        for (left, right), freq_pair in pairs.items()
        if freq_pair >= min_freq
    ]
    found.sort(
        key=lambda collocation: (
            isnan(collocation.score),
            -(0.0 if isnan(collocation.score) else collocation.score),
            -collocation.freq_pair,
            collocation.left,
            collocation.right,
        )
    )
    return found[:top_n] if top_n else found


def calc_mi(freq_a: int, freq_b: int, freq_ab: float, n: int) -> float:
    """
    Computing the mutual information MI

    Description:
        log2(f_ab · N / (f_a · f_b)); overrates rare pairs

    Arguments:
        freq_a (int): Frequency of the first word
        freq_b (int): Frequency of the second word
        freq_ab (float): Frequency of the pair
        n (int): Number of words of the text

    Returns:
        float: MI, nan for a pair of zero frequency
    """
    if not freq_ab:
        return nan
    return log2(freq_ab * n / (freq_a * freq_b))


def calc_mi3(freq_a: int, freq_b: int, freq_ab: float, n: int) -> float:
    """
    Computing the cubic mutual information MI³

    Description:
        log2(f_ab³ · N / (f_a · f_b)); unlike MI, favours frequent pairs

    Arguments:
        freq_a (int): Frequency of the first word
        freq_b (int): Frequency of the second word
        freq_ab (float): Frequency of the pair
        n (int): Number of words of the text

    Returns:
        float: MI³, nan for a pair of zero frequency
    """
    if not freq_ab:
        return nan
    return log2(freq_ab**3 * n / (freq_a * freq_b))


def calc_t_score(freq_a: int, freq_b: int, freq_ab: float, n: int) -> float:
    """
    Computing the t-score

    Description:
        (f_ab − f_a · f_b / N) / sqrt(f_ab); favours frequent pairs

    Arguments:
        freq_a (int): Frequency of the first word
        freq_b (int): Frequency of the second word
        freq_ab (float): Frequency of the pair
        n (int): Number of words of the text

    Returns:
        float: t-score, nan for a pair of zero frequency
    """
    if not freq_ab:
        return nan
    return (freq_ab - freq_a * freq_b / n) / sqrt(freq_ab)


def calc_dice(freq_a: int, freq_b: int, freq_ab: float, n: int) -> float:
    """
    Computing the Dice coefficient

    Description:
        2 · f_ab / (f_a + f_b); does not depend on the size of the text

    Arguments:
        freq_a (int): Frequency of the first word
        freq_b (int): Frequency of the second word
        freq_ab (float): Frequency of the pair
        n (int): Number of words of the text (not used)

    Returns:
        float: Dice coefficient
    """
    return 2 * freq_ab / (freq_a + freq_b)


def calc_logdice(freq_a: int, freq_b: int, freq_ab: float, n: int) -> float:
    """
    Computing logDice

    Description:
        14 + log2(2 · f_ab / (f_a + f_b)) by Rychlý (2008); does not depend on
        the size of the text, at most 14, values below zero - a weak link

    References:
        https://www.sketchengine.eu/glossary/logdice/

    Arguments:
        freq_a (int): Frequency of the first word
        freq_b (int): Frequency of the second word
        freq_ab (float): Frequency of the pair
        n (int): Number of words of the text (not used)

    Returns:
        float: logDice, nan for a pair of zero frequency
    """
    if not freq_ab:
        return nan
    return 14 + log2(2 * freq_ab / (freq_a + freq_b))


def calc_log_likelihood(freq_a: int, freq_b: int, freq_ab: float, n: int) -> float:
    """
    Computing the log-likelihood G² of a pair of words

    Description:
        Over the 2×2 contingency table (Dunning 1993): the observed frequencies
        f_ab, f_a − f_ab, f_b − f_ab, N − f_a − f_b + f_ab against the expected
        ones under independence, G² = 2 · Σ O · ln(O / E)

    Arguments:
        freq_a (int): Frequency of the first word
        freq_b (int): Frequency of the second word
        freq_ab (float): Frequency of the pair
        n (int): Number of words of the text

    Returns:
        float: G², nan if one of the words fills the whole text or the table is
            degenerate (a pair of a word with itself in a window above one gives
            a negative cell)
    """
    if freq_a >= n or freq_b >= n:
        return nan
    observed = (freq_ab, freq_a - freq_ab, freq_b - freq_ab, n - freq_a - freq_b + freq_ab)
    if min(observed) < 0:
        return nan
    expected = (
        freq_a * freq_b / n,
        freq_a * (n - freq_b) / n,
        (n - freq_a) * freq_b / n,
        (n - freq_a) * (n - freq_b) / n,
    )
    return 2 * sum(o * log(o / e) for o, e in zip(observed, expected, strict=True) if o > 0)


def calc_npmi(freq_a: int, freq_b: int, freq_ab: float, n: int) -> float:
    """
    Computing the normalized pointwise mutual information NPMI

    Description:
        MI / (−log2(f_ab / N)) by Bouma (2009); lies between −1 and 1, one - the
        words occur only together

    Arguments:
        freq_a (int): Frequency of the first word
        freq_b (int): Frequency of the second word
        freq_ab (float): Frequency of the pair
        n (int): Number of words of the text

    Returns:
        float: NPMI, nan for a pair of zero frequency or a pair as long as the text
    """
    if not freq_ab or freq_ab == n:
        return nan
    return calc_mi(freq_a, freq_b, freq_ab, n) / -log2(freq_ab / n)


def calc_min_sensitivity(freq_a: int, freq_b: int, freq_ab: float, n: int) -> float:
    """
    Computing the minimum sensitivity

    Description:
        min(f_ab / f_a, f_ab / f_b) by Pedersen (1998); lies between 0 and 1

    Arguments:
        freq_a (int): Frequency of the first word
        freq_b (int): Frequency of the second word
        freq_ab (float): Frequency of the pair
        n (int): Number of words of the text (not used)

    Returns:
        float: Minimum sensitivity
    """
    return min(freq_ab / freq_a, freq_ab / freq_b)


MEASURES = {
    "mi": calc_mi,
    "mi3": calc_mi3,
    "t_score": calc_t_score,
    "dice": calc_dice,
    "logdice": calc_logdice,
    "log_likelihood": calc_log_likelihood,
    "npmi": calc_npmi,
    "min_sensitivity": calc_min_sensitivity,
}
