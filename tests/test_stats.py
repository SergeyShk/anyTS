from math import nan
from typing import ClassVar

import pandas as pd
import pytest

from anyts import readability_stats
from anyts.constants import MESSAGES
from anyts.exceptions import ParameterError, UnknownStatError
from anyts.stats import Stats, scale_level


class Sizes(Stats):
    stats_desc: ClassVar[dict[str, str]] = {
        "n_words": "Words",
        "mean_len": "Mean word length",
        "c_lengths": "Words by length",
        "longest": "Longest word",
    }
    level_scales: ClassVar = {
        "n_words": ((100, "long"), (0, "short")),
        "mean_len": ((5, "hard"), (0, "easy")),
    }

    def __init__(self, text):
        words = text.split()
        self.n_words = len(words)
        self.c_lengths = {3: sum(len(word) == 3 for word in words), "other": {"long": 1}}
        self.longest = max(words, key=len, default="")
        self.words = words

    @property
    def mean_len(self):
        return sum(map(len, self.words)) / self.n_words if self.n_words else nan

    @property
    def unprinted(self):
        return 1


TEXT = "The cat sat on the mat beautifully"


@pytest.fixture
def sizes():
    return Sizes(TEXT)


def test_get_stats(sizes):
    assert sizes.stat_names() == ("n_words", "mean_len", "c_lengths", "longest")
    assert sizes.get_stats() == {
        "n_words": 7,
        "mean_len": 4.0,
        "c_lengths": {3: 5, "other": {"long": 1}},
        "longest": "beautifully",
    }


def test_get_stats_is_a_copy(sizes):
    stats = sizes.get_stats()
    stats["c_lengths"][3] = -1
    stats["c_lengths"]["other"]["long"] = -1
    assert sizes.c_lengths == {3: 5, "other": {"long": 1}}


def test_get_stats_flat(sizes):
    assert sizes.get_stats(flat=True) == {
        "n_words": 7,
        "mean_len": 4.0,
        "c_lengths_3": 5,
        "c_lengths_other_long": 1,
        "longest": "beautifully",
    }


def test_to_dataframe(sizes):
    frame = sizes.to_dataframe()
    assert isinstance(frame, pd.DataFrame)
    assert frame.shape == (1, 5)
    assert frame.iloc[0].to_dict() == sizes.get_stats(flat=True)
    texts = pd.concat([Sizes(text).to_dataframe() for text in (TEXT, "a b")], ignore_index=True)
    assert list(texts["n_words"]) == [7, 2]


def test_print_stats(capsys, sizes):
    sizes.print_stats()
    lengths = str(sizes.c_lengths)
    assert capsys.readouterr().out.splitlines() == [
        f"{'Statistic':^17}|{'Value':^30}",
        "-" * 48,
        f"{'Words':17}|{'7':^30}",
        f"{'Mean word length':17}|{'4.00':^30}",
        f"{'Words by length':17}|{lengths:^30}",
        f"{'Longest word':17}|{'beautifully':^30}",
    ]


def test_print_stats_headers(capsys):
    class Wide(Sizes):
        stats_desc: ClassVar[dict[str, str]] = {"n_words": "W"}
        stats_headers = ("Name of the statistic", "Value of the statistic")

    Wide(TEXT).print_stats()
    assert capsys.readouterr().out.splitlines() == [
        f"{'Name of the statistic':^22}|{'Value of the statistic':^24}",
        "-" * 47,
        f"{'W':22}|{'7':^24}",
    ]


def test_print_stats_without_stats(capsys):
    class Empty(Stats):
        pass

    assert Empty().get_stats() == {}
    Empty().print_stats()
    assert capsys.readouterr().out.splitlines() == [f"{'Statistic':^10}|{'Value':^10}", "-" * 21]


def test_describe(sizes):
    assert sizes.describe("n_words") == "short"
    assert sizes.describe("mean_len") == "easy"
    assert sizes.describe("longest") is None
    assert sizes.describe("unprinted") is None
    assert Sizes("").describe("mean_len") is None


@pytest.mark.parametrize("stat", ["unknown", "words", "_private", "stat_names", None, ["n_words"]])
def test_describe_unknown(sizes, stat):
    message = (
        f"Unknown statistic: {stat}. Available statistics: "
        "('n_words', 'mean_len', 'c_lengths', 'longest')"
    )
    with pytest.raises(UnknownStatError) as raised:
        sizes.describe(stat)
    assert str(raised.value).strip("'\"") == message


def test_level_scale_hook(sizes):
    class ByLength(Sizes):
        def level_scale(self, stat):
            return ((0, f"read by {stat}"),)

    assert sizes.level_scale("longest") is None
    assert sizes.level_scale(["n_words"]) is None
    assert ByLength(TEXT).describe("n_words") == "read by n_words"


def test_messages():
    class Own(Sizes):
        messages: ClassVar = {**MESSAGES, "unknown_stat": "Own: {stat} ({stats})"}

    with pytest.raises(UnknownStatError, match=r"Own: x \(\('n_words'"):
        Own(TEXT).describe("x")
    with pytest.raises(ParameterError):

        class Incomplete(Stats):
            messages: ClassVar = {"unknown_stat": "{stat}"}


def test_scale_level_is_reexported():
    assert readability_stats.scale_level is scale_level


@pytest.mark.parametrize(
    ("scales", "message"),
    [
        (
            {"n": ((0, "short"), (100, "long"))},
            r"^The lower bounds of the scale of n in the level_",
        ),
        ({"n": ((100, "long"), (100, "short"))}, r"must descend, not \[100, 100\]$"),
        ({"n": ()}, r"^The scale of n in the level_scales of Scaled is empty$"),
        (
            {"n": (100, 0)},
            r"^The scale of n in the level_scales of Scaled must be a list of pairs",
        ),
        (((100, "long"),), r"^The level_scales of Scaled must be a mapping of a statistic"),
    ],
)
def test_level_scales_checked_at_class_definition(scales, message):
    with pytest.raises(ParameterError, match=message):
        type("Scaled", (Stats,), {"level_scales": scales})


def test_scale_level_of_an_ascending_scale():
    with pytest.raises(ParameterError, match=r"^The lower bounds of the scale must descend"):
        scale_level(50, [(0, "short"), (100, "long")])
