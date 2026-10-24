import re
import sys
import unicodedata
from collections import Counter
from typing import ClassVar

import numpy as np
import pandas as pd
import pytest
import spacy

from anyts import SentsExtractor, WordsExtractor
from anyts.basic_stats import (
    DASH_PATTERN,
    PUNCTUATION_MARKS,
    BasicStats,
    count_punctuations,
    dash_pattern,
)
from anyts.components import start_sents_after_blank_lines
from anyts.constants import BASIC_STATS_DESC, PUNCTUATION_TYPES, SPACES
from anyts.exceptions import ParameterError, SourceError, SourceTypeError, UnknownStatError

VOWELS = re.compile(r"[aeiouy]+", re.IGNORECASE)


class Stats(BasicStats):
    """A library whose syllables are the groups of vowels"""

    def count_syllables(self, word):
        return len(VOWELS.findall(word))


TEXT = (
    "Thesauri are a special class of lexicographic resources with the following features:"
    " the completeness of the meanings of the vocabulary of a language or of some of its"
    " segments; the thematic, or ideographic, ordering of the meanings of the words."
    " The difference between thesauri and formal ontologies lies in the way out to the"
    " sphere of lexical meanings, in the relations not only between the meanings and the"
    " words that express them, but also between the meanings themselves (the record of"
    " various semantic relations within the dictionary)."
)


@pytest.fixture(scope="module")
def bs():
    return Stats(TEXT, normalize=True)


def test_small_text():
    bs = Stats("The cat sat on the mat. A beautiful day!")
    assert bs.c_letters == {1: 1, 2: 1, 3: 6, 9: 1}
    assert bs.c_syllables == {1: 8, 3: 1}
    assert (bs.n_sents, bs.n_words, bs.n_unique_words) == (2, 9, 8)
    assert (bs.n_long_words, bs.n_complex_words, bs.n_simple_words) == (1, 1, 8)
    assert (bs.n_monosyllable_words, bs.n_polysyllable_words) == (8, 1)
    assert (bs.n_chars, bs.n_letters, bs.n_spaces, bs.n_syllables) == (40, 30, 8, 11)
    assert bs.n_punctuations == 2
    assert {kind: count for kind, count in bs.c_punctuations.items() if count} == {
        "period": 1,
        "exclamation": 1,
    }


def test_counts_against_a_recount(bs):
    words = WordsExtractor().extract(TEXT)
    letters = Counter(sum(char.isalpha() for char in word) for word in words)
    syllables = Counter(len(VOWELS.findall(word)) for word in words)
    assert bs.c_letters == dict(sorted(letters.items()))
    assert bs.c_syllables == dict(sorted(syllables.items()))
    assert bs.n_words == len(words)
    assert bs.n_unique_words == len({word.lower() for word in words})
    assert bs.n_long_words == sum(count for n, count in letters.items() if n >= 7)
    assert bs.n_complex_words == sum(count for n, count in syllables.items() if n >= 3)
    assert bs.n_simple_words == sum(count for n, count in syllables.items() if 0 < n < 3)
    assert bs.n_monosyllable_words == syllables[1]
    assert bs.n_polysyllable_words == bs.n_words - syllables[1] - syllables[0]
    assert bs.n_syllables == sum(n * count for n, count in syllables.items())
    assert bs.n_sents == 2
    assert bs.n_chars == len(TEXT)
    assert bs.n_letters == sum(char.isalpha() for char in TEXT)
    assert bs.n_spaces == TEXT.count(" ")
    assert bs.n_punctuations == sum(bs.c_punctuations.values()) == 10


def test_normalized_stats(bs):
    assert bs.p_unique_words == bs.n_unique_words / bs.n_words
    assert bs.p_long_words == bs.n_long_words / bs.n_words
    assert bs.p_complex_words == bs.n_complex_words / bs.n_words
    assert bs.p_simple_words == bs.n_simple_words / bs.n_words
    assert bs.p_monosyllable_words == bs.n_monosyllable_words / bs.n_words
    assert bs.p_polysyllable_words == bs.n_polysyllable_words / bs.n_words
    assert bs.p_letters == bs.n_letters / bs.n_chars
    assert bs.p_spaces == bs.n_spaces / bs.n_chars
    assert bs.p_punctuations == bs.n_punctuations / bs.n_chars
    assert not hasattr(Stats(TEXT), "p_unique_words")


@pytest.mark.parametrize("source", ["Hello. ?! Bye.", "Hello.\n...\nBye."])
def test_sentences_without_words_are_not_counted(source):
    assert Stats(source).n_sents == 2


def test_blank_line_ends_a_sentence():
    assert Stats("Notes without a dot\n\nThe cat sleeps").n_sents == 2


def test_sentences_without_words_are_not_counted_in_a_doc():
    nlp = spacy.blank("xx")
    nlp.add_pipe("sentencizer")
    assert Stats(nlp("Hello. ?! Bye.")).n_sents == 2


def test_errors():
    with pytest.raises(SourceError, match=r"^The data source has no words$"):
        Stats("+ _")
    with pytest.raises(SourceError):
        Stats(spacy.blank("xx")("... !"))
    for source, name in ((666, "int"), (["a", "b"], "list"), ({"a": "b"}, "dict")):
        with pytest.raises(SourceTypeError, match=rf"^The data source cannot be of type {name}$"):
            Stats(source)
    with pytest.raises(
        SourceTypeError, match=r"^The data source cannot be a Span: pass span\.as_doc\(\)$"
    ):
        Stats(spacy.blank("en")("The cat sleeps")[:2])
    with pytest.raises(SourceTypeError, match=r"must be a SentsExtractor$"):
        Stats(TEXT, sents_extractor=WordsExtractor())
    with pytest.raises(SourceTypeError, match=r"must be a WordsExtractor$"):
        Stats(TEXT, words_extractor=SentsExtractor())
    for kwargs in (
        {"complex_syl_factor": 0},
        {"long_word_letter_factor": -1},
        {"complex_syl_factor": 3.0},
        {"long_word_letter_factor": True},
    ):
        with pytest.raises(ParameterError):
            Stats(TEXT, **kwargs)


def test_count_syllables_is_required():
    with pytest.raises(TypeError, match="abstract"):
        BasicStats(TEXT)


def test_count_words_by(bs):
    assert bs.count_words_by_syllables(3) == bs.n_complex_words
    assert bs.count_words_by_letters(7) == bs.n_long_words
    with pytest.raises(ParameterError, match="must be an integer"):
        bs.count_words_by_syllables(2.5)
    with pytest.raises(ParameterError, match="must be an integer"):
        bs.count_words_by_letters("7")


def test_custom_factors():
    bs = Stats(
        "The cat sat on the mat. A beautiful day!", complex_syl_factor=2, long_word_letter_factor=3
    )
    assert (bs.n_complex_words, bs.n_simple_words, bs.n_long_words) == (1, 8, 7)
    assert (bs.complex_syl_factor, bs.long_word_letter_factor, bs.normalize) == (2, 3, False)


def test_letters_only():
    bs = Stats("well-known abcdefg 1234567 cat")
    assert bs.c_letters == {0: 1, 3: 1, 4: 1, 5: 1, 7: 1}
    assert bs.n_letters == 19
    assert Stats("The cat sleeps.\r\nThe dog eats.").n_chars == (
        Stats("The cat sleeps.\nThe dog eats.").n_chars
    )


def test_custom_extractors():
    bs = Stats(
        "one, two; three, four",
        sents_extractor=SentsExtractor(tokenizer=re.compile(r"; ")),
        words_extractor=WordsExtractor(tokenizer=re.compile(r"[,; ]+")),
    )
    assert (bs.n_sents, bs.n_words) == (2, 4)


def test_extractor_classes_and_hyphens():
    class Parts(SentsExtractor):
        def sentenize(self, text):
            return text.split(";")

    class Words(WordsExtractor):
        def __init__(self):
            super().__init__(stopwords=["one"])

    class Joined(Stats):
        sents_extractor_class = Parts
        words_extractor_class = Words
        join_hyphens = True

    assert (Joined("one two; three").n_sents, Joined("one two; three").n_words) == (2, 2)
    assert (Stats("one two; three").n_sents, Stats("one two; three").n_words) == (1, 3)
    # A Doc without sentence boundaries takes its sentences from the class, its words from tokens
    blank = spacy.blank("xx")("one two; three")
    assert (Joined(blank).n_sents, Joined(blank).n_words) == (2, 3)
    doc = spacy.blank("xx")("A well-known cat.")
    assert (Stats(doc).n_words, Joined(doc).n_words) == (4, 3)


def test_doc_without_sentence_boundaries(bs):
    doc = spacy.blank("xx")(TEXT)
    assert not doc.has_annotation("SENT_START")
    assert Stats(doc, normalize=True).get_stats() == bs.get_stats()


def test_doc_with_sentence_boundaries(bs):
    nlp = spacy.blank("xx")
    nlp.add_pipe("sentencizer")
    assert Stats(nlp(TEXT), normalize=True).get_stats() == bs.get_stats()


def test_doc_with_partial_sentence_boundaries():
    """The starts after the blank lines alone leave the sentences to the extractor"""
    text = "The cat sleeps. The dog eats\n\nThe bird sings. It flies."
    doc = start_sents_after_blank_lines(spacy.blank("xx")(text))
    assert Stats(doc).n_sents == Stats(text).n_sents == 4


def test_doc_with_extractors():
    """An extractor passed explicitly is used for a Doc too, on its text"""
    nlp = spacy.blank("xx")
    nlp.add_pipe("sentencizer")
    doc = nlp("The thesauri are a class. The THESAURI are a class.")
    words_extractor = WordsExtractor(stopwords=["the", "a"], lowercase=True)
    assert Stats(doc, words_extractor=words_extractor).n_words == 6
    assert Stats(doc.text, words_extractor=words_extractor).n_words == 6
    assert Stats(doc, sents_extractor=SentsExtractor(tokenizer=re.compile(r"\. "))).n_sents == 2
    assert Stats(doc, sents_extractor=SentsExtractor(min_len=1000)).n_sents == 0


def test_count_punctuations_hook():
    class Marks(Stats):
        def count_punctuations(self, text):
            return {"marks": text.count("!")}

    bs = Marks("Wow! Wow!")
    assert (bs.c_punctuations, bs.n_punctuations) == ({"marks": 2}, 2)


NORMALIZED = (
    "p_unique_words",
    "p_long_words",
    "p_complex_words",
    "p_simple_words",
    "p_monosyllable_words",
    "p_polysyllable_words",
    "p_letters",
    "p_spaces",
    "p_punctuations",
)


def test_get_stats(bs):
    stats = bs.get_stats()
    names = ("c_letters", "c_syllables", *BASIC_STATS_DESC, "c_punctuations", *NORMALIZED)
    assert tuple(stats) == bs.stat_names() == names
    for key in names:
        assert stats[key] == getattr(bs, key)
    assert tuple(Stats(TEXT).get_stats()) == names[: -len(NORMALIZED)]
    stats["n_words"] = -1
    stats["c_letters"][2] = -1
    assert bs.n_words > 0 and bs.c_letters[2] > 0


def test_get_stats_flat(bs):
    stats = bs.get_stats(flat=True)
    assert stats["c_letters_3"] == bs.c_letters[3]
    assert [key for key in stats if key.startswith("c_letters_")] == [
        f"c_letters_{letters}" for letters in bs.c_letters
    ]
    assert stats["c_punctuations_comma"] == bs.c_punctuations["comma"] == 4
    assert stats["p_letters"] == bs.p_letters
    assert not any(isinstance(value, dict) for value in stats.values())
    assert list(bs.to_dataframe().columns) == list(stats)


def test_describe(bs):
    assert bs.describe("n_words") is None
    assert bs.describe("c_letters") is None
    with pytest.raises(UnknownStatError, match=r"^Unknown statistic: p_letters"):
        Stats(TEXT).describe("p_letters")
    with pytest.raises(UnknownStatError, match=r"^Unknown statistic: normalize"):
        bs.describe("normalize")


def test_print_stats(capsys, bs):
    bs.print_stats()
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].split("|")[0].strip() == "Statistic"
    assert len(lines) == len(BASIC_STATS_DESC) + 2
    assert [cell.strip() for cell in lines[3].split("|")] == ["Words", str(bs.n_words)]

    class Labelled(Stats):
        stats_desc: ClassVar[dict[str, str]] = {"n_words": "Palabras"}
        stats_headers = ("Estadística", "Valor")

    labelled = Labelled(TEXT)
    assert tuple(labelled.get_stats()) == ("c_letters", "c_syllables", "n_words", "c_punctuations")
    labelled.print_stats()
    assert capsys.readouterr().out.splitlines()[::2] == [
        f"{'Estadística':^12}|{'Valor':^10}",
        f"{'Palabras':12}|{bs.n_words:^10}",
    ]


def test_count_punctuations():
    text = (
        "The cat — «beast»... The dog, sure, - friend; and “someone” (who lives) – no!"
        ' ¿So? "Yes". ‘Now’ 5…'
    )
    assert count_punctuations(text) == {
        "comma": 2,
        "period": 1,
        "question": 2,
        "exclamation": 1,
        "ellipsis": 2,
        "colon": 0,
        "semicolon": 1,
        "dash": 3,
        "hyphen": 0,
        "angle_quotes": 2,
        "straight_quotes": 6,
        "parentheses": 2,
        "other": 0,
    }
    assert count_punctuations("Hi.... Bye....... Yes") == {
        **dict.fromkeys(PUNCTUATION_TYPES, 0),
        "ellipsis": 2,
    }
    assert count_punctuations("") == dict.fromkeys(PUNCTUATION_TYPES, 0)
    with pytest.raises(SourceTypeError, match=r"^A text string is expected, not int$"):
        count_punctuations(5)


def test_count_punctuations_inverted_marks():
    counts = count_punctuations("¿Who?.. ¡Nobody!.. They left... ¿Yes?.")
    assert (counts["question"], counts["exclamation"], counts["ellipsis"], counts["period"]) == (
        4,
        2,
        3,
        1,
    )
    assert count_punctuations("¿¡What!?")["question"] == 2
    assert count_punctuations("¿¡What!?")["exclamation"] == 2


def test_count_punctuations_other_marks():
    counts = count_punctuations("He said ‹so› and «so» § 5 € 20° ‰ † „so“")
    assert (counts["angle_quotes"], counts["straight_quotes"], counts["other"]) == (2, 1, 8)
    for char in "‹›§€°‰†„":
        assert count_punctuations(f"a {char} b")["other"] == 1
    assert count_punctuations("He said: ‘It is done’")["straight_quotes"] == 2


def test_count_punctuations_marks_and_dashes():
    marks = {"„": "straight_quotes", "!": "exclamation"}
    counts = count_punctuations("„so“ - yes!", marks=marks, dash_pattern=re.compile(r" - "))
    assert (counts["straight_quotes"], counts["exclamation"], counts["dash"]) == (1, 1, 1)
    assert counts["other"] == 1
    # A mark given the type other is counted with the other marks
    counts = count_punctuations("¿So? §", marks={**PUNCTUATION_MARKS, "¿": "other"})
    assert (counts["question"], counts["other"]) == (1, 2)


@pytest.mark.parametrize(
    ("kwargs", "error", "message"),
    [
        ({"marks": {"!": "bang"}}, ParameterError, r"^Unknown type of the mark '!': 'bang'\."),
        ({"marks": {"!": ["exclamation"]}}, ParameterError, r"^Unknown type of the mark '!'"),
        ({"marks": {"!!": "exclamation"}}, ParameterError, r"single character, not '!!'$"),
        ({"marks": {1: "exclamation"}}, ParameterError, r"single character, not 1$"),
        ({"marks": ["!"]}, SourceTypeError, r"^The marks must be a mapping, not list$"),
        ({"dash_pattern": " - "}, SourceTypeError, r"compiled regular expression, not str$"),
    ],
)
def test_count_punctuations_hook_errors(kwargs, error, message):
    with pytest.raises(error, match=message):
        count_punctuations("Hello", **kwargs)


@pytest.mark.parametrize(
    ("text", "dashes", "hyphens"),
    [
        ("- They left, - he said.\n- Yes-yes, - someone answered - and all.\n-", 6, 1),
        ("How young I am - and I know no fear.", 1, 0),
        ("theoretical-practical", 0, 1),
        ("house -\nmuseum", 1, 0),
        ("-Hello -said John.", 2, 0),
        ("-¿Coming? -she asked.", 2, 0),
        ("Yes -he said- sure.", 2, 0),
        ("—Hello —said John—.", 3, 0),
        ("-5 degrees and -3", 0, 2),
        ("1990-1995", 0, 1),
        ("London - Paris 2-1", 1, 1),
        ("wo-\nrd", 0, 1),
        ("a jus-\ntified text with two wo-\nrds", 0, 2),
        ("all -\nnothing", 1, 0),
        ("end-", 1, 0),
        # Two or three hyphens are one dash, as a hyphen glued after a closing mark
        ("--Hello --said John.", 2, 0),
        ("yes--he said", 1, 0),
        ("---Bye", 1, 0),
        ("of-----", 1, 0),
        ("four.-¿Five?", 1, 0),
        ("said:-¡Go!", 1, 0),
        # After an ellipsis, a horizontal bar, an underscore of italics, before an opening mark
        ("-I don't know...-he said.", 2, 0),
        ("-I don't know…-he said.", 2, 0),
        ("―¿What? ―he said―.", 3, 0),
        ("lux_-he said", 1, 0),
        ("Well yes-¿and what?", 1, 0),
        # A closing dash between a letter and a closing mark
        ("-Hello -said John-. And he left.", 3, 0),
        ("-Hello -said John-, and he left.", 3, 0),
        ("-Yes -he said-; no.", 3, 0),
        ("-¿What? -said Ann-! well", 3, 0),
        ("socio-economic.", 0, 1),
        ("e-mail.", 0, 1),
        # A hanging hyphen before any space of Unicode or a tab, not before a line break
        ("one-\u00a0two", 1, 0),
        ("one-\u202ftwo", 1, 0),
        ("one-\ttwo", 1, 0),
    ],
)
def test_count_punctuations_dashes(text, dashes, hyphens):
    counts = count_punctuations(text)
    assert (counts["dash"], counts["hyphen"]) == (dashes, hyphens)


def test_multichar_punctuation():
    bs = Stats("¡¡¡Hurray!!! ¿¡Hurray!? Hurray... Word – word… and §1")
    assert bs.n_words == 7
    assert bs.n_punctuations == 14 == sum(bs.c_punctuations.values())
    assert bs.c_punctuations["exclamation"] == 8
    assert bs.c_punctuations["other"] == 1


@pytest.mark.parametrize(
    ("text", "conjunctions", "before_comma", "dashes", "hyphens"),
    [
        ("pre- and post-war", ["and", "or"], False, 0, 2),
        ("pre- or post-war - he said", ["and", "or"], False, 1, 2),
        ("pre- andante", ["and"], False, 1, 0),
        ("two-, three- and four-year", ["and"], True, 0, 3),
        # Without the comma rule the hyphen before a comma closes a dialogue line
        ("two-, three- and four-year", ["and"], False, 1, 2),
        ("-Come -he said-, and left", ["and"], False, 3, 0),
        ("Yes- he said", ["and"], True, 1, 0),
        ("pre-- and post-war", ["and"], True, 1, 1),
        ("двух- и трёхкомнатные", ["и", "или"], True, 0, 1),
        ("5- and 10-year bonds", ["and"], False, 0, 2),
        ("2-, 3- и 4-комнатные", ["и"], True, 0, 3),
        ("PRE- AND POST-WAR", ["and"], False, 0, 2),
        # A spaced dash after a number stays a dash
        ("It was 5 - and that was all", ["and"], True, 1, 0),
    ],
)
def test_dash_pattern_hanging_hyphens(text, conjunctions, before_comma, dashes, hyphens):
    counts = count_punctuations(text, dash_pattern=dash_pattern(conjunctions, before_comma))
    assert (counts["dash"], counts["hyphen"]) == (dashes, hyphens)


def test_dash_pattern_default():
    assert dash_pattern().pattern == DASH_PATTERN.pattern
    assert dash_pattern(set(), False).pattern == DASH_PATTERN.pattern
    assert dash_pattern(["or", "and"]).pattern == dash_pattern({"and", "or"}).pattern


def test_dash_pattern_of_an_array():
    pattern = dash_pattern(["or", "and"]).pattern
    assert dash_pattern(np.array(["or", "and"])).pattern == pattern
    assert dash_pattern(pd.Series(["or", "and"])).pattern == pattern
    assert dash_pattern(np.array([], dtype=str), False).pattern == DASH_PATTERN.pattern


@pytest.mark.parametrize(
    ("conjunctions", "error"),
    [
        ("and", SourceTypeError),
        ([1], SourceTypeError),
        (iter(["and"]), SourceTypeError),
        ([""], ParameterError),
    ],
)
def test_dash_pattern_errors(conjunctions, error):
    with pytest.raises(error):
        dash_pattern(conjunctions)


def test_spaces_of_unicode():
    separators = {chr(code) for code in range(sys.maxunicode + 1)}
    assert set(SPACES) == {char for char in separators if unicodedata.category(char) == "Zs"} | {
        "\t"
    }
    # a no-break space, a narrow one, an ideographic one, a space and a tab; not a line break
    bs = Stats("one\u00a0two\u202fthree\u3000four five\tsix\nseven", normalize=True)
    assert bs.n_spaces == 5
    assert bs.p_spaces == 5 / bs.n_chars


@pytest.mark.parametrize("space", [" ", "\u00a0", "\u202f", "\t"])
def test_hanging_hyphen_before_a_conjunction_after_any_space(space):
    counts = count_punctuations(f"pre-{space}and post-war", dash_pattern=dash_pattern(["and"]))
    assert (counts["dash"], counts["hyphen"]) == (0, 2)


def test_normalize_is_a_bool():
    with pytest.raises(ParameterError, match=r"^The normalization must be a bool, not str$"):
        Stats(TEXT, normalize="yes")
