import re
from pathlib import Path

import pytest
import spacy
from spacy.tokens import Doc

import anyts
from anyts import SentsExtractor
from anyts.basic_stats import BasicStats
from anyts.components import StatsComponent
from anyts.constants import MESSAGES
from anyts.diversity_stats import DiversityStats, calc_ttr, calc_windowed, check_params
from anyts.exceptions import ParameterError, SourceError, SourceTypeError, UnknownStatError
from anyts.readability_stats import ReadabilityStats, calc_reading_time

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


CASES = {
    "source_type": (SourceTypeError, lambda: Stats(5)),
    "no_words": (SourceError, lambda: Stats("?!")),
    "no_sentences": (
        SourceError,
        lambda: Readability(TEXT, sents_extractor=SentsExtractor(min_len=1000)),
    ),
    "sents_extractor_type": (SourceTypeError, lambda: Stats(TEXT, sents_extractor=5)),
    "words_extractor_type": (SourceTypeError, lambda: Readability(TEXT, words_extractor=5)),
    "complex_syl_factor": (ParameterError, lambda: Stats(TEXT, complex_syl_factor=0)),
    "long_word_letter_factor": (ParameterError, lambda: Stats(TEXT, long_word_letter_factor=0)),
    "preset_type": (ParameterError, lambda: Readability(TEXT, preset=5)),
    "unknown_preset": (ParameterError, lambda: Readability(TEXT, preset="unknown")),
    "basic_stats_type": (SourceTypeError, lambda: Readability(OtherStats(TEXT))),
    "no_basic_stats_class": (SourceTypeError, lambda: Bare(TEXT)),
    "not_grade_formula": (ParameterError, lambda: Readability(TEXT).describe_grade("lix")),
    "no_scale": (ParameterError, lambda: Readability(TEXT).describe_level("smog_index")),
    "unknown_metric": (UnknownStatError, lambda: Readability(TEXT).describe("unknown")),
    "unknown_norm": (ParameterError, lambda: Readability(TEXT).reading_time_by_norm("unknown")),
    "reading_speed": (ParameterError, lambda: Readability(TEXT).reading_time_by_speed(0)),
    "window_len": (ParameterError, lambda: Diversity(TEXT.split(), window_len=0)),
    "window_step": (ParameterError, lambda: Diversity(TEXT.split()).windowed("ttr", 2, 0)),
    "window_metric": (ParameterError, lambda: calc_windowed(TEXT.split(), 5, messages=OWN)),
    "confidence": (ParameterError, lambda: Diversity(TEXT.split()).windowed("ttr", 2, 1, 2.0)),
    "mtld_threshold": (ParameterError, lambda: Diversity(TEXT.split(), mtld_threshold=2.0)),
    "mtld_min_len": (ParameterError, lambda: Diversity(TEXT.split(), mtld_min_len=-1)),
    "hdd_sample_size": (ParameterError, lambda: Diversity(TEXT.split(), hdd_sample_size=0)),
    "log_base": (ParameterError, lambda: Diversity(TEXT.split(), log_base=1.0)),
    "missing_extension": (SourceError, lambda: component_error("own_factory")),
    "missing_extension_any": (SourceError, lambda: component_error("")),
    "foreign_extension": (ParameterError, foreign_extension),
}


def test_cases_cover_the_messages():
    assert set(CASES) == set(MESSAGES)


@pytest.mark.parametrize("key", CASES)
def test_own_messages(key):
    """A class of a library raises its own message of every key, with the fields filled"""
    error, call = CASES[key]
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
