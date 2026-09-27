import pytest
import spacy
from spacy.tokens import Doc

from anyts.syntax import (
    base_dep,
    calc_coordination_chains,
    calc_dependency_distances,
    calc_tree_depth,
    calc_valency,
    count_children,
    get_children,
    get_words,
    has_feature,
    is_root,
    is_word,
    subtree_len,
)

VOCAB = spacy.blank("xx").vocab


def parse(words, heads, deps, morphs=None, spaces=None):
    """A Doc with a hand-made dependency tree: heads are the indices of the head tokens"""
    return Doc(
        VOCAB,
        words=words,
        spaces=spaces or [True] * len(words),
        heads=heads,
        deps=deps,
        morphs=morphs,
    )


@pytest.fixture
def house():
    # The white house , by the way , is nice %
    return parse(
        ["The", "white", "house", ",", "is", "nice", "%"],
        [2, 2, 5, 2, 5, 5, 5],
        ["det", "amod", "nsubj", "punct", "cop", "ROOT", "punct"],
    )


def test_is_word(house):
    assert [token.text for token in house if is_word(token)] == [
        "The",
        "white",
        "house",
        "is",
        "nice",
    ]
    assert [token.text for token in get_words(house)] == ["The", "white", "house", "is", "nice"]


def test_invisible_characters_are_not_words():
    doc = parse(["one", "​", "two"], [2, 2, 2], ["dep", "dep", "ROOT"])
    assert [token.text for token in get_words(doc)] == ["one", "two"]


def test_is_root(house):
    assert [token.text for token in house if is_root(token)] == ["nice"]


def test_base_dep():
    doc = parse(["It", "was", "built"], [2, 2, 2], ["nsubj:pass", "aux:pass", "ROOT"])
    assert [base_dep(token) for token in doc] == ["nsubj", "aux", "ROOT"]


def test_children_and_subtree(house):
    noun = house[2]
    assert [child.text for child in get_children(noun)] == ["The", "white"]
    assert count_children(noun) == 2
    assert subtree_len(noun) == 3
    assert subtree_len(house[5]) == 5


def test_dependency_distances(house):
    # Positions of the words: The 0, white 1, house 2, is 3, nice 4
    assert calc_dependency_distances(house) == [2, 1, 2, 1]
    assert calc_dependency_distances(house[4:]) == [1]
    assert calc_dependency_distances(parse(["Hello"], [0], ["ROOT"])) == []


def test_tree_depth(house):
    assert calc_tree_depth(house) == 2
    assert calc_tree_depth(house[4:6]) == 1
    assert calc_tree_depth(parse(["Hello"], [0], ["ROOT"])) == 0
    assert calc_tree_depth(parse(["!"], [0], ["ROOT"])) == 0


def test_has_feature():
    doc = parse(
        ["Children", "play"],
        [1, 1],
        ["nsubj", "ROOT"],
        morphs=["Number=Plur", "Mood=Ind|VerbForm=Fin"],
    )
    assert has_feature(doc[1], "VerbForm", "Fin")
    assert not has_feature(doc[1], "VerbForm", "Inf")
    assert not has_feature(doc[0], "Mood", "Ind")


def test_valency():
    # The director made a review and signed
    doc = parse(
        ["The", "director", "made", "a", "review", "and", "signed", "."],
        [1, 2, 2, 4, 2, 6, 2, 2],
        ["det", "nsubj", "ROOT", "det", "obj", "cc", "conj", "punct"],
    )
    assert calc_valency(doc[2]) == 2
    assert count_children(doc[2]) == 3


# apples , pears and plums
COORDINATION = ["apples", ",", "pears", "and", "plums"]


@pytest.mark.parametrize(
    ("heads", "expected"),
    [
        # Universal Dependencies: every conjunct hangs on the first one
        ([0, 2, 0, 4, 0], [3]),
        # ClearNLP: every conjunct hangs on the previous one
        ([0, 2, 0, 4, 2], [3]),
    ],
    ids=["ud", "clearnlp"],
)
def test_coordination_chains_schemes(heads, expected):
    doc = parse(COORDINATION, heads, ["ROOT", "punct", "conj", "cc", "conj"])
    assert calc_coordination_chains(doc) == expected


def test_coordination_chains_nested():
    # cats and dogs , or birds: the nested coordination is one chain of three
    doc = parse(
        ["cats", "and", "dogs", ",", "or", "birds"],
        [0, 2, 0, 5, 5, 2],
        ["ROOT", "cc", "conj", "punct", "cc", "conj"],
    )
    assert calc_coordination_chains(doc) == [3]


def test_coordination_chains_order_and_span():
    # red , green and blue cars , fast and slow trains
    doc = parse(
        ["red", ",", "green", "and", "blue", "cars", ",", "fast", "and", "slow", "trains"],
        [5, 2, 0, 4, 0, 5, 10, 10, 9, 7, 5],
        ["amod", "punct", "conj", "cc", "conj", "ROOT", "punct", "amod", "cc", "conj", "conj"],
    )
    assert calc_coordination_chains(doc) == [3, 2, 2]
    # The head of blue lies outside the span, so blue is in no chain
    assert calc_coordination_chains(doc[4:]) == [2, 2]
    assert calc_coordination_chains(doc[:5]) == [3]


def test_coordination_chains_none(house):
    assert calc_coordination_chains(house) == []
    # A conjunct hanging on punctuation starts no chain
    doc = parse(["a", ",", "b"], [0, 0, 1], ["ROOT", "punct", "conj"])
    assert calc_coordination_chains(doc) == []
