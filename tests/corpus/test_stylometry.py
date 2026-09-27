from math import isclose, log2, sqrt

import numpy as np
import pandas as pd
import pytest
import spacy
from scipy.spatial.distance import jensenshannon

from anyts import CharNgramsExtractor, WordsExtractor
from anyts.constants import DELTA_VARIANTS
from anyts.corpus import (
    ZetaScore,
    delta,
    delta_profiles,
    frequency_table,
    kilgarriff_chi2,
    mendenhall_curve,
    mendenhall_distance,
    z_scores,
    zeta,
)
from anyts.exceptions import ParameterError, SourceError, SourceTypeError

# Three short texts, every word replaced by a token of the same length that keeps
# the alphabetical order of the words
texts = {
    "A": (
        "Ab acab acaaaa ac ad bcaaaaa c adcaab adc bacaaaa. "
        "Adc bacaaaa bb acaaab c ab acab aaacbd ac ad bcaaaaa."
    ),
    "B": "Ab babaa acaaaa ac ab bcaaa c aaacbb. Aaacbaa ab babaa aaaca c baaa bcb aaacbb ac ab bcaaa.",
    "C": "Adcaaa ab acab bcbaaaa a ad bcaaaaa c adcaac adc bacaaaa, baba ab babaa aaacbab.",
}
extractor = WordsExtractor(lowercase=True)
corpus = {name: extractor.extract(text) for name, text in texts.items()}


def test_frequency_table():
    table = frequency_table(corpus, n_mfw=5)
    assert list(table.index) == ["A", "B", "C"]
    assert list(table.columns) == ["ab", "c", "ac", "babaa", "acab"]
    assert table.loc["B", "ab"] == pytest.approx(4 / 19)
    assert table.loc["A", "babaa"] == 0
    assert frequency_table(corpus, n_mfw=None).shape == (3, 26)
    assert list(frequency_table(corpus, n_mfw=None, culling=1.0).columns) == ["ab", "c"]
    assert list(frequency_table(corpus, n_mfw=None, culling=0.5).columns)[:5] == [
        "ab",
        "c",
        "ac",
        "babaa",
        "acab",
    ]
    assert frequency_table({"A": ["a"]}, n_mfw=None).loc["A", "a"] == 1


def test_z_scores():
    table = frequency_table(corpus, n_mfw=5)
    scores = z_scores(table)
    column = table["ab"]
    assert scores["ab"].tolist() == pytest.approx(
        ((column - column.mean()) / column.std(ddof=1)).tolist()
    )
    assert scores.std(ddof=1).tolist() == pytest.approx([1.0] * 5)
    constant = z_scores(frequency_table({"A": ["a", "b"], "B": ["a", "c"]}, n_mfw=None))
    assert constant["a"].tolist() == [0.0, 0.0]
    assert constant["b"].tolist() == pytest.approx([sqrt(2) / 2, -sqrt(2) / 2])


def test_constant_column_with_float_noise():
    # 0.1 in three texts: the rounding of the mean leaves a deviation of noise and not zero
    reference = {
        "A": ["ab", "acab", "aaac", "bab", "c", "aaacbc", "adcab", "ac", "aaab", "acb"],
        "B": ["ab", "babaa", "adaaa", "acaaac", "c", "aaacb", "babb", "bac", "aaaa", "ca"],
        "C": ["ab", "adcb", "adb", "adbaaa", "b", "acbaa", "bbaa", "ac", "bc", "aaacba"],
    }
    table = frequency_table(reference, n_mfw=3)
    assert list(table.columns) == ["ab", "ac", "c"]
    assert z_scores(table)["ab"].tolist() == [0.0, 0.0, 0.0]
    varying = table[["ac", "c"]]
    expected = (varying - varying.mean()) / varying.std(ddof=1)
    a, b = expected.loc["A"], expected.loc["B"]
    assert delta(reference, n_mfw=3, variant="cosine").loc["A", "B"] == pytest.approx(
        1 - (a * b).sum() / sqrt((a**2).sum() * (b**2).sum())
    )
    # The tested text has el at 0.2: the constant column is zeroed for it as well
    distances = delta_profiles(reference, {"?": ["ab", *reference["A"][1:-1], "ab"]}, n_mfw=3)
    tested = (pd.Series({"ac": 0.1, "c": 0.1}) - varying.mean()) / varying.std(ddof=1)
    assert distances.loc["?"].tolist() == pytest.approx(
        [(tested - expected.loc[name]).abs().sum() / 3 for name in reference]
    )


def test_delta():
    scores = z_scores(frequency_table(corpus, n_mfw=5))
    difference = (scores.loc["A"] - scores.loc["B"]).abs()
    distances = delta(corpus, n_mfw=5)
    assert list(distances.index) == list(distances.columns) == ["A", "B", "C"]
    assert np.allclose(distances, distances.T)
    assert np.diag(distances).tolist() == [0.0, 0.0, 0.0]
    assert distances.loc["A", "B"] == pytest.approx(difference.sum() / 5)
    assert delta(corpus, n_mfw=5, variant="quadratic").loc["A", "B"] == pytest.approx(
        sqrt((difference**2).sum()) / 5
    )
    weights = [(5 - rank + 2) / 5 for rank in range(1, 6)]
    assert delta(corpus, n_mfw=5, variant="eder").loc["A", "B"] == pytest.approx(
        (difference * weights).sum()
    )
    a, b = scores.loc["A"], scores.loc["B"]
    assert delta(corpus, n_mfw=5, variant="cosine").loc["A", "B"] == pytest.approx(
        1 - (a * b).sum() / sqrt((a**2).sum() * (b**2).sum())
    )
    assert distances.loc["A", "C"] < distances.loc["A", "B"]
    assert set(DELTA_VARIANTS) == {"burrows", "quadratic", "eder", "cosine"}


def test_delta_identical_texts():
    same = {"A": corpus["A"], "B": corpus["A"], "C": corpus["B"]}
    distances = delta(same, n_mfw=5, variant="cosine")
    assert abs(distances.loc["A", "B"]) < 1e-12
    assert distances.loc["A", "C"] > 0
    assert abs(delta(same, n_mfw=5).loc["A", "B"]) < 1e-12


def test_delta_char_ngrams():
    sentences = {
        "A": "The cat sat at the window and watched the birds in the garden.",
        "B": "Heavy rain flooded every road of the valley before the morning.",
        "C": "The cat sat at the window and slept until the birds came back.",
    }
    ngrams = CharNgramsExtractor(n=2, lowercase=True)
    distances = delta({name: ngrams.extract(text) for name, text in sentences.items()}, n_mfw=20)
    assert distances.shape == (3, 3)
    assert distances.loc["A", "C"] < distances.loc["A", "B"]


def test_delta_profiles():
    samples = {
        "A2": corpus["A"],
        "D": extractor.extract("Ab babaa aaacbb ac ab bcaaa c ab acab adcaab ad bcaaaaa."),
    }
    distances = delta_profiles(corpus, samples, n_mfw=5)
    assert list(distances.index) == ["A2", "D"]
    assert list(distances.columns) == ["A", "B", "C"]
    # A reference text under test: the same z-scores, the distances of delta
    for variant in DELTA_VARIANTS:
        expected = delta(corpus, n_mfw=5, variant=variant).loc["A"]
        row = delta_profiles(corpus, samples, n_mfw=5, variant=variant).loc["A2"]
        assert np.allclose(row.to_numpy(), expected.to_numpy())
    # The units and the scaling come from the references: the neighbours do not matter
    alone = delta_profiles(corpus, {"D": samples["D"]}, n_mfw=5)
    assert np.allclose(alone.loc["D"].to_numpy(), distances.loc["D"].to_numpy())
    # Words of a tested text outside the list of the references only change its length
    extra = delta_profiles(corpus, {"D": (*samples["D"], "abaaaaaa", "abaaaaaa")}, n_mfw=5)
    assert not np.allclose(extra.loc["D"].to_numpy(), distances.loc["D"].to_numpy())
    with pytest.raises(ParameterError):
        delta_profiles(corpus, samples, variant="manhattan")
    with pytest.raises(SourceError):
        delta_profiles({"A": corpus["A"], "B": corpus["B"]}, samples)
    with pytest.raises(SourceError):
        delta_profiles(corpus, {})
    with pytest.raises(SourceError):
        delta_profiles(corpus, {"D": []})
    with pytest.raises(SourceTypeError):
        delta_profiles(corpus, {"D": "ab acab aaacbb"})
    # Statistics of a separate set: two references are allowed, scaled by statistics
    two = {"A": corpus["A"], "B": corpus["B"]}
    scaled = delta_profiles(two, samples, n_mfw=5, statistics=corpus)
    assert list(scaled.columns) == ["A", "B"]
    assert np.allclose(scaled.loc["A2"].to_numpy(), distances.loc["A2", ["A", "B"]].to_numpy())
    with pytest.raises(SourceError):
        delta_profiles(two, samples, n_mfw=5)


def test_delta_errors():
    with pytest.raises(ParameterError):
        delta(corpus, variant="manhattan")
    with pytest.raises(SourceError):
        delta({"A": corpus["A"], "B": corpus["B"]})
    with pytest.raises(ParameterError):
        delta(corpus, n_mfw=0)
    with pytest.raises(ParameterError):
        frequency_table(corpus, n_mfw=-1)
    with pytest.raises(ParameterError, match=r"must be an integer, not float$"):
        delta(corpus, n_mfw=5.0)
    with pytest.raises(SourceError):
        frequency_table({})
    with pytest.raises(SourceError):
        frequency_table({"A": corpus["A"], "B": []})
    with pytest.raises(ParameterError):
        frequency_table(corpus, culling=2)
    with pytest.raises(SourceError):
        delta({"A": ["a"], "B": ["b"], "C": ["c"]}, culling=1.0)
    with pytest.raises(SourceTypeError):
        frequency_table({"A": texts["A"]})
    with pytest.raises(SourceTypeError):
        frequency_table({"A": spacy.blank("xx")(texts["A"])})


def test_zeta():
    # 21 and 19 words give four segments each
    scores = zeta(corpus["A"], corpus["B"], segment_size=5)
    assert scores[0] == ZetaScore("acab", 0.5, 0.0, 0.5, log2(0.5 / (0.5 / 4)))
    assert [score.word for score in scores[:4]] == ["acab", "ad", "bacaaaa", "bcaaaaa"]
    el = next(score for score in scores if score.word == "ab")
    assert el == ZetaScore("ab", 0.5, 0.75, -0.25, pytest.approx(log2(0.5 / 0.75)))
    assert scores[-1] == ZetaScore("bcaaa", 0.0, 0.5, -0.5, log2((0.5 / 4) / 0.5))
    assert zeta(corpus["A"], corpus["B"], segment_size=5, top_n=2) == scores[:2]
    assert zeta(corpus["A"], corpus["B"], segment_size=100)[0].zeta == 1.0
    # Four segments of A with gato in two, three of C with it in one
    several = zeta([corpus["A"], corpus["C"]], [corpus["B"]], segment_size=5)
    assert next(score for score in several if score.word == "acab").dp_target == 3 / 7
    assert zeta([corpus["A"], []], corpus["B"], segment_size=5) == scores
    assert zeta(["a"] * 2500, ["b"] * 100, segment_size=1000)[0].dp_target == 1.0
    scores = zeta(["a"] * 2500 + ["b"], ["b"] * 100, segment_size=1000)
    assert next(score for score in scores if score.word == "b").dp_target == pytest.approx(1 / 3)


def test_zeta_errors():
    with pytest.raises(ParameterError):
        zeta(corpus["A"], corpus["B"], segment_size=0)
    with pytest.raises(SourceError):
        zeta([], corpus["B"])
    with pytest.raises(SourceError):
        zeta(corpus["A"], [[]])
    with pytest.raises(ParameterError):
        zeta(corpus["A"], corpus["B"], top_n=0)
    with pytest.raises(ParameterError, match=r"^The size of a segment must be an integer"):
        zeta(corpus["A"], corpus["B"], segment_size=5.0)
    with pytest.raises(ParameterError, match=r"^The number of words must be an integer"):
        zeta(corpus["A"], corpus["B"], top_n=2.0)
    with pytest.raises(SourceTypeError):
        zeta(texts["A"], corpus["B"])
    # A text among lists of words, a Doc among the texts
    with pytest.raises(SourceTypeError):
        zeta(["acab", ["babaa"]], corpus["B"])
    with pytest.raises(SourceTypeError):
        zeta([spacy.blank("xx")(texts["A"])], corpus["B"])


def test_kilgarriff_chi2():
    words_a = ["a"] * 6 + ["b"] * 3 + ["c"]
    words_b = ["a"] * 2 + ["b"] * 5 + ["d"] * 3
    expected = 0.0
    for count_a, count_b in ((6, 2), (3, 5)):
        joint = count_a + count_b
        expected += (count_a - joint / 2) ** 2 / (joint / 2) * 2
    assert kilgarriff_chi2(words_a, words_b, n_mfw=2) == pytest.approx(expected)
    assert kilgarriff_chi2(words_a, words_a) == 0
    assert kilgarriff_chi2(words_a, words_b) > kilgarriff_chi2(words_a, words_b, n_mfw=2)
    with pytest.raises(SourceError):
        kilgarriff_chi2([], words_b)
    with pytest.raises(ParameterError):
        kilgarriff_chi2(words_a, words_b, n_mfw=0)
    with pytest.raises(ParameterError, match=r"must be an integer, not float$"):
        kilgarriff_chi2(words_a, words_b, n_mfw=2.0)
    with pytest.raises(SourceTypeError):
        kilgarriff_chi2(texts["A"], words_b)


def test_mendenhall():
    curve = mendenhall_curve(corpus["A"])
    assert list(curve) == [1, 2, 3, 4, 6, 7]
    assert curve[2] == pytest.approx(7 / 21)
    assert isclose(sum(curve.values()), 1.0)
    curve_b = mendenhall_curve(corpus["B"])
    lengths = sorted(set(curve) | set(curve_b))
    assert mendenhall_distance(corpus["A"], corpus["B"]) == pytest.approx(
        jensenshannon(
            [curve.get(length, 0) for length in lengths],
            [curve_b.get(length, 0) for length in lengths],
            base=2,
        )
    )
    assert mendenhall_distance(corpus["A"], corpus["A"]) == 0
    assert mendenhall_distance(["a"], ["bb"]) == pytest.approx(1.0)
    with pytest.raises(SourceError):
        mendenhall_curve([])
    with pytest.raises(SourceTypeError):
        mendenhall_curve(texts["A"])


@pytest.mark.parametrize("container", [np.array, pd.Series])
def test_arrays_of_words(container):
    words = ["a", "b", "a", "c", "a", "b"]
    assert zeta(container(words), ["d"]) == zeta(words, ["d"])
    assert mendenhall_curve(container(words)) == mendenhall_curve(words)
    assert mendenhall_distance(container(words), container(["dd", "e"])) == pytest.approx(
        mendenhall_distance(words, ["dd", "e"])
    )


def test_frequency_table_ties_do_not_depend_on_the_order_of_the_texts():
    def tokens(n, prefix):
        return [f"{prefix}{i}" for i in range(n)]

    corpus = {
        "A": ["a"] * 3 + ["b"] + tokens(6, "x"),
        "B": ["a"] * 2 + ["b"] * 2 + tokens(6, "y"),
        "C": ["a"] + ["b"] * 3 + tokens(6, "z"),
    }
    reversed_corpus = dict(reversed(corpus.items()))
    assert frequency_table(corpus, n_mfw=1).columns.tolist() == ["a"]
    assert frequency_table(reversed_corpus, n_mfw=1).columns.tolist() == ["a"]
    for variant in DELTA_VARIANTS:
        distances = delta(corpus, n_mfw=2, variant=variant)
        backwards = delta(reversed_corpus, n_mfw=2, variant=variant)
        assert distances.loc["A", "C"] == backwards.loc["A", "C"]
