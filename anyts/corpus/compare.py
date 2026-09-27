from collections.abc import Sequence
from math import nan, sqrt
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu

from ..exceptions import ParameterError

Values = Sequence[float] | np.ndarray[Any, Any]


COMPARISON_COLUMNS = (
    "mean_a",
    "mean_b",
    "median_a",
    "median_b",
    "median_diff",
    "ci_low",
    "ci_high",
    "cohen_d",
    "cliff_delta",
    "auc",
    "u",
    "p_value",
    "p_holm",
    "n_a",
    "n_b",
    "n_texts_a",
    "n_texts_b",
)


def compare_features(
    table_a: pd.DataFrame,
    table_b: pd.DataFrame,
    labels: tuple[str, str] = ("A", "B"),
    n_bootstrap: int = 1000,
    seed: int | None = 0,
) -> pd.DataFrame:
    """
    Comparing two corpora by the tables of the features of their windows

    Description:
        The tables are compared column by column: for every feature the two
        sets of values give the means and the medians, the difference of the
        medians with its bootstrap interval, Cohen's d, Cliff's delta, the AUC
        (the share of the pairs of windows where the value in A is greater than
        in B, ties counted as half; Cliff's delta = 2·AUC − 1), the two-sided
        Mann-Whitney U test and Holm's correction for the number of features.
        Undefined and infinite values are dropped; with fewer than two values
        on a side the statistics are nan. The rows are sorted by descending
        absolute Cliff's delta, the features without statistics last
        The test and the effect sizes take the windows as independent, while
        the windows of one text are not: with few texts the p-values are too
        small. The bootstrap resamples whole texts by the level text of the
        index, so its interval accounts for the spread between texts; a table
        without that level takes every row for a text of its own. A column
        missing from one of the tables gives nan

    References:
        https://doi.org/10.1037/0033-2909.114.3.494
        https://en.wikipedia.org/wiki/Mann–Whitney_U_test

    Arguments:
        table_a (DataFrame): Features of the windows of the first corpus (rows - the windows)
        table_b (DataFrame): Features of the windows of the second corpus
        labels (tuple[str, str]): Names of the corpora for the columns (mean_<a>, ...)
        n_bootstrap (int): Number of bootstrap samples
        seed (int): Seed of the random number generator; None - a random one

    Returns:
        DataFrame: Features × statistics of the comparison (COMPARISON_COLUMNS
            with the names of the corpora in the columns)

    Raises:
        ParameterError: If the number of samples is below one
    """
    if n_bootstrap < 1:
        raise ParameterError("The number of bootstrap samples must be greater than 0")
    rng = np.random.default_rng(seed)
    rows = {}
    for name in table_a.columns.union(table_b.columns, sort=False):
        values_a, texts_a = _finite(table_a, name)
        values_b, texts_b = _finite(table_b, name)
        rows[name] = compare_values(values_a, values_b, n_bootstrap, rng, texts_a, texts_b)
    result = pd.DataFrame.from_dict(rows, orient="index", columns=list(COMPARISON_COLUMNS))
    result["p_holm"] = holm_correction(result["p_value"].to_numpy())
    result = result.iloc[(-result["cliff_delta"].abs()).fillna(np.inf).argsort(kind="stable")]
    counts = ["n_a", "n_b", "n_texts_a", "n_texts_b"]
    result[counts] = result[counts].astype(int)
    label_a, label_b = labels
    return result.rename(
        columns={
            "mean_a": f"mean_{label_a}",
            "mean_b": f"mean_{label_b}",
            "median_a": f"median_{label_a}",
            "median_b": f"median_{label_b}",
            "n_a": f"n_{label_a}",
            "n_b": f"n_{label_b}",
            "n_texts_a": f"n_texts_{label_a}",
            "n_texts_b": f"n_texts_{label_b}",
        }
    )


def _finite(table: pd.DataFrame, name: str) -> tuple[np.ndarray, np.ndarray | None]:
    """
    Finite values of a column and the texts of their windows (level text of the index, or None)
    """
    if name not in table:
        return np.array([]), None
    values = table[name].to_numpy(dtype=float)
    finite = np.isfinite(values)
    texts = (
        table.index.get_level_values("text").to_numpy()[finite]
        if "text" in table.index.names
        else None
    )
    return np.asarray(values[finite], dtype=float), texts


def compare_values(
    values_a: np.ndarray,
    values_b: np.ndarray,
    n_bootstrap: int = 1000,
    rng: np.random.Generator | None = None,
    texts_a: np.ndarray | None = None,
    texts_b: np.ndarray | None = None,
) -> tuple[float, ...]:
    """
    Comparing two sets of values of a feature

    Arguments:
        values_a (ndarray): Finite values in the first corpus
        values_b (ndarray): Finite values in the second corpus
        n_bootstrap (int): Number of bootstrap samples
        rng (Generator): Random number generator
        texts_a (ndarray): Texts of the values in the first corpus for the
            bootstrap; None - every value a text of its own
        texts_b (ndarray): Texts of the values in the second corpus

    Returns:
        tuple[float, ...]: Values in the order of COMPARISON_COLUMNS, p_holm - nan

    Raises:
        ParameterError: If the texts are given and are not as many as the values
    """
    _check_texts(values_a, texts_a)
    _check_texts(values_b, texts_b)
    n_a, n_b = len(values_a), len(values_b)
    n_texts_a = n_a if texts_a is None else len(np.unique(texts_a))
    n_texts_b = n_b if texts_b is None else len(np.unique(texts_b))
    if n_a < 2 or n_b < 2:
        return (*(nan,) * 13, n_a, n_b, n_texts_a, n_texts_b)
    u, p_value = mannwhitneyu(values_a, values_b, alternative="two-sided")
    auc = float(u) / (n_a * n_b)
    ci_low, ci_high = bootstrap_median_diff(
        values_a, values_b, n_bootstrap, rng, texts_a=texts_a, texts_b=texts_b
    )
    return (
        float(values_a.mean()),
        float(values_b.mean()),
        float(np.median(values_a)),
        float(np.median(values_b)),
        float(np.median(values_a) - np.median(values_b)),
        ci_low,
        ci_high,
        calc_cohen_d(values_a, values_b),
        2 * auc - 1,
        auc,
        float(u),
        float(p_value),
        nan,
        n_a,
        n_b,
        n_texts_a,
        n_texts_b,
    )


def calc_cohen_d(values_a: Values, values_b: Values) -> float:
    """
    Computing Cohen's d - the standardized difference of the means

    Description:
        (mean_a − mean_b) / s, where s is the pooled standard deviation with
        the sample variances (ddof=1); by Cohen 0.2 is a small effect, 0.5
        a medium one, 0.8 a large one

    Arguments:
        values_a (list[float]): Values in the first corpus
        values_b (list[float]): Values in the second corpus

    Returns:
        float: Cohen's d, nan with fewer than two values on a side or a zero variance

    Example:
        >>> from anyts.corpus import calc_cohen_d
        >>> round(calc_cohen_d([2, 4, 6, 8], [1, 3, 5, 7]), 3)
        0.387
    """
    a = np.asarray(values_a, dtype=float)
    b = np.asarray(values_b, dtype=float)
    if len(a) < 2 or len(b) < 2:
        return nan
    pooled = ((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1)) / (len(a) + len(b) - 2)
    if not pooled:
        return nan
    return float((a.mean() - b.mean()) / sqrt(pooled))


def calc_cliff_delta(values_a: Values, values_b: Values) -> float:
    """
    Computing Cliff's delta - a probabilistic effect size

    Description:
        The share of the pairs (x from A, y from B) with x > y minus the share
        of the pairs with x < y (Cliff 1993); from −1 to 1, 0 - the
        distributions do not differ; |δ| < 0.147 - a negligible effect,
        < 0.33 - small, < 0.474 - medium, a large one otherwise (Romano et al. 2006)

    Arguments:
        values_a (list[float]): Values in the first corpus
        values_b (list[float]): Values in the second corpus

    Returns:
        float: Cliff's delta, nan for an empty set

    Example:
        >>> from anyts.corpus import calc_cliff_delta
        >>> calc_cliff_delta([2, 4, 6, 8], [1, 3, 5, 7])
        0.25
    """
    a = np.asarray(values_a, dtype=float)
    b = np.asarray(values_b, dtype=float)
    if not len(a) or not len(b):
        return nan
    comparison = np.sign(a[:, None] - b[None, :])
    return float(comparison.mean())


def bootstrap_median_diff(
    values_a: Values,
    values_b: Values,
    n_bootstrap: int = 1000,
    rng: np.random.Generator | None = None,
    confidence: float = 0.95,
    texts_a: Values | None = None,
    texts_b: Values | None = None,
) -> tuple[float, float]:
    """
    Computing the percentile bootstrap interval of the difference of the medians

    Description:
        Both sets are resampled with replacement n_bootstrap times, and the
        bounds are the percentiles (1 − confidence) / 2 and
        1 − (1 − confidence) / 2 of median_a − median_b. With the texts of the
        values given, whole texts are resampled (a cluster bootstrap), which
        needs at least two texts on each side

    Arguments:
        values_a (list[float]): Values in the first corpus
        values_b (list[float]): Values in the second corpus
        n_bootstrap (int): Number of samples
        rng (Generator): Random number generator; None - a new one without a seed
        confidence (float): Confidence level
        texts_a (list): Texts of the values in the first corpus; None - every
            value is resampled on its own
        texts_b (list): Texts of the values in the second corpus

    Returns:
        tuple[float, float]: Lower and upper bounds, nan for an empty set or,
            with the texts given, fewer than two texts on a side

    Raises:
        ParameterError: If the number of samples is below one, the confidence
            level is outside the interval (0, 1) or the texts are given and are
            not as many as the values

    Example:
        >>> from anyts.corpus import bootstrap_median_diff
        >>> bootstrap_median_diff([3.0, 3.0, 3.0], [1.0, 1.0, 1.0], n_bootstrap=10)
        (2.0, 2.0)
    """
    if n_bootstrap < 1:
        raise ParameterError("The number of bootstrap samples must be greater than 0")
    if not 0 < confidence < 1:
        raise ParameterError("The confidence level must lie in the interval (0, 1)")
    _check_texts(values_a, texts_a)
    _check_texts(values_b, texts_b)
    a = np.asarray(values_a, dtype=float)
    b = np.asarray(values_b, dtype=float)
    if not len(a) or not len(b):
        return nan, nan
    if any(texts is not None and len(np.unique(texts)) < 2 for texts in (texts_a, texts_b)):
        return nan, nan
    generator = rng if rng is not None else np.random.default_rng()
    differences = _resampled_medians(a, texts_a, n_bootstrap, generator) - _resampled_medians(
        b, texts_b, n_bootstrap, generator
    )
    tail = (1 - confidence) / 2 * 100
    low, high = np.percentile(differences, [tail, 100 - tail])
    return float(low), float(high)


def _check_texts(values: Values, texts: Values | None) -> None:
    """Checking that the texts of the values are as many as the values"""
    if texts is not None and len(texts) != len(values):
        raise ParameterError(
            f"The texts must match the values one to one: {len(texts)} texts, {len(values)} values"
        )


def _resampled_medians(
    values: np.ndarray, texts: Values | None, n_bootstrap: int, generator: np.random.Generator
) -> np.ndarray:
    """
    Medians of bootstrap samples of values, drawn one by one or by whole texts

    Description:
        A draw of texts is the number of times every text is taken; the median
        is read from the sorted values weighted by those numbers
    """
    if texts is None:
        return np.asarray(
            np.median(generator.choice(values, size=(n_bootstrap, len(values))), axis=1)
        )
    labels, inverse = np.unique(np.asarray(texts), return_inverse=True)
    draws = generator.multinomial(len(labels), np.full(len(labels), 1 / len(labels)), n_bootstrap)
    order = np.argsort(values, kind="stable")
    cumulative = draws[:, inverse[order]].cumsum(axis=1)
    total = cumulative[:, -1:]
    lower = (cumulative > (total - 1) // 2).argmax(axis=1)
    upper = (cumulative > total // 2).argmax(axis=1)
    ordered = values[order]
    return np.asarray((ordered[lower] + ordered[upper]) / 2)


def holm_correction(p_values: Sequence[float]) -> np.ndarray:
    """
    Holm's correction for multiple comparisons

    Description:
        The p-values are sorted in ascending order, the i-th is multiplied by
        (m − i + 1), where m is the number of defined values, then the
        running maximum is taken and capped at one; nan stays nan

    Arguments:
        p_values (list[float]): p-values

    Returns:
        ndarray: Corrected p-values in the original order

    Raises:
        ParameterError: If a p-value lies outside [0, 1]

    Example:
        >>> from anyts.corpus import holm_correction
        >>> holm_correction([0.01, 0.04, 0.03]).round(3).tolist()
        [0.03, 0.06, 0.06]
    """
    values = np.asarray(p_values, dtype=float)
    defined = np.flatnonzero(~np.isnan(values))
    if ((values[defined] < 0) | (values[defined] > 1)).any():
        raise ParameterError("The p-values must lie within [0, 1]")
    adjusted = np.full(len(values), nan)
    if not len(defined):
        return adjusted
    order = defined[np.argsort(values[defined], kind="stable")]
    m = len(order)
    scaled = values[order] * (m - np.arange(m))
    adjusted[order] = np.minimum(np.maximum.accumulate(scaled), 1.0)
    return adjusted
