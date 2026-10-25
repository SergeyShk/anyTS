import pickle
from typing import ClassVar

import pytest
import spacy
from spacy.language import Language
from spacy.tokens import Doc

from anyts import DiversityStats
from anyts.basic_stats import BasicStats
from anyts.cohesion_stats import CohesionStats
from anyts.components import (
    BasicStatsComponent,
    CohesionStatsComponent,
    DiversityStatsComponent,
    LexicalStatsComponent,
    MorphStatsComponent,
    PhonStatsComponent,
    ReadabilityStatsComponent,
    StatsComponent,
    StyleStatsComponent,
    SyntaxStatsComponent,
    start_sents_after_blank_lines,
)
from anyts.constants import MATTR_WINDOW_LEN, NAUSEA_TOP_N, PHON_WINDOW_LEN
from anyts.diversity_stats import check_params
from anyts.exceptions import ParameterError, SourceError, SourceTypeError
from anyts.morph_stats import MorphStats
from anyts.readability_stats import ReadabilityStats
from anyts.style_stats import StyleStats
from anyts.syntax_stats import SyntaxStats
from anyts.utils import iter_doc_words


@Language.factory("anyts_test_diversity")
class DiversityComponent(StatsComponent):
    """A component of a library: the diversity of the lower-cased words"""

    def __init__(self, nlp: Language, name: str = "anyts_test_diversity", window_len: int = 5):
        check_params(window_len=window_len)
        self.window_len = window_len
        super().__init__(nlp, name)

    def compute(self, doc: Doc) -> DiversityStats:
        words = [word.lower() for _, _, word in iter_doc_words(doc)]
        return DiversityStats(words, window_len=self.window_len)


Language.component("anyts_test_blank_lines", func=start_sents_after_blank_lines)


@Language.factory("anyts_test_ratio")
class RatioComponent(StatsComponent):
    """A component that reuses the statistics of another one"""

    def __init__(self, nlp: Language, name: str = "anyts_test_ratio", source: str = "diversity"):
        self.source = source
        super().__init__(nlp, name)

    def compute(self, doc: Doc) -> float:
        return (
            self.from_extension(doc, self.source, DiversityStats, "anyts_test_diversity").ttr * 2
        )


@Language.factory("anyts_test_digits")
class DigitsComponent(StatsComponent):
    """A component that prepares its pipeline and takes only the texts with a digit"""

    def prepare(self, nlp: Language) -> None:
        nlp.tokenizer.add_special_case("A1", [{"ORTH": "A"}, {"ORTH": "1"}])

    def accepts(self, doc: Doc) -> bool:
        return any(char.isdigit() for char in doc.text)

    def compute(self, doc: Doc) -> int:
        return len(doc)


class ClichedStyle(StyleStats):
    cliches_list = ("at the end of the day",)


@Language.factory("anyts_test_style")
class ClichedStyleComponent(StyleStatsComponent):
    stats_class = ClichedStyle


@pytest.fixture
def nlp():
    return spacy.blank("xx")


def test_component(nlp):
    component = nlp.add_pipe("anyts_test_diversity", name="diversity")
    assert isinstance(component, DiversityComponent)
    assert component.name == "diversity"
    doc = nlp("The cat and the dog")
    assert isinstance(doc._.diversity, DiversityStats)
    assert doc._.diversity.ttr == 0.8
    assert doc._.diversity.words == ("the", "cat", "and", "the", "dog")


def test_default_name(nlp):
    nlp.add_pipe("anyts_test_diversity")
    assert nlp("The cat")._.anyts_test_diversity.ttr == 1.0


def test_config(nlp):
    nlp.add_pipe("anyts_test_diversity", name="diversity", config={"window_len": 2})
    assert nlp("a b a b")._.diversity.window_len == 2


def test_parameters_checked_at_add_pipe(nlp):
    with pytest.raises(ParameterError, match="window size"):
        nlp.add_pipe("anyts_test_diversity", name="diversity", config={"window_len": 0})
    assert nlp.pipe_names == []


@pytest.mark.parametrize("text", ["", "   ", "?! ..."])
def test_document_without_words(nlp, text):
    nlp.add_pipe("anyts_test_diversity", name="diversity")
    assert nlp(text)._.diversity is None


def test_pipe(nlp):
    nlp.add_pipe("anyts_test_diversity", name="diversity")
    docs = list(nlp.pipe(["The cat", "?!", "A dog and a cat"]))
    assert [doc._.diversity and doc._.diversity.ttr for doc in docs] == [1.0, None, 0.8]


def test_prepare_and_accepts(nlp):
    nlp.add_pipe("anyts_test_digits", name="digits")
    assert [token.text for token in nlp("A1 is here")] == ["A", "1", "is", "here"]
    assert nlp("A1 is here")._.digits == 4
    assert nlp("No digit")._.digits is None


def test_from_extension(nlp):
    nlp.add_pipe("anyts_test_diversity", name="diversity")
    nlp.add_pipe("anyts_test_ratio", name="ratio")
    assert nlp("The cat and the dog")._.ratio == 1.6


def test_from_extension_errors(nlp):
    nlp.add_pipe("anyts_test_ratio", name="ratio", config={"source": "missing"})
    message = (
        r"^The extension missing holds no DiversityStats: add the component "
        r"anyts_test_diversity with the name missing before ratio$"
    )
    with pytest.raises(SourceError, match=message):
        nlp("The cat")
    other = spacy.blank("xx")
    other.add_pipe("anyts_test_digits", name="count")
    other.add_pipe("anyts_test_ratio", name="ratio", config={"source": "count"})
    with pytest.raises(SourceError, match=r"^The extension count holds no DiversityStats"):
        other("A1 and 2")


def test_from_extension_without_the_factory(nlp):
    class Reuser(DigitsComponent):
        def compute(self, doc):
            return self.from_extension(doc, "missing", DiversityStats)

    reuser = Reuser(nlp, "reuser")
    with pytest.raises(
        SourceError, match=r"add the component with the name missing before reuser$"
    ):
        reuser(nlp("1 cat"))


def test_stats_class_or_compute_is_required(nlp):
    with pytest.raises(
        ParameterError, match=r"^StatsComponent has no concrete class of statistics"
    ):
        StatsComponent(nlp, "anyts_test_base")

    @Language.factory("anyts_test_unfinished")
    class Unfinished(StatsComponent):
        pass

    with pytest.raises(ParameterError, match=r"^Unfinished has no concrete class"):
        nlp.add_pipe("anyts_test_unfinished")
    assert nlp.pipe_names == []
    # An abstract class of statistics is none either, and diversity has no default
    for component in (
        BasicStatsComponent,
        LexicalStatsComponent,
        PhonStatsComponent,
        DiversityStatsComponent,
    ):
        with pytest.raises(ParameterError, match=rf"^{component.__name__} has no concrete class"):
            component(nlp, "anyts_test_bare")
    # Readability reads a Doc only through the basic statistics of a library
    with pytest.raises(SourceTypeError, match=r"^ReadabilityStats has no basic_stats_class"):
        ReadabilityStatsComponent(nlp, "anyts_test_bare")

    class Unknown(ReadabilityStatsComponent):
        stats_class = None

    with pytest.raises(ParameterError, match=r"^Unknown has no concrete class"):
        Unknown(nlp, "anyts_test_bare")


def test_attributes_of_stats_params_are_required(nlp):
    class Typo(Generic):
        stats_params = ("sise",)

    with pytest.raises(ParameterError, match=r"^Typo has no attribute sise of stats_params$"):
        Typo(nlp, "anyts_test_typo")


def test_pickled_component_registers_its_extension(nlp):
    component = nlp.add_pipe("anyts_test_diversity", name="anyts_test_pickled")
    data = pickle.dumps(component)
    Doc.remove_extension("anyts_test_pickled")
    restored = pickle.loads(data)
    assert Doc.has_extension("anyts_test_pickled")
    assert restored(nlp("The cat and the dog"))._.anyts_test_pickled.ttr == 0.8


def test_renamed_component_follows_with_its_extension(nlp):
    nlp.add_pipe("anyts_test_diversity", name="anyts_test_before")
    nlp.rename_pipe("anyts_test_before", "anyts_test_after")
    assert nlp("The cat and the dog")._.anyts_test_after.ttr == 0.8
    other = spacy.blank("xx")
    other.add_pipe("anyts_test_after", source=nlp, name="anyts_test_sourced")
    assert other("The cat and the dog")._.anyts_test_sourced.ttr == 0.8
    # The component is shared: the first pipeline writes to its last name too
    assert other.get_pipe("anyts_test_sourced") is nlp.get_pipe("anyts_test_after")
    assert nlp("The cat and the dog")._.anyts_test_sourced.ttr == 0.8


def test_extension_of_another_package_is_kept(nlp):
    Doc.set_extension("anyts_test_foreign", getter=lambda doc: 0.5)
    try:
        with pytest.raises(ParameterError, match=r"^The extension anyts_test_foreign of Doc"):
            nlp.add_pipe("anyts_test_diversity", name="anyts_test_foreign")
        assert nlp("The cat")._.anyts_test_foreign == 0.5
        assert nlp.pipe_names == []
    finally:
        Doc.remove_extension("anyts_test_foreign")
    # An extension without a getter, setter, method or default is another package's too
    Doc.set_extension("anyts_test_plain", default=None)
    try:
        with pytest.raises(ParameterError, match=r"^The extension anyts_test_plain of Doc"):
            nlp.add_pipe("anyts_test_diversity", name="anyts_test_plain")
    finally:
        Doc.remove_extension("anyts_test_plain")
    # A component added again takes its own extension back
    nlp.add_pipe("anyts_test_diversity", name="anyts_test_again")
    spacy.blank("xx").add_pipe("anyts_test_diversity", name="anyts_test_again")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "Notes without a dot\n\nThe cat sleeps. The dog eats.",
            ["Notes without a dot", "The cat sleeps.", "The dog eats."],
        ),
        ("One. Two.\n\nThree.\n \nFour", ["One.", "Two.", "Three.", "Four"]),
        ("One \n \t\nTwo\r\n\r\nThree\n\n\n\nFour", ["One", "Two", "Three", "Four"]),
        ("A list\n- one\n- two", ["A list\n- one\n- two"]),
        ("\n\nOne\n\n", ["One"]),
    ],
)
def test_blank_lines_start_sentences(nlp, text, expected):
    nlp.add_pipe("anyts_test_blank_lines")
    nlp.add_pipe("sentencizer")
    assert [sent.text.strip() for sent in nlp(text).sents] == expected
    assert list(nlp.pipe([text, ""]))[1].text == ""


def test_blank_lines_set_only_their_starts(nlp):
    doc = start_sents_after_blank_lines(nlp("One. Two\n\nThree"))
    assert [token.is_sent_start for token in doc] == [True, None, None, False, True]
    doc = start_sents_after_blank_lines(nlp("One.\nTwo"))
    assert [token.is_sent_start for token in doc] == [True, None, None, None]


def test_blank_lines_keep_the_opening_marks_with_the_first_word(nlp):
    """A dash or an opening mark of a paragraph does not end up a sentence of its own"""
    doc = start_sents_after_blank_lines(nlp("Fin:\n\n--¡Vaya, vaya!\n\n«Bueno»"))
    assert [(token.text, token.is_sent_start) for token in doc] == [
        ("Fin", True),
        (":", None),
        ("\n\n", False),
        ("--¡Vaya", True),
        (",", None),
        ("vaya", None),
        ("!", None),
        ("\n\n", False),
        ("«", True),
        ("Bueno", False),
        ("»", None),
    ]
    # Every line break after an opening mark leaves the next word to the parser
    for line_break in ("\n", "\r", "\u2028", "\x85"):
        doc = start_sents_after_blank_lines(nlp(f"Fin:\n\n«{line_break}Bueno"))
        assert doc[-1].text == "Bueno" and doc[-1].is_sent_start is None, repr(line_break)
    # A paragraph of marks alone leaves the next paragraph to its own blank line
    doc = start_sents_after_blank_lines(nlp("Uno.\n\n* * *\n\nDos"))
    assert [token.text for token in doc if token.is_sent_start] == ["Uno", "*", "Dos"]
    # A space after the mark keeps it with the word, a line break ends the marks
    doc = start_sents_after_blank_lines(nlp("Fin:\n\n—\u00a0¡Vaya!"))
    assert [(token.text, token.is_sent_start) for token in doc][3:] == [
        ("—", True),
        ("\u00a0", False),
        ("¡", False),
        ("Vaya", False),
        ("!", None),
    ]
    doc = start_sents_after_blank_lines(nlp("Uno.\n\n* * *\nDos"))
    assert [(token.text, token.is_sent_start) for token in doc][-2:] == [
        ("\n", None),
        ("Dos", None),
    ]


def test_blank_lines_of_a_parsed_document(nlp):
    """A parsed document, passed through the pipeline again, keeps its sentences"""
    doc = Doc(nlp.vocab, words=["One", "two"], heads=[1, 1], deps=["dep", "ROOT"])
    starts = [token.is_sent_start for token in doc]
    assert start_sents_after_blank_lines(doc) is doc
    assert [token.is_sent_start for token in doc] == starts


class Recorded:
    """Statistics that keep their source and their keyword arguments"""

    presets: ClassVar[dict[str, dict]] = {"original": {}, "other": {}}
    basic_stats_class: ClassVar[type | None] = None

    def __init__(self, source, **kwargs):
        self.source = source
        self.kwargs = kwargs


class RecordedBasic(Recorded):
    pass


class RecordedReadability(Recorded):
    basic_stats_class = RecordedBasic


@Language.factory("anyts_test_generic")
class Generic(StatsComponent):
    """A component of a class of statistics with a parameter of its config"""

    stats_class = Recorded
    stats_params = ("size",)

    def __init__(self, nlp: Language, name: str, size: int = 3):
        self.size = size
        super().__init__(nlp, name)


@Language.factory("anyts_test_basic")
class Basic(BasicStatsComponent):
    stats_class = RecordedBasic


@Language.factory("anyts_test_readability")
class Readability(ReadabilityStatsComponent):
    stats_class = RecordedReadability
    basic_factory = "anyts_test_basic"


def test_generic_compute(nlp):
    nlp.add_pipe("anyts_test_generic", name="generic", config={"size": 7})
    doc = nlp("The cat")
    assert doc._.generic.source is doc and doc._.generic.kwargs == {"size": 7}
    assert nlp.config["components"]["generic"] == {"factory": "anyts_test_generic", "size": 7}


def test_component_saved_and_loaded(nlp, tmp_path):
    nlp.add_pipe("anyts_test_generic", name="generic", config={"size": 7})
    nlp.add_pipe("anyts_test_readability", name="readability", config={"preset": "other"})
    nlp.to_disk(tmp_path)
    loaded = spacy.load(tmp_path)
    doc = loaded("The cat")
    assert doc._.generic.kwargs == {"size": 7}
    assert doc._.readability.kwargs == {"preset": "other"}


def test_components_of_the_core_classes():
    assert BasicStatsComponent.stats_class is BasicStats
    assert ReadabilityStatsComponent.stats_class is ReadabilityStats
    assert StyleStatsComponent.stats_class is StyleStats
    assert SyntaxStatsComponent.stats_class is SyntaxStats
    assert CohesionStatsComponent.stats_class is CohesionStats
    assert MorphStatsComponent.stats_class is MorphStats
    assert DiversityStatsComponent.stats_class is None


def test_syntax_and_cohesion_components_on_their_core_classes(nlp):
    doc = Doc(
        nlp.vocab,
        words=["Cats", "sleep", ".", "Cats", "eat"],
        heads=[1, 1, 1, 4, 4],
        deps=["nsubj", "ROOT", "punct", "nsubj", "ROOT"],
        pos=["NOUN", "VERB", "PUNCT", "NOUN", "VERB"],
        lemmas=["cat", "sleep", ".", "cat", "eat"],
    )
    SyntaxStatsComponent(nlp, "anyts_test_syntax")(doc)
    CohesionStatsComponent(nlp, "anyts_test_cohesion")(doc)
    MorphStatsComponent(nlp, "anyts_test_morph")(doc)
    assert doc._.anyts_test_syntax.n_sents == 2
    assert doc._.anyts_test_cohesion.noun_overlap_adjacent == 1.0
    assert doc._.anyts_test_morph.pos == ("NOUN", "VERB", "NOUN", "VERB")


def test_readability_component(nlp):
    nlp.add_pipe("anyts_test_basic", name="basic")
    nlp.add_pipe("anyts_test_readability", name="default")
    nlp.add_pipe("anyts_test_readability", name="other", config={"preset": "other"})
    nlp.add_pipe("anyts_test_readability", name="reused", config={"basic": "basic"})
    doc = nlp("The cat")
    assert doc._.default.kwargs == {} and doc._.default.source is doc
    assert doc._.other.kwargs == {"preset": "other"}
    assert doc._.reused.source is doc._.basic
    missing = spacy.blank("xx")
    missing.add_pipe("anyts_test_readability", config={"basic": "basic"})
    with pytest.raises(SourceError, match=r"anyts_test_basic"):
        missing("The cat")


@pytest.mark.parametrize(
    ("config", "message"),
    [
        ({"preset": "unknown"}, r"^Unknown coefficient preset: unknown"),
        ({"preset": 5}, r"^The preset must be a string, not int$"),
        ({"basic": 5}, r"^The name of an extension must be a string, not int$"),
    ],
)
def test_readability_component_errors(nlp, config, message):
    with pytest.raises(ParameterError, match=message):
        nlp.add_pipe("anyts_test_readability", config=config)


def test_components_pass_their_parameters(nlp):
    class Diversity(DiversityStatsComponent):
        stats_class = Recorded

    class Style(StyleStatsComponent):
        stats_class = Recorded

    class Phon(PhonStatsComponent):
        stats_class = Recorded

    class Lexical(LexicalStatsComponent):
        stats_class = Recorded

    doc = nlp("The cat")
    assert Diversity(nlp, "d").compute(doc).kwargs["window_len"] == MATTR_WINDOW_LEN
    assert Diversity(nlp, "d", window_len=7).compute(doc).kwargs["window_len"] == 7
    assert Style(nlp, "s").compute(doc).kwargs == {
        "stopwords": None,
        "top_n": NAUSEA_TOP_N,
        "nausea_stopwords": None,
        "cliches": None,
    }
    assert Style(nlp, "s", stopwords={"the"}, top_n=2).compute(doc).kwargs["top_n"] == 2
    assert Phon(nlp, "p").compute(doc).kwargs == {"window_len": PHON_WINDOW_LEN}
    assert Lexical(nlp, "l").compute(doc).kwargs == {"freq_dict": None}
    lexical = Lexical(nlp, "l")
    assert not lexical.accepts(nlp("1999 2020")) and lexical.accepts(nlp("1999 cats"))

    class Ordinals(Lexical):
        join_hyphens = True

        def is_number(self, word):
            return word in {"5-th", "1st"}

    # The numbers of a language, a hyphenated one taken whole
    ordinals = Ordinals(nlp, "o")
    assert not ordinals.accepts(nlp("5-th 1st")) and ordinals.accepts(nlp("5-th cats"))
    with pytest.raises(ParameterError):
        Diversity(nlp, "d", window_len=0)
    with pytest.raises(ParameterError):
        Style(nlp, "s", top_n=0)
    with pytest.raises(SourceTypeError):
        Style(nlp, "s", stopwords="the")
    with pytest.raises(SourceTypeError):
        Style(nlp, "s", nausea_stopwords=[1])
    with pytest.raises(SourceTypeError):
        Style(nlp, "s", cliches="at the end of the day")
    with pytest.raises(ParameterError):
        Phon(nlp, "p", window_len=1)


def test_style_component_with_its_cliches(nlp, tmp_path):
    nlp.add_pipe("anyts_test_style", name="class_cliches")
    nlp.add_pipe("anyts_test_style", name="own_cliches", config={"cliches": ["the cat slept"]})
    nlp.add_pipe("anyts_test_style", name="no_cliches", config={"cliches": []})
    nlp.to_disk(tmp_path)
    doc = spacy.load(tmp_path)("At the end of the day the cat slept")
    assert doc._.class_cliches.cliches_list == ("at the end of the day",)
    assert doc._.class_cliches.cliches == pytest.approx(100 / 9)
    assert doc._.own_cliches.cliches_list == ("the cat slept",)
    assert doc._.own_cliches.cliches == pytest.approx(100 / 9)
    assert doc._.no_cliches.cliches == 0.0


def test_component_renamed_to_an_extension_of_another_package(nlp):
    nlp.add_pipe("anyts_test_diversity", name="anyts_test_own")
    Doc.set_extension("anyts_test_taken", getter=lambda doc: 0.5)
    try:
        nlp.rename_pipe("anyts_test_own", "anyts_test_taken")
        with pytest.raises(ParameterError, match=r"^The extension anyts_test_taken of Doc"):
            nlp("The cat")
        nlp.add_pipe("sentencizer")
        nlp.rename_pipe("anyts_test_taken", "anyts_test_own")
        assert nlp("The cat")._.anyts_test_own.ttr == 1.0
        assert Doc(nlp.vocab, words=["a"])._.anyts_test_taken == 0.5
    finally:
        Doc.remove_extension("anyts_test_taken")
