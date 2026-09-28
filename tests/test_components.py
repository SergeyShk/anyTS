import pytest
import spacy
from spacy.language import Language
from spacy.tokens import Doc

from anyts import DiversityStats
from anyts.components import StatsComponent
from anyts.diversity_stats import check_params
from anyts.exceptions import ParameterError, SourceError
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


@Language.factory("anyts_test_ratio")
class RatioComponent(StatsComponent):
    """A component that reuses the statistics of another one"""

    def __init__(self, nlp: Language, name: str = "anyts_test_ratio", source: str = "diversity"):
        self.source = source
        super().__init__(nlp, name)

    def compute(self, doc: Doc) -> float:
        return self.from_extension(doc, self.source, DiversityStats).ttr * 2


@Language.factory("anyts_test_digits")
class DigitsComponent(StatsComponent):
    """A component that prepares its pipeline and takes only the texts with a digit"""

    def prepare(self, nlp: Language) -> None:
        nlp.tokenizer.add_special_case("A1", [{"ORTH": "A"}, {"ORTH": "1"}])

    def accepts(self, doc: Doc) -> bool:
        return any(char.isdigit() for char in doc.text)

    def compute(self, doc: Doc) -> int:
        return len(doc)


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
    message = r"^The extension missing holds no DiversityStats: add the component"
    with pytest.raises(SourceError, match=message):
        nlp("The cat")
    other = spacy.blank("xx")
    other.add_pipe("anyts_test_digits", name="count")
    other.add_pipe("anyts_test_ratio", name="ratio", config={"source": "count"})
    with pytest.raises(SourceError, match=r"^The extension count holds no DiversityStats"):
        other("A1 and 2")


def test_compute_of_the_base(nlp):
    component = StatsComponent(nlp, "anyts_test_base")
    assert component(nlp("?!"))._.anyts_test_base is None
    with pytest.raises(NotImplementedError):
        component(nlp("The cat"))
