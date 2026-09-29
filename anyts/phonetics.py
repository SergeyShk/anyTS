from collections.abc import Collection, Sequence
from math import comb, fsum, nan

import numpy as np

from .exceptions import ParameterError
from .utils import check_integer, check_sequence, check_words, safe_divide


def calc_repetition_index(
    words: Sequence[Sequence[str]], window_len: int, features: Collection[str] | None = None
) -> float:
    """
    Computing the repetition index

    Description:
        The number of windows of window_len neighbouring words where a feature
        occurs in two words or more, summed over the features, to the number
        expected if the words stood in random order: about 1 - random
        repetitions, well above 1 - the repetitions gather in neighbouring
        words. The features of a word are the characters of a string or the
        items of a list, each counted once

    Arguments:
        words (list[str]|list[list[str]]): Features of every word, such as its
            letters or the sounds of its transcription
        window_len (int): Window in words
        features (Collection[str]|None): Features to count, all of them by default

    Returns:
        float: Value of the index, nan for a text shorter than the window or
            without a feature shared by two words

    Raises:
        SourceTypeError: If the words are not a list (check_sequence), a word is
            neither a string nor a collection of strings, or the features are not
            a collection of strings
        ParameterError: If the window is not an integer or is below 2

    Example:
        >>> from anyts.phonetics import calc_repetition_index
        >>> words = ["sal", "sol", "mes", "luz", "paz", "mar"]
        >>> calc_repetition_index(words, 2, {"s"})
        2.0
    """
    check_sequence(words)
    for word in words:
        if not isinstance(word, str):
            check_words(word, "features of a word", ordered=False)
    if features is not None:
        check_words(features, "features", ordered=False)
    check_integer(window_len, "window")
    if window_len < 2:
        raise ParameterError("The window must be at least 2")
    n_words = len(words)
    if n_words < window_len:
        return nan
    sets = [frozenset(word) for word in words]
    unique = list(dict.fromkeys(sets))
    alphabet = sorted(frozenset().union(*unique))
    if features is not None:
        alphabet = [feature for feature in alphabet if feature in features]
    presence = np.array(
        [[feature in word for feature in alphabet] for word in unique], dtype=np.int32
    ).reshape(len(unique), len(alphabet))
    indices = dict(zip(unique, range(len(unique)), strict=True))
    rows = np.fromiter(map(indices.__getitem__, sets), dtype=np.int64, count=n_words)
    cumulative = np.zeros((n_words + 1, len(alphabet)), dtype=np.int32)
    np.cumsum(presence[rows], axis=0, out=cumulative[1:])
    observed = int((cumulative[window_len:] - cumulative[:-window_len] >= 2).sum())
    n_windows = n_words - window_len + 1
    expected = n_windows * fsum(
        _repetition_probability(int(count), n_words, window_len) for count in cumulative[-1]
    )
    return safe_divide(observed, expected, nan)


def _repetition_probability(count: int, n_words: int, window_len: int) -> float:
    """
    Probability that a window of the words in random order holds two or more
    of the count words with a feature (the hypergeometric distribution)
    """
    rest = n_words - count
    total = comb(n_words, window_len)
    return (total - comb(rest, window_len) - count * comb(rest, window_len - 1)) / total
