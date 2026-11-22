import io
import pickle
import re
import tempfile
import zipfile
from pathlib import Path
from typing import ClassVar
from unittest import mock

import pandas as pd
import pytest
import spacy
from spacy.tokens import Doc

import anyts
from anyts import CharNgramsExtractor, SentsExtractor, WordsExtractor, datasets
from anyts.basic_stats import BasicStats
from anyts.cohesion_stats import CohesionStats, ConnectorMatcher
from anyts.components import (
    CohesionStatsComponent,
    DiversityStatsComponent,
    LexicalStatsComponent,
    PhonStatsComponent,
    ReadabilityStatsComponent,
    StatsComponent,
    StyleStatsComponent,
    UnadaptedReadabilityStatsComponent,
)
from anyts.constants import MESSAGES
from anyts.corpus import (
    FrequencyReference,
    bootstrap_median_diff,
    check_comparison_params,
    collocations,
    compare_features,
    delta,
    delta_profiles,
    dispersion,
    format_kwic,
    frequency_table,
    holm_correction,
    keyness,
    kwic,
    rolling_delta,
    sentence_rhythm,
    split_windows,
    z_scores,
    zeta_segments,
)
from anyts.datasets import (
    download_file,
    extract_archive,
    fetch_archive,
    length_filters,
    sha256,
    substring_filter,
    to_path,
)
from anyts.diversity_stats import DiversityStats, calc_ttr, calc_windowed, check_params
from anyts.document import document_part, to_document
from anyts.exceptions import (
    DataFileError,
    DownloadError,
    ParameterError,
    SourceError,
    SourceTypeError,
    UnknownStatError,
)
from anyts.lexical_stats import LexicalStats, LexicalWord
from anyts.morph_stats import MorphStats
from anyts.phon_stats import PhonStats
from anyts.readability_stats import ReadabilityStats, calc_reading_time
from anyts.stats import stats_dataframe
from anyts.style_stats import StyleStats, WordFlags
from anyts.syntax_stats import SyntaxStats
from anyts.unadapted_readability_stats import UnadaptedReadabilityStats
from anyts.utils import check_counts, check_messages
from anyts.visualizers.highlight import Highlight, HighlightedText
from anyts.visualizers.highlight import check_params as check_highlight_params

# Messages of a language library: every message differs from the default and keeps its fields
OWN = {key: f"Own: {message}" for key, message in MESSAGES.items()}
TEXT = "The cat sleeps on the mat. The dog barks."
WORDS = ["the", "cat", "sleeps", "the", "cat"]
UNITS = {"a": ["x"], "b": ["y"]}
TEN = ["a"] * 10
LONG = {"A": TEN, "B": TEN}
FEATURES = pd.DataFrame({"a": [1.0, 2.0]})


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


class Unadapted(UnadaptedReadabilityStats):
    basic_stats_class = Stats
    messages = OWN


class BareUnadapted(UnadaptedReadabilityStats):
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


class Cohesion(CohesionStats):
    messages = OWN


class Morph(MorphStats):
    messages = OWN


class Lemmas(Syntax):
    requires_lemmas = True


VOCAB = spacy.blank("xx").vocab
PARSED = Doc(VOCAB, words=["Yes"], heads=[0], deps=["ROOT"])
TAGGED_PARSE = Doc(VOCAB, words=["Yes"], heads=[0], deps=["ROOT"], pos=["INTJ"])
TAGGED = Doc(VOCAB, words=["Yes"], pos=["INTJ"])
# A token merged over a blank line, which no document can hold
MERGED = Doc(VOCAB, words=["Yes", "\n\n", "no"], spaces=[False, False, False])
with MERGED.retokenize() as retokenizer:
    retokenizer.merge(MERGED[0:3])


class Layers(HighlightedText):
    layers_desc: ClassVar[dict[str, str]] = {"all": "all", "parsed": "parsed", "bare": "bare"}
    layer_annotations: ClassVar[dict[str, tuple[str, ...]]] = {"parsed": ("deprel",), "bare": ()}
    messages = OWN

    def find(self, layer, words, sents, doc):
        if layer == "all":
            return [Highlight(0, len(self.text) + 1, layer)]
        return [Highlight(0, 1, "other")]


class OtherLayer(Layers):
    layers_desc: ClassVar[dict[str, str]] = {"bare": "bare"}
    layer_annotations: ClassVar[dict[str, tuple[str, ...]]] = {}

    def __init__(self, source):
        super().__init__(source, ["bare"])


class OwnReadability(ReadabilityStatsComponent):
    stats_class = Readability
    messages = OWN


class OwnUnadapted(UnadaptedReadabilityStatsComponent):
    messages = OWN


class OwnDiversity(DiversityStatsComponent):
    messages = OWN


class OwnStyle(StyleStatsComponent):
    messages = OWN


class OwnPhon(PhonStatsComponent):
    messages = OWN


class OwnCohesion(CohesionStatsComponent):
    messages = OWN


class BareComponent(StatsComponent):
    messages = OWN


class OwnLexical(LexicalStatsComponent):
    stats_class = Lexical
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


def foreign_extension_on_unpickling():
    data = pickle.dumps(Component(spacy.blank("en"), "own_unpickled"))
    Doc.remove_extension("own_unpickled")
    Doc.set_extension("own_unpickled", getter=lambda doc: 0)
    try:
        pickle.loads(data)(spacy.blank("en")(TEXT))
    finally:
        Doc.remove_extension("own_unpickled")


def hooked(cls, **hooks):
    """A subclass with hooks that return what the core cannot use"""
    return type(f"Hooked{cls.__name__}", (cls,), hooks)


WORDS = TEXT.split()


# One case for every raise site of the classes, a key raised at several sites several times
def scratch() -> Path:
    """A new empty directory"""
    return Path(tempfile.mkdtemp())


def zip_archive(members: dict[str, str], name: str = "data.zip") -> Path:
    """A ZIP archive with the files given, in a new directory"""
    path = scratch() / name
    with zipfile.ZipFile(path, "w") as archive:
        for member, text in members.items():
            archive.writestr(member, text)
    return path


def fetched(archive: Path, checksum: str) -> None:
    """The archive fetched by its file address into a new directory"""
    fetch_archive(archive.as_uri(), scratch() / archive.name, checksum, True, messages=OWN)


def cannot_replace() -> None:
    """The extracted directory of a fetched archive cannot take its place"""
    archive = zip_archive({"data/a.txt": "a"})
    with mock.patch.object(datasets, "_replace", side_effect=[None, OSError("busy")]):
        fetched(archive, sha256(archive))


def cut_download() -> None:
    """An answer shorter than its Content-Length"""

    class Answer(io.BytesIO):
        headers: ClassVar[dict[str, str]] = {"Content-Length": "10"}

    with mock.patch.object(datasets.urllib.request, "urlopen", return_value=Answer(b"abc")):
        download_file("https://example.com/a.zip", scratch(), messages=OWN)


def put_over(member: str, existing: str, directory: bool) -> None:
    """An archive of several roots whose member would replace a file or a directory"""
    archive = zip_archive({member: "x", "other.txt": "y"})
    target = scratch()
    if directory:
        (target / existing).mkdir()
    else:
        (target / existing).write_text("x")
    extract_archive(archive, target, messages=OWN)


def blocked_directory() -> Path:
    """A path under a file, which cannot be a directory"""
    blocker = scratch() / "file"
    blocker.write_text("x")
    return blocker / "sub"


def not_an_archive() -> Path:
    path = scratch() / "a.zip"
    path.write_text("x")
    return path


def cannot_extract() -> None:
    archive = zip_archive({"data/a.txt": "a"})
    with mock.patch.object(datasets, "_replace", side_effect=OSError("busy")):
        extract_archive(archive, messages=OWN)


CASES = [
    ("source_type", SourceTypeError, lambda: Stats(5)),
    ("document_tokens", SourceError, lambda: Stats(MERGED)),
    ("source_span", SourceTypeError, lambda: Stats(spacy.blank("en")(TEXT)[:2])),
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
    ("basic_stats_type", SourceTypeError, lambda: Unadapted(OtherStats(TEXT))),
    ("basic_filter_nums", ParameterError, lambda: Readability(Stats(TEXT), filter_nums=True)),
    ("basic_filter_nums", ParameterError, lambda: Unadapted(Stats(TEXT), filter_nums=True)),
    ("no_basic_stats_class", SourceTypeError, lambda: BareUnadapted(TEXT)),
    (
        "no_sentences",
        SourceError,
        lambda: Unadapted(TEXT, sents_extractor=SentsExtractor(min_len=1000)),
    ),
    ("sents_extractor_type", SourceTypeError, lambda: Unadapted(TEXT, sents_extractor=5)),
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
    ("window_metric", SourceTypeError, lambda: calc_windowed(WORDS, 5, messages=OWN)),
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
    ("connector_words", SourceTypeError, lambda: Matcher({}).find("and")),
    ("connector_sent_index", ParameterError, lambda: Matcher({}).find(["and"], 1.5)),
    ("connector_pos_list", SourceTypeError, lambda: Matcher({}).find(["and"], pos="CCONJ")),
    ("connector_breaks_type", SourceTypeError, lambda: Matcher({}).find(["a", "b"], breaks=1)),
    ("connector_blocked_type", ParameterError, lambda: Matcher({}).find(["a"], blocked=[0.5])),
    ("connector_pos_type", SourceTypeError, lambda: Matcher({}).find(["and"], pos=[1])),
    ("connector_class", ParameterError, lambda: Matcher({"and": ("other", "primary")})),
    (
        "hook_string",
        SourceTypeError,
        lambda: hooked(Matcher, normalize=lambda self, word: None)(
            {"and": ("additive", "primary")}
        ),
    ),
    (
        "matcher_class",
        ParameterError,
        lambda: type("Bad", (Cohesion,), {"connector_matcher_class": dict}),
    ),
    ("connector_pos", ParameterError, lambda: Matcher({}).find(["and"], pos=[])),
    ("connector_breaks", ParameterError, lambda: Matcher({}).find(["a", "b"], breaks={2})),
    ("connector_breaks_short", ParameterError, lambda: Matcher({}).find(["a"], breaks={1})),
    ("connector_blocked", ParameterError, lambda: Matcher({}).find(["a"], blocked={1})),
    ("connector_blocked_empty", ParameterError, lambda: Matcher({}).find([], blocked={0})),
    ("connector_type", SourceTypeError, lambda: Matcher({}).is_subordinator("and")),
    ("text_type", SourceTypeError, lambda: split_windows(5, messages=OWN)),
    ("window_len", ParameterError, lambda: split_windows(TEXT, 0, messages=OWN)),
    ("min_words", ParameterError, lambda: split_windows(TEXT, 5, 0, messages=OWN)),
    ("min_words_window", ParameterError, lambda: split_windows(TEXT, 5, 6, messages=OWN)),
    ("sentence_lengths", SourceTypeError, lambda: sentence_rhythm([1.5], messages=OWN)),
    ("negative_lengths", ParameterError, lambda: sentence_rhythm([-1], messages=OWN)),
    ("top_n", ParameterError, lambda: Style(TEXT, top_n=0)),
    ("freq_dict_type", SourceTypeError, lambda: Checked(TEXT, freq_dict={})),
    ("no_freq_dict_class", SourceTypeError, lambda: Lexical(TEXT)),
    ("no_freq_dict_class", ParameterError, lambda: OwnLexical(spacy.blank("en"), "own_lexical")),
    ("bands_type", ParameterError, lambda: Lexical(TEXT, Frequencies()).band_coverage(5)),
    ("band_bound", ParameterError, lambda: Lexical(TEXT, Frequencies()).band_coverage([0])),
    ("phon_window_len", ParameterError, lambda: Phon(TEXT, window_len=1)),
    ("source_type", SourceTypeError, lambda: Phon(5)),
    ("source_span", SourceTypeError, lambda: Phon(PARSED[:1])),
    ("source_type", SourceTypeError, lambda: Style(5)),
    ("source_span", SourceTypeError, lambda: Style(PARSED[:1])),
    ("source_type", SourceTypeError, lambda: Syntax(5)),
    ("source_span", SourceTypeError, lambda: Syntax(PARSED[:1])),
    ("no_parse", SourceError, lambda: Syntax(Doc(VOCAB, words=["Yes"]))),
    ("no_pos", SourceError, lambda: Syntax(PARSED)),
    ("no_lemmas", SourceError, lambda: Lemmas(TAGGED_PARSE)),
    ("source_type", SourceTypeError, lambda: Cohesion(5)),
    ("source_span", SourceTypeError, lambda: Cohesion(PARSED[:1])),
    ("source_type", SourceTypeError, lambda: Morph(5)),
    ("source_span", SourceTypeError, lambda: Morph(PARSED[:1])),
    ("no_pos", SourceError, lambda: Morph(PARSED)),
    ("unknown_stat", UnknownStatError, lambda: Morph(TAGGED).get_stats("cases")),
    ("no_words", SourceError, lambda: Morph(Doc(VOCAB, words=["."], pos=["PUNCT"]))),
    (
        "hook_morph_words",
        SourceTypeError,
        lambda: hooked(Morph, analyze=lambda self, source: ["Yes"])(PARSED),
    ),
    ("morph_features", ParameterError, lambda: type("Bad", (Morph,), {"feature_names": ["case"]})),
    (
        "morph_markers",
        SourceTypeError,
        lambda: type("Markers", (Morph,), {"markers_desc": {"p_past": "Past"}})(
            TAGGED
        ).print_markers(),
    ),
    (
        "morph_stats_desc",
        ParameterError,
        lambda: type("Bad", (Morph,), {"feature_names": {"case": "Case"}}),
    ),
    (
        "morph_values_desc",
        ParameterError,
        lambda: type("Bad", (Morph,), {"values_desc": [5]}),
    ),
    ("no_stats_class", ParameterError, lambda: BareComponent(spacy.blank("en"), "own_bare")),
    (
        "hook_document",
        SourceTypeError,
        lambda: hooked(Stats, parse=lambda self, source: "Yes")(TEXT),
    ),
    (
        "hook_document",
        SourceTypeError,
        lambda: hooked(Style, parse=lambda self, source: "Yes")(TEXT),
    ),
    (
        "hook_document",
        SourceTypeError,
        lambda: hooked(Phon, parse=lambda self, source: "Yes")(TEXT),
    ),
    (
        "hook_document",
        SourceTypeError,
        lambda: hooked(Syntax, parse=lambda self, source: "Yes")(PARSED),
    ),
    (
        "hook_lexical_words",
        SourceTypeError,
        lambda: hooked(Lexical, analyze=lambda self, source: ["a"])(TEXT, Frequencies()),
    ),
    (
        "hook_cohesion_words",
        SourceTypeError,
        lambda: hooked(Cohesion, analyze=lambda self, s: [["a"]])(PARSED),
    ),
    (
        "hook_lexical_words",
        SourceTypeError,
        lambda: hooked(Lexical, analyze=lambda self, s: None)(TEXT, Frequencies()),
    ),
    (
        "hook_cohesion_words",
        SourceTypeError,
        lambda: hooked(Cohesion, analyze=lambda self, s: None)(PARSED),
    ),
    (
        "hook_cohesion_words",
        SourceTypeError,
        lambda: hooked(Cohesion, analyze=lambda self, s: [5])(PARSED),
    ),
    (
        "hook_syllables",
        SourceTypeError,
        lambda: hooked(Phon, syllabify=lambda self, word: None)(TEXT),
    ),
    ("hook_words", SourceTypeError, lambda: hooked(Phon, doc_words=lambda self, d: [5])(TEXT)),
    ("hook_words", SourceTypeError, lambda: hooked(Stats, doc_words=lambda self, d: "a")(TEXT)),
    ("hook_words", SourceTypeError, lambda: hooked(Style, doc_words=lambda self, d: 5)(TEXT)),
    (
        "hook_flags",
        SourceTypeError,
        lambda: hooked(Style, doc_flags=lambda self, d: 5)(TEXT).water,
    ),
    (
        "hook_flags_check",
        SourceTypeError,
        lambda: hooked(Style, doc_flags=lambda self, d: WordFlags(water=(True,)))(TEXT).water,
    ),
    (
        "hook_word_pairs",
        SourceTypeError,
        lambda: hooked(Syntax, find_split_predicates=lambda self, words: ["ab"])(TAGGED_PARSE),
    ),
    (
        "hook_sounds",
        SourceTypeError,
        lambda: hooked(Phon, transcribe=lambda self, word: None)(TEXT),
    ),
    (
        "fragment_outside",
        ParameterError,
        lambda: hooked(Layers, find=lambda self, *args: [Highlight("0", "1", "all")])(
            TEXT, ["all"]
        ),
    ),
    (
        "hook_highlights",
        SourceTypeError,
        lambda: hooked(Layers, find=lambda self, *args: None)(TEXT, ["all"]),
    ),
    (
        "hook_highlights",
        SourceTypeError,
        lambda: hooked(Layers, find=lambda self, *args: [5])(TEXT, ["all"]),
    ),
    ("source_type", SourceTypeError, lambda: Layers(5)),
    ("source_span", SourceTypeError, lambda: Layers(PARSED[:1])),
    ("no_words", SourceError, lambda: Layers("?!")),
    ("layers_type", ParameterError, lambda: Layers(TEXT, 5)),
    ("unknown_layer", ParameterError, lambda: Layers(TEXT, ["rhymes"])),
    ("layer_annotations", ParameterError, lambda: Layers(TEXT, ["parsed"])),
    ("fragment_outside", ParameterError, lambda: Layers(TEXT, ["all"])),
    ("fragment_layer", ParameterError, lambda: OtherLayer(TEXT)),
    ("hook_document", SourceTypeError, lambda: hooked(Layers, parse=lambda self, s: s)(TEXT)),
    (
        "layer_columns",
        ParameterError,
        lambda: type("Columns", (Layers,), {"layer_annotations": {"parsed": ("DEP",)}}),
    ),
    ("layer_unavailable", ParameterError, lambda: Layers._select_layers(["bare"], [])),
    (
        "long_sent_word_factor",
        ParameterError,
        lambda: check_highlight_params(0, 1, 0.5, messages=OWN),
    ),
    (
        "complex_syl_factor",
        ParameterError,
        lambda: check_highlight_params(1, 0, 0.5, messages=OWN),
    ),
    (
        "alliteration_threshold",
        ParameterError,
        lambda: check_highlight_params(1, 1, 0, messages=OWN),
    ),
    ("removed_attribute", ParameterError, lambda: type("Old", (Stats,), {"join_hyphens": True})),
    (
        "removed_attribute_either",
        ParameterError,
        lambda: hooked(Layers, iter_words=lambda self, t: ()),
    ),
    (
        "removed_component_attribute",
        ParameterError,
        lambda: type("Old", (BareComponent,), {"join_hyphens": True}),
    ),
    (
        "stats_param",
        ParameterError,
        lambda: type("Typo", (BareComponent,), {"stats_class": dict, "stats_params": ("x",)})(
            spacy.blank("en"), "own_typo"
        ),
    ),
    (
        "no_basic_stats_class",
        SourceTypeError,
        lambda: type("NoBasic", (OwnReadability,), {"stats_class": Bare})(spacy.blank("en"), "r"),
    ),
    (
        "extension_name",
        ParameterError,
        lambda: OwnReadability(spacy.blank("en"), "own_r", basic=5),
    ),
    (
        "empty_extension",
        ParameterError,
        lambda: OwnReadability(spacy.blank("en"), "own_r", basic=""),
    ),
    (
        "empty_extension",
        ParameterError,
        lambda: OwnUnadapted(spacy.blank("en"), "own_u", basic=""),
    ),
    ("no_basic_stats_class", SourceTypeError, lambda: OwnUnadapted(spacy.blank("en"), "own_u")),
    (
        "extension_name",
        ParameterError,
        lambda: OwnUnadapted(spacy.blank("en"), "own_u", basic=5),
    ),
    ("preset_type", ParameterError, lambda: OwnReadability(spacy.blank("en"), "own_r", preset=5)),
    (
        "unknown_preset",
        ParameterError,
        lambda: OwnReadability(spacy.blank("en"), "own_r", preset="x"),
    ),
    ("window_len", ParameterError, lambda: OwnDiversity(spacy.blank("en"), "own_d", window_len=0)),
    ("top_n", ParameterError, lambda: OwnStyle(spacy.blank("en"), "own_s", top_n=0)),
    ("words_param", ParameterError, lambda: OwnStyle(spacy.blank("en"), "own_s", cliches="a")),
    ("integer_param", ParameterError, lambda: OwnStyle(spacy.blank("en"), "own_s", top_n="5")),
    (
        "number_param",
        ParameterError,
        lambda: OwnDiversity(spacy.blank("en"), "own_d", log_base="e"),
    ),
    ("bool_param", ParameterError, lambda: Cohesion(PARSED, blank_lines=1)),
    ("bool_param", ParameterError, lambda: Words(filter_punct=1)),
    ("integer_param", ParameterError, lambda: Words(min_len=1.5)),
    ("integer_param", ParameterError, lambda: Stats(TEXT).count_words_by_letters("5")),
    ("number_param", ParameterError, lambda: Readability(TEXT).reading_ease_to_grade("5")),
    ("words_param", SourceTypeError, lambda: Diversity("some text")),
    ("words_param", SourceTypeError, lambda: Words(stopwords="the")),
    ("words_param", SourceTypeError, lambda: Style(TEXT).keyword_density(5)),
    ("negative_words", ParameterError, lambda: calc_reading_time(-1, messages=OWN)),
    (
        "mark_length",
        ParameterError,
        lambda: split_windows(TEXT, closing_marks=["--"], messages=OWN),
    ),
    (
        "hook_bounds",
        SourceTypeError,
        lambda: to_document(TEXT, tokenize=lambda text: 5, messages=OWN),
    ),
    (
        "document_tokens",
        SourceTypeError,
        lambda: to_document("a\n\nb", tokenize=lambda text: [(0, 4, "a\n\nb")], messages=OWN),
    ),
    (
        "bool_param",
        ParameterError,
        lambda: OwnCohesion(spacy.blank("en"), "own_c", blank_lines=1),
    ),
    ("phon_window_len", ParameterError, lambda: OwnPhon(spacy.blank("en"), "own_p", window_len=1)),
    ("sents_extractor_type", SourceTypeError, lambda: Cohesion(PARSED, sents_extractor="x")),
    ("no_pos", SourceError, lambda: Cohesion(PARSED)),
    ("no_lemmas", SourceError, lambda: Cohesion(Doc(VOCAB, words=["Yes"], pos=["INTJ"]))),
    (
        "no_words",
        SourceError,
        lambda: Cohesion(Doc(VOCAB, words=["."], pos=["PUNCT"], lemmas=["."])),
    ),
    (
        "temporal_features",
        ParameterError,
        lambda: type("Bad", (Cohesion,), {"temporal_features": ("voice",)}),
    ),
    (
        "no_words",
        SourceError,
        lambda: Syntax(Doc(VOCAB, words=["."], heads=[0], deps=["ROOT"], pos=["PUNCT"])),
    ),
    (
        "phon_classes",
        ParameterError,
        lambda: type("Bad", (Phon,), {"vowels": frozenset("a"), "skipped": frozenset("a")}),
    ),
    # The corpus functions take the messages of a library as a parameter
    ("callable_param", SourceTypeError, lambda: kwic(TEXT, "cat", fold=5, messages=OWN)),
    ("callable_param", SourceTypeError, lambda: kwic(TEXT, "cat", tokenize=5, messages=OWN)),
    (
        "hook_bounds",
        SourceTypeError,
        lambda: split_windows(TEXT, tokenize=str.split, messages=OWN),
    ),
    ("negative_param", ParameterError, lambda: kwic(TEXT, "cat", window=-1, messages=OWN)),
    ("positive_param", ParameterError, lambda: format_kwic([], width=0, messages=OWN)),
    ("keyword_type", SourceTypeError, lambda: kwic(TEXT, 5, messages=OWN)),
    ("no_keyword", ParameterError, lambda: kwic(TEXT, "?!", messages=OWN)),
    ("concordances_type", SourceTypeError, lambda: format_kwic("x", messages=OWN)),
    ("counts_type", SourceTypeError, lambda: check_counts([("a", 1)], messages=OWN)),
    ("counts_words", SourceTypeError, lambda: check_counts({1: 2}, messages=OWN)),
    ("frequency_type", SourceTypeError, lambda: check_counts({"a": "2"}, messages=OWN)),
    ("frequency_value", SourceError, lambda: check_counts({"a": -1}, messages=OWN)),
    ("words_doc", SourceTypeError, lambda: collocations(spacy.blank("en")(TEXT), messages=OWN)),
    (
        "association_measure",
        ParameterError,
        lambda: collocations(WORDS, measure="x", messages=OWN),
    ),
    ("node_type", ParameterError, lambda: collocations(WORDS, node=5, messages=OWN)),
    (
        "collocation_side",
        ParameterError,
        lambda: collocations(WORDS, node="cat", side="up", messages=OWN),
    ),
    ("side_node", ParameterError, lambda: collocations(WORDS, side="left", messages=OWN)),
    ("word_type", ParameterError, lambda: dispersion(WORDS, word=5, messages=OWN)),
    ("parts_number", ParameterError, lambda: dispersion(WORDS, parts=1, messages=OWN)),
    ("parts_type", ParameterError, lambda: dispersion(WORDS, parts="x", messages=OWN)),
    ("parts_sizes", ParameterError, lambda: dispersion(WORDS, parts=[1, 1], messages=OWN)),
    ("keyness_measure", ParameterError, lambda: keyness(WORDS, WORDS, "x", messages=OWN)),
    (
        "reference_ngrams",
        ParameterError,
        lambda: keyness(WORDS, FrequencyReference({"a": 1.0}, 10.0), n=2, messages=OWN),
    ),
    ("ngram_frequencies", ParameterError, lambda: keyness({"a": 1}, WORDS, n=2, messages=OWN)),
    (
        "no_kept_words",
        SourceError,
        lambda: keyness(
            WORDS, FrequencyReference({"a": 1.0}, 10.0, keep=lambda word: False), messages=OWN
        ),
    ),
    ("short_texts", SourceError, lambda: keyness([["a"]], [["a", "b"]], n=2, messages=OWN)),
    (
        "reference_counts",
        SourceTypeError,
        lambda: keyness(WORDS, FrequencyReference([1], 10.0), messages=OWN),
    ),
    ("target_counts", SourceTypeError, lambda: keyness({"a": 1.5}, WORDS, messages=OWN)),
    ("corpus_type", SourceTypeError, lambda: frequency_table([1], messages=OWN)),
    ("text_words", SourceTypeError, lambda: frequency_table({"a": "x"}, messages=OWN)),
    (
        "text_doc",
        SourceTypeError,
        lambda: frequency_table({"a": spacy.blank("en")(TEXT)}, messages=OWN),
    ),
    ("corpus_texts", SourceError, lambda: frequency_table({}, messages=OWN)),
    ("corpus_empty_text", SourceError, lambda: frequency_table({"a": []}, messages=OWN)),
    ("culling_share", ParameterError, lambda: frequency_table(UNITS, culling=2, messages=OWN)),
    ("culled_units", SourceError, lambda: frequency_table(UNITS, culling=1, messages=OWN)),
    ("delta_variant", ParameterError, lambda: delta(UNITS, variant="x", messages=OWN)),
    ("delta_texts", SourceError, lambda: delta(UNITS, messages=OWN)),
    ("scaling_texts", SourceError, lambda: delta_profiles(UNITS, UNITS, messages=OWN)),
    ("step_window", ParameterError, lambda: rolling_delta(LONG, TEN, 5, 6, messages=OWN)),
    ("rolling_texts", SourceError, lambda: rolling_delta({"A": TEN}, TEN, 5, 1, messages=OWN)),
    (
        "corpus_short_text",
        SourceError,
        lambda: rolling_delta({"A": TEN[:3], "B": TEN[:3]}, TEN, 5, 1, messages=OWN),
    ),
    ("short_text", SourceError, lambda: rolling_delta(LONG, TEN[:3], 5, 1, messages=OWN)),
    (
        "scaling_windows",
        SourceError,
        lambda: rolling_delta({"A": TEN[:5], "B": TEN[:5]}, TEN, 5, 5, messages=OWN),
    ),
    ("corpora_type", SourceTypeError, lambda: zeta_segments([1], ["a"], ["b"], messages=OWN)),
    ("no_corpora", SourceError, lambda: zeta_segments({}, ["a"], ["b"], messages=OWN)),
    ("param_words", SourceError, lambda: zeta_segments({"c": ["a"]}, [], ["b"], messages=OWN)),
    ("corpus_words", SourceError, lambda: zeta_segments({"c": []}, ["a"], ["b"], messages=OWN)),
    ("features_type", SourceTypeError, lambda: compare_features([1], [1], messages=OWN)),
    ("frequency_table_type", SourceTypeError, lambda: z_scores({"a": ["b"]}, messages=OWN)),
    (
        "feature_names",
        SourceTypeError,
        lambda: compare_features(
            pd.DataFrame([[1, 2]], columns=["a", "a"]), FEATURES, messages=OWN
        ),
    ),
    (
        "feature_numeric",
        SourceTypeError,
        lambda: compare_features(pd.DataFrame({"a": ["x"]}), FEATURES, messages=OWN),
    ),
    ("corpus_labels", ParameterError, lambda: check_comparison_params(("A", "A"), messages=OWN)),
    ("rng_type", ParameterError, lambda: bootstrap_median_diff([1], [1], rng=5, messages=OWN)),
    ("values_type", SourceTypeError, lambda: holm_correction(["a"], messages=OWN)),
    (
        "texts_type",
        SourceTypeError,
        lambda: bootstrap_median_diff([1], [1], texts_a="a", messages=OWN),
    ),
    (
        "texts_values",
        ParameterError,
        lambda: bootstrap_median_diff([1, 2], [1], texts_a=["a"], messages=OWN),
    ),
    (
        "texts_labels",
        SourceTypeError,
        lambda: bootstrap_median_diff([1, 2], [1], texts_a=["a", 1], messages=OWN),
    ),
    ("p_values", ParameterError, lambda: holm_correction([2.0], messages=OWN)),
    (
        "words_texts",
        SourceTypeError,
        lambda: keyness(["the cat sleeps", "the dog barks"], WORDS, messages=OWN),
    ),
    (
        "part_bounds",
        ParameterError,
        lambda: document_part(to_document(TEXT), 5, 2, messages=OWN),
    ),
    ("parts_kind", ParameterError, lambda: Stats.by_parts(TEXT, "words")),
    ("no_part_kinds", ParameterError, lambda: Diversity.by_parts(TEXT)),
    ("stats_objects", SourceTypeError, lambda: stats_dataframe([5], messages=OWN)),
    (
        "reference_keys",
        SourceTypeError,
        lambda: keyness(
            WORDS, FrequencyReference({"cat": 1.0}, 10.0, keys=lambda words: ()), messages=OWN
        ),
    ),
    (
        "archive_extension",
        ParameterError,
        lambda: fetch_archive("https://example.com/a", scratch() / "a", "0", True, messages=OWN),
    ),
    ("checksum", DownloadError, lambda: fetched(zip_archive({"data/a.txt": "a"}), "0" * 64)),
    ("replace_directory", DataFileError, cannot_replace),
    ("filter_value", ParameterError, lambda: substring_filter("author", 5, messages=OWN)),
    ("text_len_order", ParameterError, lambda: length_filters(5, 2, messages=OWN)),
    ("path_type", SourceTypeError, lambda: to_path(5, messages=OWN)),
    (
        "create_directory",
        DownloadError,
        lambda: download_file("https://example.com/a.zip", blocked_directory(), messages=OWN),
    ),
    (
        "no_file_name",
        DownloadError,
        lambda: download_file("https://example.com/", scratch(), messages=OWN),
    ),
    (
        "file_name",
        DownloadError,
        lambda: download_file("https://example.com/a", scratch(), "../a", messages=OWN),
    ),
    (
        "download_file",
        DownloadError,
        lambda: download_file((scratch() / "a.zip").as_uri(), scratch(), messages=OWN),
    ),
    ("download_length", DownloadError, cut_download),
    ("no_archive", DataFileError, lambda: extract_archive(scratch() / "a.zip", messages=OWN)),
    ("not_archive", DataFileError, lambda: extract_archive(not_an_archive(), messages=OWN)),
    ("extract_archive", DataFileError, cannot_extract),
    ("empty_archive", DataFileError, lambda: extract_archive(zip_archive({}), messages=OWN)),
    (
        "archive_paths",
        DataFileError,
        lambda: extract_archive(zip_archive({"../a.txt": "a"}), messages=OWN),
    ),
    ("archive_directory", DataFileError, lambda: put_over("a/b.txt", "a", directory=False)),
    ("archive_file", DataFileError, lambda: put_over("a.txt", "a.txt", directory=True)),
    (
        "archive_itself",
        DataFileError,
        lambda: extract_archive(zip_archive({"data/a.txt": "a"}, name="data"), messages=OWN),
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


def test_messages_without_fields_are_raised_as_they_are():
    """A message whose default has no fields may hold braces, and they come out as written"""
    braced = {**MESSAGES, "ngram_range": "Range {n}", "sentence_lengths": "Lengths {x}"}

    class BracedWords(WordsExtractor):
        messages = braced

    with pytest.raises(ParameterError, match=r"^Range \{n\}$"):
        BracedWords(ngram_range=(1.5, 2))
    with pytest.raises(SourceTypeError, match=r"^Lengths \{x\}$"):
        sentence_rhythm("123", messages=braced)


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
        HighlightedText,
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


def test_partial_messages_of_functions():
    """Functions with MESSAGES by default take messages of some keys too: a valid call works,
    a given key is used"""
    from anyts.style_stats import calc_zipf_naturalness, find_nausea_words

    partial = {"reading_speed": "The speed is not positive"}
    assert calc_reading_time(100, messages=partial) == calc_reading_time(100)
    assert find_nausea_words(["a", "b", "a"], messages=partial) == {"a": 2, "b": 1}
    assert calc_zipf_naturalness(["a"] * 4 + ["b"] * 2, messages=partial) == 100.0
    assert to_document("A cat.", messages=partial).text == "A cat."
    with pytest.raises(ParameterError, match=r"^The speed is not positive$"):
        calc_reading_time(100, 0, messages=partial)
