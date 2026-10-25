import pickle
from math import nan
from typing import ClassVar

import pytest
import spacy
from spacy.tokens import Doc

from anyts.constants import MESSAGES, MORPH_FEATURES, MORPH_STATS_DESC, MORPH_VALUES_DESC
from anyts.exceptions import ParameterError, SourceError, SourceTypeError, UnknownStatError
from anyts.morph_stats import MorphStats, MorphWord

VOCAB = spacy.blank("en").vocab
WORDS = ["The", "cats", "slept", "and", "they", "dream", "."]
POS = ["DET", "NOUN", "VERB", "CCONJ", "PRON", "VERB", "PUNCT"]
MORPHS = [
    "Definite=Def|PronType=Art",
    "Number=Plur",
    "Mood=Ind|Tense=Past|VerbForm=Fin",
    "",
    "Case=Nom|Number=Plur|Person=3|PronType=Prs",
    "Mood=Ind|Tense=Pres|VerbForm=Fin",
    "PunctType=Peri",
]


def make_doc(pos=True):
    return Doc(VOCAB, words=WORDS, pos=POS if pos else None, morphs=MORPHS)


@pytest.fixture(scope="module")
def stats():
    return MorphStats(make_doc())


def test_words_and_features(stats):
    # The punctuation mark is no word
    assert stats.words == ("The", "cats", "slept", "and", "they", "dream")
    assert stats.pos == ("DET", "NOUN", "VERB", "CCONJ", "PRON", "VERB")
    assert stats.tags == (
        "Definite=Def|PronType=Art",
        "Number=Plur",
        "Mood=Ind|Tense=Past|VerbForm=Fin",
        "_",
        "Case=Nom|Number=Plur|Person=3|PronType=Prs",
        "Mood=Ind|Tense=Pres|VerbForm=Fin",
    )
    assert stats.number == (None, "Plur", None, None, "Plur", None)
    assert stats.pron_type == ("Art", None, None, None, "Prs", None)
    assert stats.voice == (None,) * 6
    assert list(stats.stat_names()) == ["pos", *MORPH_FEATURES]


def test_get_stats(stats):
    values = stats.get_stats()
    assert list(values) == list(MORPH_STATS_DESC)
    # The values in the order of their first occurrences, None for the words without them
    assert values["pos"] == {"DET": 1, "NOUN": 1, "VERB": 2, "CCONJ": 1, "PRON": 1}
    assert values["tense"] == {None: 4, "Past": 1, "Pres": 1}
    assert values["voice"] == {None: 6}
    assert stats.get_stats("number", "tense", filter_none=True) == {
        "number": {"Plur": 2},
        "tense": {"Past": 1, "Pres": 1},
    }
    assert stats.get_stats("voice", filter_none=True) == {"voice": {}}
    assert stats.get_stats("pos", "tense", flat=True) == {
        "pos_DET": 1,
        "pos_NOUN": 1,
        "pos_VERB": 2,
        "pos_CCONJ": 1,
        "pos_PRON": 1,
        "tense_Past": 1,
        "tense_Pres": 1,
    }
    # The counts are copies
    values["pos"]["DET"] = 5
    assert stats.get_stats("pos")["pos"]["DET"] == 1


def test_frame_and_describe(stats):
    frame = stats.to_dataframe()
    assert frame.loc[0, "pos_VERB"] == 2 and "voice_None" not in frame.columns
    assert stats.describe("pos") is None and stats.describe("pos_ADJ") is None


def test_explain_text(stats):
    assert stats.explain_text("pos", "tense")[2] == ("slept", {"pos": "VERB", "tense": "Past"})
    assert stats.explain_text("pos", "tense")[0] == ("The", {"pos": "DET", "tense": None})
    assert stats.explain_text("tense", filter_none=True)[:3] == (
        ("The", {}),
        ("cats", {}),
        ("slept", {"tense": "Past"}),
    )
    assert list(stats.explain_text()[0][1]) == list(MORPH_STATS_DESC)


@pytest.mark.parametrize("call", ["get_stats", "explain_text", "print_stats"])
def test_unknown_statistic(stats, call):
    with pytest.raises(UnknownStatError, match=r"^Unknown statistic: cases\."):
        getattr(stats, call)("pos", "cases")

    class Lemmas(MorphStats):
        @property
        def lemmas(self):
            return tuple(word.lower() for word in self.words)

    # A property is no statistic to count
    with pytest.raises(UnknownStatError, match=r"^Unknown statistic: lemmas\."):
        getattr(Lemmas(make_doc()), call)("lemmas")


def test_print_stats(capsys):
    doc = Doc(
        VOCAB,
        words=["who", "what", "that", "it"],
        pos=["PRON", "PRON", "PRON", "PRON"],
        morphs=["PronType=Int,Rel", "PronType=Int,Rel", "PronType=Odd", ""],
    )
    MorphStats(doc).print_stats("pron_type")
    assert capsys.readouterr().out.splitlines() == [
        "--------------Pronoun type--------------",
        f"{'Interrogative / Relative':30}|{'2':^10}",
        f"{'Odd':30}|{'1':^10}",
        f"{'Unknown':30}|{'1':^10}",
        "",
    ]
    MorphStats(doc).print_stats("pron_type", "pos", filter_none=True)
    lines = capsys.readouterr().out.splitlines()
    assert "Unknown" not in "".join(lines)
    assert lines[4:] == [
        "Part of speech".center(40, "-"),
        f"{'Pronoun':30}|{'4':^10}",
        "",
    ]


def test_markers(capsys, stats):
    assert stats.get_markers() == {}
    stats.print_markers()
    assert capsys.readouterr().out.splitlines() == [f"{'Marker':^7}|{'Value':^10}", "-" * 18]

    class Verbs(MorphStats):
        markers_desc: ClassVar = {"p_past": "Past among the tensed forms", "p_none": "None"}
        markers_headers = ("Form", "Share")

        def get_markers(self):
            tenses = [tense for tense in self.tense if tense]
            return {"p_past": tenses.count("Past") / len(tenses), "p_none": nan}

    Verbs(make_doc()).print_markers()
    # A marker of markers_desc that get_markers does not give
    with pytest.raises(
        SourceTypeError,
        match=r"^The get_markers of Verbs gives no values of the markers \['p_none'\]$",
    ):
        type("Verbs", (Verbs,), {"get_markers": lambda self: {"p_past": 0.5}})(
            make_doc()
        ).print_markers()
    assert capsys.readouterr().out.splitlines() == [
        f"{'Form':^28}|{'Share':^10}",
        "-" * 39,
        f"{'Past among the tensed forms':28}|{'0.50':^10}",
        f"{'None':28}|{'nan':^10}",
    ]


class Words(MorphStats):
    """A language whose analysis reads a string and knows the number of a word"""

    feature_names: ClassVar = {"number": "Number", "evident": "Evident"}
    stats_desc: ClassVar = {"pos": "Class", "number": "Number", "evident": "Evidentiality"}
    values_desc: ClassVar = {"number": {"Plur": "Many"}}
    unknown_value = "?"

    def analyze(self, source):
        return [
            MorphWord(word, "NOUN", {"Number": "Plur"} if word.endswith("s") else {})
            for word in source.split()
        ]


def test_a_library_subclass(capsys):
    stats = Words("cats sleep")
    assert stats.get_stats() == {
        "pos": {"NOUN": 2},
        "number": {"Plur": 1, None: 1},
        "evident": {None: 2},
    }
    assert stats.tags == ("Number=Plur", "_")
    stats.print_stats("number")
    assert capsys.readouterr().out.splitlines()[1:3] == [
        f"{'Many':30}|{'1':^10}",
        f"{'?':30}|{'1':^10}",
    ]
    assert pickle.loads(pickle.dumps(stats)).get_stats() == stats.get_stats()


def test_a_feature_without_value_is_none():
    class Empty(MorphStats):
        def analyze(self, source):
            return [MorphWord("cats", "", {"Number": "", "Case": "Nom"})]

    stats = Empty(None)
    assert (stats.number, stats.case, stats.pos, stats.tags) == (
        (None,),
        ("Nom",),
        (None,),
        ("Case=Nom",),
    )


@pytest.mark.parametrize(
    ("source", "error", "message"),
    [
        ("The cats", SourceTypeError, MESSAGES["source_type"].format(type="str")),
        (make_doc()[:2], SourceTypeError, MESSAGES["source_span"]),
        (make_doc(pos=False), SourceError, MESSAGES["no_pos"]),
        (Doc(VOCAB, words=[".", "!"], pos=["PUNCT", "PUNCT"]), SourceError, MESSAGES["no_words"]),
    ],
)
def test_source_errors(source, error, message):
    with pytest.raises(error, match=f"^{message}$".replace("(", r"\(").replace(")", r"\)")):
        MorphStats(source)


@pytest.mark.parametrize(
    "result",
    [
        ["cats"],
        None,
        MorphWord("cats", None, {}),
        [("cats", None, {})],
        # The features of spaCy are no mapping, its numbers of the parts of speech no strings
        [MorphWord("cats", "NOUN", Doc(VOCAB, words=["cats"], morphs=["Number=Plur"])[0].morph)],
        [MorphWord("cats", 92, {})],
        [MorphWord(5, "NOUN", {})],
        [MorphWord("cats", "NOUN", {"Number": ["Plur"]})],
    ],
)
def test_analyze_must_give_words(result):
    hooked = type("Hooked", (MorphStats,), {"analyze": lambda self, source: result})
    # A single word is a tuple of its fields, no list of words
    with pytest.raises(SourceTypeError, match=r"^The analyze of Hooked must return MorphWord"):
        hooked(None)


@pytest.mark.parametrize(
    ("attributes", "key"),
    [
        ({"feature_names": ["case"]}, "morph_features"),
        ({"feature_names": {"case": 5}}, "morph_features"),
        ({"feature_names": {5: "Case"}}, "morph_features"),
        ({"feature_names": {"pos": "Pos", "case": "Case"}}, "morph_features"),
        # A statistic would replace the words, the tags or a method of the class
        ({"feature_names": {"words": "Number"}}, "morph_features"),
        ({"feature_names": {"tags": "Number"}}, "morph_features"),
        ({"feature_names": {"get_markers": "Number"}}, "morph_features"),
        ({"feature_names": {"two words": "Number"}}, "morph_features"),
        ({"feature_names": {"case": ""}}, "morph_features"),
        ({"feature_names": {"case": "Case"}}, "morph_stats_desc"),
        ({"stats_desc": {**MORPH_STATS_DESC, "extra": "Extra"}}, "morph_stats_desc"),
        (
            {"stats_desc": {key: MORPH_STATS_DESC[key] for key in list(MORPH_STATS_DESC)[1:]}},
            "morph_stats_desc",
        ),
        ({"values_desc": [5]}, "morph_values_desc"),
        ({"values_desc": {"pos": ["Noun"]}}, "morph_values_desc"),
        ({"values_desc": {"pos": {"NOUN": 5}}}, "morph_values_desc"),
    ],
)
def test_hooks_checked_at_class_definition(attributes, key):
    message = MESSAGES[key].split("{cls}")[0]
    with pytest.raises(ParameterError, match=f"^{message}Bad "):
        type("Bad", (MorphStats,), attributes)


def test_stats_desc_in_another_order():
    names = {"number": "Number", "case": "Case"}
    stats_desc = {"case": "Case", "pos": "Part of speech", "number": "Number"}
    reordered = type(
        "Reordered", (MorphStats,), {"feature_names": names, "stats_desc": stats_desc}
    )
    assert list(reordered(make_doc()).get_stats()) == ["case", "pos", "number"]
    assert MORPH_VALUES_DESC["pos"]["NOUN"] == "Noun"
