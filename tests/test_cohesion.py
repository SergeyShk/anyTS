import os
import random
import subprocess
import sys
from fractions import Fraction
from itertools import combinations
from math import isnan

import pytest
import spacy

from anyts.cohesion import (
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
from anyts.exceptions import SourceTypeError


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
    sets = [{str(rng.randrange(12)) for _ in range(rng.randrange(5))} for _ in range(40)]
    overlap = calc_overlaps(sets)
    assert isinstance(overlap, Overlap)
    assert overlap.adjacent == pytest.approx(calc_overlap(sets))
    assert overlap.all == pytest.approx(calc_overlap(sets, adjacent=False))
    assert overlap.prop_adjacent == pytest.approx(calc_proportional_overlap(sets))
    assert overlap.prop_all == pytest.approx(calc_proportional_overlap(sets, adjacent=False))


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
        "from anyts.cohesion import _sum_dice\n"
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
    doc = spacy.blank("xx")("The cat. The dog.")
    with pytest.raises(SourceTypeError, match=r"not a Doc"):
        func(doc)


def test_dominant_checked():
    with pytest.raises(SourceTypeError, match=r"^A list of values is expected, not a string$"):
        dominant("Pres")
