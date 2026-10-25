from collections import Counter
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
    rolling_delta,
    z_scores,
    zeta,
    zeta_segments,
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
    with pytest.raises(ParameterError):
        delta(corpus, variant=["burrows"])
    with pytest.raises(ParameterError):
        delta_profiles(corpus, corpus, variant=["burrows"])
    with pytest.raises(SourceTypeError):
        frequency_table({"A": set(corpus["A"])})
    with pytest.raises(ParameterError, match=r"must be a number, not str$"):
        frequency_table(corpus, culling="0.5")
    texts_list = list(corpus.values())
    for call in (
        lambda: frequency_table(texts_list),
        lambda: frequency_table("abc"),
        lambda: delta(texts_list[:2]),
        lambda: delta_profiles(texts_list, corpus),
        lambda: delta_profiles(corpus, texts_list),
        lambda: delta_profiles(corpus, corpus, statistics=texts_list),
    ):
        with pytest.raises(SourceTypeError, match="must be a mapping of the names of the texts"):
            call()
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


def naive_rolling_delta(reference, text, window, step, n_mfw, variant, culling=0.0):
    """Distances of the windows of a text to the centroids of the windows of the references"""

    def windows(units):
        return [units[start : start + window] for start in range(0, len(units) - window + 1, step)]

    parts = {name: windows(units) for name, units in reference.items()}
    pooled = {
        f"{name}{i}": units for name, chunks in parts.items() for i, units in enumerate(chunks)
    }
    table = frequency_table(pooled, n_mfw, culling)
    mean, deviation = table.mean(), table.std()

    def scaled(units):
        counts = Counter(units)
        frequencies = pd.Series({unit: counts[unit] / len(units) for unit in table.columns})
        return np.where(deviation > 0, (frequencies - mean) / deviation.where(deviation > 0, 1), 0)

    n = len(table.columns)
    weights = np.array([(n - rank + 2) / n for rank in range(1, n + 1)])
    rows = []
    for units in windows(text):
        row = []
        for chunks in parts.values():
            a, b = scaled(units), np.mean([scaled(chunk) for chunk in chunks], axis=0)
            row.append(
                {
                    "burrows": np.abs(a - b).sum() / n,
                    "quadratic": np.sqrt(((a - b) ** 2).sum()) / n,
                    "eder": (weights * np.abs(a - b)).sum(),
                    "cosine": 1 - a @ b / (np.linalg.norm(a) * np.linalg.norm(b)),
                }[variant]
            )
        rows.append(row)
    return np.array(rows)


def test_rolling_delta():
    text = corpus["A"] + corpus["B"]
    for variant in DELTA_VARIANTS:
        for window, step, culling in ((8, 3, 0.0), (6, 6, 0.0), (8, 1, 0.5)):
            distances = rolling_delta(corpus, text, window, step, 6, variant, culling)
            expected = naive_rolling_delta(corpus, text, window, step, 6, variant, culling)
            assert np.allclose(distances.to_numpy(), expected)
    distances = rolling_delta(corpus, text, window=8, step=3, n_mfw=6)
    assert list(distances.columns) == ["A", "B", "C"]
    # The windows by their middles, the rest shorter than a window dropped
    assert list(distances.index) == list(range(4, len(text) - 8 + 5, 3))
    # Over all the units, the windows of A are nearest to A and those of B to B; the
    # middle of the first window mostly of B is 24, the text of A ends at 21
    nearest = rolling_delta(corpus, text, window=12, step=3, n_mfw=None).idxmin(axis=1)
    assert nearest.to_dict() == {middle: "A" if middle < 24 else "B" for middle in range(6, 34, 3)}
    # Texts of one window each: the distances of delta_profiles
    length = min(len(units) for units in corpus.values())
    cut = {name: units[:length] for name, units in corpus.items()}
    sample = corpus["B"][-length:]
    for variant in DELTA_VARIANTS:
        rolled = rolling_delta(cut, sample, window=length, step=length, n_mfw=5, variant=variant)
        profiles = delta_profiles(cut, {"x": sample}, n_mfw=5, variant=variant)
        assert list(rolled.index) == [length // 2]
        assert np.allclose(rolled.to_numpy(), profiles.to_numpy())


def test_rolling_delta_with_statistics():
    text = corpus["A"] + corpus["B"]
    two = {"A": corpus["A"], "B": corpus["B"]}
    # Scaled by their own windows, the cosine distances to two references add up to 2
    alone = rolling_delta(two, text, window=8, step=2, n_mfw=None, variant="cosine")
    assert np.allclose(alone["A"] + alone["B"], 2)
    # Statistics of other texts free them, and allow a single reference
    other = {name: units[::-1] for name, units in corpus.items()}
    scaled = rolling_delta(two, text, 8, 2, None, "cosine", statistics={**corpus, **other})
    assert not np.allclose(scaled["A"] + scaled["B"], 2)
    single = rolling_delta({"A": corpus["A"]}, text, 8, 2, None, "cosine", statistics=corpus)
    assert list(single.columns) == ["A"] and np.isfinite(single.to_numpy()).all()
    # The statistics of the references themselves give the same distances
    for variant in DELTA_VARIANTS:
        assert np.allclose(
            rolling_delta(two, text, 8, 2, 6, variant, statistics=two),
            rolling_delta(two, text, 8, 2, 6, variant),
        )
    with pytest.raises(
        SourceError, match=r"^One of the statistics texts is shorter than a window$"
    ):
        rolling_delta(two, text, 8, 2, statistics={"S": corpus["A"][:7]})
    with pytest.raises(SourceError, match=r"at least three windows$"):
        rolling_delta(two, text, 8, 8, statistics={"S": corpus["A"][:16]})
    with pytest.raises(SourceTypeError, match="must be a mapping"):
        rolling_delta(two, text, 8, 2, statistics=[corpus["A"]])
    # A unit only in the rest of a reference shorter than a window is in no window
    tail = rolling_delta({"A": [*text[:16], "zz"], "B": text[16:32]}, text, 8, 8, None)
    assert tail.equals(rolling_delta({"A": text[:16], "B": text[16:32]}, text, 8, 8, None))
    # No unit in every window
    with pytest.raises(SourceError, match=r"^No unit is left after culling$"):
        rolling_delta(
            {"A": list("abcdefgh"), "B": list("ijklmnop")}, list("abcd"), 4, 4, culling=1.0
        )


def test_rolling_delta_errors():
    text = corpus["A"]
    with pytest.raises(ParameterError, match=r"^Unknown variant of Delta: manhattan$"):
        rolling_delta(corpus, text, 8, 3, variant="manhattan")
    for window, step, message in (
        (0, 1, r"^The size of a window must be greater than 0$"),
        (8, 0, r"^The step must be greater than 0$"),
        (8.0, 3, r"^The size of a window must be an integer, not float$"),
        (8, "3", r"^The step must be an integer, not str$"),
        (8, 9, r"^The step must not exceed the size of a window$"),
    ):
        with pytest.raises(ParameterError, match=message):
            rolling_delta(corpus, text, window, step)
    two = {"A": text[:8], "B": text[8:16]}
    for reference, units, message in (
        ({}, text, r"^There are no reference texts$"),
        ({**corpus, "D": []}, text, r"^One of the reference texts has no units$"),
        ({"A": corpus["A"]}, text, r"^The rolling Delta needs at least two reference texts$"),
        # One unit short of a window
        ({"A": text[:7], "B": text[8:16]}, text, r"^One of the reference texts is shorter"),
        (two, text[:7], r"^The text is shorter than a window$"),
        (two, text, r"at least three windows$"),
    ):
        with pytest.raises(SourceError, match=message):
            rolling_delta(reference, units, 8, 8)
    # A reference text and the text of exactly one window are enough
    assert rolling_delta({**two, "C": text[2:10]}, text[:8], 8, 8).shape == (1, 3)
    with pytest.raises(SourceTypeError, match="must be a mapping of the names of the texts"):
        rolling_delta(list(corpus.values()), text, 8, 3)
    with pytest.raises(SourceTypeError):
        rolling_delta(corpus, texts["A"], 8, 3)


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
    with pytest.raises(SourceTypeError):
        zeta(set(corpus["A"]), corpus["B"])
    with pytest.raises(SourceTypeError):
        zeta([set(corpus["A"])], corpus["B"])


def test_zeta_segments():
    scores = zeta(corpus["A"], corpus["B"], segment_size=5)
    preferred = [score.word for score in scores if score.zeta > 0]
    avoided = [score.word for score in scores if score.zeta < 0]
    corpora = {"A": corpus["A"], "B": [corpus["B"]], "AC": [corpus["A"], [], corpus["C"]]}
    segments = zeta_segments(corpora, preferred, avoided, segment_size=5)
    assert list(segments.columns) == ["corpus", "preferred", "avoided"]
    # Four segments of A and of B, three more of C after an empty text
    assert segments["corpus"].tolist() == ["A"] * 4 + ["B"] * 4 + ["AC"] * 7
    first = set(np.array_split(np.array(corpus["A"], dtype=object), 4)[0])
    assert segments.loc[0, "preferred"] == len(first & set(preferred)) / len(set(preferred))
    assert segments.loc[0, "avoided"] == len(first & set(avoided)) / len(set(avoided))
    means = segments.groupby("corpus")[["preferred", "avoided"]].mean()
    assert means.loc["A", "preferred"] > means.loc["B", "preferred"]
    assert means.loc["A", "avoided"] < means.loc["B", "avoided"]
    # A set or repeats of the markers give the same shares
    same = zeta_segments(corpora, set(preferred), avoided * 2, segment_size=5)
    pd.testing.assert_frame_equal(same, segments)
    # One marker: the mean share over the segments is its share of the segments in zeta
    acab = next(score for score in scores if score.word == "acab")
    alone = zeta_segments({"A": corpus["A"], "B": corpus["B"]}, ["acab"], ["acab"], 5)
    assert alone.groupby("corpus")["preferred"].mean().to_dict() == {
        "A": acab.dp_target,
        "B": acab.dp_comparison,
    }


def test_zeta_segments_errors():
    corpora = {"A": corpus["A"]}
    with pytest.raises(ParameterError, match=r"^The size of a segment must be greater than 0$"):
        zeta_segments(corpora, ["ab"], ["ac"], segment_size=0)
    with pytest.raises(ParameterError, match=r"^The size of a segment must be an integer"):
        zeta_segments(corpora, ["ab"], ["ac"], segment_size=5.0)
    with pytest.raises(SourceTypeError, match=r"^The corpora must be a mapping of their names"):
        zeta_segments([corpus["A"]], ["ab"], ["ac"])
    for corpora_, preferred, avoided, message in (
        ({}, ["ab"], ["ac"], r"^There are no corpora$"),
        (corpora, [], ["ac"], r"^There are no preferred words$"),
        (corpora, ["ab"], set(), r"^There are no avoided words$"),
        ({"A": corpus["A"], "B": []}, ["ab"], ["ac"], r"^The corpus B has no words$"),
        ({"A": [[], []]}, ["ab"], ["ac"], r"^The corpus A has no words$"),
    ):
        with pytest.raises(SourceError, match=message):
            zeta_segments(corpora_, preferred, avoided)
    for corpora_, preferred in (
        (corpora, "ab"),
        (corpora, [1]),
        ({"A": texts["A"]}, ["ab"]),
        ({"A": ["acab", ["babaa"]]}, ["ab"]),
    ):
        with pytest.raises(SourceTypeError):
            zeta_segments(corpora_, preferred, ["ac"])


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
    assert zeta(dict(enumerate(words)).values(), ["d"]) == zeta(words, ["d"])
    expected = zeta_segments({"A": words}, ["a"], ["d"], segment_size=2)
    pd.testing.assert_frame_equal(
        zeta_segments({"A": container(words)}, ["a"], ["d"], 2), expected
    )
    reference = {"A": words * 2, "B": words[::-1] * 2, "C": ["c", *words, "c"]}
    expected = rolling_delta(reference, words * 2, window=4, step=2, n_mfw=3)
    arrays = {name: container(units) for name, units in reference.items()}
    rolled = rolling_delta(arrays, container(words * 2), window=4, step=2, n_mfw=3)
    pd.testing.assert_frame_equal(rolled, expected)
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
