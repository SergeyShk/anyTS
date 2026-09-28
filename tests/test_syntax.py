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
    joins_previous,
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


def hyphenated(one_head=3):
    # Some-one came with a well-known cat . - the parser hangs both parts of Some-one on the verb
    return parse(
        ["Some", "-", "one", "came", "with", "a", "well", "-", "known", "cat", "."],
        [3, 0, one_head, 3, 9, 9, 9, 6, 9, 3, 3],
        [
            "nsubj",
            "punct",
            "nsubj",
            "ROOT",
            "case",
            "det",
            "amod",
            "punct",
            "amod",
            "obl",
            "punct",
        ],
        spaces=[False, False, True, True, True, True, False, False, True, False, False],
    )


def texts(tokens):
    return [token.text for token in tokens]


def test_joins_previous():
    doc = hyphenated()
    assert [token.text for token in doc if joins_previous(token)] == ["one", "known"]
    spaced = parse(["Some", "-", "one"], [0, 0, 0], ["ROOT", "punct", "dep"])
    assert not joins_previous(spaced[2])
    assert not joins_previous(spaced[0])


def test_words_of_hyphenated_words():
    doc = hyphenated()
    assert texts(get_words(doc)) == ["Some", "one", "came", "with", "a", "well", "known", "cat"]
    assert texts(get_words(doc, join_hyphens=True)) == ["Some", "came", "with", "a", "well", "cat"]
    # A part whose first part lies outside the sequence is a word of its own
    assert texts(get_words(doc[2:5], join_hyphens=True)) == ["one", "came", "with"]


def test_children_of_hyphenated_words():
    doc = hyphenated()
    assert (calc_valency(doc[3]), calc_valency(doc[3], join_hyphens=True)) == (3, 2)
    assert texts(get_children(doc[3], join_hyphens=True)) == ["Some", "cat"]
    assert (count_children(doc[9]), count_children(doc[9], join_hyphens=True)) == (4, 3)
    # Every part of a word gives the dependents of the whole word
    assert get_children(doc[6], join_hyphens=True) == get_children(doc[8], join_hyphens=True) == []
    # The second part hanging on the first one is no dependent of either
    nested = hyphenated(one_head=0)
    assert texts(get_children(nested[3], join_hyphens=True)) == ["Some", "cat"]
    assert get_children(nested[0], join_hyphens=True) == []
    assert texts(get_children(nested[0])) == ["one"]


def test_subtree_of_hyphenated_words():
    doc = hyphenated()
    assert (subtree_len(doc[3]), subtree_len(doc[3], join_hyphens=True)) == (8, 6)
    assert (subtree_len(doc[9]), subtree_len(doc[9], join_hyphens=True)) == (5, 4)


def test_dependency_distances_of_hyphenated_words():
    doc = hyphenated()
    assert calc_dependency_distances(doc) == [2, 1, 4, 3, 2, 1, 5]
    assert calc_dependency_distances(doc, join_hyphens=True) == [1, 3, 2, 1, 4]
    assert calc_dependency_distances(hyphenated(one_head=0), join_hyphens=True) == [1, 3, 2, 1, 4]


def test_first_part_hanging_on_a_later_one():
    # She said : n-no . - "n" hangs on "no", which carries the relation to the verb
    doc = parse(
        ["She", "said", ":", "n", "-", "no", "."],
        [1, 1, 1, 5, 5, 1, 1],
        ["nsubj", "ROOT", "punct", "reparandum", "punct", "ccomp", "punct"],
        spaces=[True, False, True, False, False, False, False],
    )
    assert texts(get_children(doc[1], join_hyphens=True)) == ["She", "no"]
    assert calc_valency(doc[1], join_hyphens=True) == 2
    assert calc_dependency_distances(doc, join_hyphens=True) == [1, 1]


def test_word_holding_the_root():
    # He came-to home . - the word with the head of the sentence has no dependency
    doc = parse(
        ["He", "came", "-", "to", "home", "."],
        [1, 1, 1, 1, 1, 1],
        ["nsubj", "ROOT", "punct", "advmod", "obl", "punct"],
        spaces=[True, False, False, True, False, False],
    )
    assert calc_dependency_distances(doc) == [1, 1, 2]
    assert calc_dependency_distances(doc, join_hyphens=True) == [1, 1]
    assert texts(get_children(doc[3], join_hyphens=True)) == ["He", "home"]
    # "to" hangs on "home" but belongs to the word with the root, not to the subtree of "home"
    moved = parse(
        ["He", "came", "-", "to", "home", "."],
        [1, 1, 4, 4, 1, 1],
        ["nsubj", "ROOT", "punct", "advmod", "obl", "punct"],
        spaces=[True, False, False, True, False, False],
    )
    assert get_children(moved[4], join_hyphens=True) == []
    assert (subtree_len(moved[4]), subtree_len(moved[4], join_hyphens=True)) == (2, 1)
    assert subtree_len(moved[1], join_hyphens=True) == 3


def test_word_hanging_by_its_hyphen():
    # On clothes not re-ca-ll . - the parser hangs the parts and a hyphen on the noun
    doc = parse(
        ["On", "clothes", "not", "re", "-", "ca", "-", "ll", "."],
        [1, 1, 4, 4, 1, 1, 1, 1, 1],
        ["case", "ROOT", "advmod", "case", "nmod", "nmod", "nmod", "nmod", "punct"],
        spaces=[True, True, True, False, False, False, False, False, False],
    )
    # The part that is a word is the head rather than the hyphen
    assert texts(get_children(doc[1], join_hyphens=True)) == ["On", "ca"]
    assert texts(get_children(doc[3], join_hyphens=True)) == ["not"]
    assert calc_dependency_distances(doc, join_hyphens=True) == [1, 1, 2]
    # A word that hangs by a hyphen alone is given by its first part
    alone = parse(
        ["On", "clothes", "re", "-", "call", "."],
        [1, 1, 3, 1, 3, 1],
        ["case", "ROOT", "case", "nmod", "fixed", "punct"],
        spaces=[True, True, False, False, False, False],
    )
    assert texts(get_children(alone[1], join_hyphens=True)) == ["On", "re"]
    assert calc_dependency_distances(alone, join_hyphens=True) == [1, 1]


def test_subtree_of_the_whole_word():
    # Over-seer me obeys . - "Over" hangs on "seer", "me" on "Over"
    doc = parse(
        ["Over", "-", "seer", "me", "obeys", "."],
        [2, 2, 4, 0, 4, 4],
        ["compound", "punct", "nsubj", "obj", "ROOT", "punct"],
        spaces=[False, False, True, True, False, False],
    )
    assert subtree_len(doc[0], join_hyphens=True) == subtree_len(doc[2], join_hyphens=True) == 2
    assert texts(get_children(doc[2], join_hyphens=True)) == ["me"]
    assert (subtree_len(doc[0]), subtree_len(doc[2])) == (2, 3)


def test_word_with_parts_on_several_heads():
    # dog re-call barks - "re" hangs on "dog", "call" on the verb: the word depends on the verb
    doc = parse(
        ["dog", "re", "-", "call", "barks"],
        [4, 0, 1, 4, 4],
        ["nsubj", "nmod", "punct", "obj", "ROOT"],
        spaces=[True, False, False, True, False],
    )
    assert texts(get_children(doc[0])) == ["re"]
    assert get_children(doc[0], join_hyphens=True) == []
    assert texts(get_children(doc[4], join_hyphens=True)) == ["dog", "call"]
    assert calc_dependency_distances(doc, join_hyphens=True) == [2, 1]
