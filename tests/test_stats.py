from collections import Counter
from math import nan
from typing import ClassVar

import pandas as pd
import pytest
import spacy

from anyts import readability_stats
from anyts.basic_stats import BasicStats
from anyts.cohesion_stats import CohesionStats
from anyts.constants import MESSAGES
from anyts.diversity_stats import DiversityStats
from anyts.document import document_part, to_document
from anyts.exceptions import ParameterError, SourceError, SourceTypeError, UnknownStatError
from anyts.readability_stats import ReadabilityStats
from anyts.stats import Stats, scale_level, stats_dataframe
from anyts.syntax_stats import SyntaxStats
from anyts.unadapted_readability_stats import UnadaptedReadabilityStats


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


def test_get_stats_flat_is_a_keyword_bool(sizes):
    # A name of a statistic is no flat: flat is named, and a bool
    with pytest.raises(TypeError):
        sizes.get_stats("n_words")
    with pytest.raises(ParameterError, match=r"^The flat must be a bool, not str$"):
        sizes.get_stats(flat="n_words")


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


@pytest.mark.parametrize(
    ("name", "replacement"),
    [
        ("words_extractor_class", "parse or doc_words"),
        ("sents_extractor_class", "parse"),
        ("join_hyphens", "parse"),
        ("doc_units", "analyze"),
    ],
)
def test_attributes_of_0_4_raise_at_class_definition(name, replacement):
    """A class with an attribute the core no longer reads fails at once, not with other numbers"""
    with pytest.raises(ParameterError) as raised:
        type("Old", (Sizes,), {name: None})
    assert (
        str(raised.value) == f"Old defines {name}, which is no longer read: override {replacement}"
    )


def test_scale_level_of_an_ascending_scale():
    with pytest.raises(ParameterError, match=r"^The lower bounds of the scale must descend"):
        scale_level(50, [(0, "short"), (100, "long")])


class Vowels(BasicStats):
    def count_syllables(self, word):
        return sum(char in "aeiou" for char in word.lower())


PARTS_TEXT = "The cat sleeps. A dog barks loudly!\n\nA bird sings.\n\n***\n\nThe end."


def test_by_parts_of_sentences():
    """A row per sentence with its bounds; the words and the sentences of the parts add up to
    those of the text, and a sentence without words has its row without statistics"""
    parts = Vowels.by_parts(PARTS_TEXT)
    assert parts.index.name == "sentence"
    assert list(parts.columns[:2]) == ["start", "end"]
    assert parts[["start", "end"]].values.tolist() == [
        [0, 15],
        [16, 35],
        [37, 50],
        [52, 55],
        [57, 65],
    ]
    assert [PARTS_TEXT[start:end] for start, end in parts[["start", "end"]].values][3] == "***"
    assert parts.loc[3].drop(["start", "end"]).isna().all()
    whole = Vowels(PARTS_TEXT)
    for stat in ("n_words", "n_sents", "n_syllables", "n_letters"):
        assert parts[stat].sum() == getattr(whole, stat)
    assert parts.loc[1, "n_words"] == Vowels("A dog barks loudly!").n_words


def test_by_parts_of_paragraphs_with_parameters():
    parts = Vowels.by_parts(PARTS_TEXT, "paragraphs", complex_syl_factor=2)
    assert parts.index.name == "paragraph"
    assert parts["n_sents"].fillna(0).tolist() == [2, 1, 0, 1]
    assert (
        parts.loc[0, "n_complex_words"]
        == Vowels("The cat sleeps. A dog barks loudly!", complex_syl_factor=2).n_complex_words
    )


def test_by_parts_of_a_string_a_doc_and_a_document():
    doc = spacy.blank("en")(PARTS_TEXT)
    frames = [Vowels.by_parts(source) for source in (PARTS_TEXT, doc, to_document(PARTS_TEXT))]
    assert frames[0].equals(frames[1]) and frames[0].equals(frames[2])


def test_by_parts_parses_the_source_once():
    sources = []

    class Counted(Vowels):
        def parse(self, source):
            sources.append(type(source).__name__)
            return super().parse(source)

    Counted.by_parts(PARTS_TEXT)
    assert sources.count("str") == 1


def test_by_parts_of_readability_parses_as_its_basic_stats():
    sources = []

    class Basic(Vowels):
        def parse(self, source):
            sources.append(type(source).__name__)
            return super().parse(source)

    class Readability(ReadabilityStats):
        basic_stats_class = Basic

    parts = Readability.by_parts(PARTS_TEXT)
    assert sources[0] == "str" and sources.count("str") == 1
    assert len(parts) == 5 and parts["flesch_kincaid_grade"].notna().sum() == 4
    with pytest.raises(SourceTypeError, match=r"^ReadabilityStats has no basic_stats_class"):
        ReadabilityStats.by_parts(PARTS_TEXT)


def test_by_parts_of_unadapted_readability():
    class Unadapted(UnadaptedReadabilityStats):
        basic_stats_class = Vowels

    parts = Unadapted.by_parts(PARTS_TEXT, "paragraphs")
    assert parts["forcast"].notna().tolist() == [True, True, False, True]
    assert parts.loc[1, "forcast"] == Unadapted("A bird sings.").forcast


def test_by_parts_of_syntax():
    doc = spacy.tokens.Doc(
        spacy.blank("en").vocab,
        words=["Cats", "sleep", ".", "Dogs", "bark", "."],
        heads=[1, 1, 1, 4, 4, 4],
        deps=["nsubj", "ROOT", "punct", "nsubj", "ROOT", "punct"],
        pos=["NOUN", "VERB", "PUNCT", "NOUN", "VERB", "PUNCT"],
    )
    parts = SyntaxStats.by_parts(doc)
    assert parts["tree_depth"].tolist() == [1, 1]
    assert parts["mean_dependency_distance"].tolist() == [
        SyntaxStats(doc[:3].as_doc()).mean_dependency_distance,
        SyntaxStats(doc[3:].as_doc()).mean_dependency_distance,
    ]


@pytest.mark.parametrize(
    ("cls", "parts", "message"),
    [
        (
            Vowels,
            "words",
            r"^The parts must be one of \('sentences', 'paragraphs'\), not 'words'$",
        ),
        (Vowels, 1, "not 1$"),
        (CohesionStats, "sentences", r"one of \('paragraphs',\)"),
        (DiversityStats, "paragraphs", r"one of \(\), not 'paragraphs'$"),
    ],
)
def test_by_parts_kinds(cls, parts, message):
    with pytest.raises(ParameterError, match=message):
        cls.by_parts(PARTS_TEXT, parts)


class Lengths(Stats):
    stats_desc: ClassVar[dict[str, str]] = {
        "n_words": "Words",
        "c_lengths": "Words by length",
        "share": "Share",
    }

    def __init__(self, text, share=None):
        words = text.split()
        self.n_words = len(words)
        self.c_lengths = dict(sorted(Counter(map(len, words)).items()))
        self.share = share


def test_stats_dataframe():
    """A count of a dictionary an object lacks is 0, in the order of the keys of numbers"""
    frame = stats_dataframe(
        [Lengths("The cat sat", 0.5), Lengths("A mouse ran away")], index=["a", "b"]
    )
    assert list(frame.columns) == [
        "n_words",
        "c_lengths_1",
        "c_lengths_3",
        "c_lengths_4",
        "c_lengths_5",
        "share",
    ]
    assert frame.loc["a"].tolist()[:5] == [3, 0, 3, 0, 0]
    assert frame.loc["b", "c_lengths_1"] == 1
    assert pd.isna(frame.loc["b", "share"])
    assert stats_dataframe([]).empty
    assert list(stats_dataframe(iter([Lengths("x")])).index) == [0]


@pytest.mark.parametrize("stats", ["text", 5, [Lengths("x"), {"n_words": 1}]])
def test_stats_dataframe_type_errors(stats):
    with pytest.raises(
        SourceTypeError, match=r"^A list of objects of statistics is expected, not "
    ):
        stats_dataframe(stats)


def test_by_parts_keeps_a_part_the_class_cannot_count():
    """A number alone on a line is a sentence of words, but none for a class without numbers:
    its row stays without statistics; a text of such parts alone raises the error of the class"""
    parts = Vowels.by_parts("Chapter one.\n\n1\n\nThe cat sleeps.", filter_nums=True)
    assert parts["n_words"].tolist()[0::2] == [2, 3]
    assert parts.loc[1].drop(["start", "end"]).isna().all()
    with pytest.raises(SourceError, match=r"^The data source has no words$"):
        Vowels.by_parts("1\n\n2", filter_nums=True)


def test_parts_document_takes_the_parameters():
    """parts_document gets the parameters of the class, for a parse that needs them"""
    calls = []

    class Upper(Vowels):
        @classmethod
        def parts_document(cls, source, **params):
            calls.append(params)
            return to_document(source.upper())

    parts = Upper.by_parts("The cat sleeps. A dog barks.", complex_syl_factor=2)
    assert calls == [{"complex_syl_factor": 2}]
    assert parts["n_words"].tolist() == [3, 3]
    assert Upper.by_parts("The cat.")["n_letters"].tolist() == [6]


def test_by_parts_of_multiword_tokens():
    vocab = spacy.blank("es").vocab
    doc = spacy.tokens.Doc(
        vocab,
        words=["Vino", "del", "mar", ".", "Fue", "al", "río", "."],
        spaces=[True, True, False, True, True, True, False, False],
        sent_starts=[True, False, False, False, True, False, False, False],
    )
    import anyseg.spacy  # noqa: F401 - the extension token._.anyseg_words

    doc[1]._.anyseg_words = [{"form": "de", "upos": "ADP"}, {"form": "el", "upos": "DET"}]
    doc[5]._.anyseg_words = [{"form": "a", "upos": "ADP"}, {"form": "el", "upos": "DET"}]
    document = to_document(doc)
    assert [
        [word.form for word in to_document(document_part(document, start, end)).words]
        for start, end in Vowels.by_parts(doc)[["start", "end"]].values
    ] == [["Vino", "de", "el", "mar", "."], ["Fue", "a", "el", "río", "."]]
