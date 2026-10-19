import os
import random
import re
import subprocess
import sys
from fractions import Fraction
from itertools import combinations, pairwise
from math import isnan
from typing import ClassVar

import numpy as np
import pandas as pd
import pytest
import spacy
from spacy.tokens import Doc

from anyts.cohesion_stats import (
    CohesionStats,
    CohesionWord,
    Connector,
    ConnectorMatcher,
    Overlap,
    _count_sharing_pairs,
    _sum_dice,
    calc_overlap,
    calc_overlaps,
    calc_proportional_overlap,
    calc_repetition,
    count_given,
    dice,
    dominant,
)
from anyts.constants import COHESION_STATS_DESC, MESSAGES
from anyts.exceptions import ParameterError, SourceError, SourceTypeError
from anyts.extractors import SentsExtractor


@pytest.mark.parametrize(
    ("sets", "adjacent", "expected"),
    [
        ([{"a"}, {"a"}, {"b"}], True, 0.5),
        ([{"a"}, {"a"}, {"b"}], False, 1 / 3),
        ([{"a"}], True, None),
        ([{"a", "b"}, {"b", "c"}], True, 1.0),
    ],
)
def test_calc_overlap(sets, adjacent, expected):
    value = calc_overlap(sets, adjacent)
    assert isnan(value) if expected is None else value == pytest.approx(expected)


@pytest.mark.parametrize(
    ("sets", "adjacent", "expected"),
    [
        ([{"a", "b"}, {"b", "c"}], True, 0.5),
        ([{"a"}, {"a"}, {"b"}], False, 1 / 3),
        ([{"a"}], False, None),
        ([set(), set()], True, 0.0),
    ],
)
def test_calc_proportional_overlap(sets, adjacent, expected):
    value = calc_proportional_overlap(sets, adjacent)
    assert isnan(value) if expected is None else value == pytest.approx(expected)


@pytest.mark.parametrize(
    ("first", "second", "expected"),
    [
        ({"a", "b"}, {"b", "c"}, 0.5),
        ({"a"}, {"a"}, 1.0),
        ({"a"}, {"b"}, 0.0),
        (set(), set(), 0.0),
    ],
)
def test_dice(first, second, expected):
    assert dice(frozenset(first), frozenset(second)) == pytest.approx(expected)


def test_calc_overlaps_matches_the_direct_computation():
    rng = random.Random(17)
    sets = [frozenset(str(rng.randrange(12)) for _ in range(rng.randrange(5))) for _ in range(40)]
    adjacent = list(pairwise(sets))
    all_pairs = list(combinations(sets, 2))
    shared = [sum(1 for a, b in pairs if a & b) / len(pairs) for pairs in (adjacent, all_pairs)]
    dices = [
        sum(Fraction(2 * len(a & b), len(a) + len(b)) if a or b else 0 for a, b in pairs)
        / len(pairs)
        for pairs in (adjacent, all_pairs)
    ]
    overlap = calc_overlaps(sets)
    assert isinstance(overlap, Overlap)
    assert overlap.adjacent == calc_overlap(sets) == pytest.approx(shared[0])
    assert overlap.all == calc_overlap(sets, adjacent=False) == pytest.approx(shared[1])
    assert overlap.prop_adjacent == calc_proportional_overlap(sets)
    assert overlap.prop_adjacent == pytest.approx(float(dices[0]), rel=1e-15)
    assert overlap.prop_all == calc_proportional_overlap(sets, adjacent=False)
    assert overlap.prop_all == pytest.approx(float(dices[1]), rel=1e-15)


def test_sum_dice_exact():
    rng = random.Random(3)
    sets = [
        frozenset(f"w{rng.randrange(30)}" for _ in range(rng.randrange(1, 12))) for _ in range(60)
    ]
    exact = sum(
        (Fraction(2 * len(first & second), len(first) + len(second)))
        for first, second in combinations(sets, 2)
    )
    assert _sum_dice(sets) == pytest.approx(float(exact), rel=1e-15)


def test_sum_dice_does_not_depend_on_the_hash_seed():
    code = (
        "import random\n"
        "from anyts.cohesion_stats import _sum_dice\n"
        "rng = random.Random(5)\n"
        "sets = [frozenset(f'w{rng.randrange(400)}' for _ in range(rng.randrange(1, 25)))"
        " for _ in range(300)]\n"
        "print(repr(_sum_dice(sets)))\n"
    )
    values = {
        subprocess.run(
            [sys.executable, "-c", code],
            env={**os.environ, "PYTHONHASHSEED": seed},
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        for seed in ("0", "1", "2", "3")
    }
    assert len(values) == 1


def test_calc_overlaps_without_the_proportional_half():
    sets = [{"a", "b"}, {"b", "c"}, {"d"}]
    overlap = calc_overlaps(sets, proportional=False)
    assert overlap.adjacent == calc_overlaps(sets).adjacent
    assert overlap.all == calc_overlaps(sets).all
    assert isnan(overlap.prop_adjacent)
    assert isnan(overlap.prop_all)


def test_calc_overlaps_of_a_single_sentence():
    assert all(isnan(value) for value in calc_overlaps([{"a"}]))


def test_count_sharing_pairs_in_blocks():
    sets = [frozenset({"a"}), frozenset({"a"}), frozenset({"b"}), frozenset({"a", "b"})]
    assert _count_sharing_pairs(sets) == _count_sharing_pairs(sets, block_size=2) == 4


def test_sum_dice_without_shared_elements():
    assert _sum_dice([frozenset({"a"}), frozenset({"b"}), frozenset()]) == 0


def test_count_given():
    assert count_given([["a", "b"], ["b", "c"], ["a"]]) == 2
    assert count_given([["a", "a", "a"]]) == 2
    assert count_given([]) == 0


@pytest.mark.parametrize(
    ("values", "expected"),
    [(["a", "b", "a"], "a"), (["a", "b"], "a"), ([], None)],
)
def test_dominant(values, expected):
    assert dominant(values) == expected
    assert dominant(pd.Series(values)) == expected


def test_dominant_of_an_array():
    assert dominant(np.array(["a", "b", "b"])) == "b"
    assert dominant(np.array([], dtype=str)) is None


@pytest.mark.parametrize(
    ("sents", "expected"),
    [
        ([["Pres"], ["Pres"], ["Past"]], 0.5),
        ([["Pres"], [], ["Pres"]], None),
        ([["Pres", "Past", "Past"], ["Past"]], 1.0),
        ([[], []], None),
    ],
)
def test_calc_repetition(sents, expected):
    value = calc_repetition(sents)
    assert isnan(value) if expected is None else value == pytest.approx(expected)


@pytest.mark.parametrize(
    "func",
    [calc_overlap, calc_proportional_overlap, calc_overlaps, count_given, calc_repetition],
)
def test_sentences_checked(func):
    with pytest.raises(SourceTypeError, match=r"^A list of sentences is expected, not a string$"):
        func("the cat sleeps")
    with pytest.raises(SourceTypeError, match=r"not an iterator$"):
        func(iter([["a"], ["b"]]))
    with pytest.raises(SourceTypeError, match=r"^A list of \w+ of a sentence is expected"):
        func(["the cat", "the dog"])
    doc = spacy.blank("xx")("the cat and the cat")
    tokens = [list(doc[:2]), list(doc[3:])]
    with pytest.raises(
        SourceTypeError, match=r"^The \w+ of a sentence must be strings, not Token$"
    ):
        func(tokens)
    doc = spacy.blank("xx")("The cat. The dog.")
    with pytest.raises(SourceTypeError, match=r"not a Doc"):
        func(doc)
    with pytest.raises(SourceTypeError, match=r"^A list of sentences is expected, not set$"):
        func({frozenset({"a"}), frozenset({"b"})})


@pytest.mark.parametrize("func", [count_given, calc_repetition])
def test_ordered_sentences_checked(func):
    with pytest.raises(SourceTypeError, match=r"of a sentence is expected, not set$"):
        func([{"a", "b"}, {"b"}])


def test_dominant_checked():
    with pytest.raises(SourceTypeError, match=r"^A list of values is expected, not a string$"):
        dominant("Pres")
    with pytest.raises(SourceTypeError, match=r"^A list of values is expected, not set$"):
        dominant({"Pres", "Past"})
    with pytest.raises(SourceTypeError, match=r"^The values must be strings, not Token$"):
        dominant(list(spacy.blank("xx")("Pres Pres")))


CONNECTORS = {
    "and": ("additive", "primary"),
    "because": ("causal", "primary"),
    "before": ("temporal", "primary"),
    "after": ("temporal", "primary"),
    "so": ("causal", "primary"),
    "well": ("reformulative", "primary"),
    "still": ("concessive", "primary"),
    "however": ("adversative", "secondary"),
    "above all": ("additive", "secondary"),
    "as well as": ("additive", "secondary"),
    "on the other hand": ("adversative", "secondary"),
    "in addition": ("additive", "secondary"),
    "e.g.": ("reformulative", "secondary"),
    "Summing up": ("reformulative", "secondary"),
    "summing": ("reformulative", "secondary"),
}


class Matcher(ConnectorMatcher):
    """The context rules of a language, here on English words"""

    pos_tags = frozenset({*ConnectorMatcher.pos_tags, "PROPN"})
    pos_extra: ClassVar = {"summing": frozenset({"VERB"})}
    not_after_pos = frozenset({"DET"})
    start_only_pos = frozenset({"PROPN"})
    blocked_after: ClassVar = {"before": frozenset({"the", "a"}), "after": frozenset({"the"})}
    blocked_before: ClassVar = {"as well as": frozenset({"something"})}
    blocked_after_pos: ClassVar = {"above all": frozenset({"DET"})}
    not_at_start = frozenset({"well"})
    only_after: ClassVar = {"still": frozenset({"and", "but"})}


@pytest.fixture(scope="module")
def matcher():
    return Matcher(CONNECTORS)


def texts(found):
    return [connector.text for connector in found]


def test_find_longest_without_overlaps():
    found = ConnectorMatcher(CONNECTORS).find(
        ["On", "the", "other", "hand", "and", "in", "addition"]
    )
    assert found == [
        Connector(0, 0, 4, "on the other hand", "adversative", "secondary"),
        Connector(0, 4, 5, "and", "additive", "primary"),
        Connector(0, 5, 7, "in addition", "additive", "secondary"),
    ]


def test_find_by_the_normalized_forms():
    matcher = ConnectorMatcher(CONNECTORS)
    assert texts(matcher.find(["HOWEVER", "Summing", "UP"])) == ["however", "Summing up"]
    assert texts(matcher.find(["e", "g", "water"])) == ["e.g."]
    assert texts(matcher.find(["e.g.", "water"])) == ["e.g."]
    assert matcher.find(["and"], sent_index=3)[0].sent == 3

    class Apostrophes(ConnectorMatcher):
        def normalize(self, text):
            return text.lower().replace("’", "'")

    assert texts(Apostrophes({"don't": ("adversative", "primary")}).find(["Don’t"])) == ["don't"]


def test_rules_are_empty_by_default():
    words = ["Well", "before", "the", "end", "and", "still"]
    pos = ["PROPN", "ADV", "DET", "NOUN", "CCONJ", "ADV"]
    assert texts(ConnectorMatcher(CONNECTORS).find(words)) == ["well", "before", "and", "still"]
    assert texts(ConnectorMatcher(CONNECTORS).find(words, pos=pos)) == ["before", "and", "still"]


@pytest.mark.parametrize(
    ("text", "found"),
    [
        ("He left before the end", []),
        ("He left before noon", ["before"]),
        ("Before he left", ["before"]),
        ("After the rain", []),
        ("something as well as cats", ["well"]),
        ("As well as cats", ["as well as"]),
        ("Well he left", []),
        ("He did well", ["well"]),
        ("And still it rains", ["and", "still"]),
        ("Still it rains", ["still"]),
        ("It still rains", []),
    ],
)
def test_context_rules(matcher, text, found):
    assert texts(matcher.find(text.split())) == found


def test_rules_of_the_parts_of_speech(matcher):
    words = ["The", "before", "and", "the", "after"]
    assert texts(matcher.find(words, pos=["DET", "ADV", "CCONJ", "DET", "ADV"])) == ["and"]
    assert texts(matcher.find(words)) == ["before", "and", "after"]
    assert texts(matcher.find(["So", "he", "left"], pos=["PROPN", "PRON", "VERB"])) == ["so"]
    assert matcher.find(["Ann", "So", "left"], pos=["PROPN", "PROPN", "VERB"]) == []
    assert texts(matcher.find(["summing"], pos=["VERB"])) == ["summing"]
    assert matcher.find(["and"], pos=["VERB"]) == []
    assert texts(matcher.find(["and"], pos=[None])) == ["and"]
    words = ["above", "all", "the", "text"]
    assert matcher.find(words, pos=["ADV", "ADV", "DET", "NOUN"]) == []
    assert texts(matcher.find(words)) == ["above all"]
    assert texts(matcher.find(["above", "all"], pos=["ADV", "ADV"])) == ["above all"]


def test_a_connector_of_punctuation():
    assert ConnectorMatcher({".": ("additive", "primary")}).find(["and", "so"]) == []


@pytest.mark.parametrize(
    ("connectors", "error", "message"),
    [
        (["and"], SourceTypeError, "must be a dictionary"),
        ({"and": "additive"}, SourceTypeError, "a pair of its class and kind: 'and'"),
        ({"and": ("additive",)}, SourceTypeError, "a pair of its class and kind"),
        ({1: ("additive", "primary")}, SourceTypeError, "a pair of its class and kind"),
        ({"and": ("additive", 1)}, SourceTypeError, "a pair of its class and kind"),
        ({"and": ("other", "primary")}, ParameterError, "Unknown class or kind"),
        ({"and": ("additive", "other")}, ParameterError, "Unknown class or kind"),
    ],
)
def test_matcher_errors(connectors, error, message):
    with pytest.raises(error, match=message):
        ConnectorMatcher(connectors)


def test_find_errors(matcher):
    with pytest.raises(SourceTypeError):
        matcher.find("and so")
    with pytest.raises(SourceTypeError):
        matcher.find(["and"], pos="CCONJ")
    with pytest.raises(ParameterError, match="as many as the words"):
        matcher.find(["and", "so"], pos=["CCONJ"])
    with pytest.raises(ParameterError, match="number of the sentence"):
        matcher.find(["The", "before"], ["DET", "ADV"])
    for sent_index in (None, "3", 1.5):
        with pytest.raises(ParameterError, match="number of the sentence"):
            matcher.find(["and"], sent_index)


@pytest.mark.parametrize("tag", [89, spacy.blank("en")("and")[0]], ids=["number", "token"])
def test_find_parts_of_speech_of_another_type(matcher, tag):
    with pytest.raises(SourceTypeError, match="must be a string or None, not"):
        matcher.find(["and"], pos=[tag])


def test_own_classes_and_messages():
    class Own(ConnectorMatcher):
        classes = ("contrast",)
        kinds = ("single",)
        messages: ClassVar = {**MESSAGES, "connector_class": "Own: {cls} {kind}"}

    assert Own({"but": ("contrast", "single")}).find(["but"])[0].cls == "contrast"
    with pytest.raises(ParameterError, match=r"^Own: additive primary$"):
        Own({"and": ("additive", "primary")})
    with pytest.raises(ParameterError, match="lack the keys"):

        class Incomplete(ConnectorMatcher):
            messages: ClassVar = {"connector_pos": "No"}


def test_matcher_does_not_depend_on_the_hash_seed():
    code = (
        "from anyts.cohesion_stats import ConnectorMatcher\n"
        "m = ConnectorMatcher({'so': ('causal', 'primary'), 'so that': ('causal', 'secondary'),"
        " 'so-so': ('additive', 'primary'), 'so far': ('temporal', 'secondary')})\n"
        "print(m._by_first)"
    )
    outputs = {
        subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            check=True,
            text=True,
            env={**os.environ, "PYTHONHASHSEED": seed},
        ).stdout
        for seed in ("0", "1", "2")
    }
    assert len(outputs) == 1


# The cat sat on the mat. It saw this bird. However, the bird and the cat slept.
CAT_TEXT = [
    ("The", "DET", "the", "PronType=Art", True),
    ("cat", "NOUN", "cat", "", True),
    ("sat", "VERB", "sit", "Aspect=Perf|Mood=Ind|Tense=Past", True),
    ("on", "ADP", "on", "", True),
    ("the", "DET", "the", "PronType=Art", True),
    ("mat", "NOUN", "mat", "", False),
    (".", "PUNCT", ".", "", True),
    ("It", "PRON", "it", "PronType=Prs", True),
    ("saw", "VERB", "see", "Aspect=Perf|Mood=Ind|Tense=Past", True),
    ("this", "DET", "this", "PronType=Dem", True),
    ("bird", "NOUN", "bird", "", False),
    (".", "PUNCT", ".", "", True),
    ("However", "ADV", "however", "", False),
    (",", "PUNCT", ",", "", True),
    ("the", "DET", "the", "PronType=Art", True),
    ("bird", "NOUN", "bird", "", True),
    ("and", "CCONJ", "and", "", True),
    ("the", "DET", "the", "PronType=Art", True),
    ("cat", "NOUN", "cat", "", True),
    ("slept", "VERB", "sleep", "Aspect=Imp|Mood=Ind|Tense=Past", False),
    (".", "PUNCT", ".", "", False),
]
CAT_STARTS = {0, 7, 12}
VOCAB = spacy.blank("en").vocab
TEXT_CONNECTORS = {"however": ("adversative", "secondary"), "and": ("additive", "primary")}


def text_doc(starts=CAT_STARTS, lemmas=True, pos=True):
    words, tags, lemma_list, morphs, spaces = (
        list(column) for column in zip(*CAT_TEXT, strict=True)
    )
    return Doc(
        VOCAB,
        words=words,
        spaces=spaces,
        pos=tags if pos else None,
        lemmas=lemma_list if lemmas else None,
        morphs=morphs,
        sent_starts=[i in starts for i in range(len(words))] if starts is not None else None,
    )


class English(CohesionStats):
    @classmethod
    def load_connectors(cls):
        return TEXT_CONNECTORS


def test_cohesion_stats_counts():
    stats = CohesionStats(text_doc())
    assert stats.words == (
        ("The", "cat", "sat", "on", "the", "mat"),
        ("It", "saw", "this", "bird"),
        ("However", "the", "bird", "and", "the", "cat", "slept"),
    )
    assert stats.lemmas[2] == ("however", "the", "bird", "and", "the", "cat", "sleep")
    assert (stats.n_sents, stats.n_words, stats.n_nouns) == (3, 17, 5)
    # It and this are pronouns, this a demonstrative; the article is neither
    assert (stats.n_pronouns, stats.n_demonstratives) == (2, 1)
    # cat, sit, mat | see, bird | however, bird, cat, sleep: bird and cat are given
    assert (stats.n_content_words, stats.n_given) == (9, 2)
    assert stats.n_connectors == 0 and stats.connector_spans == () and stats.c_connectors == {}
    assert stats.n_inter_connectors == 0


def test_cohesion_stats_metrics():
    stats = CohesionStats(text_doc())
    values = stats.get_stats()
    assert list(values) == list(COHESION_STATS_DESC)
    # The nouns and the arguments share bird in the last pair, cat in the first and the last
    for name in ("noun", "argument", "content"):
        assert values[f"{name}_overlap_adjacent"] == 0.5
        assert values[f"{name}_overlap_all"] == 2 / 3
    assert values["content_overlap_prop_adjacent"] == pytest.approx((0 + 2 / 6) / 2)
    assert values["content_overlap_prop_all"] == pytest.approx((0 + 2 / 7 + 2 / 6) / 3)
    assert values["p_pronouns"] == 2 / 17 and values["p_demonstratives"] == 1 / 17
    assert values["pronoun_noun_ratio"] == 2 / 5 and values["p_given"] == 2 / 9
    # The tense repeats in both pairs, the aspect in the first only
    assert (values["tense_repetition"], values["aspect_repetition"]) == (1.0, 0.5)
    assert values["temporal_cohesion"] == 0.75
    assert stats.mood_repetition == 1.0
    assert all(values[name] == 0 for name in values if name.startswith("connectors"))


def test_connectors():
    stats = English(text_doc())
    assert stats.connector_spans == (
        Connector(2, 0, 1, "however", "adversative", "secondary"),
        Connector(2, 3, 4, "and", "additive", "primary"),
    )
    assert stats.c_connectors == {"and": 1, "however": 1}
    per_1000 = 1000 / 17
    assert stats.connectors == 2 * per_1000
    # However opens its sentence and links it to the ones before; and is inside
    assert stats.n_inter_connectors == 1
    assert stats.connectors_inter == stats.connectors_intra == per_1000
    assert stats.connectors_adversative == stats.connectors_additive == per_1000
    assert stats.connectors_primary == stats.connectors_secondary == per_1000
    assert stats.connectors_causal == 0
    # A dictionary given replaces that of the class
    assert CohesionStats(text_doc(), connectors={"and": ("additive", "primary")}).n_connectors == 1
    assert English(text_doc(), connectors={}).n_connectors == 0


def test_connectors_read_once_for_a_class():
    calls = []

    class Counted(CohesionStats):
        @classmethod
        def load_connectors(cls):
            calls.append(cls)
            return TEXT_CONNECTORS

    Counted(text_doc())
    Counted(text_doc())
    assert calls == [Counted]
    assert Counted.connector_matcher() is Counted.connector_matcher()
    assert calls == [Counted]

    class Own(ConnectorMatcher):
        pass

    class Child(Counted):
        connector_matcher_class = Own

    # A subclass builds its own matcher, of its own class
    assert type(Child.connector_matcher()) is Own
    assert type(Counted.connector_matcher()) is ConnectorMatcher
    assert calls == [Counted, Child]


def test_a_subordinating_conjunction_opening_a_sentence_is_intra_sentential():
    class Subordinating(CohesionStats):
        @classmethod
        def load_connectors(cls):
            return {"when": ("temporal", "primary"), "however": ("adversative", "secondary")}

    # When it saw this bird however : the clause of when belongs to its sentence
    doc = Doc(
        VOCAB,
        words=["When", "it", "saw", "this", "bird", "However", "it", "slept"],
        pos=["SCONJ", "PRON", "VERB", "DET", "NOUN", "ADV", "PRON", "VERB"],
        lemmas=["when", "it", "see", "this", "bird", "however", "it", "sleep"],
        sent_starts=[True, False, False, False, False, True, False, False],
    )
    stats = Subordinating(doc)
    assert [connector.start for connector in stats.connector_spans] == [0, 0]
    assert stats.n_inter_connectors == 1
    assert stats.connectors_inter == stats.connectors_intra == 1000 / 8


def test_densities_by_the_classes_of_the_matcher():
    class Contrast(ConnectorMatcher):
        classes = ("contrast",)
        kinds = ("single",)

    class Own(CohesionStats):
        connector_matcher_class = Contrast

        @classmethod
        def load_connectors(cls):
            return {"however": ("contrast", "single")}

    stats = Own(text_doc())
    assert stats.connectors == stats.connectors_contrast == stats.connectors_single == 1000 / 17
    assert not hasattr(stats, "connectors_causal")


def test_temporal_features():
    class Mood(CohesionStats):
        temporal_features = ("tense", "mood")

    assert Mood(text_doc()).temporal_cohesion == 1.0


@pytest.mark.parametrize(
    "features",
    [("tense", "voice"), (), ("tense", "tense", "aspect"), "tense", ["tense"], (["tense"],)],
)
def test_temporal_features_must_be_distinct_known_ones(features):
    with pytest.raises(ParameterError, match=r"^The temporal features of Bad must be one or more"):
        type("Bad", (CohesionStats,), {"temporal_features": features})


def test_sentences_by_an_extractor():
    # Without boundaries the Doc is split by the default extractor over its text
    assert CohesionStats(text_doc(starts=None)).n_sents == 3

    class Halves(SentsExtractor):
        def sentenize(self, text):
            return [text[:23], text[24:]]

    stats = CohesionStats(text_doc(), sents_extractor=Halves())
    assert stats.words == (
        ("The", "cat", "sat", "on", "the", "mat"),
        ("It", "saw", "this", "bird", "However", "the", "bird", "and", "the", "cat", "slept"),
    )


def test_default_word_info():
    doc = Doc(
        VOCAB,
        words=["My", "well", "-", "known", "Ann"],
        spaces=[True, False, False, True, False],
        pos=["DET", "ADJ", "PUNCT", "ADJ", "PROPN"],
        lemmas=["my", "well", "-", "know", "Ann"],
        morphs=["Poss=Yes", "Degree=Pos", "", "", ""],
        sent_starts=[True, False, False, False, False],
    )

    class Hyphens(CohesionStats):
        join_hyphens = True

    stats = CohesionStats(doc)
    assert stats.n_words == 4 and stats.n_pronouns == 1
    word = Hyphens(doc).analyze(doc)[0][1]
    assert word == CohesionWord(
        "well-known", "well-known", "ADJ", False, False, False, False, True
    )
    assert stats.lemmas == (("my", "well", "know", "ann"),)


def test_own_analysis():
    class Words(CohesionStats):
        def analyze(self, source):
            return [
                [
                    CohesionWord(word, word.lower(), None, True, False, False, True, True)
                    for word in sent.split()
                ]
                for sent in source.split(". ")
            ] + [[]]

    stats = Words("Cats sleep. Cats eat")
    assert stats.words == (("Cats", "sleep"), ("Cats", "eat"))
    assert stats.noun_overlap_adjacent == 1.0
    assert isnan(stats.tense_repetition) and isnan(stats.temporal_cohesion)


@pytest.mark.parametrize(
    ("source", "kwargs", "error", "message"),
    [
        ("The cat", {}, SourceTypeError, MESSAGES["source_type"]),
        (None, {"sents_extractor": "x"}, SourceTypeError, MESSAGES["sents_extractor_type"]),
        (text_doc(pos=False), {}, SourceError, MESSAGES["no_pos"]),
        (text_doc(lemmas=False), {}, SourceError, MESSAGES["no_lemmas"]),
        (
            Doc(VOCAB, words=[".", "!"], pos=["PUNCT", "PUNCT"], lemmas=[".", "!"]),
            {},
            SourceError,
            MESSAGES["no_words"],
        ),
    ],
)
def test_cohesion_stats_errors(source, kwargs, error, message):
    with pytest.raises(error, match=f"^{re.escape(message)}$"):
        CohesionStats(text_doc() if source is None else source, **kwargs)


@pytest.mark.parametrize(
    ("attributes", "message"),
    [
        ({"blocked_after": {"on": "top"}}, r"^A list of blocked_after is expected, not a string$"),
        ({"pos_tags": "ADV"}, r"^A list of pos_tags is expected, not a string$"),
        (
            {"only_after": [("so", {"and"})]},
            r"^The only_after of Ruled must be a mapping, not list$",
        ),
        ({"classes": {"causal"}}, r"^A list of classes is expected, not set$"),
    ],
)
def test_rules_of_a_matcher_checked_at_class_definition(attributes, message):
    with pytest.raises(SourceTypeError, match=message):
        type("Ruled", (ConnectorMatcher,), attributes)


def test_sentences_of_analyze_as_iterators():
    class Lazy(CohesionStats):
        def analyze(self, source):
            return ((word for word in sent) for sent in super().analyze(source))

    assert Lazy(text_doc()).get_stats() == CohesionStats(text_doc()).get_stats()
