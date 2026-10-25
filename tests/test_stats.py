from collections import Counter
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


def test_get_stats_flat_is_a_bool(sizes):
    # A name of a statistic is no flat
    with pytest.raises(ParameterError, match=r"^The flat must be a bool, not str$"):
        sizes.get_stats("n_words")


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


@pytest.mark.parametrize("stat", ["c_lengths_3", "c_lengths_other_long"])
def test_describe_flat_key(sizes, stat):
    assert stat in sizes.get_stats(flat=True)
    assert sizes.describe(stat) is None


def test_describe_key_of_another_text(sizes):
    # a column of a table of several objects
    assert "c_lengths_4" not in sizes.get_stats(flat=True)
    assert sizes.describe("c_lengths_4") is None


class Tagged(Stats):
    """Statistics of per-word values, counted by get_stats"""

    stats_desc: ClassVar = {"pos": "Parts of speech"}

    def __init__(self, tags):
        self.pos = tuple(tags)

    def get_stats(self, flat=False):
        counts = {"pos": dict(Counter(self.pos))}
        return {f"pos_{tag}": n for tag, n in counts["pos"].items()} if flat else counts


class Failing(Stats):
    """A statistic that cannot be computed"""

    stats_desc: ClassVar = {"n_words": "Words", "c_tags": "Tags"}
    n_words = 3

    @property
    def c_tags(self):
        raise ValueError("no tags")


def test_describe_unknown_computes_nothing():
    with pytest.raises(UnknownStatError):
        Failing().describe("typo")
    with pytest.raises(ValueError, match="no tags"):
        Failing().describe("c_tags_NOUN")


def test_describe_flat_key_of_an_own_get_stats():
    tagged = Tagged(["NOUN", "VERB", "NOUN"])
    assert tagged.describe("pos_NOUN") is None and tagged.describe("pos") is None
    # a value of another text, a column of a table of several objects
    assert tagged.describe("pos_ADJ") is None


@pytest.mark.parametrize(
    "stat",
    ["unknown", "words", "_private", "stat_names", None, ["n_words"], "n_words_3"],
)
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
