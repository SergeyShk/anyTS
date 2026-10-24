import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from matplotlib.axes import Axes

from anyts import WordsExtractor
from anyts.corpus import delta, mendenhall_curve, rolling_delta, zeta, zeta_segments
from anyts.exceptions import ParameterError, SourceError, SourceTypeError
from anyts.visualizers import (
    delta_histogram_plot,
    dendrogram_plot,
    mds_plot,
    mendenhall_plot,
    pca_plot,
    rolling_delta_plot,
    zeta_scatter_plot,
)

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
distances = delta(corpus, n_mfw=10)


def test_dendrogram_plot():
    ax = dendrogram_plot(distances)
    assert isinstance(ax, Axes)
    assert sorted(label.get_text() for label in ax.get_yticklabels()) == ["A", "B", "C"]
    assert ax.get_xlabel() == "Distance"
    assert ax.get_title() == "Clustering of the texts"
    assert len(ax.collections) >= 2
    _, given = plt.subplots()
    assert dendrogram_plot(distances, method="average", ax=given) is given
    plt.close("all")
    with pytest.raises(SourceError):
        dendrogram_plot(distances.iloc[:1, :1])
    with pytest.raises(SourceError, match="square matrix"):
        dendrogram_plot(distances.iloc[:2, :3])
    with pytest.raises(SourceError, match="finite"):
        dendrogram_plot(distances.replace(0.0, np.nan))
    with pytest.raises(ParameterError, match="Unknown method of linkage: wrad"):
        dendrogram_plot(distances, method="wrad")
    for method in (["ward"], {"ward": 1}):
        with pytest.raises(ParameterError, match="Unknown method of linkage"):
            dendrogram_plot(distances, method=method)
    for plot in (dendrogram_plot, mds_plot):
        with pytest.raises(SourceTypeError, match="must be a DataFrame"):
            plot(distances.to_numpy())
    assert len(plt.get_fignums()) == 0


def test_pca_plot():
    ax = pca_plot(corpus, n_mfw=10)
    assert isinstance(ax, Axes)
    assert [text.get_text() for text in ax.texts] == ["A", "B", "C"]
    offsets = ax.collections[0].get_offsets()
    assert offsets.shape == (3, 2)
    assert np.allclose(offsets.mean(axis=0), 0, atol=1e-9)
    assert ax.get_xlabel().startswith("Component 1 (")
    assert ax.get_ylabel().startswith("Component 2 (")
    with pytest.raises(SourceError):
        pca_plot({name: corpus[name] for name in ("A", "B")}, n_mfw=10)
    with pytest.raises(SourceTypeError, match="must be a mapping"):
        pca_plot(5)
    _, given = plt.subplots()
    assert pca_plot(corpus, n_mfw=10, ax=given) is given
    ax = pca_plot(corpus, n_mfw=1)
    assert ax.get_xlabel() == "Component 1 (100.0%)"
    assert np.allclose(ax.collections[0].get_offsets()[:, 1], 0)
    # A table of constant columns has no variance to explain
    same = dict.fromkeys(("A", "B", "C"), corpus["A"])
    assert pca_plot(same, n_mfw=5).get_xlabel() == "Component 1 (0.0%)"
    plt.close("all")


def test_mds_plot():
    ax = mds_plot(distances)
    assert isinstance(ax, Axes)
    assert [text.get_text() for text in ax.texts] == ["A", "B", "C"]
    offsets = np.asarray(ax.collections[0].get_offsets())
    assert offsets.shape == (3, 2)
    assert np.allclose(offsets.mean(axis=0), 0, atol=1e-9)
    recovered = np.linalg.norm(offsets[0] - offsets[1])
    assert recovered <= distances.loc["A", "B"] + 1e-9
    assert ax.get_title() == "Multidimensional scaling"
    _, given = plt.subplots()
    assert mds_plot(distances, ax=given) is given
    with pytest.raises(SourceError):
        mds_plot(distances.iloc[:1, :1])
    with pytest.raises(SourceError):
        mds_plot(distances.replace(0.0, np.inf))
    plt.close("all")


def test_mds_plot_exact():
    exact = distances.copy()
    exact.loc[:, :] = [[0, 3, 4], [3, 0, 5], [4, 5, 0]]
    offsets = np.asarray(mds_plot(exact).collections[0].get_offsets())
    for i, j, expected in ((0, 1, 3), (0, 2, 4), (1, 2, 5)):
        assert np.linalg.norm(offsets[i] - offsets[j]) == pytest.approx(expected)
    plt.close("all")


# Two texts of A and two of B: within the authors 1 and 2, between them 5 to 8
PAIRS = pd.DataFrame(
    [[0, 1, 5, 6], [1, 0, 7, 8], [5, 7, 0, 2], [6, 8, 2, 0]],
    index=["A1", "A2", "B1", "B2"],
    columns=["A1", "A2", "B1", "B2"],
    dtype=float,
)
AUTHORS = {"A1": "A", "A2": "A", "B1": "B", "B2": "B"}


def test_delta_histogram_plot():
    ax = delta_histogram_plot(PAIRS, AUTHORS, bins=7)
    assert isinstance(ax, Axes)
    # Common bins of width 1 from 1 to 8, the densities of the pairs within, then between
    heights = [patch.get_height() for patch in ax.patches]
    assert heights == [0.5, 0.5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0.25, 0.25, 0.5]
    assert {patch.get_x() for patch in ax.patches} == set(range(1, 8))
    assert [text.get_text() for text in ax.get_legend().get_texts()] == [
        "Same author",
        "Different authors",
    ]
    assert (ax.get_xlabel(), ax.get_ylabel()) == ("Distance", "Density")
    assert ax.get_title() == "Distances within and between authors"
    _, given = plt.subplots()
    ax = delta_histogram_plot(PAIRS, AUTHORS, ax=given, labels={"within": "Same"})
    assert ax is given
    assert ax.get_legend().get_texts()[0].get_text() == "Same"
    # The columns follow the rows, extra authors do not matter
    reordered = PAIRS.iloc[::-1][["B2", "A1", "B1", "A2"]]
    ax = delta_histogram_plot(reordered, {**AUTHORS, "C": "C"}, bins=7)
    assert [patch.get_height() for patch in ax.patches] == heights
    plt.close("all")


def test_delta_histogram_plot_errors():
    for authors, error, message in (
        (list(AUTHORS), SourceTypeError, r"^The authors must be a mapping of the names"),
        ({"A1": "A", "A2": "A", "B1": "B"}, SourceError, r"^The texts have no authors: \['B2'\]$"),
        (
            dict(zip(PAIRS.index, "ABCD", strict=True)),
            SourceError,
            r"needs two texts by one author$",
        ),
        (dict.fromkeys(PAIRS.index, "A"), SourceError, r"needs texts by different authors$"),
    ):
        with pytest.raises(error, match=message):
            delta_histogram_plot(PAIRS, authors)
    with pytest.raises(ParameterError, match=r"^The number of bins must be greater than 0$"):
        delta_histogram_plot(PAIRS, AUTHORS, bins=0)
    with pytest.raises(ParameterError, match=r"^The number of bins must be an integer"):
        delta_histogram_plot(PAIRS, AUTHORS, bins=5.0)
    with pytest.raises(
        SourceError, match=r"^The histogram of the distances needs a square matrix"
    ):
        delta_histogram_plot(PAIRS.iloc[:, :3], AUTHORS)
    with pytest.raises(SourceTypeError, match="must be a DataFrame"):
        delta_histogram_plot(PAIRS.to_numpy(), AUTHORS)
    assert plt.get_fignums() == []


def test_rolling_delta_plot():
    text = corpus["A"] + corpus["B"]
    distances = rolling_delta(corpus, text, window=12, step=3, n_mfw=None)
    ax = rolling_delta_plot(distances)
    assert isinstance(ax, Axes)
    assert [line.get_label() for line in ax.get_lines()] == ["A", "B", "C"]
    for line, name in zip(ax.get_lines(), distances.columns, strict=True):
        assert list(line.get_xdata()) == list(distances.index)
        assert list(line.get_ydata()) == list(distances[name])
    assert (ax.get_xlabel(), ax.get_ylabel()) == ("Middle of the window", "Distance")
    assert ax.get_title() == "Rolling Delta"
    _, given = plt.subplots()
    assert rolling_delta_plot(distances, ax=given, labels={"title": "Rolling"}) is given
    assert given.get_title() == "Rolling"
    # A distance a rounding error below zero is drawn
    noisy = distances.copy()
    noisy.iloc[0, 0] = -2.2e-16
    rolling_delta_plot(noisy)
    plt.close("all")
    for frame, error, message in (
        (distances.to_numpy(), SourceTypeError, r"^The distances must be a DataFrame"),
        (distances.iloc[:0], SourceError, r"needs a window and a reference text$"),
        (distances.iloc[:, :0], SourceError, r"needs a window and a reference text$"),
        (distances.assign(A="far"), SourceTypeError, r"must be numbers$"),
        (distances.set_axis([f"w{i}" for i in range(len(distances))]), SourceTypeError, "numbers"),
        (
            distances.set_axis([2, np.inf, *distances.index[2:]]),
            SourceError,
            "position of a window",
        ),
        (
            distances.set_axis([2, np.nan, *distances.index[2:]]),
            SourceError,
            "position of a window",
        ),
        (distances.replace(distances.iloc[0, 0], np.inf), SourceError, r"to be finite$"),
        (distances - 1, SourceError, r"non-negative distances$"),
    ):
        with pytest.raises(error, match=message):
            rolling_delta_plot(frame)
    assert plt.get_fignums() == []


def test_zeta_scatter_plot():
    scores = zeta(corpus["A"], corpus["B"], segment_size=5)
    preferred = [score.word for score in scores if score.zeta > 0]
    avoided = [score.word for score in scores if score.zeta < 0]
    segments = zeta_segments(corpus, preferred, avoided, segment_size=5)
    ax = zeta_scatter_plot(segments)
    assert isinstance(ax, Axes)
    assert len(ax.collections) == 3
    for points, name in zip(ax.collections, ["A", "B", "C"], strict=True):
        selected = segments[segments["corpus"] == name]
        assert np.asarray(points.get_offsets()).tolist() == (
            selected[["avoided", "preferred"]].to_numpy().tolist()
        )
    assert [text.get_text() for text in ax.get_legend().get_texts()] == ["A", "B", "C"]
    assert ax.get_xlabel() == "Share of the avoided words"
    assert ax.get_ylabel() == "Share of the preferred words"
    assert ax.get_title() == "Zeta markers in the segments"
    _, given = plt.subplots()
    assert zeta_scatter_plot(segments, ax=given) is given
    # Segments without the name of a corpus are a corpus of their own
    unnamed = segments.assign(corpus=segments["corpus"].where(segments["corpus"] != "C"))
    ax = zeta_scatter_plot(unnamed)
    assert [len(points.get_offsets()) for points in ax.collections] == [4, 4, 3]
    assert ax.get_legend().get_texts()[2].get_text() == "nan"
    plt.close("all")
    for frame, error, message in (
        (segments.to_numpy(), SourceTypeError, r"^The segments must be a DataFrame"),
        (
            segments.drop(columns="avoided"),
            SourceError,
            r"^The segments have no columns \['avoided'\]$",
        ),
        (
            pd.concat([segments, segments[["avoided"]]], axis=1),
            SourceError,
            r"^The segments have repeated columns \['avoided'\]$",
        ),
        (
            pd.concat([segments, segments[["corpus"]]], axis=1),
            SourceError,
            r"^The segments have repeated columns \['corpus'\]$",
        ),
        (segments.iloc[:0], SourceError, r"^The plot needs at least one segment$"),
        (segments.assign(avoided="x"), SourceTypeError, r"must be numbers$"),
        (segments.assign(preferred=np.nan), SourceError, r"to be finite$"),
    ):
        with pytest.raises(error, match=message):
            zeta_scatter_plot(frame)
    assert plt.get_fignums() == []


def test_mendenhall_plot_missing_lengths():
    # A length that no word has is drawn at zero, not between its neighbours
    ax = mendenhall_plot({"A": ["a", "abc", "abc"]})
    assert ax.get_lines()[0].get_xydata().tolist() == [[1, 1 / 3], [2, 0.0], [3, 2 / 3]]
    plt.close("all")


def test_mendenhall_plot():
    ax = mendenhall_plot(corpus)
    assert isinstance(ax, Axes)
    assert [line.get_label() for line in ax.get_lines()] == ["A", "B", "C"]
    curve = mendenhall_curve(corpus["A"])
    lengths = list(range(1, max(curve) + 1))
    assert list(ax.get_lines()[0].get_xdata()) == lengths
    assert list(ax.get_lines()[0].get_ydata()) == [curve.get(n, 0.0) for n in lengths]
    assert ax.get_legend() is not None
    _, given = plt.subplots()
    assert mendenhall_plot(corpus, ax=given) is given
    with pytest.raises(SourceError):
        mendenhall_plot({})
    with pytest.raises(SourceTypeError, match="must be a mapping"):
        mendenhall_plot([corpus["A"]])
    plt.close("all")
    with pytest.raises(SourceError):
        mendenhall_plot({"A": []})
    assert len(plt.get_fignums()) == 0


EXACT = pd.DataFrame(
    [[0, 3, 4], [3, 0, 5], [4, 5, 0]], index=list("ABC"), columns=list("ABC"), dtype=float
)


def _heights(ax):
    """Distances at which the dendrogram joins its clusters"""
    return {
        round(x, 9) for lines in ax.collections for line in lines.get_segments() for x, _ in line
    }


def test_distance_matrix_in_any_order():
    # The columns follow the rows, whatever their order
    offsets = np.asarray(mds_plot(EXACT.sort_index(ascending=False)).collections[0].get_offsets())
    for i, j, expected in ((0, 1, 5), (0, 2, 4), (1, 2, 3)):
        assert np.linalg.norm(offsets[i] - offsets[j]) == pytest.approx(expected)
    assert _heights(dendrogram_plot(EXACT[["C", "A", "B"]], method="single")) == {0, 3, 4}
    assert _heights(dendrogram_plot(EXACT, method="single")) == {0, 3, 4}
    plt.close("all")


@pytest.mark.parametrize(
    ("matrix", "error", "message"),
    [
        (EXACT.rename(columns={"C": "D"}), SourceError, "same texts in the rows and the columns"),
        (EXACT.rename(index={"C": "A"}), SourceError, "same texts in the rows and the columns"),
        (
            EXACT.replace({4.0: 100.0}).where(np.triu(np.ones((3, 3))) == 1, EXACT),
            SourceError,
            "symmetric",
        ),
        (EXACT * -1, SourceError, "non-negative"),
        (EXACT + np.eye(3), SourceError, "zero distances on the diagonal"),
        (EXACT.astype(object).replace({3.0: "far"}), SourceTypeError, "must be numbers"),
    ],
)
def test_distance_matrix_errors(matrix, error, message):
    for plot in (dendrogram_plot, mds_plot):
        with pytest.raises(error, match=message):
            plot(matrix)
    assert plt.get_fignums() == []


def test_distance_matrix_rounding_error():
    # A cosine distance of a text to itself may come out a rounding error below zero
    noisy = EXACT.copy()
    noisy.iloc[0, 0] = noisy.iloc[1, 1] = -2.2e-16
    offsets = np.asarray(mds_plot(noisy).collections[0].get_offsets())
    assert np.linalg.norm(offsets[0] - offsets[1]) == pytest.approx(3)
    assert _heights(dendrogram_plot(noisy, method="single")) == {0, 3, 4}
    plt.close("all")
