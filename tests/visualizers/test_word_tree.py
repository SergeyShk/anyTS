import pytest
from graphviz import Digraph

from anyts.exceptions import ParameterError, SourceError, SourceTypeError
from anyts.visualizers import wordtree


@pytest.fixture(scope="module")
def texts():
    return [["the", "class", "war"], ["every", "class", "of", "people"]]


def test_wordtree_type_error():
    with pytest.raises(TypeError):
        wordtree(1, "test")
    with pytest.raises(SourceTypeError):
        wordtree("the working class", "class")
    with pytest.raises(SourceTypeError):
        wordtree([["the", "class"], "the working class"], "class")
    with pytest.raises(SourceTypeError, match=r"^The keyword must be a string, not list$"):
        wordtree([["the", "class"]], ["class"])


def test_wordtree_value_error(texts):
    with pytest.raises(ValueError):
        wordtree(texts, "test")
    with pytest.raises(SourceError):
        wordtree([], "test")
    with pytest.raises(SourceError, match="has no word next to it"):
        wordtree([["cat"]], "cat")
    for kwargs in ({"max_n": 1}, {"max_per_n": 0}, {"max_n": 2.5}, {"max_per_n": 2.0}):
        with pytest.raises(ParameterError):
            wordtree(texts, "class", **kwargs)


def test_wordtree_html_like_words():
    g = wordtree([["<script>", "cat", "sleeps"], ["bad", "<script>", "eats"]], "<script>")
    assert g.source.splitlines()[0] == 'digraph "<script>" {'
    assert '\tn0 [label="<script>"' in g.source
    assert "\t<script>" not in g.source


def test_wordtree(texts):
    g = wordtree(texts, "class", max_n=2)
    assert isinstance(g, Digraph)
    assert len(g.body) == 11
    assert g.name == "class"


def test_wordtree_identifiers():
    # A colon would be a port of graphviz and hyphens would join the paths of two branches
    g = wordtree([["it", "is", "10:30", "now"]], "is", max_n=3)
    assert '\tn2 [label="10:30" fontsize=30]' in g.source
    assert "\tn0 -> n2" in g.source and "\tn2 -> n3" in g.source
    g = wordtree([["said", "well-known", "no"], ["said", "well", "known", "no"]], "said")
    assert g.source.count("[label=no ") == 2
    assert sum(line.endswith("-> n0\n") for line in g.body) == 0
    assert len([line for line in g.body if " -> " in line]) == 5


def test_wordtree_max_per_n():
    # class of people is frequent, class of is not among the two most frequent bigrams:
    # the trigram does not show up without its bigram, and a level holds max_per_n nodes
    texts = (
        [["class", "war"]] * 4
        + [["class", "middle"]] * 3
        + [["class", "of", "people"]] * 2
        + [["class", "high", "and", "low"]]
    )
    g = wordtree(texts, "class", max_n=3, max_per_n=2)
    labels = [line.split("label=")[1].split()[0] for line in g.body if "label=" in line]
    assert labels == ["class", "war", "middle"]
    g = wordtree(texts, "class", max_n=4, max_per_n=4)
    labels = [line.split("label=")[1].split()[0] for line in g.body if "label=" in line]
    assert labels == ["class", "war", "middle", "of", "people", "high", "and", "low"]
