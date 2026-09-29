from collections.abc import Collection, Sequence
from math import comb, fsum, nan

import numpy as np

from .exceptions import ParameterError
from .utils import check_integer, check_sequence, check_words, safe_divide


def calc_repetition_index(
    words: Sequence[Collection[str]], window_len: int, features: Collection[str] | None = None
) -> float:
    """
    Computing the repetition index

    Description:
        The number of windows of window_len neighbouring words where a feature
        occurs in two words or more, summed over the features, to the number
        expected if the words stood in random order: about 1 - random
        repetitions, well above 1 - the repetitions gather in neighbouring
        words. The features of a word are the characters of a string or the
        items of a collection, each counted once

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
        >>> words = ["sea", "sun", "gas", "fog", "box", "hat"]
        >>> calc_repetition_index(words, 2, {"s"})
        2.0
    """
    check_sequence(words)
    keys = list(map(_word_key, words))
    unique = list(dict.fromkeys(keys))
    for word in unique:
        if not isinstance(word, str):
            check_words(word, "features of a word", ordered=False)
    if features is not None:
        check_words(features, "features", ordered=False)
        features = frozenset(features)
    check_integer(window_len, "window")
    if window_len < 2:
        raise ParameterError("The window must be at least 2")
    n_words = len(words)
    if n_words < window_len:
        return nan
    columns: dict[str, int] = {}
    cells: tuple[list[int], list[int]] = ([], [])
    for row, word in enumerate(unique):
        for feature in word:
            if features is None or feature in features:
                cells[0].append(row)
                cells[1].append(columns.setdefault(feature, len(columns)))
    presence = np.zeros((len(unique), len(columns)), dtype=np.int8)
    presence[cells] = 1
    indices = dict(zip(unique, range(len(unique)), strict=True))
    rows = np.fromiter(map(indices.__getitem__, keys), dtype=np.int64, count=n_words)
    observed, counts = _count_windows(presence, rows, window_len)
    total = comb(n_words, window_len)
    expected = (n_words - window_len + 1) * fsum(
        _repetition_probability(count, n_words, window_len, total) for count in counts
    )
    return safe_divide(observed, expected, nan)


def _word_key(word: Collection[str]) -> Collection[str]:
    """A word itself, or the tuple of its features when it cannot be a key of a dict"""
    try:
        hash(word)
    except TypeError:
        check_words(word, "features of a word", ordered=False)
        return tuple(word)
    return word


def _count_windows(
    presence: np.ndarray, rows: np.ndarray, window_len: int, block_size: int = 64
) -> tuple[int, list[int]]:
    """
    Number of the windows with a feature in two words or more, summed over the
    features, and the number of the words with every feature

    Description:
        The features are counted in blocks of columns, so that a large alphabet
        takes little memory
    """
    observed = 0
    counts: list[int] = []
    for start in range(0, presence.shape[1], block_size):
        block = presence[rows, start : start + block_size]
        cumulative = np.zeros((len(rows) + 1, block.shape[1]), dtype=np.int32)
        np.cumsum(block, axis=0, out=cumulative[1:])
        observed += int((cumulative[window_len:] - cumulative[:-window_len] >= 2).sum())
        counts.extend(cumulative[-1].tolist())
    return observed, counts


def _repetition_probability(count: int, n_words: int, window_len: int, total: int) -> float:
    """
    Probability that a window of the words in random order holds two or more
    of the count words with a feature (the hypergeometric distribution); total
    is C(n_words, window_len)
    """
    rest = n_words - count
    return (total - comb(rest, window_len) - count * comb(rest, window_len - 1)) / total
