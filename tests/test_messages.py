import pickle
import re
from pathlib import Path
from typing import ClassVar

import pytest
import spacy
from spacy.tokens import Doc

import anyts
from anyts import CharNgramsExtractor, SentsExtractor, WordsExtractor
from anyts.basic_stats import BasicStats
from anyts.cohesion import ConnectorMatcher
from anyts.components import StatsComponent
from anyts.constants import MESSAGES
from anyts.corpus import sentence_rhythm, split_windows
from anyts.diversity_stats import DiversityStats, calc_ttr, calc_windowed, check_params
from anyts.exceptions import ParameterError, SourceError, SourceTypeError, UnknownStatError
from anyts.lexical_stats import LexicalStats, LexicalWord
from anyts.phon_stats import PhonStats
from anyts.readability_stats import ReadabilityStats, calc_reading_time
from anyts.style_stats import StyleStats
from anyts.syntax_stats import SyntaxStats
from anyts.utils import check_messages

# Messages of a language library: every message differs from the default and keeps its fields
OWN = {key: f"Own: {message}" for key, message in MESSAGES.items()}
TEXT = "The cat sleeps on the mat. The dog barks."


class Stats(BasicStats):
    messages = OWN

    def count_syllables(self, word):
        return 1


class OtherStats(BasicStats):
    def count_syllables(self, word):
        return 1


class Readability(ReadabilityStats):
    basic_stats_class = Stats
    messages = OWN


class Bare(ReadabilityStats):
    basic_stats_class = None
    messages = OWN


class Diversity(DiversityStats):
    messages = OWN


class Sents(SentsExtractor):
    messages = OWN


class Words(WordsExtractor):
    messages = OWN


class CharNgrams(CharNgramsExtractor):
    messages = OWN


class Matcher(ConnectorMatcher):
    messages = OWN


class Style(StyleStats):
    messages = OWN


class Frequencies:
    min_ipm = 1.0

    def lookup(self, lemma):
        return None

    def ipm(self, lemma):
        return 0.0


class Lexical(LexicalStats):
    messages = OWN

    def analyze(self, source):
        return [LexicalWord(word, word, True) for word in source.split()]


class Checked(Lexical):
    freq_dict_class = Frequencies


class Phon(PhonStats):
    messages = OWN

    def syllabify(self, word):
        return [word]


class Syntax(SyntaxStats):
    messages = OWN


class Lemmas(Syntax):
    requires_lemmas = True


VOCAB = spacy.blank("xx").vocab
PARSED = Doc(VOCAB, words=["Yes"], heads=[0], deps=["ROOT"])


class Component(StatsComponent):
    messages = OWN

    def compute(self, doc):
        return self.from_extension(doc, "own_missing", DiversityStats, self.factory)


def component_error(factory):
    nlp = spacy.blank("en")
    component = Component(nlp, "own_component")
    component.factory = factory
    return component(nlp(TEXT))


def foreign_extension():
    Doc.set_extension("own_foreign", getter=lambda doc: 0)
    try:
        Component(spacy.blank("en"), "own_foreign")
    finally:
        Doc.remove_extension("own_foreign")


def foreign_extension_on_unpickling():
    data = pickle.dumps(Component(spacy.blank("en"), "own_unpickled"))
    Doc.remove_extension("own_unpickled")
    Doc.set_extension("own_unpickled", getter=lambda doc: 0)
    try:
        pickle.loads(data)
    finally:
        Doc.remove_extension("own_unpickled")


WORDS = TEXT.split()
# One case for every raise site of the classes, a key raised at several sites several times
CASES = [
    ("source_type", SourceTypeError, lambda: Stats(5)),
    ("no_words", SourceError, lambda: Stats("?!")),
    ("no_words", SourceError, lambda: Diversity([])),
    (
        "no_sentences",
        SourceError,
        lambda: Readability(TEXT, sents_extractor=SentsExtractor(min_len=1000)),
    ),
    ("sents_extractor_type", SourceTypeError, lambda: Stats(TEXT, sents_extractor=5)),
    ("words_extractor_type", SourceTypeError, lambda: Readability(TEXT, words_extractor=5)),
    ("complex_syl_factor", ParameterError, lambda: Stats(TEXT, complex_syl_factor=0)),
    ("long_word_letter_factor", ParameterError, lambda: Stats(TEXT, long_word_letter_factor=0)),
    ("preset_type", ParameterError, lambda: Readability(TEXT, preset=5)),
    ("unknown_preset", ParameterError, lambda: Readability(TEXT, preset="unknown")),
    ("basic_stats_type", SourceTypeError, lambda: Readability(OtherStats(TEXT))),
    ("no_basic_stats_class", SourceTypeError, lambda: Bare(TEXT)),
    ("not_grade_formula", ParameterError, lambda: Readability(TEXT).describe_grade("lix")),
    ("no_scale", ParameterError, lambda: Readability(TEXT).describe_level("smog_index")),
    ("unknown_stat", UnknownStatError, lambda: Stats(TEXT).describe("unknown")),
    ("unknown_stat", UnknownStatError, lambda: Readability(TEXT).describe("unknown")),
    ("unknown_stat", UnknownStatError, lambda: Diversity(WORDS).windowed("unknown")),
    ("unknown_norm", ParameterError, lambda: Readability(TEXT).reading_time_by_norm("unknown")),
    ("reading_speed", ParameterError, lambda: Readability(TEXT).reading_time_by_speed(0)),
    ("window_len", ParameterError, lambda: Diversity(WORDS, window_len=0)),
    ("window_len", ParameterError, lambda: Diversity(WORDS).windowed("ttr", 0)),
    ("window_step", ParameterError, lambda: Diversity(WORDS).windowed("ttr", 2, 0)),
    ("window_metric", ParameterError, lambda: calc_windowed(WORDS, 5, messages=OWN)),
    ("confidence", ParameterError, lambda: Diversity(WORDS).windowed("ttr", 2, 1, 2.0)),
    ("mtld_threshold", ParameterError, lambda: Diversity(WORDS, mtld_threshold=2.0)),
    ("mtld_min_len", ParameterError, lambda: Diversity(WORDS, mtld_min_len=-1)),
    ("hdd_sample_size", ParameterError, lambda: Diversity(WORDS, hdd_sample_size=0)),
    ("log_base", ParameterError, lambda: Diversity(WORDS, log_base=1.0)),
    ("missing_extension", SourceError, lambda: component_error("own_factory")),
    ("missing_extension_any", SourceError, lambda: component_error("")),
    ("foreign_extension", ParameterError, foreign_extension),
    ("foreign_extension", ParameterError, foreign_extension_on_unpickling),
    ("sent_len_bounds", ParameterError, lambda: Sents(min_len=-1)),
    ("sent_len_order", ParameterError, lambda: Sents(min_len=5, max_len=2)),
    ("word_len_bounds", ParameterError, lambda: Words(max_len=-1)),
    ("word_len_order", ParameterError, lambda: Words(min_len=5, max_len=2)),
    ("ngram_range", ParameterError, lambda: Words(ngram_range=(1,))),
    ("ngram_lower", ParameterError, lambda: Words(ngram_range=(0, 1))),
    ("ngram_order", ParameterError, lambda: Words(ngram_range=(2, 1))),
    ("ngram_len", ParameterError, lambda: CharNgrams(n=0)),
    ("top_words", ParameterError, lambda: Words().get_most_common(0)),
    ("top_ngrams", ParameterError, lambda: CharNgrams().get_most_common(0)),
    ("text_type", SourceTypeError, lambda: Sents().extract(5)),
    ("text_type", SourceTypeError, lambda: Words().extract(5)),
    ("text_type", SourceTypeError, lambda: CharNgrams().extract(5)),
    ("tokenizer", SourceTypeError, lambda: Words(tokenizer=5).extract(TEXT)),
    ("tokenizer_iterable", SourceTypeError, lambda: Words(tokenizer=len).extract(TEXT)),
    (
        "tokenizer_strings",
        SourceTypeError,
        lambda: Words(tokenizer=lambda text: [1]).extract(TEXT),
    ),
    ("connector_dict", SourceTypeError, lambda: Matcher(["and"])),
    ("connector_entry", SourceTypeError, lambda: Matcher({"and": "additive"})),
    ("connector_pos_type", SourceTypeError, lambda: Matcher({}).find(["and"], pos=[1])),
    ("connector_class", ParameterError, lambda: Matcher({"and": ("other", "primary")})),
    ("connector_pos", ParameterError, lambda: Matcher({}).find(["and"], pos=[])),
    ("text_type", SourceTypeError, lambda: split_windows(5, messages=OWN)),
    ("window_len", ParameterError, lambda: split_windows(TEXT, 0, messages=OWN)),
    ("min_words", ParameterError, lambda: split_windows(TEXT, 5, 0, messages=OWN)),
    ("min_words_window", ParameterError, lambda: split_windows(TEXT, 5, 6, messages=OWN)),
    ("sentence_lengths", SourceTypeError, lambda: sentence_rhythm([1.5], messages=OWN)),
    ("negative_lengths", ParameterError, lambda: sentence_rhythm([-1], messages=OWN)),
    ("top_n", ParameterError, lambda: Style(TEXT, top_n=0)),
    ("freq_dict_type", SourceTypeError, lambda: Checked(TEXT, freq_dict={})),
    ("no_freq_dict_class", SourceTypeError, lambda: Lexical(TEXT)),
    ("bands_type", ParameterError, lambda: Lexical(TEXT, Frequencies()).band_coverage(5)),
    ("band_bound", ParameterError, lambda: Lexical(TEXT, Frequencies()).band_coverage([0])),
    ("phon_window_len", ParameterError, lambda: Phon(TEXT, window_len=1)),
    ("source_type", SourceTypeError, lambda: Syntax("Yes")),
    ("no_parse", SourceError, lambda: Syntax(Doc(VOCAB, words=["Yes"]))),
    ("no_lemmas", SourceError, lambda: Lemmas(PARSED)),
    ("no_words", SourceError, lambda: Syntax(Doc(VOCAB, words=["."], heads=[0], deps=["ROOT"]))),
    (
        "phon_classes",
        ParameterError,
        lambda: type("Bad", (Phon,), {"vowels": frozenset("a"), "skipped": frozenset("a")}),
    ),
]


def test_cases_cover_the_messages():
    assert {key for key, _, _ in CASES} == set(MESSAGES)


@pytest.mark.parametrize(("key", "error", "call"), CASES, ids=[key for key, _, _ in CASES])
def test_own_messages(key, error, call):
    """A class of a library raises its own message at every site, with the fields filled"""
    with pytest.raises(error) as raised:
        call()
    message = str(raised.value).strip("'")
    assert message.startswith("Own: ")
    pattern = re.escape(OWN[key])
    pattern = re.sub(r"\\\{\w+\\\}", ".+", pattern)
    assert re.fullmatch(pattern, message)
    assert "{" not in message


def test_messages_of_functions():
    """A function takes the messages as a parameter with the English default"""
    with pytest.raises(ParameterError, match=r"^Own: The reading speed"):
        calc_reading_time(10, 0, messages=OWN)
    with pytest.raises(ParameterError, match=r"^Own: The window size"):
        check_params(window_len=0, messages=OWN)
    with pytest.raises(ParameterError, match=r"^The window size"):
        calc_windowed(TEXT.split(), calc_ttr, 0)


def test_every_message_is_raised():
    """No message of MESSAGES is left unused by the code"""
    code = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path(anyts.__file__).parent.rglob("*.py")
        if path.name != "constants.py"
    )
    assert {key for key in MESSAGES if f'"{key}"' in code} == set(MESSAGES)


@pytest.mark.parametrize(
    ("messages", "match"),
    [
        (["no_words"], "must be a mapping"),
        ({"no_words": "No words"}, "lack the keys"),
        ({**MESSAGES, "unknown": "Unknown"}, "Unknown messages"),
        ({**MESSAGES, "no_words": 5}, "must be strings"),
        ({**MESSAGES, "unknown_norm": "Norm {name}"}, "unknown fields"),
        ({**MESSAGES, "unknown_norm": "Norm {norm"}, "not a format string"),
    ],
)
def test_check_messages(messages, match):
    with pytest.raises(ParameterError, match=match):
        check_messages(messages)


@pytest.mark.parametrize(
    "base",
    [
        BasicStats,
        ReadabilityStats,
        DiversityStats,
        StatsComponent,
        SentsExtractor,
        WordsExtractor,
        CharNgramsExtractor,
        ConnectorMatcher,
    ],
)
def test_messages_checked_when_a_class_is_defined(base):
    """A library learns of a wrong message when it defines its class, not when a user errs"""
    with pytest.raises(ParameterError, match="lack the keys"):

        class Incomplete(base):
            messages: ClassVar[dict[str, str]] = {"no_words": "No words"}


def test_doubled_braces():
    braces = {**MESSAGES, "no_words": "{No} words", "unknown_norm": "{{{norm}}}"}
    check_messages(braces)

    class Braces(Diversity):
        messages = braces

    with pytest.raises(SourceError, match=r"^\{No\} words$"):
        Braces([])
