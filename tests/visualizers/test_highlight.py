from typing import ClassVar

import pytest
import spacy
from spacy.tokens import Doc

from anyts.exceptions import ParameterError, SourceError, SourceTypeError
from anyts.utils import iter_doc_units
from anyts.visualizers import Highlight, HighlightedText
from anyts.visualizers.highlight import (
    Sent,
    Word,
    get_doc_words,
    get_text_sents,
    group_words_by_sents,
    iter_doc_sents,
    split_segments,
    tokens_span,
)

STOPWORDS = {"the", "a", "and"}


class Marks(HighlightedText):
    """A library of four layers: two of the words, one of a parse, one of the tags"""

    layers_desc: ClassVar[dict[str, str]] = {
        "long_sents": "long sentence",
        "stopwords": "stopword & co",
        "subjects": "subject",
        "nouns": "noun",
    }
    default_layers = ("long_sents", "subjects")
    layer_annotations: ClassVar[dict[str, tuple[str, ...]]] = {
        "subjects": ("DEP",),
        "nouns": ("POS", "LEMMA"),
    }
    layer_styles: ClassVar[dict[str, str]] = {
        "long_sents": "background: #fef9c3;",
        "stopwords": "background: #bae6fd;",
        "subjects": "border-bottom: 2px solid #7c3aed;",
    }
    css_prefix = "xx"

    def find(self, layer, words, sents, doc):
        if layer == "long_sents":
            return [
                Highlight(sent.start, sent.end, layer, f"{sent.n_words} words")
                for sent in sents
                if sent.n_words >= 5
            ]
        if layer == "stopwords":
            return [Highlight(w.start, w.end, layer) for w in words if w.text.lower() in STOPWORDS]
        if layer == "subjects":
            return [
                Highlight(*tokens_span([token]), layer, "subject")
                for token in doc
                if token.dep_ == "nsubj"
            ]
        return [Highlight(w.start, w.end, layer, w.lemma) for w in words if w.pos == "NOUN"]


text = "The old cat sleeps on the mat and the dog eats. A bird sings."


def parsed(sentences=True, tags=True):
    """The text as a Doc with a parse, the tags and the lemmas made by hand"""
    words = ["The", "old", "cat", "sleeps", "on", "the", "mat", "and", "the", "dog", "eats", "."]
    words += ["A", "bird", "sings", "."]
    spaces = [True] * 10 + [False, True] + [True, True, False, False]
    heads = [2, 2, 3, 3, 3, 6, 4, 10, 9, 10, 3, 3, 13, 14, 14, 14]
    deps = ["det", "amod", "nsubj", "ROOT", "prep", "det", "pobj", "cc", "det", "nsubj", "conj"]
    deps += ["punct", "det", "nsubj", "ROOT", "punct"]
    pos = ["DET", "ADJ", "NOUN", "VERB", "ADP", "DET", "NOUN", "CCONJ", "DET", "NOUN", "VERB"]
    pos += ["PUNCT", "DET", "NOUN", "VERB", "PUNCT"]
    kwargs = {"heads": heads, "deps": deps}
    if tags:
        kwargs |= {"pos": pos, "lemmas": [word.lower() for word in words]}
    if not sentences:
        # Without the parse there are no sentence boundaries either
        kwargs = {key: value for key, value in kwargs.items() if key not in ("heads", "deps")}
    return Doc(spacy.blank("xx").vocab, words=words, spaces=spaces, **kwargs)


def spans(ht, layer):
    return [ht.text[h.start : h.end] for h in ht.highlights if h.layer == layer]


def test_string():
    ht = Marks(text, layers="all")
    assert ht.text == text
    assert ht.layers == ("long_sents", "stopwords")
    assert spans(ht, "long_sents") == ["The old cat sleeps on the mat and the dog eats."]
    assert spans(ht, "stopwords") == ["The", "the", "and", "the", "A"]
    assert ht.counts == {"long_sents": 1, "stopwords": 5}
    assert repr(ht) == "Marks(counts={'long_sents': 1, 'stopwords': 5})"
    assert Marks(text).layers == ("long_sents",)


def test_doc():
    doc = parsed()
    ht = Marks(doc, layers="all")
    assert ht.layers == ("long_sents", "stopwords", "subjects", "nouns")
    assert spans(ht, "subjects") == ["cat", "dog", "bird"]
    assert [h.note for h in ht.highlights if h.layer == "nouns"] == ["cat", "mat", "dog", "bird"]
    assert Marks(doc).layers == ("long_sents", "subjects")
    # The same sentences from the boundaries of a Doc and from the text
    assert spans(ht, "long_sents") == spans(Marks(text), "long_sents")


def test_doc_without_the_annotations():
    ht = Marks(parsed(tags=False), layers="all")
    assert ht.layers == ("long_sents", "stopwords", "subjects")
    # Without the boundaries the sentences come from the text
    blank = spacy.blank("xx")(text)
    assert not blank.has_annotation("SENT_START")
    assert spans(Marks(blank), "long_sents") == spans(Marks(text), "long_sents")
    assert Marks(blank, layers="all").layers == ("long_sents", "stopwords")


@pytest.mark.parametrize(
    ("layer", "requirement"),
    [("subjects", "a dependency parse$"), ("nouns", "the parts of speech and the lemmas$")],
)
def test_layers_unavailable(layer, requirement):
    with pytest.raises(ParameterError, match=f"^The layer {layer} needs a Doc with {requirement}"):
        Marks(text, layers=layer)


def test_layers_unknown_annotation():
    class Entities(Marks):
        layers_desc: ClassVar[dict[str, str]] = {"entities": "entity"}
        layer_annotations: ClassVar[dict[str, tuple[str, ...]]] = {"entities": ("SPACY",)}

    with pytest.raises(ParameterError, match=r"needs a Doc with SPACY$"):
        Entities(text, layers="entities")


def test_layers_selection():
    assert Marks(text, layers=["stopwords", "long_sents"]).layers == ("long_sents", "stopwords")
    assert Marks(text, layers=(layer for layer in ["stopwords"])).layers == ("stopwords",)
    with pytest.raises(ParameterError, match=r"^Unknown layer of the highlighting: rhymes$"):
        Marks(text, layers=["stopwords", "rhymes"])
    with pytest.raises(ParameterError, match=r"^Unknown layer"):
        Marks(text, layers=[["stopwords"]])
    with pytest.raises(ParameterError, match="list of names"):
        Marks(text, layers=5)


@pytest.mark.parametrize("source", [666, ["a", "b"], {"a": "b"}])
def test_source_type(source):
    with pytest.raises(SourceTypeError):
        Marks(source)


def test_source_without_words():
    with pytest.raises(SourceError):
        Marks("?! ...")


def test_base_class():
    # The core has no layers of its own: a library implements find
    assert HighlightedText(text).layers == ()

    class Unfinished(HighlightedText):
        layers_desc: ClassVar[dict[str, str]] = {"stopwords": "stopword"}

    with pytest.raises(NotImplementedError):
        Unfinished(text, layers="all")


def test_sentences_count_the_words_of_the_hook():
    class Units(Marks):
        def doc_words(self, doc):
            return [
                Word(unit[0].idx, unit[-1].idx + len(unit[-1]), "".join(t.text for t in unit))
                for unit in iter_doc_units(doc, join_hyphens=True)
            ]

    sample = "A well-known old cat sleeps. It eats."
    nlp = spacy.blank("xx")
    nlp.add_pipe("sentencizer")
    for source in (nlp(sample), spacy.blank("xx")(sample)):
        assert Units(source, layers="long_sents").counts == {"long_sents": 1}
        assert Units(source, layers="long_sents").highlights[0].note == "5 words"
    assert Marks(nlp(sample), layers="long_sents").highlights[0].note == "6 words"


def test_find_of_another_layer():
    class Typo(Marks):
        def find(self, layer, words, sents, doc):
            return [Highlight(0, 3, "stopword")]

    with pytest.raises(
        ParameterError, match=r"^A fragment of the layer stopword is found for stopwords$"
    ):
        Typo(text, layers="stopwords")


@pytest.mark.parametrize(("start", "end"), [(3, 3), (5, 2), (-4, 2), (8, 10_000)])
def test_find_outside_the_text(start, end):
    class Astray(Marks):
        def find(self, layer, words, sents, doc):
            return [Highlight(start, end, layer)]

    with pytest.raises(ParameterError, match=rf"lies outside the text: {start}-{end}$"):
        Astray(text, layers="stopwords")


def test_defaults_are_read_only():
    with pytest.raises(TypeError):
        HighlightedText.layer_styles["x"] = "color: red;"  # type: ignore[index]
    with pytest.raises(TypeError):
        HighlightedText.layers_desc["x"] = "x"  # type: ignore[index]


def test_layer_requirements_listed():
    class Heavy(Marks):
        layer_annotations: ClassVar[dict[str, tuple[str, ...]]] = {
            "subjects": ("DEP", "POS", "LEMMA")
        }

    message = r"needs a Doc with a dependency parse, the parts of speech and the lemmas$"
    with pytest.raises(ParameterError, match=message):
        Heavy(text, layers="subjects")
    with pytest.raises(ParameterError, match=r"^The layer long_sents is not available$"):
        Marks._select_layers(["long_sents"], [])


def test_highlights_sorted():
    ht = Marks(parsed(), layers="all")
    positions = [(h.start, -h.end) for h in ht.highlights]
    assert positions == sorted(positions)


def test_iter_hooks():
    words = list(Marks.iter_words(None, "Hello, world!"))
    assert words == [(0, 5, "Hello"), (7, 12, "world")]
    assert list(Marks.iter_sents(None, " Hi.  Bye! ")) == [(1, 4, "Hi."), (6, 10, "Bye!")]

    class Words(Marks):
        def iter_words(self, text):
            return [(0, len(text), text)]

    assert Words("?!", layers="long_sents").counts == {"long_sents": 0}


def test_get_doc_words():
    assert get_doc_words(parsed())[:2] == [
        Word(0, 3, "The", "DET", "the"),
        Word(4, 7, "old", "ADJ", "old"),
    ]
    assert get_doc_words(parsed(tags=False))[0] == Word(0, 3, "The")
    # The part of speech and the lemma are taken each when the Doc has it
    doc = Doc(spacy.blank("xx").vocab, words=["The", "cat"], pos=["DET", "NOUN"])
    assert get_doc_words(doc) == [Word(0, 3, "The", "DET"), Word(4, 7, "cat", "NOUN")]
    doc = Doc(spacy.blank("xx").vocab, words=["The", "cats"], lemmas=["the", "cat"])
    assert get_doc_words(doc)[1] == Word(4, 8, "cats", None, "cat")


def test_byte_order_mark():
    sample = "\ufeffThe cat and the dog sleep on a mat."
    assert get_doc_words(spacy.blank("xx")(sample))[0] == Word(1, 4, "The")
    counts = Marks(sample, layers="stopwords").counts
    assert Marks(spacy.blank("xx")(sample), layers="stopwords").counts == counts
    assert counts == {"stopwords": 4}


def test_iter_doc_sents():
    nlp = spacy.blank("xx")
    nlp.add_pipe("sentencizer")
    assert list(iter_doc_sents(nlp("\n\nHello, world.  How are you?"))) == [
        (2, 15, "Hello, world."),
        (17, 29, "How are you?"),
    ]
    # A sentence of whitespace alone is skipped
    doc = Doc(
        spacy.blank("xx").vocab,
        words=["Hi", ".", "\n\n", "Bye", "."],
        spaces=[False, False, False, False, False],
        sent_starts=[True, False, True, True, False],
    )
    assert list(iter_doc_sents(doc)) == [(0, 3, "Hi."), (5, 9, "Bye.")]


def test_get_text_sents():
    sample = "Hello, world. How are you?"
    sents = get_text_sents(
        Marks.iter_sents(None, sample),
        [Word(*word) for word in Marks.iter_words(None, sample)],
    )
    assert sents == [Sent(0, 13, 2), Sent(14, 26, 3)]
    assert get_text_sents([(0, 6, "Hello.")], []) == [Sent(0, 6, 0)]


def test_group_words_by_sents():
    words = [Word(0, 5, "Hello"), Word(7, 12, "world"), Word(14, 17, "How"), Word(30, 33, "end")]
    sents = [Sent(0, 13, 2), Sent(14, 28, 1)]
    assert group_words_by_sents(words, sents) == [words[:2], [words[2]]]


def test_tokens_span():
    # The punctuation at the edge is left out
    doc = parsed()
    start, end = tokens_span(doc[8:12])
    assert doc.text[start:end] == "the dog eats"


def test_split_segments():
    highlights = [Highlight(0, 4, "a"), Highlight(2, 6, "b")]
    segments = [
        (start, end, [h.layer for h in active])
        for start, end, active in split_segments(8, highlights)
    ]
    assert segments == [(0, 2, ["a"]), (2, 4, ["a", "b"]), (4, 6, ["b"]), (6, 8, [])]
    assert list(split_segments(3, [])) == [(0, 3, [])]


def test_to_html():
    ht = Marks(text, layers="all")
    markup = ht.to_html()
    assert markup.startswith('<div class="xx-highlight"><style>')
    assert '<div class="xx-highlight-legend">' in markup
    assert '<span class="xx-hl xx-hl-stopwords">stopword &amp; co</span>' in markup
    assert '<span class="xx-highlight-count">5</span>' in markup
    assert 'title="11 words"' in markup
    assert ht._repr_html_() == markup
    bare = ht.to_html(legend=False, css=False)
    assert "<style>" not in bare and "xx-highlight-legend" not in bare
    assert bare.startswith('<div class="xx-highlight"><div class="xx-highlight-text">')


def test_to_html_nested_classes():
    # A segment of several layers lists them in the order of drawing, the notes joined
    markup = Marks(parsed(), layers=["nouns", "subjects"]).to_html(legend=False)
    assert (
        '<span class="xx-hl xx-hl-subjects xx-hl-nouns" title="subject; cat">cat</span>' in markup
    )


def test_to_html_escaping():
    markup = Marks("The <cat> & the dog\nsleep.", layers="stopwords").to_html()
    assert "&lt;cat&gt; &amp;" in markup
    assert "&#10;" in markup
    # A line break of Windows or of an old Mac is one break too
    for sample in ("The cat\r\nsleeps.\rThe dog\n", "The cat\nsleeps.\nThe dog\n"):
        markup = Marks(sample, layers="stopwords").to_html()
        assert "\r" not in markup
        assert markup.count("&#10;") == 3


def test_css():
    css = Marks.css()
    assert css.startswith(".xx-highlight { line-height: 1.7; }\n")
    assert (
        ".xx-highlight .xx-hl.xx-hl-long_sents, .xx-highlight .xx-hl.xx-hl-stopwords "
        "{ color: #1f2328; border-radius: 2px; }"
    ) in css
    assert ".xx-hl-subjects { border-bottom: 2px solid #7c3aed; }" in css
    assert "color: #1f2328" not in HighlightedText.css()
    assert HighlightedText.css().startswith(".anyts-highlight")
