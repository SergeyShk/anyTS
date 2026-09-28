from math import inf, isnan, nan, sqrt

import numpy as np
import pandas as pd
import pytest
from scipy.stats import mannwhitneyu

from anyts.corpus import (
    bootstrap_median_diff,
    calc_cliff_delta,
    calc_cohen_d,
    check_comparison_params,
    compare_features,
    holm_correction,
)
from anyts.corpus.compare import COMPARISON_COLUMNS, _resampled_medians, compare_values
from anyts.exceptions import ParameterError, SourceTypeError


def test_compare_values():
    a = np.array([1.0, 2.0, 3.0, 4.0])
    b = np.array([3.0, 4.0, 5.0, 6.0])
    values = compare_values(a, b, n_bootstrap=100, rng=np.random.default_rng(0))
    assert len(values) == len(COMPARISON_COLUMNS)
    assert values[:5] == (2.5, 4.5, 2.5, 4.5, -2.0)
    assert values[8] == pytest.approx(calc_cliff_delta(a, b))
    assert values[9] == pytest.approx(mannwhitneyu(a, b)[0] / 16)
    assert values[11] == pytest.approx(mannwhitneyu(a, b, alternative="two-sided")[1])
    assert isnan(values[12])
    assert values[13:] == (4, 4, 4, 4)
    assert all(isnan(value) for value in compare_values(np.array([1.0]), b)[:13])
    assert compare_values(np.array([1.0]), b)[13:] == (1, 4, 1, 4)
    texts = np.array([0, 0, 1, 1])
    assert compare_values(a, b, 100, np.random.default_rng(0), texts, texts)[13:] == (4, 4, 2, 2)


def test_compare_values_of_lists_with_undefined_values():
    rng = np.random.default_rng(0)
    expected = compare_values(np.array([1.0, 2.0, 3.0]), np.array([4.0, 5.0, 6.0]), 50, rng)
    rng = np.random.default_rng(0)
    values = compare_values([1.0, nan, 2, 3, inf], [4.0, 5, -inf, 6], 50, rng)
    assert values == pytest.approx(expected, nan_ok=True)
    # The texts of the dropped values go with them: the first text keeps no value
    texts = compare_values([nan, nan, 2.0, 3.0], [4.0, 5.0], 10, None, ["x", "x", "y", "z"])
    assert texts[13:] == (2, 2, 2, 2)
    with pytest.raises(ParameterError, match=r"^The texts must match the values one to one"):
        compare_values([1.0, nan], [2.0, 3.0], texts_a=["x"])


def test_effect_sizes():
    a = [2.0, 4.0, 6.0, 8.0]
    b = [1.0, 3.0, 5.0, 7.0]
    assert calc_cohen_d(a, b) == pytest.approx(1 / sqrt(20 / 3))
    assert isnan(calc_cohen_d([1.0, 1.0], [1.0, 1.0]))
    assert isnan(calc_cohen_d([1.0], [2.0, 3.0]))
    assert calc_cliff_delta(a, b) == pytest.approx((10 - 6) / 16)
    assert calc_cliff_delta([1, 1], [1, 1]) == 0.0
    assert calc_cliff_delta([5, 6], [1, 2]) == 1.0
    assert isnan(calc_cliff_delta([], [1.0]))
    assert isnan(calc_cliff_delta([1.0, nan], [0.0]))
    assert isnan(calc_cliff_delta([1.0], [0.0, nan]))
    assert calc_cliff_delta([inf], [inf, 1.0]) == 0.5
    low, high = bootstrap_median_diff(a, b, n_bootstrap=500, rng=np.random.default_rng(0))
    assert low <= 1.0 <= high
    assert bootstrap_median_diff([3.0, 3.0, 3.0], [1.0, 1.0, 1.0], n_bootstrap=10) == (2.0, 2.0)
    assert all(isnan(value) for value in bootstrap_median_diff([], [1.0]))
    with pytest.raises(ParameterError):
        bootstrap_median_diff(a, b, n_bootstrap=0)
    with pytest.raises(ParameterError, match=r"must be an integer, not float$"):
        bootstrap_median_diff(a, b, n_bootstrap=10.0)
    with pytest.raises(ParameterError):
        bootstrap_median_diff(a, b, confidence=1.0)


def test_cluster_bootstrap():
    # Windows alike within a text: resampling whole texts widens the interval
    rng = np.random.default_rng(1)
    texts = np.repeat(np.arange(4), 20)
    a = np.repeat([10.0, 12.0, 14.0, 16.0], 20) + rng.normal(scale=0.1, size=80)
    b = np.repeat([9.0, 11.0, 13.0, 15.0], 20) + rng.normal(scale=0.1, size=80)
    windows = bootstrap_median_diff(a, b, n_bootstrap=500, rng=np.random.default_rng(0))
    clusters = bootstrap_median_diff(
        a, b, n_bootstrap=500, rng=np.random.default_rng(0), texts_a=texts, texts_b=texts
    )
    assert clusters[1] - clusters[0] > 1.5 * (windows[1] - windows[0])
    assert clusters[0] <= 1.0 <= clusters[1]
    assert all(
        isnan(value) for value in bootstrap_median_diff(a, b, texts_a=np.zeros(80), texts_b=texts)
    )
    # The medians of the draws equal np.median of the drawn texts put together
    values = rng.normal(size=40)
    groups = rng.integers(0, 6, size=40)
    medians = _resampled_medians(values, groups, 200, np.random.default_rng(0))
    labels = np.unique(groups)
    draws = np.random.default_rng(0).multinomial(
        len(labels), np.full(len(labels), 1 / len(labels)), 200
    )
    expected = [
        np.median(
            np.concatenate(
                [
                    np.repeat(values[groups == label], n)
                    for label, n in zip(labels, row, strict=True)
                ]
            )
        )
        for row in draws
    ]
    assert medians == pytest.approx(expected)


def test_holm_correction():
    adjusted = holm_correction([0.01, 0.04, 0.03, float("nan")])
    assert adjusted[:3] == pytest.approx([0.03, 0.06, 0.06])
    assert isnan(adjusted[3])
    assert list(holm_correction([0.5, 0.9])) == [1.0, 1.0]
    assert list(holm_correction([])) == []
    assert all(isnan(value) for value in holm_correction([float("nan")]))


@pytest.mark.parametrize(
    "p_values", ["0.5", 0.5, [[0.1, 0.2]], ["a"], ["0.1"], [True], [0.1, None], {0.1, 0.2}, None]
)
def test_holm_correction_input(p_values):
    with pytest.raises(SourceTypeError):
        holm_correction(p_values)


def test_holm_correction_containers():
    expected = holm_correction([0.01, 0.04]).tolist()
    assert holm_correction({"a": 0.01, "b": 0.04}.values()).tolist() == expected
    assert holm_correction(pd.Series([0.01, 0.04])).tolist() == expected
    assert holm_correction((0.01, 0.04)).tolist() == expected


@pytest.mark.parametrize("values", ["123", {1.0, 2.0, 3.0}, ["a", "b"], [1.0, None], [[1.0, 2.0]]])
def test_values_checked(values):
    for call in (
        lambda: calc_cohen_d(values, [1.0, 2.0]),
        lambda: calc_cliff_delta([1.0, 2.0], values),
        lambda: bootstrap_median_diff(values, [1.0, 2.0]),
        lambda: compare_values([1.0, 2.0], values),
    ):
        with pytest.raises(SourceTypeError):
            call()


def test_generator_and_confidence_checked():
    with pytest.raises(ParameterError, match=r"must be a numpy Generator, not int$"):
        compare_values([1.0, 2.0], [1.0, 3.0], rng=0)
    with pytest.raises(ParameterError, match=r"must be a numpy Generator, not int$"):
        bootstrap_median_diff([1.0, 2.0], [1.0, 3.0], rng=0)
    with pytest.raises(ParameterError, match=r"^The confidence level must be a number"):
        bootstrap_median_diff([1.0, 2.0], [1.0, 3.0], confidence=None)


def test_holm_correction_range():
    with pytest.raises(ParameterError, match=r"^The p-values must lie within \[0, 1\]$"):
        holm_correction([0.5, 1.5])
    with pytest.raises(ParameterError):
        holm_correction([-0.1])
    assert list(holm_correction([0.0, 1.0])) == [0.0, 1.0]


SHORT = pd.DataFrame({"length": [14.0, 15.0, 13.0], "constant": [1.0, 1.0, 1.0]})
LONG = pd.DataFrame({"length": [33.0, 35.0, 31.0], "constant": [1.0, 1.0, 1.0]})


def test_compare_features():
    result = compare_features(SHORT, LONG, labels=("short", "long"), n_bootstrap=200)
    columns = [
        column.replace("_a", "_short").replace("_b", "_long") for column in COMPARISON_COLUMNS
    ]
    assert list(result.columns) == columns
    assert list(result.index) == ["length", "constant"]
    row = result.loc["length"]
    assert (row["mean_short"], row["mean_long"]) == (14.0, 33.0)
    assert (row["median_short"], row["median_long"], row["median_diff"]) == (14.0, 33.0, -19.0)
    assert row["cliff_delta"] == -1.0
    assert row["auc"] == 0.0
    assert row["ci_low"] <= row["median_diff"] <= row["ci_high"]
    assert row["p_holm"] >= row["p_value"]
    counts = (row["n_short"], row["n_long"], row["n_texts_short"], row["n_texts_long"])
    assert counts == (3, 3, 3, 3)
    assert result["n_short"].dtype.kind == "i"
    constant = result.loc["constant"]
    assert isnan(constant["cohen_d"])
    assert constant["cliff_delta"] == 0.0


def test_compare_features_seed_and_errors():
    first = compare_features(SHORT, LONG, n_bootstrap=50, seed=1)
    assert first.equals(compare_features(SHORT, LONG, n_bootstrap=50, seed=1))
    with pytest.raises(ParameterError, match=r"^The number of bootstrap samples"):
        compare_features(SHORT, LONG, n_bootstrap=0)
    with pytest.raises(ParameterError, match=r"must be an integer, not float$"):
        compare_features(SHORT, LONG, n_bootstrap=50.0)
    with pytest.raises(ParameterError, match=r"^The seed must not be negative$"):
        compare_features(SHORT, LONG, seed=-1)
    with pytest.raises(ParameterError, match=r"^The names of the corpora"):
        compare_features(SHORT, LONG, labels=("A", "A"))
    generated = compare_features(SHORT, LONG, n_bootstrap=50, seed=np.random.default_rng(1))
    assert generated.equals(first)
    named = compare_features(SHORT, LONG, labels=np.array(["x", "y"]), n_bootstrap=5)
    assert list(named.columns[:4]) == ["mean_x", "mean_y", "median_x", "median_y"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"labels": ("A",)},
        {"labels": ("A", "B", "C")},
        {"labels": ("A", "A")},
        {"labels": ("A", 1)},
        {"labels": "AB"},
        {"labels": None},
        {"labels": ("diff", "B")},
        {"labels": ("A", "texts_A")},
        {"labels": iter(("A", "B"))},
        {"labels": {"A": 1, "B": 2}},
        {"n_bootstrap": 0},
        {"n_bootstrap": 1.0},
        {"seed": 1.5},
        {"seed": -1},
        {"seed": True},
        {"seed": "1"},
    ],
)
def test_check_comparison_params(kwargs):
    with pytest.raises(ParameterError):
        check_comparison_params(**kwargs)


def test_check_comparison_params_valid():
    assert check_comparison_params(["short", "long"], 1, None) is None
    assert check_comparison_params(seed=np.int64(3)) is None


def test_compare_features_undefined_values():
    extra = SHORT.assign(extra=1.0, sparse=[1.0, float("nan"), float("inf")])
    result = compare_features(extra, LONG.assign(sparse=[2.0, 3.0, 4.0]), n_bootstrap=10)
    # A column missing from one of the tables gives no statistics and goes last
    assert isnan(result.loc["extra", "cliff_delta"])
    assert (result.loc["extra", "n_A"], result.loc["extra", "n_B"]) == (3, 0)
    # Undefined and infinite values are dropped, and one value is too few
    assert (result.loc["sparse", "n_A"], result.loc["sparse", "n_B"]) == (1, 3)
    assert isnan(result.loc["sparse", "cliff_delta"])
    assert list(result.index[:2]) == ["length", "constant"]


def test_compare_features_texts():
    index = pd.MultiIndex.from_product([range(3), range(4)], names=["text", "window"])
    rng = np.random.default_rng(2)
    table_a = pd.DataFrame({"length": rng.normal(10, 1, 12)}, index=index)
    table_b = pd.DataFrame({"length": rng.normal(12, 1, 12)}, index=index)
    result = compare_features(table_a, table_b, n_bootstrap=50)
    assert result.loc["length", "n_texts_A"] == 3
    assert result.loc["length", "n_A"] == 12
    flat = compare_features(table_a.reset_index(drop=True), table_b, n_bootstrap=50)
    assert flat.loc["length", "n_texts_A"] == flat.loc["length", "n_A"] == 12


@pytest.mark.parametrize("texts", [np.array([0, 0, 1, 1, 2, 3]), np.array([0, 1])])
def test_texts_match_the_values(texts):
    values = np.array([1.0, 2.0, 3.0, 4.0])
    message = rf"^The texts must match the values one to one: {len(texts)} texts, 4 values$"
    with pytest.raises(ParameterError, match=message):
        bootstrap_median_diff(values, values, texts_a=texts)
    with pytest.raises(ParameterError, match=message):
        compare_values(values, values, texts_b=texts)
    with pytest.raises(ParameterError, match=message):
        compare_values(values[:1], values, texts_b=texts)
