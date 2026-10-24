from math import isnan, nan
from statistics import fmean, pstdev
from typing import ClassVar

import pytest
import spacy
from spacy.tokens import Doc

from anyts.constants import MESSAGES, SYNTAX_STATS_DESC
from anyts.exceptions import SourceError, SourceTypeError
from anyts.syntax_stats import (
    SyntaxStats,
    base_dep,
    calc_coordination_chains,
    calc_dependency_distances,
    calc_modifier_chains,
    calc_tree_depth,
    calc_valency,
    count_children,
    count_noun_modifiers,
    get_children,
    get_words,
    has_agent,
    is_agentless,
    is_clause_head,
    is_infinitive_clause,
    is_infinitive_clause_head,
    is_passive,
    is_predicate,
    is_prep_complement,
    is_root,
    is_subordinate_clause_head,
    predicate_form,
    subtree_len,
)
from anyts.utils import is_word, joins_previous

VOCAB = spacy.blank("xx").vocab


def parse(words, heads, deps, morphs=None, spaces=None, pos=None):
    """A Doc with a hand-made dependency tree: heads are the indices of the head tokens"""
    return Doc(
        VOCAB,
        words=words,
        spaces=spaces or [True] * len(words),
        heads=heads,
        deps=deps,
        morphs=morphs,
        pos=pos,
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


def predicate(words, deps, morphs):
    """The last word with every other word attached to it"""
    last = len(words) - 1
    return parse(words, [last] * len(words), [*deps, "ROOT"], morphs)[last]


@pytest.mark.parametrize(
    ("words", "deps", "morphs", "form"),
    [
        (["arrived"], [], ["VerbForm=Part"], "Part"),
        (["house"], [], ["Number=Sing"], ""),
        (["had", "arrived"], ["aux"], ["VerbForm=Fin", "VerbForm=Part"], "Fin"),
        (["to", "have", "gone"], ["mark", "aux"], ["", "VerbForm=Inf", "VerbForm=Part"], "Inf"),
        (["being", "chosen"], ["aux:pass"], ["VerbForm=Ger", "VerbForm=Part"], "Ger"),
        (["been", "chosen"], ["aux:pass"], ["VerbForm=Part", "VerbForm=Part"], "Fin"),
        (["is", "nice"], ["cop"], ["VerbForm=Fin", "Degree=Pos"], "Fin"),
        (["will", "have", "gone"], ["aux", "aux"], ["VerbForm=Fin", "VerbForm=Inf", ""], "Fin"),
        (["had", "gone"], ["aux"], ["", "VerbForm=Part"], "Part"),
        (["not", "gone"], ["advmod"], ["VerbForm=Fin", "VerbForm=Part"], "Part"),
        (["having", "eaten"], ["aux"], ["Tense=Pres|VerbForm=Part", "VerbForm=Part"], "Part"),
        (["been", "eaten"], ["aux"], ["Tense=Past|VerbForm=Part", "VerbForm=Part"], "Fin"),
        (["to", "be", "eaten"], ["mark", "aux"], ["", "VerbForm=Inf", "VerbForm=Part"], "Inf"),
    ],
)
def test_predicate_form(words, deps, morphs, form):
    assert predicate_form(predicate(words, deps, morphs)) == form


def test_predicate_form_of_a_finite_auxiliary_after_another():
    # A verb-final clause: dass er gekommen sein wird, every auxiliary on the participle
    doc = parse(
        ["dass", "er", "gekommen", "sein", "wird"],
        [2, 2, 2, 2, 2],
        ["mark", "nsubj", "ROOT", "aux", "aux"],
        morphs=["", "Case=Nom", "VerbForm=Part", "VerbForm=Inf", "VerbForm=Fin"],
    )
    assert predicate_form(doc[2]) == "Fin"


def test_predicate_form_of_an_auxiliary_without_a_form():
    token = predicate(["habéis", "llegado"], ["aux"], ["", "VerbForm=Part"])
    assert predicate_form(token, lambda aux: "Fin") == "Fin"
    assert predicate_form(token, lambda aux: "") == "Part"
    token = predicate(["á", "haber", "llegado"], ["aux", "aux"], ["", "VerbForm=Inf", ""])
    assert predicate_form(token, lambda aux: "Fin" if aux.text == "habéis" else "") == "Inf"
    with_form = predicate(["had", "arrived"], ["aux"], ["VerbForm=Fin", "VerbForm=Part"])
    assert predicate_form(with_form, lambda aux: pytest.fail("read by its form")) == "Fin"


def test_predicate_form_hook_must_be_callable():
    with pytest.raises(
        SourceTypeError, match=r"^The verb form of an auxiliary must be callable, not str$"
    ):
        predicate_form(predicate(["arrived"], [], ["VerbForm=Part"]), "Fin")


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


def test_hyphen_at_a_sentence_start():
    # Tick- | tock came . - a sentence starts at the second part, which is not joined
    doc = parse(
        ["Tick", "-", "tock", "came", "."],
        [0, 0, 3, 3, 3],
        ["ROOT", "punct", "nsubj", "ROOT", "punct"],
        spaces=[False, False, True, False, False],
    )
    tick, _, tock, came, _ = doc
    assert [texts(sent) for sent in doc.sents] == [["Tick", "-"], ["tock", "came", "."]]
    assert not joins_previous(tock)
    assert texts(get_words(doc, join_hyphens=True)) == ["Tick", "tock", "came"]
    assert texts(get_children(came, join_hyphens=True)) == ["tock"]
    assert subtree_len(came, join_hyphens=True) == 2
    assert subtree_len(tick, join_hyphens=True) == 1
    whole = calc_dependency_distances(doc, join_hyphens=True)
    by_sentence = [d for sent in doc.sents for d in calc_dependency_distances(sent, True)]
    assert whole == by_sentence == [1]


def test_words_of_hyphenated_words():
    doc = hyphenated()
    assert texts(get_words(doc)) == ["Some", "one", "came", "with", "a", "well", "known", "cat"]
    assert texts(get_words(doc, join_hyphens=True)) == ["Some", "came", "with", "a", "well", "cat"]
    # A part whose first part lies outside the sequence is a word of its own
    assert texts(get_words(doc[2:5], join_hyphens=True)) == ["one", "came", "with"]
    # A word is given by its part that holds its relation, not by its first part
    governor = parse(
        ["He", "is", "vice", "-", "governor", "of", "the", "vice", "-", "region"],
        [4, 4, 4, 4, 4, 9, 9, 9, 7, 4],
        ["nsubj", "cop", "amod", "punct", "ROOT", "case", "det", "amod", "punct", "nmod"],
        spaces=[True, True, False, False, True, True, True, False, False, False],
    )
    assert texts(get_words(governor, join_hyphens=True)) == [
        "He",
        "is",
        "governor",
        "of",
        "the",
        "region",
    ]
    assert texts(get_children(governor[2], join_hyphens=True)) == ["He", "is", "region"]
    # A word whose relation a hyphen holds, or whose parts form a loop, is given by its first part
    laugh = parse(
        ["Ha", "-", "ha", "!"], [1, 1, 1, 1], ["dep", "ROOT", "dep", "punct"], spaces=[False] * 4
    )
    hanging = parse(
        ["some", "-", "one", "came"],
        [1, 3, 1, 3],
        ["det", "nsubj", "dep", "ROOT"],
        spaces=[False, False, True, False],
    )
    loop = parse(["a", "-", "b"], [2, 0, 1], ["dep", "punct", "dep"], spaces=[False] * 3)
    assert texts(get_words(laugh, join_hyphens=True)) == ["Ha"]
    assert texts(get_words(hanging, join_hyphens=True)) == ["some", "came"]
    assert texts(get_words(loop, join_hyphens=True)) == ["a"]


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


def test_tree_depth_of_hyphenated_words():
    # I saw some-thing and more . - "more" hangs on the second part of some-thing
    doc = parse(
        ["I", "saw", "some", "-", "thing", "and", "more", "."],
        [1, 1, 4, 4, 1, 6, 4, 1],
        ["nsubj", "ROOT", "det", "punct", "obj", "cc", "conj", "punct"],
        spaces=[True, True, False, False, True, True, False, False],
    )
    assert calc_tree_depth(doc) == calc_tree_depth(doc, join_hyphens=True) == 3
    # The parts of a word of one sentence are no levels of its tree
    tick = parse(
        ["Tick", "-", "tock", "!"],
        [0, 0, 0, 0],
        ["ROOT", "punct", "dep", "punct"],
        spaces=[False, False, False, False],
    )
    assert (calc_tree_depth(tick), calc_tree_depth(tick, join_hyphens=True)) == (1, 0)
    assert calc_tree_depth(hyphenated(), join_hyphens=True) == 2
    assert calc_tree_depth(hyphenated(one_head=0), join_hyphens=True) == 2


def test_tree_depth_through_a_hyphen():
    # A word that hangs on the inner hyphen of a word is one level below that word
    doc = parse(
        ["came", "well", "-", "known", "there"],
        [0, 3, 3, 0, 2],
        ["ROOT", "amod", "punct", "obl", "advmod"],
        spaces=[True, False, False, True, False],
    )
    assert calc_tree_depth(doc, join_hyphens=True) == 2


def test_tree_depth_through_tokens_outside_the_words():
    # well-known , new - "new" hangs on the comma, and the comma on "known"
    doc = parse(
        ["well", "-", "known", ",", "new"],
        [2, 2, 2, 2, 3],
        ["amod", "punct", "ROOT", "punct", "dep"],
        spaces=[False, False, False, True, False],
    )
    assert calc_tree_depth(doc) == calc_tree_depth(doc, join_hyphens=True) == 1
    # A word whose head is outside the sequence is the head of its tree
    assert calc_tree_depth([doc[0], doc[4]], join_hyphens=True) == 0


def test_coordination_chains_of_hyphenated_words():
    # member and vice-governor - the parts of vice-governor are two conjuncts for the parser
    doc = parse(
        ["member", "and", "vice", "-", "governor"],
        [0, 2, 0, 2, 2],
        ["ROOT", "cc", "conj", "punct", "conj"],
        spaces=[True, True, False, False, False],
    )
    assert calc_coordination_chains(doc) == [3]
    assert calc_coordination_chains(doc, join_hyphens=True) == [2]
    # A conjunct of the second part of a word joins its chain
    saw = parse(
        ["I", "saw", "some", "-", "thing", "and", "more"],
        [1, 1, 4, 4, 1, 6, 4],
        ["nsubj", "ROOT", "det", "punct", "obj", "cc", "conj"],
        spaces=[True, True, False, False, True, True, False],
    )
    assert calc_coordination_chains(saw, join_hyphens=True) == [2]
    # A strict, haughty-learned face: the first part is the conjunct, the last one hangs on the noun
    face = parse(
        ["strict", ",", "haughty", "-", "learned", "face"],
        [5, 2, 0, 4, 5, 5],
        ["amod", "punct", "conj", "punct", "amod", "ROOT"],
        spaces=[False, True, False, False, True, False],
    )
    assert calc_coordination_chains(face) == [2]
    assert calc_coordination_chains(face, join_hyphens=True) == [2]


def test_subtree_of_a_loop():
    doc = parse(["a", "b", "c"], [1, 0, 1], ["dep", "dep", "dep"])
    assert subtree_len(doc[0]) == subtree_len(doc[0], join_hyphens=True) == 3


def test_tree_depth_of_a_loop():
    # a, b and c hang on each other in a Doc of ten tokens
    doc = parse(list("abcdefghij"), [1, 2, 0] + [3] * 7, ["dep"] * 10)
    assert calc_tree_depth(doc[:3]) == calc_tree_depth(doc[:3], join_hyphens=True) == 2


def test_loop_inside_a_hyphenated_word():
    doc = parse(["a", "-", "b"], [2, 0, 1], ["dep", "punct", "dep"], spaces=[False, False, False])
    assert calc_tree_depth(doc, join_hyphens=True) == 0
    assert calc_coordination_chains(doc, join_hyphens=True) == []
    assert calc_dependency_distances(doc, join_hyphens=True) == []


# The house built by workers was sold . She said that he did not want to leave and left .
TWO_SENTS = [
    ("The", 1, "det", "", "DET"),
    ("house", 6, "nsubj:pass", "", "NOUN"),
    ("built", 1, "acl", "VerbForm=Part|Voice=Pass", "VERB"),
    ("by", 4, "case", "", "ADP"),
    ("workers", 2, "obl:agent", "", "NOUN"),
    ("was", 6, "aux:pass", "VerbForm=Fin", "AUX"),
    ("sold", 6, "ROOT", "VerbForm=Part|Voice=Pass", "VERB"),
    (".", 6, "punct", "", "PUNCT"),
    ("She", 9, "nsubj", "", "PRON"),
    ("said", 9, "ROOT", "VerbForm=Fin", "VERB"),
    ("that", 14, "mark", "", "SCONJ"),
    ("he", 14, "nsubj", "", "PRON"),
    ("did", 14, "aux", "VerbForm=Fin", "AUX"),
    ("not", 14, "advmod", "Polarity=Neg", "PART"),
    ("want", 9, "ccomp", "VerbForm=Inf", "VERB"),
    ("to", 16, "mark", "", "PART"),
    ("leave", 14, "xcomp", "VerbForm=Inf", "VERB"),
    ("and", 18, "cc", "", "CCONJ"),
    ("left", 9, "conj", "VerbForm=Fin", "VERB"),
    (".", 9, "punct", "", "PUNCT"),
]


def two_sents():
    words, heads, deps, morphs, pos = (list(column) for column in zip(*TWO_SENTS, strict=True))
    return parse(words, heads, deps, morphs, pos=pos)


def test_syntax_stats_counts():
    stats = SyntaxStats(two_sents())
    assert [[token.text for token in sent] for sent in stats.sents] == [
        ["The", "house", "built", "by", "workers", "was", "sold"],
        ["She", "said", "that", "he", "did", "not", "want", "to", "leave", "and", "left"],
    ]
    assert (stats.n_sents, stats.n_words, stats.n_leaves, stats.n_subtrees) == (2, 18, 10, 8)
    assert stats.c_children == {0: 10, 1: 4, 2: 2, 3: 1, 5: 1}
    assert stats.c_deps["nsubj"] == 2 and "punct" not in stats.c_deps
    # Clauses: sold; said, want (ccomp, subordinate), leave (xcomp, infinitive) and left
    assert (stats.n_clauses, stats.n_subordinate_clauses, stats.n_complex_sents) == (5, 1, 1)
    assert stats.n_infinitive_clauses == 1
    assert stats.n_coordination_chains == 1
    # built by workers is a participial clause, and both participles are passive
    assert (stats.n_nouns, stats.n_verbs, stats.n_participle_clauses) == (2, 6, 1)
    assert (stats.n_passive, stats.n_agentless_passive) == (2, 1)
    assert (stats.n_infinitives, stats.n_negations, stats.n_split_predicates) == (2, 1, 0)
    assert stats.split_predicates == ()


def test_syntax_stats_metrics():
    stats = SyntaxStats(two_sents())
    # The distances of the first sentence, then of the second
    distances = [1, 5, 1, 1, 2, 1, 1, 4, 3, 2, 1, 5, 1, 2, 1, 9]
    assert stats.get_stats() == {
        "mean_dependency_distance": fmean(distances),
        "std_dependency_distance": pstdev(distances),
        "max_dependency_distance": 7.0,
        "p_adjacent_dependencies": 0.5,
        "tree_depth": 3.5,
        "leaves_per_sent": 5.0,
        "subtrees_per_sent": 4.0,
        "nodes_per_leaf": fmean([7 / 3, 11 / 7]),
        # sold is the seventh word of its sentence, said the second
        "words_before_root": 3.5,
        "verb_valency": 1.0,
        "coordination_chains_per_sent": 0.5,
        "mean_coordination_chain_len": 2.0,
        "clauses_per_sent": 2.5,
        "mean_clause_len": 3.6,
        "subordinate_clauses_per_sent": 0.5,
        "p_complex_sents": 0.5,
        "infinitive_clauses_per_sent": 0.5,
        "modifiers_per_noun": 1.0,
        # by workers is one complement with a preposition, no chain
        "prep_chains_per_sent": 0.0,
        "max_prep_chain_len": 0,
        "participle_clauses_per_sent": 0.5,
        "mean_participle_clause_len": 3.0,
        "p_passive": 1 / 3,
        "p_agentless_passive": 0.5,
        "infinitives_per_sent": 1.0,
        "negations_per_sent": 0.5,
        "split_predicates_per_sent": 0.0,
        # house is the only nominal subject, before sold; there is no nominal object
        "p_preverbal_subjects": 1.0,
        "p_preverbal_objects": nan,
        "noun_verb_ratio": 1 / 3,
    }
    assert list(stats.get_stats()) == list(SYNTAX_STATS_DESC)


def test_syntax_stats_without_constructions(house):
    stats = SyntaxStats(house)
    assert stats.n_words == 5 and stats.n_clauses == 1
    for name in ("verb_valency", "mean_coordination_chain_len", "mean_participle_clause_len"):
        assert isnan(getattr(stats, name))
    assert isnan(stats.p_passive) and isnan(stats.p_agentless_passive)
    assert isnan(stats.noun_verb_ratio)
    one_word = SyntaxStats(parse(["Yes", "."], [0, 0], ["ROOT", "punct"]))
    assert isnan(one_word.mean_dependency_distance) and isnan(one_word.max_dependency_distance)
    assert isnan(one_word.std_dependency_distance) and isnan(one_word.p_adjacent_dependencies)
    assert one_word.tree_depth == 0 and one_word.nodes_per_leaf == 1.0


class Default(SyntaxStats):
    pass


DEFAULT = Default.__new__(Default)


@pytest.mark.parametrize(
    ("words", "heads", "deps", "pos", "morphs", "heads_of_clauses"),
    [
        # A parenthetical word under parataxis is no clause, a predicate is
        (
            ["Well", ",", "he", "came", ",", "I", "think"],
            [3, 3, 3, 3, 6, 6, 3],
            ["parataxis", "punct", "nsubj", "ROOT", "punct", "nsubj", "parataxis"],
            ["INTJ", "PUNCT", "PRON", "VERB", "PUNCT", "PRON", "VERB"],
            None,
            ["came", "think"],
        ),
        # An infinitive under acl and a gerund under advcl are no clauses
        (
            ["the", "wish", "to", "leave", "came", "smiling"],
            [1, 4, 3, 1, 4, 4],
            ["det", "nsubj", "mark", "acl", "ROOT", "advcl"],
            ["DET", "NOUN", "PART", "VERB", "VERB", "VERB"],
            ["", "", "", "VerbForm=Inf", "VerbForm=Fin", "VerbForm=Ger"],
            ["came"],
        ),
        # A subtype counts as its base relation; a conjunct must be a predicate
        (
            ["the", "man", "who", "came", "and", "Ann"],
            [1, 1, 3, 1, 5, 1],
            ["det", "ROOT", "nsubj", "acl:relcl", "cc", "conj"],
            ["DET", "NOUN", "PRON", "VERB", "CCONJ", "PROPN"],
            None,
            ["man", "came"],
        ),
        # A nominal conjunct with a subject of its own is a predicate
        (
            ["He", "came", "and", "she", "glad"],
            [1, 1, 4, 4, 1],
            ["nsubj", "ROOT", "cc", "nsubj", "conj"],
            ["PRON", "VERB", "CCONJ", "PRON", "ADJ"],
            None,
            ["came", "glad"],
        ),
    ],
)
def test_default_clause_heads(words, heads, deps, pos, morphs, heads_of_clauses):
    doc = parse(words, heads, deps, morphs, pos=pos)
    assert [token.text for token in doc if DEFAULT.is_clause_head(token)] == heads_of_clauses


def test_default_subordinate_clauses():
    # He said that she came and left: left is a conjunct of a subordinate clause
    doc = parse(
        ["He", "said", "that", "she", "came", "and", "left", "and", "slept"],
        [1, 1, 4, 4, 1, 6, 4, 8, 1],
        ["nsubj", "ROOT", "mark", "nsubj", "ccomp", "cc", "conj", "cc", "conj"],
        pos=["PRON", "VERB", "SCONJ", "PRON", "VERB", "CCONJ", "VERB", "CCONJ", "VERB"],
    )
    assert [token.text for token in doc if DEFAULT.is_subordinate_clause_head(token)] == [
        "came",
        "left",
    ]


def test_default_participle_clauses():
    doc = parse(
        ["the", "letters", "written", "has", "written", "sent", "written", "home"],
        [1, 5, 1, 4, 5, 5, 5, 6],
        ["det", "nsubj", "acl", "aux", "advcl", "ROOT", "advcl", "obl"],
        ["", "", "VerbForm=Part", "", "VerbForm=Part", "VerbForm=Part", "VerbForm=Part", ""],
        pos=["DET", "NOUN", "VERB", "AUX", "VERB", "VERB", "VERB", "NOUN"],
    )
    # No dependent, an auxiliary, the head of the sentence: only written home is a clause
    assert [token.i for token in doc if DEFAULT.is_participle_clause(token)] == [6]


@pytest.mark.parametrize(
    ("deps", "passive", "agentless"),
    [
        (["nsubj:pass", "aux:pass", "ROOT", "case", "obl:agent"], True, False),
        (["nsubjpass", "auxpass", "ROOT", "prep", "agent"], True, False),
        (["nsubjpass", "auxpass", "ROOT", "prep", "obl"], True, True),
        (["nsubj", "aux", "ROOT", "case", "obl"], False, False),
    ],
)
def test_default_passive_by_both_schemes(deps, passive, agentless):
    doc = parse(
        ["It", "was", "built", "by", "them"],
        [2, 2, 2, 4, 2],
        deps,
        pos=["PRON", "AUX", "VERB", "ADP", "PRON"],
    )
    assert DEFAULT.is_passive(doc[2]) is passive
    assert DEFAULT.is_agentless(doc[2]) is agentless
    assert not DEFAULT.is_passive(doc[1])


def test_default_passive_by_voice():
    doc = parse(["built"], [0], ["ROOT"], ["Voice=Pass"], pos=["VERB"])
    assert DEFAULT.is_passive(doc[0]) and DEFAULT.is_agentless(doc[0])


def test_default_negations():
    doc = parse(
        ["Neither", "he", "nor", "she", "never", "came"],
        [1, 5, 3, 1, 5, 5],
        ["cc:preconj", "nsubj", "cc", "conj", "advmod", "ROOT"],
        ["Polarity=Neg", "", "Polarity=Neg", "", "", ""],
        pos=["CCONJ", "PRON", "CCONJ", "PRON", "ADV", "VERB"],
    )
    assert not any(DEFAULT.is_negation(token) for token in doc)

    class Negations(SyntaxStats):
        negation_words = frozenset({"never"})

    assert Negations(doc).n_negations == 1


class Hooked(SyntaxStats):
    """A language with split predicates, its own statistic and a parser of strings"""

    join_hyphens = True
    requires_lemmas = True
    stats_desc: ClassVar[dict[str, str]] = {
        **SYNTAX_STATS_DESC,
        "chains_per_sent": "Chains of nmod per sentence",
    }

    def __init__(self, source):
        super().__init__(source)
        chains = [
            length
            for sent in self.sents
            for length in calc_modifier_chains(sent, self.is_chain, self.join_hyphens)
        ]
        self.chains_per_sent = len(chains) / self.n_sents

    @staticmethod
    def is_chain(token):
        return token.dep_ == "nmod"

    def parse(self, source):
        if isinstance(source, str):
            words = source.split()
            return Doc(
                VOCAB,
                words=words,
                heads=[1, 1, 3, 1, 5, 3],
                deps=["det", "ROOT", "det", "nmod", "det", "nmod"],
                lemmas=[word.lower() for word in words],
                pos=["DET", "VERB", "DET", "NOUN", "DET", "NOUN"],
            )
        return super().parse(source)

    def find_split_predicates(self, words):
        return [(words[1], words[3])]


def test_hooks():
    stats = Hooked("The use the water the river")
    assert stats.split_predicates == ("use water",)
    assert stats.n_split_predicates == 1 and stats.split_predicates_per_sent == 1.0
    assert stats.get_stats()["chains_per_sent"] == 1.0
    assert list(stats.get_stats())[-1] == "chains_per_sent"


def test_hyphenated_words_in_the_statistics():
    doc = parse(
        ["vice", "-", "governor", "came"],
        [3, 2, 0, 3],
        ["compound", "punct", "nsubj", "ROOT"],
        pos=["NOUN", "PUNCT", "NOUN", "VERB"],
        spaces=[False, False, True, False],
    )

    class Hyphens(SyntaxStats):
        join_hyphens = True

    assert SyntaxStats(doc).n_words == 3
    assert Hyphens(doc).n_words == 2
    assert Hyphens(doc).c_children == {0: 1, 1: 1}


@pytest.mark.parametrize(
    ("source", "error", "message"),
    [
        ("The house", SourceTypeError, MESSAGES["source_type"].format(type="str")),
        (Doc(VOCAB, words=["The", "house"]), SourceError, MESSAGES["no_parse"]),
        (parse([",", "."], [1, 1], ["punct", "ROOT"]), SourceError, MESSAGES["no_words"]),
    ],
)
def test_syntax_stats_errors(source, error, message):
    with pytest.raises(error, match=f"^{message}$"):
        SyntaxStats(source)


def test_lemmas_required():
    class Lemmas(SyntaxStats):
        requires_lemmas = True

    doc = parse(["Yes"], [0], ["ROOT"])
    assert SyntaxStats(doc).n_words == 1
    with pytest.raises(SourceError, match=f"^{MESSAGES['no_lemmas']}$"):
        Lemmas(doc)


def test_is_predicate():
    doc = parse(
        ["She", "is", "tall", ",", "surely"],
        [2, 2, 2, 2, 2],
        ["nsubj", "cop", "ROOT", "punct", "parataxis"],
        pos=["PRON", "AUX", "ADJ", "PUNCT", "ADV"],
    )
    assert [token.text for token in doc if is_predicate(token)] == ["is", "tall"]


def test_count_noun_modifiers():
    doc = parse(
        ["the", "two", "old", "houses", "of", "Ann", "and", "flats", ",", "sold"],
        [3, 3, 3, 3, 5, 3, 7, 3, 9, 3],
        ["det", "nummod", "amod", "ROOT", "case", "nmod:poss", "cc", "conj", "punct", "acl"],
    )
    assert count_noun_modifiers(doc[3]) == 5
    assert count_noun_modifiers(doc[5]) == 0


def test_modifier_chains():
    # the use of the water of the river of the town, and the color of the sky
    doc = parse(
        ["use", "water", "river", "town", "color", "sky", "x"],
        [0, 0, 1, 2, 1, 4, 6],
        ["ROOT", "nmod", "nmod", "nmod", "nmod", "nmod", "ROOT"],
    )
    nmod = lambda token: token.dep_ == "nmod"  # noqa: E731
    # One chain from water: its longest branch is water - river - town
    assert calc_modifier_chains(doc, nmod) == [3]
    assert calc_modifier_chains(doc, lambda token: False) == []


# Yesterday the cat of the neighbour slept on the mat of the house of the mayor . Came the
# spring , and the guests it saw the city .
ORDER = [
    ("Yesterday", 6, "advmod", "ADV"),
    ("the", 2, "det", "DET"),
    ("cat", 6, "nsubj", "NOUN"),
    ("of", 5, "case", "ADP"),
    ("the", 5, "det", "DET"),
    ("neighbour", 2, "nmod", "NOUN"),
    ("slept", 6, "ROOT", "VERB"),
    ("on", 9, "case", "ADP"),
    ("the", 9, "det", "DET"),
    ("mat", 6, "obl", "NOUN"),
    ("of", 12, "case", "ADP"),
    ("the", 12, "det", "DET"),
    ("house", 9, "nmod", "NOUN"),
    ("of", 15, "case", "ADP"),
    ("the", 15, "det", "DET"),
    ("mayor", 12, "nmod", "NOUN"),
    (".", 6, "punct", "PUNCT"),
    ("Came", 17, "ROOT", "VERB"),
    ("the", 19, "det", "DET"),
    ("spring", 17, "nsubj", "NOUN"),
    (",", 25, "punct", "PUNCT"),
    ("and", 25, "cc", "CCONJ"),
    ("the", 23, "det", "DET"),
    ("guests", 25, "nsubj", "NOUN"),
    ("it", 25, "obj", "PRON"),
    ("saw", 17, "conj", "VERB"),
    ("the", 27, "det", "DET"),
    ("city", 25, "obj", "NOUN"),
    (".", 17, "punct", "PUNCT"),
]


def order_doc():
    words, heads, deps, pos = (list(column) for column in zip(*ORDER, strict=True))
    starts = [i in (0, 17) for i in range(len(words))]
    return Doc(VOCAB, words=words, heads=heads, deps=deps, pos=pos, sent_starts=starts)


def test_prepositional_chains_and_the_order_of_the_members():
    stats = SyntaxStats(order_doc())
    # of the neighbour is a single complement; on the mat of the house of the mayor starts at
    # the complement of the verb (obl) and holds three
    assert stats.n_prep_chains == 1 and stats.max_prep_chain_len == 3
    assert stats.prep_chains_per_sent == 0.5
    # slept is the seventh word, Came the first
    assert stats.words_before_root == 3.0
    # cat and guests stand before their verbs, spring after; the pronoun it is no nominal object
    assert (stats.n_nominal_subjects, stats.n_preverbal_subjects) == (3, 2)
    assert stats.p_preverbal_subjects == 2 / 3
    assert (stats.n_nominal_objects, stats.n_preverbal_objects) == (1, 0)
    assert stats.p_preverbal_objects == 0.0


def test_prepositional_complements():
    doc = order_doc()
    assert [token.text for token in doc if is_prep_complement(token)] == [
        "neighbour",
        "mat",
        "house",
        "mayor",
    ]
    # A complement without an adposition (a case of its own) is none
    bare = parse(
        ["the", "use", "water"], [1, 1, 1], ["det", "ROOT", "nmod"], pos=["DET", "NOUN", "NOUN"]
    )
    assert not is_prep_complement(bare[2])
    # A subtype is the base relation; a possessive marker is no adposition
    sub = parse(
        ["went", "to", "town", "John", "'s"],
        [0, 2, 0, 0, 3],
        ["ROOT", "case", "obl:to", "nmod:poss", "case"],
        pos=["VERB", "ADP", "NOUN", "PROPN", "PART"],
    )
    assert is_prep_complement(sub[2]) and not is_prep_complement(sub[3])


def test_hook_of_the_prepositional_complements():
    class OnlyNmod(SyntaxStats):
        def is_prep_complement(self, token):
            return token.dep_ == "nmod" and super().is_prep_complement(token)

    # Without the obl of the verb the chain is of the house of the mayor
    stats = OnlyNmod(order_doc())
    assert stats.n_prep_chains == 1 and stats.max_prep_chain_len == 2


def test_prepositional_complements_of_several_words_and_of_a_copula():
    # sat close to the door of the house: close begins the preposition, to is fixed to it
    doc = parse(
        ["sat", "close", "to", "the", "door", "of", "the", "house"],
        [0, 4, 1, 4, 0, 7, 7, 4],
        ["ROOT", "case", "fixed", "det", "obl", "case", "det", "nmod"],
        pos=["VERB", "ADV", "ADP", "DET", "NOUN", "ADP", "DET", "NOUN"],
    )
    assert is_prep_complement(doc[4]) and SyntaxStats(doc).max_prep_chain_len == 2
    # was in the house of the mayor: the predicate with a copula is the first link
    doc = parse(
        ["was", "in", "the", "house", "of", "the", "mayor"],
        [3, 3, 3, 3, 6, 6, 3],
        ["cop", "case", "det", "ROOT", "case", "det", "nmod"],
        pos=["AUX", "ADP", "DET", "NOUN", "ADP", "DET", "NOUN"],
    )
    assert is_prep_complement(doc[3]) and SyntaxStats(doc).max_prep_chain_len == 2
    # talked about the house that was by the river: the predicate of the relative clause is
    # no link of the chain of house
    doc = parse(
        ["talked", "about", "the", "house", "that", "was", "by", "the", "river"],
        [0, 3, 3, 0, 8, 8, 8, 8, 3],
        ["ROOT", "case", "det", "obl", "nsubj", "cop", "case", "det", "acl:relcl"],
        pos=["VERB", "ADP", "DET", "NOUN", "PRON", "AUX", "ADP", "DET", "NOUN"],
    )
    assert not is_prep_complement(doc[8]) and SyntaxStats(doc).n_prep_chains == 0
    # A conjunct of a complement starts no chain of its own
    doc = parse(
        ["lived", "in", "town", "and", "in", "the", "centre", "of", "the", "city"],
        [0, 2, 0, 6, 6, 6, 2, 9, 9, 6],
        ["ROOT", "case", "obl", "cc", "case", "det", "conj", "case", "det", "nmod"],
        pos=["VERB", "ADP", "NOUN", "CCONJ", "ADP", "DET", "NOUN", "ADP", "DET", "NOUN"],
    )
    assert SyntaxStats(doc).n_prep_chains == 0


def test_prepositional_complement_of_a_hyphenated_word():
    # lives in north-west of the city: in hangs on north, the relation obl on west
    doc = parse(
        ["He", "lives", "in", "north", "-", "west", "of", "the", "city"],
        [1, 1, 3, 5, 5, 1, 8, 8, 5],
        ["nsubj", "ROOT", "case", "compound", "punct", "obl", "case", "det", "nmod"],
        spaces=[True, True, True, False, False, True, True, True, True],
        pos=["PRON", "VERB", "ADP", "NOUN", "PUNCT", "NOUN", "ADP", "DET", "NOUN"],
    )
    assert is_prep_complement(doc[5], join_hyphens=True) and not is_prep_complement(doc[5])

    class Hyphens(SyntaxStats):
        join_hyphens = True

    assert Hyphens(doc).n_prep_chains == 1 and SyntaxStats(doc).n_prep_chains == 0


def test_words_before_a_root_out_of_the_words():
    # The root of the sentence is a mark, so the sentence gives no position
    doc = parse(["Well", "!"], [1, 1], ["discourse", "ROOT"], pos=["INTJ", "PUNCT"])
    assert isnan(SyntaxStats(doc).words_before_root)


def test_modifier_chains_skip_punctuation():
    doc = parse(["use", "\u00ab", "water"], [0, 0, 1], ["ROOT", "nmod", "nmod"])
    assert calc_modifier_chains(doc, lambda token: token.dep_ == "nmod") == []


def test_modifier_chains_of_hyphenated_words():
    doc = parse(
        ["use", "vice", "-", "governor", "town"],
        [0, 0, 3, 1, 3],
        ["ROOT", "nmod", "punct", "compound", "nmod"],
        spaces=[True, False, False, True, False],
    )
    nmod = lambda token: token.dep_ == "nmod"  # noqa: E731
    assert calc_modifier_chains(doc, nmod) == []
    assert calc_modifier_chains(doc, nmod, join_hyphens=True) == [2]
    # Every word a modifier: the head of the sentence starts the only chain
    assert calc_modifier_chains(doc, lambda token: True, join_hyphens=True) == [3]


def test_modifier_check_must_be_callable():
    with pytest.raises(
        SourceTypeError, match=r"^The check of a modifier must be callable, not str$"
    ):
        calc_modifier_chains(parse(["Yes"], [0], ["ROOT"]), "nmod")


def test_default_clause_heads_by_the_form_of_the_predicate():
    # He said that it has been built: a participle with a finite auxiliary is finite
    doc = parse(
        ["He", "said", "that", "it", "has", "been", "built", "."],
        [1, 1, 6, 6, 6, 6, 1, 1],
        ["nsubj", "ROOT", "mark", "nsubj:pass", "aux", "aux:pass", "ccomp", "punct"],
        ["", "VerbForm=Fin", "", "", "VerbForm=Fin", "VerbForm=Part", "VerbForm=Part", ""],
        pos=["PRON", "VERB", "SCONJ", "PRON", "AUX", "AUX", "VERB", "PUNCT"],
    )
    stats = SyntaxStats(doc)
    assert (stats.n_clauses, stats.n_subordinate_clauses, stats.n_complex_sents) == (2, 1, 1)
    assert stats.n_participle_clauses == 0
    # the fear to have been robbed: an infinitive auxiliary keeps the clause out
    doc = parse(
        ["fear", "to", "have", "been", "robbed"],
        [0, 4, 4, 4, 0],
        ["ROOT", "mark", "aux", "aux:pass", "acl"],
        ["", "", "VerbForm=Inf", "VerbForm=Part", "VerbForm=Part"],
        pos=["NOUN", "PART", "AUX", "AUX", "VERB"],
    )
    assert not DEFAULT.is_clause_head(doc[4])


def finite_by_ending(token):
    """Form of an auxiliary without VerbForm: habéis is finite"""
    return "Fin" if token.text == "habéis" else ""


def test_clause_heads_by_the_form_of_an_auxiliary():
    # Sé que os habéis posado: the model leaves habéis without a form
    doc = parse(
        ["Sé", "que", "os", "habéis", "posado", "."],
        [0, 4, 4, 4, 0, 0],
        ["ROOT", "mark", "obj", "aux", "ccomp", "punct"],
        ["VerbForm=Fin", "", "", "", "VerbForm=Part", ""],
        pos=["VERB", "SCONJ", "PRON", "AUX", "VERB", "PUNCT"],
    )
    assert not is_clause_head(doc[4]) and not is_subordinate_clause_head(doc[4])
    assert is_clause_head(doc[4], auxiliary_form=finite_by_ending)
    assert is_subordinate_clause_head(doc[4], auxiliary_form=finite_by_ending)
    assert is_subordinate_clause_head(
        doc[4], lambda token: is_clause_head(token, auxiliary_form=finite_by_ending)
    )

    class Spanish(SyntaxStats):
        def auxiliary_form(self, token):
            return finite_by_ending(token)

    assert DEFAULT.auxiliary_form(doc[3]) == ""
    assert (SyntaxStats(doc).n_clauses, SyntaxStats(doc).n_subordinate_clauses) == (1, 0)
    assert (Spanish(doc).n_clauses, Spanish(doc).n_subordinate_clauses) == (2, 1)


def test_infinitive_clauses_by_the_form_of_an_auxiliary():
    # Quiere haber llegado: the model leaves haber without a form
    doc = parse(
        ["Quiere", "haber", "llegado"],
        [0, 2, 0],
        ["ROOT", "aux", "xcomp"],
        ["VerbForm=Fin", "", "VerbForm=Part"],
        pos=["VERB", "AUX", "VERB"],
    )
    infinitive = lambda token: "Inf" if token.text == "haber" else ""  # noqa: E731
    assert not is_infinitive_clause(doc[2]) and not is_infinitive_clause_head(doc[2])
    assert is_infinitive_clause(doc[2], auxiliary_form=infinitive)
    assert is_infinitive_clause_head(doc[2], auxiliary_form=infinitive)
    assert is_clause_head(doc[2], auxiliary_form=infinitive)
    # a complement of a non-finite complement: llegado completes the word above it
    doc = parse(
        ["Dijo", "querer", "haber", "llegado"],
        [0, 0, 3, 1],
        ["ROOT", "xcomp", "aux", "xcomp"],
        ["VerbForm=Fin", "VerbForm=Inf", "", "VerbForm=Part"],
        pos=["VERB", "VERB", "AUX", "VERB"],
    )
    assert is_infinitive_clause(doc[3], auxiliary_form=infinitive)
    # Sé que habéis querido ir: ir completes querido, finite by habéis without a form
    doc = parse(
        ["Sé", "que", "habéis", "querido", "ir"],
        [0, 3, 3, 0, 3],
        ["ROOT", "mark", "aux", "ccomp", "xcomp"],
        ["VerbForm=Fin", "", "", "VerbForm=Part", "VerbForm=Inf"],
        pos=["VERB", "SCONJ", "AUX", "VERB", "VERB"],
    )
    assert not is_infinitive_clause(doc[4]) and not is_infinitive_clause_head(doc[4])
    assert is_infinitive_clause(doc[4], auxiliary_form=finite_by_ending)
    assert is_infinitive_clause_head(doc[4], auxiliary_form=finite_by_ending)
    # ir completes querido under xcomp of a participle, finite by habéis without a form
    doc = parse(
        ["Vio", "hombres", "dispuestos", "habéis", "querido", "ir"],
        [0, 0, 1, 4, 2, 4],
        ["ROOT", "obj", "acl", "aux", "xcomp", "xcomp"],
        ["VerbForm=Fin", "", "VerbForm=Part", "", "VerbForm=Part", "VerbForm=Inf"],
        pos=["VERB", "NOUN", "VERB", "AUX", "VERB", "VERB"],
    )
    assert not is_infinitive_clause(doc[5]) and not is_clause_head(doc[5])
    assert is_infinitive_clause(doc[5], auxiliary_form=finite_by_ending)
    assert is_clause_head(doc[5], auxiliary_form=finite_by_ending)


def test_infinitive_clauses_by_the_hook_of_the_class():
    # Quiere haber llegado: an infinitive clause by the form of haber, not a subordinate one
    doc = parse(
        ["Quiere", "haber", "llegado"],
        [0, 2, 0],
        ["ROOT", "aux", "xcomp"],
        ["VerbForm=Fin", "", "VerbForm=Part"],
        pos=["VERB", "AUX", "VERB"],
    )

    def infinitive(token):
        return "Inf" if token.text == "haber" else ""

    assert not is_subordinate_clause_head(doc[2], auxiliary_form=infinitive)

    class Hooked(SyntaxStats):
        def auxiliary_form(self, token):
            return infinitive(token)

    stats = Hooked(doc)
    assert (stats.n_clauses, stats.n_subordinate_clauses, stats.n_infinitive_clauses) == (2, 0, 1)


@pytest.mark.parametrize(
    "check",
    [
        lambda token: is_clause_head(token, auxiliary_form="Fin"),
        lambda token: is_infinitive_clause(token, auxiliary_form="Fin"),
        lambda token: is_subordinate_clause_head(token, auxiliary_form="Fin"),
        lambda token: is_infinitive_clause_head(token, auxiliary_form="Fin"),
    ],
)
def test_form_of_an_auxiliary_must_be_callable(check):
    with pytest.raises(
        SourceTypeError, match=r"^The verb form of an auxiliary must be callable, not str$"
    ):
        check(parse(["Yes"], [0], ["ROOT"])[0])


def listing(n, pos, dep):
    """He listed w0, w1, ...: every conjunct hangs on the previous one, as in ClearNLP"""
    return parse(
        ["He", "listed"] + [f"w{i}" for i in range(n)],
        [1, 1, 1] + [i + 2 for i in range(n - 1)],
        ["nsubj", "ROOT", dep] + ["conj"] * (n - 1),
        pos=["PRON", "VERB"] + [pos] * n,
    )


def test_long_chains_of_conjuncts():
    nouns = SyntaxStats(listing(2000, "NOUN", "obj"))
    assert (nouns.n_clauses, nouns.n_subordinate_clauses) == (1, 0)
    verbs = SyntaxStats(listing(50, "VERB", "ccomp"))
    assert (verbs.n_clauses, verbs.n_subordinate_clauses) == (51, 50)


def test_a_loop_of_conjuncts():
    doc = parse(["a", "b", "c"], [1, 0, 1], ["conj", "conj", "dep"], pos=["VERB"] * 3)
    assert not any(DEFAULT.is_clause_head(token) for token in doc)
    assert not any(DEFAULT.is_subordinate_clause_head(token) for token in doc)


def test_a_dependency_label_without_heads():
    doc = Doc(VOCAB, words=["a", "b"])
    doc[0].dep_ = "nsubj"
    with pytest.raises(SourceError, match=f"^{MESSAGES['no_parse']}$"):
        SyntaxStats(doc)


@pytest.mark.parametrize("mark", ["punct", "nmod"])
def test_modifier_chains_under_punctuation(mark):
    # use << water river: the chain below the mark is the same whatever its label
    doc = parse(["use", "\u00ab", "water", "river"], [0, 0, 1, 2], ["ROOT", mark, "nmod", "nmod"])
    assert calc_modifier_chains(doc, lambda token: token.dep_ == "nmod") == [2]


def test_modifier_chains_through_an_inner_part():
    # use vice-governor town city: town hangs on governor, an inner part of the word
    doc = parse(
        ["use", "vice", "-", "governor", "town", "city"],
        [0, 0, 3, 1, 3, 4],
        ["ROOT", "nmod", "punct", "compound", "nmod", "nmod"],
        spaces=[True, False, False, True, True, False],
    )
    nmod = lambda token: token.dep_ == "nmod"  # noqa: E731
    assert calc_modifier_chains(doc, nmod, join_hyphens=True) == [3]
    assert calc_modifier_chains(doc, nmod) == [2]


def test_negation_words_checked_at_class_definition():
    with pytest.raises(
        SourceTypeError, match=r"^A list of negation_words is expected, not a string$"
    ):
        type("Negated", (SyntaxStats,), {"negation_words": "not"})


def test_predicates_of_the_module_match_the_hooks():
    doc = parse(
        ["He", "said", "that", "it", "was", "built", "and", "left", "by", "them"],
        [1, 1, 5, 5, 5, 1, 7, 5, 9, 7],
        [
            "nsubj",
            "ROOT",
            "mark",
            "nsubj:pass",
            "aux:pass",
            "ccomp",
            "cc",
            "conj",
            "case",
            "obl:agent",
        ],
        pos=["PRON", "VERB", "SCONJ", "PRON", "AUX", "VERB", "CCONJ", "VERB", "ADP", "PRON"],
    )
    for token in doc:
        assert is_clause_head(token) is DEFAULT.is_clause_head(token)
        assert is_subordinate_clause_head(token) is DEFAULT.is_subordinate_clause_head(token)
        assert is_passive(token) is DEFAULT.is_passive(token)
        assert is_agentless(token) is DEFAULT.is_agentless(token)
    assert [token.text for token in doc if is_subordinate_clause_head(token)] == ["built", "left"]
    assert has_agent(doc[7]) and not has_agent(doc[5])
    assert is_agentless(doc[5]) and not is_agentless(doc[7])


def test_subordinate_clause_head_by_a_hook():
    doc = parse(
        ["He", "said", "that", "she", "came"],
        [1, 1, 4, 4, 1],
        ["nsubj", "ROOT", "mark", "nsubj", "ccomp"],
        pos=["PRON", "VERB", "SCONJ", "PRON", "VERB"],
    )
    assert is_subordinate_clause_head(doc[4])
    assert not is_subordinate_clause_head(doc[4], lambda token: False)
    with pytest.raises(SourceTypeError):
        is_subordinate_clause_head(doc[4], "clause")


# He can come and go . She wants to leave and rest , seems happy and said he came
INFINITIVES = [
    ("He", 1, "nsubj", "", "PRON"),
    ("can", 1, "ROOT", "VerbForm=Fin", "VERB"),
    ("come", 1, "xcomp", "VerbForm=Inf", "VERB"),
    ("and", 4, "cc", "", "CCONJ"),
    ("go", 2, "conj", "VerbForm=Inf", "VERB"),
    ("She", 6, "nsubj", "", "PRON"),
    ("wants", 6, "ROOT", "VerbForm=Fin", "VERB"),
    ("to", 8, "mark", "", "PART"),
    ("leave", 6, "xcomp", "VerbForm=Inf", "VERB"),
    ("and", 10, "cc", "", "CCONJ"),
    ("rest", 8, "conj", "VerbForm=Inf", "VERB"),
    ("seems", 6, "conj", "VerbForm=Fin", "VERB"),
    ("happy", 11, "xcomp", "", "ADJ"),
    ("said", 6, "conj", "VerbForm=Fin", "VERB"),
    ("he", 15, "nsubj", "", "PRON"),
    ("came", 13, "xcomp", "VerbForm=Fin", "VERB"),
]


def infinitives():
    words, heads, deps, morphs, pos = (list(column) for column in zip(*INFINITIVES, strict=True))
    return parse(words, heads, deps, morphs, pos=pos)


def is_modal(token):
    return token.head.text == "can"


@pytest.mark.parametrize(
    ("periphrasis", "heads_of_clauses", "infinitive"),
    [
        # Without periphrases every infinitive complement is a clause
        (
            None,
            ["can", "come", "go", "wants", "leave", "rest", "seems", "said", "came"],
            ["come", "go", "leave", "rest"],
        ),
        # can come and go is one predicate, conjunct included
        (
            is_modal,
            ["can", "wants", "leave", "rest", "seems", "said", "came"],
            ["leave", "rest"],
        ),
    ],
)
def test_infinitive_clauses(periphrasis, heads_of_clauses, infinitive):
    doc = infinitives()

    def is_head(token):
        return is_clause_head(token, is_infinitive_periphrasis=periphrasis)

    assert [token.text for token in doc if is_head(token)] == heads_of_clauses
    # came is finite under xcomp: a complement clause, subordinate
    assert [token.text for token in doc if is_subordinate_clause_head(token, is_head)] == ["came"]
    assert [token.text for token in doc if is_infinitive_clause_head(token, is_head)] == infinitive
    assert is_infinitive_clause(doc[8], periphrasis) and not is_infinitive_clause(doc[12])
    assert is_infinitive_clause(doc[2], periphrasis) is (periphrasis is None)
    assert not is_infinitive_clause(doc[4]) and not is_infinitive_clause(doc[15])


def test_infinitive_clause_by_the_hooks_of_its_clause_head():
    # Debe salir y querer, pide cantar: pide hangs on querer, a conjunct of the periphrasis,
    # so the clause of pide is the one of the periphrasis
    doc = parse(
        ["Debe", "salir", "y", "querer", "pide", "cantar"],
        [0, 0, 3, 0, 3, 4],
        ["ROOT", "xcomp", "cc", "conj", "conj", "xcomp"],
        ["VerbForm=Fin", "VerbForm=Inf", "", "VerbForm=Inf", "VerbForm=Fin", "VerbForm=Inf"],
        pos=["AUX", "VERB", "CCONJ", "VERB", "VERB", "VERB"],
    )

    def periphrasis(token):
        return token.head.text == "Debe"

    assert not is_infinitive_clause(doc[5], periphrasis)
    assert is_infinitive_clause(doc[5], periphrasis, is_clause_head)


@pytest.mark.parametrize(("verb", "dep"), [("Tiene", "conj"), ("Hay", "csubj")])
def test_infinitive_clause_under_a_periphrasis_attached_as_conj_or_csubj(verb, dep):
    # Tiene que intentar salir, Hay que intentar salir: the models attach intentar to the
    # verb of the periphrasis as conj or csubj
    doc = parse(
        [verb, "que", "intentar", "salir"],
        [0, 2, 0, 2],
        ["ROOT", "mark", dep, "xcomp"],
        ["VerbForm=Fin", "", "VerbForm=Inf", "VerbForm=Inf"],
        pos=["VERB", "SCONJ", "VERB", "VERB"],
    )

    def periphrasis(token):
        return token.head.text == verb

    assert not is_clause_head(doc[2], is_infinitive_periphrasis=periphrasis)
    assert is_infinitive_clause(doc[3], periphrasis)
    assert is_clause_head(doc[3], is_infinitive_periphrasis=periphrasis)


def is_has(token):
    return token.head.text == "has"


@pytest.mark.parametrize(
    ("words", "heads", "deps", "morphs", "periphrasis", "heads_of_clauses", "infinitive"),
    [
        # A participial phrase and an infinitive under acl hold their infinitives
        (
            ["Trying", "to", "leave", "he", "fell"],
            [4, 2, 0, 4, 4],
            ["advcl", "mark", "xcomp", "nsubj", "ROOT"],
            ["VerbForm=Ger", "", "VerbForm=Inf", "", "VerbForm=Fin"],
            None,
            ["fell"],
            [],
        ),
        (
            ["He", "had", "the", "wish", "to", "try", "to", "leave"],
            [1, 1, 3, 1, 5, 3, 7, 5],
            ["nsubj", "ROOT", "det", "obj", "mark", "acl", "mark", "xcomp"],
            ["", "VerbForm=Fin", "", "", "", "VerbForm=Inf", "", "VerbForm=Inf"],
            None,
            ["had"],
            [],
        ),
        # An infinitive under a periphrasis completes its verb
        (
            ["He", "can", "try", "to", "leave"],
            [1, 1, 1, 4, 2],
            ["nsubj", "ROOT", "xcomp", "mark", "xcomp"],
            ["", "VerbForm=Fin", "VerbForm=Inf", "", "VerbForm=Inf"],
            is_modal,
            ["can", "leave"],
            ["leave"],
        ),
        # An infinitive completes the word above its non-finite complements
        (
            ["He", "kept", "trying", "to", "leave"],
            [1, 1, 1, 4, 2],
            ["nsubj", "ROOT", "xcomp", "mark", "xcomp"],
            ["", "VerbForm=Fin", "VerbForm=Ger", "", "VerbForm=Inf"],
            None,
            ["kept", "leave"],
            ["leave"],
        ),
        (
            ["He", "seemed", "able", "to", "leave"],
            [1, 1, 1, 4, 2],
            ["nsubj", "ROOT", "xcomp", "mark", "xcomp"],
            ["", "VerbForm=Fin", "", "", "VerbForm=Inf"],
            None,
            ["seemed", "leave"],
            ["leave"],
        ),
        # The form comes from the auxiliaries: to be chosen is an infinitive
        (
            ["She", "wants", "to", "be", "chosen"],
            [1, 1, 4, 4, 1],
            ["nsubj", "ROOT", "mark", "aux:pass", "xcomp"],
            ["", "VerbForm=Fin", "", "VerbForm=Inf", "VerbForm=Part"],
            None,
            ["wants", "chosen"],
            ["chosen"],
        ),
        # A model may attach the infinitive of a periphrasis to its verb as conj
        (
            ["He", "has", "to", "leave"],
            [1, 1, 3, 1],
            ["nsubj", "ROOT", "cc", "conj"],
            ["", "VerbForm=Fin", "", "VerbForm=Inf"],
            is_has,
            ["has"],
            [],
        ),
        (
            ["He", "has", "to", "leave"],
            [1, 1, 3, 1],
            ["nsubj", "ROOT", "cc", "conj"],
            ["", "VerbForm=Fin", "", "VerbForm=Inf"],
            None,
            ["has", "leave"],
            [],
        ),
    ],
)
def test_infinitive_clause_cases(
    words, heads, deps, morphs, periphrasis, heads_of_clauses, infinitive
):
    doc = parse(words, heads, deps, morphs, pos=["VERB"] * len(words))

    def is_head(token):
        return is_clause_head(token, is_infinitive_periphrasis=periphrasis)

    assert [token.text for token in doc if is_head(token)] == heads_of_clauses
    assert not any(is_subordinate_clause_head(token, is_head) for token in doc)
    assert [token.text for token in doc if is_infinitive_clause_head(token, is_head)] == infinitive


def is_need(token):
    return token.head.text == "Need"


@pytest.mark.parametrize(
    ("periphrasis", "heads_of_clauses"), [(None, ["Need", "leave"]), (is_need, ["Need"])]
)
def test_infinitive_subject_of_a_modal_word(periphrasis, heads_of_clauses):
    # Need to leave: a model may hang the infinitive on the modal word as csubj
    doc = parse(
        ["Need", "to", "leave"],
        [0, 2, 0],
        ["ROOT", "mark", "csubj"],
        ["", "", "VerbForm=Inf"],
        pos=["ADJ", "PART", "VERB"],
    )

    def is_head(token):
        return is_clause_head(token, is_infinitive_periphrasis=periphrasis)

    assert [token.text for token in doc if is_head(token)] == heads_of_clauses
    # An infinitive subject that is a clause stays a subordinate one
    assert [token.text for token in doc if is_subordinate_clause_head(token, is_head)] == (
        heads_of_clauses[1:]
    )
    assert not any(is_infinitive_clause_head(token, is_head) for token in doc)


def test_infinitive_clause_head_by_a_hook():
    doc = infinitives()
    assert is_infinitive_clause_head(doc[8]) and not is_infinitive_clause_head(doc[6])
    assert not is_infinitive_clause_head(doc[8], lambda token: False)
    with pytest.raises(SourceTypeError):
        is_infinitive_clause_head(doc[8], "clause")


def test_infinitive_clause_by_a_check_of_a_clause_head():
    doc = parse(
        ["She", "wants", "to", "leave"],
        [1, 1, 3, 1],
        ["nsubj", "ROOT", "mark", "xcomp"],
        ["", "VerbForm=Fin", "", "VerbForm=Inf"],
    )
    assert is_infinitive_clause(doc[3])
    assert not is_infinitive_clause(doc[3], is_clause_head=lambda token: False)
    with pytest.raises(SourceTypeError):
        is_infinitive_clause(doc[3], is_clause_head="clause")


def test_infinitive_clause_in_a_loop():
    # leave completes go, a conjunct of leave: the checks would go round
    doc = parse(
        ["She", "go", "leave"],
        [1, 2, 1],
        ["nsubj", "conj", "xcomp"],
        ["", "VerbForm=Fin", "VerbForm=Inf"],
        pos=["PRON", "VERB", "VERB"],
    )
    assert not is_infinitive_clause(doc[2]) and not is_clause_head(doc[2])
    assert not is_clause_head(doc[1])


def test_long_chain_of_infinitives_and_conjuncts():
    # Each infinitive completes a conjunct of the infinitive before it
    n = 1001
    doc = parse(
        ["go"] * n,
        [0, *range(n - 1)],
        ["ROOT", *("xcomp" if i % 2 else "conj" for i in range(1, n))],
        ["VerbForm=Fin", *["VerbForm=Inf"] * (n - 1)],
        pos=["VERB"] * n,
    )
    assert is_clause_head(doc[n - 1]) and is_clause_head(doc[n - 2])


def test_infinitive_periphrasis_hook():
    class Modal(SyntaxStats):
        def is_infinitive_periphrasis(self, token):
            return is_modal(token)

    doc = infinitives()
    assert not DEFAULT.is_infinitive_periphrasis(doc[2])
    assert (SyntaxStats(doc).n_clauses, Modal(doc).n_clauses) == (9, 7)
    assert (Modal(doc).n_subordinate_clauses, Modal(doc).n_infinitive_clauses) == (1, 2)
    assert SyntaxStats(doc).n_infinitive_clauses == 4
    for check in (is_clause_head, is_infinitive_clause):
        with pytest.raises(SourceTypeError):
            check(doc[2], is_infinitive_periphrasis="modal")


def test_clause_head_of_a_loop_of_conjuncts():
    doc = parse(
        ["He", "came", "left", "slept"],
        [1, 1, 3, 2],
        ["nsubj", "ROOT", "conj", "conj"],
        pos=["PRON", "VERB", "VERB", "VERB"],
    )
    assert not is_clause_head(doc[2]) and not is_subordinate_clause_head(doc[2])


def test_pickle_and_copy():
    import copy
    import pickle

    doc = parse(
        ["He", "came", "and", "left", ".", "She", "slept"],
        [1, 1, 3, 1, 1, 6, 6],
        ["nsubj", "ROOT", "cc", "conj", "punct", "nsubj", "ROOT"],
        pos=["PRON", "VERB", "CCONJ", "VERB", "PUNCT", "PRON", "VERB"],
    )
    stats = SyntaxStats(doc)
    data = pickle.dumps(stats)
    assert len(data) < len(pickle.dumps(doc.vocab))
    for clone in (pickle.loads(data), copy.deepcopy(stats), copy.copy(stats)):
        assert repr(clone.get_stats()) == repr(stats.get_stats())
        assert [[token.text for token in sent] for sent in clone.sents] == [
            ["He", "came", "and", "left"],
            ["She", "slept"],
        ]
        assert clone.sents[0][1].dep_ == "ROOT"


def test_sents_keep_no_tensor_and_no_user_data():
    import numpy as np

    doc = parse(["He", "came"], [1, 1], ["nsubj", "ROOT"], pos=["PRON", "VERB"])
    doc.tensor = np.ones((2, 4), dtype="float32")
    doc.user_data["stats"] = object()
    light = SyntaxStats(doc).sents[0][0].doc
    assert light is not doc
    assert light.tensor.size == 0 and not light.user_data
    assert [(token.text, token.dep_, token.head.i) for token in light] == [
        ("He", "nsubj", 1),
        ("came", "ROOT", 1),
    ]


def test_copula_makes_a_predicate():
    # y estaba cansado: a nominal predicate without a subject of its own
    doc = parse(
        ["Lo", "pensó", "y", "estaba", "cansado"],
        [1, 1, 4, 4, 1],
        ["obj", "ROOT", "cc", "cop", "conj"],
        pos=["PRON", "VERB", "CCONJ", "AUX", "ADJ"],
    )
    assert is_predicate(doc[4]) and not is_predicate(doc[0])
    assert is_clause_head(doc[4])


@pytest.mark.parametrize(
    "check",
    [
        is_clause_head,
        is_infinitive_clause,
        is_subordinate_clause_head,
        is_infinitive_clause_head,
        predicate_form,
        is_predicate,
        is_passive,
        has_agent,
        is_agentless,
        is_prep_complement,
    ],
)
def test_checks_of_a_token(check):
    with pytest.raises(SourceTypeError, match=r"^A Token is expected, not NoneType$"):
        check(None)
    with pytest.raises(SourceTypeError, match=r"^A Token is expected, not str$"):
        check("came")


def test_error_of_a_hook_on_a_token():
    # An AttributeError of a hook on a real token is no error of the argument
    doc = parse(
        ["Wants", "to", "leave"], [0, 2, 0], ["ROOT", "mark", "xcomp"], ["", "", "VerbForm=Inf"]
    )
    with pytest.raises(AttributeError):
        is_clause_head(doc[2], is_infinitive_periphrasis=lambda token: token.missing)


def test_pickle_without_a_language_and_without_sents():
    import copy
    import pickle

    from spacy.vocab import Vocab

    doc = Doc(
        Vocab(), words=["He", "came"], heads=[1, 1], deps=["nsubj", "ROOT"], pos=["PRON", "VERB"]
    )
    clone = pickle.loads(pickle.dumps(SyntaxStats(doc)))
    assert [token.text for token in clone.sents[0]] == ["He", "came"]
    bare = copy.deepcopy(SyntaxStats.__new__(SyntaxStats))
    assert not hasattr(bare, "sents")


def test_pickle_of_the_object_of_a_component():
    import pickle

    from anyts.components import SyntaxStatsComponent

    nlp = spacy.blank("xx")
    component = SyntaxStatsComponent(nlp, "syntax_pickle")
    doc = component(parse(["He", "came"], [1, 1], ["nsubj", "ROOT"], pos=["PRON", "VERB"]))
    clone = pickle.loads(pickle.dumps(doc._.syntax_pickle))
    assert clone.n_words == 2
