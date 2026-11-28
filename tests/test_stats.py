from collections import Counter
from math import nan
from typing import ClassVar

import pandas as pd
import pytest
from anyseg import Document

from anyts import readability_stats
from anyts.basic_stats import BasicStats
from anyts.cohesion_stats import CohesionStats
from anyts.constants import MESSAGES
from anyts.diversity_stats import DiversityStats
from anyts.document import document_part, to_document
from anyts.exceptions import ParameterError, SourceError, SourceTypeError, UnknownStatError
from anyts.morph_stats import MorphStats
from anyts.readability_stats import ReadabilityStats
from anyts.stats import Stats, scale_level, stats_dataframe
from anyts.syntax_stats import SyntaxStats
from anyts.unadapted_readability_stats import UnadaptedReadabilityStats
from tests.documents import parsed


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


LINES_TEXT = "The cat sleeps. A dog barks.\nA bird sings\nin the tree.\n\nThe end."


def test_by_parts_of_lines():
    """A line is the sentences between line breaks, a sentence over a line break in one of them,
    and the lines of a paragraph add up to it"""
    lines = Vowels.by_parts(LINES_TEXT, "lines")
    assert lines.index.name == "line"
    assert [LINES_TEXT[start:end] for start, end in lines[["start", "end"]].values] == [
        "The cat sleeps. A dog barks.",
        "A bird sings\nin the tree.",
        "The end.",
    ]
    assert lines["n_sents"].tolist() == [2, 1, 1]
    paragraphs = Vowels.by_parts(LINES_TEXT, "paragraphs")
    assert paragraphs["n_words"].tolist() == [lines["n_words"][:2].sum(), 2]


def test_by_parts_of_cohesion_by_lines():
    """The lines, the paragraphs of the class by default, are its first parts"""
    words = ["A", "cat", "sleeps", ".", "The", "cat", "eats", ".", "\n", "A", "dog", "barks", "."]
    document = parsed(
        words,
        spaces=[index not in {2, 6, 7, 8, 11, 12} for index in range(len(words))],
        pos=[
            {"cat": "NOUN", "dog": "NOUN", ".": "PUNCT", "\n": "SPACE"}.get(w, "VERB")
            for w in words
        ],
        lemmas=[word.lower() for word in words],
        sent_starts=[not index or words[index - 1] == "." for index in range(len(words))],
    )
    parts = CohesionStats.by_parts(document)
    assert parts.index.name == "line"
    assert [document.text[start:end] for start, end in parts[["start", "end"]].values] == [
        "A cat sleeps. The cat eats.",
        "A dog barks.",
    ]
    assert parts["noun_overlap_adjacent"].tolist()[0] == 1.0


def test_by_parts_counts_stay_integers():
    """A count stays an integer in the rows of the parts without statistics"""
    parts = Vowels.by_parts(PARTS_TEXT)
    assert str(parts["n_words"].dtype) == "Int64"
    assert parts["n_words"].isna().tolist() == [False, False, False, True, False]
    assert parts["letters_entropy"].dtype == float


@pytest.mark.parametrize("source", ["", "***", "***\n\n* * *"])
def test_by_parts_of_a_source_without_words(source):
    """A source without words raises as the class does, its parameters checked"""
    with pytest.raises(SourceError, match=r"^The data source has no words$"):
        Vowels.by_parts(source)
    with pytest.raises(ParameterError, match=r"syllables in a complex word must be greater"):
        Vowels.by_parts(source, complex_syl_factor=0)


def test_by_parts_raises_the_error_of_the_parts():
    """A class that counts the whole text but none of its parts raises the error of a part"""

    class Fussy(Vowels):
        def __init__(self, source):
            super().__init__(source)
            if self.n_words < 5:
                raise SourceError("Too few words")

    assert Fussy("The cat sleeps. A dog barks.").n_words == 6
    with pytest.raises(SourceError, match=r"^Too few words$"):
        Fussy.by_parts("The cat sleeps. A dog barks.")


def test_value_desc_of_a_class_is_the_value():
    assert Vowels("The cat sleeps.").value_desc("c_letters", 3) == "3"


def test_by_parts_reads_the_statistics_once():
    reads = []

    class Counted(Vowels):
        stats_desc: ClassVar[dict[str, str]] = {**Vowels.stats_desc, "slow": "Slow"}

        @property
        def slow(self):
            reads.append(self.n_words)
            return self.n_words

    Counted.by_parts(PARTS_TEXT)
    assert reads == [3, 4, 3, 2]


def test_by_parts_of_a_string_and_a_document():
    frames = [Vowels.by_parts(source) for source in (PARTS_TEXT, to_document(PARTS_TEXT))]
    assert frames[0].equals(frames[1])


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
    def sentence(words, heads):
        return parsed(
            words, heads, ["nsubj", "ROOT", "punct"] * 2, pos=["NOUN", "VERB", "PUNCT"] * 2
        )

    document = sentence(["Cats", "sleep", ".", "Dogs", "bark", "."], [1, 1, 1, 4, 4, 4])
    parts = SyntaxStats.by_parts(document)
    assert parts["tree_depth"].tolist() == [1, 1]
    assert parts["mean_dependency_distance"].tolist() == [
        SyntaxStats(sentence(["Cats", "sleep", "."], [1, 1, 1])).mean_dependency_distance,
        SyntaxStats(sentence(["Dogs", "bark", "."], [1, 1, 1])).mean_dependency_distance,
    ]


@pytest.mark.parametrize(
    ("cls", "parts", "message"),
    [
        (
            Vowels,
            "words",
            r"^The parts must be one of \('sentences', 'lines', 'paragraphs'\), not 'words'$",
        ),
        (Vowels, 1, "not 1$"),
        (CohesionStats, "sentences", r"one of \('lines', 'paragraphs'\)"),
        (DiversityStats, "paragraphs", "^DiversityStats counts a whole text, not its parts$"),
        (DiversityStats, None, "^DiversityStats counts a whole text, not its parts$"),
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


def test_stats_dataframe_of_the_flat_statistics():
    """The columns are those of get_stats(flat=True): MorphStats leaves out the words without a
    feature"""
    words = ["The", "cats", "sleep", "."]
    document = parsed(
        words, pos=["DET", "NOUN", "VERB", "PUNCT"], morphs=["", "Number=Plur", "Tense=Pres", ""]
    )
    stats = MorphStats(document)
    frame = stats_dataframe([stats])
    assert list(frame.columns) == list(stats.to_dataframe().columns)
    assert not any(column.endswith("_None") for column in frame.columns)
    assert list(MorphStats.by_parts(document).columns[2:]) == list(frame.columns)


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
    document = Document.from_tokens(
        "Vino del mar. Fue al río.",
        [0, 5, 9, 12, 14, 18, 21, 24],
        [4, 8, 12, 13, 17, 20, 24, 25],
        sentence_starts=[0, 4],
        words={1: ["de", "el"], 5: ["a", "el"]},
    )
    document.set_columns(upos=[None, "ADP", "DET", None, None, None, "ADP", "DET", None, None])
    assert [
        [word.form for word in to_document(document_part(document, start, end)).words]
        for start, end in Vowels.by_parts(document)[["start", "end"]].values
    ] == [["Vino", "de", "el", "mar", "."], ["Fue", "a", "el", "río", "."]]
