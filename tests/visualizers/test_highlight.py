import re
from typing import ClassVar

import pandas as pd
import pytest
import spacy
from spacy.tokens import Doc

from anyts.cohesion_stats import ConnectorMatcher
from anyts.components import start_sents_after_blank_lines
from anyts.exceptions import ParameterError, SourceError, SourceTypeError
from anyts.utils import iter_doc_units
from anyts.visualizers import Highlight, HighlightedText
from anyts.visualizers.highlight import (
    Sent,
    Word,
    calc_alliteration_runs,
    check_params,
    find_alliteration,
    find_complex_words,
    find_connector_highlights,
    find_long_sents,
    find_phrase_highlights,
    find_split_predicate_highlights,
    find_words,
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


def test_doc_with_partial_boundaries():
    """The starts after the blank lines alone leave the sentences to the text"""
    paragraphs = f"{text}\n\n{text}"
    partial = start_sents_after_blank_lines(spacy.blank("xx")(paragraphs))
    assert spans(Marks(partial), "long_sents") == spans(Marks(paragraphs), "long_sents")
    assert len(spans(Marks(partial), "long_sents")) == 2


@pytest.mark.parametrize(
    ("layer", "requirement"),
    [("subjects", "dependency parse$"), ("nouns", "parts of speech, lemmas$")],
)
def test_layers_unavailable(layer, requirement):
    message = f"^The layer {layer} needs a Doc with the annotations: {requirement}"
    with pytest.raises(ParameterError, match=message):
        Marks(text, layers=layer)


def test_layers_unknown_annotation():
    class Entities(Marks):
        layers_desc: ClassVar[dict[str, str]] = {"entities": "entity"}
        layer_annotations: ClassVar[dict[str, tuple[str, ...]]] = {"entities": ("SPACY",)}

    with pytest.raises(ParameterError, match=r"needs a Doc with the annotations: SPACY$"):
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

    message = r"needs a Doc with the annotations: dependency parse, parts of speech, lemmas$"
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


def test_sentences_of_a_series():
    words = [Word(0, 5, "Hello"), Word(7, 12, "world"), Word(14, 17, "How")]
    sents = [Sent(0, 13, 2), Sent(14, 18, 1)]
    spans = [(0, 13, "Hello, world."), (14, 18, "How?")]
    gapped_words = pd.Series([None, *words]).iloc[1:]
    gapped_sents = pd.Series([None, *sents]).iloc[1:]
    assert get_text_sents(spans, gapped_words) == sents
    assert group_words_by_sents(words, gapped_sents) == [words[:2], [words[2]]]


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


class Lines(Marks):
    """A library whose sentences end only at a final mark"""

    def iter_sents(self, text):
        for match in re.finditer(r"[^.!?\s][^.!?]*[.!?]*", text):
            yield match.start(), match.end(), match.group()


def test_blank_line_ends_a_sentence_of_iter_sents():
    sample = "Notes without a dot here\n\nThe old cat sleeps on the mat."
    sents = [(h.start, h.end) for h in Lines(sample, layers=["long_sents"]).highlights]
    assert [sample[start:end] for start, end in sents] == [
        "Notes without a dot here",
        "The old cat sleeps on the mat.",
    ]
    doc = spacy.blank("xx")(sample)
    assert [h.start for h in Lines(doc, layers=["long_sents"]).highlights] == [0, 26]


def test_check_params():
    check_params(30, 4, 0.001)
    check_params(1, 1, 1)
    for args, message in [
        ((0, 4, 0.001), r"^The number of words of a long sentence must be greater than 0$"),
        ((30, 0, 0.001), r"^The minimum number of syllables in a complex word"),
        ((30, 4, 0), r"^The threshold of the alliteration must lie in the interval \(0, 1\]$"),
        ((30, 4, 1.5), r"^The threshold of the alliteration"),
        ((2.5, 4, 0.001), r"^The number of words of a long sentence must be an integer"),
        ((30, 4, "x"), r"^The threshold of the alliteration must be a number"),
    ]:
        with pytest.raises(ParameterError, match=message):
            check_params(*args)


def words_of(text):
    return [Word(m.start(), m.end(), m.group()) for m in re.finditer(r"\w+", text)]


def test_find_long_sents_and_complex_words():
    sents = [Sent(0, 10, 1), Sent(11, 30, 6)]
    assert find_long_sents(sents, 5) == [Highlight(11, 30, "long_sents", "long sentence, 6 words")]
    assert find_long_sents(sents, 1, lambda n: f"{n}")[0] == Highlight(0, 10, "long_sents", "1")
    words = words_of("a beautiful extraordinary cat")
    vowels = lambda word: len(re.findall("[aeiouy]+", word))  # noqa: E731
    assert find_complex_words(words, 4, vowels) == [
        Highlight(12, 25, "complex_words", "complex word, 5 syllables")
    ]
    assert find_complex_words(words, 1, vowels, str)[0].note == "1"


def test_find_words():
    words = words_of("The cat and the dog")
    stop = lambda word: word.text.lower() in STOPWORDS  # noqa: E731
    assert find_words(words, stop, "stopwords", "stopword") == [
        Highlight(0, 3, "stopwords", "stopword"),
        Highlight(8, 11, "stopwords", "stopword"),
        Highlight(12, 15, "stopwords", "stopword"),
    ]
    assert find_words(words, lambda word: False, "stopwords") == []


def test_find_phrase_highlights():
    words = words_of("In fact, the cat sat in front of the mat")
    found = find_phrase_highlights(words, ["in front of", "in fact"], "phrases")
    assert [(h.start, h.end, h.note) for h in found] == [
        (0, 7, "\u00abin fact\u00bb"),
        (21, 32, "\u00abin front of\u00bb"),
    ]
    # Variants that stand for a phrase of the list, matched by an own normalization
    variants = {"IN FRONT OF": "in front of", "in   front of": "before"}
    found = find_phrase_highlights(
        words, variants, "phrases", lambda p: f"phrase: {p}", normalize=str.upper
    )
    assert [h.note for h in found] == ["phrase: in front of"]


class Connectors(ConnectorMatcher):
    pos_tags = frozenset({"ADV", "CCONJ"})


def test_find_connector_highlights():
    matcher = Connectors({"however": ("adversative", "secondary"), "and": ("additive", "primary")})
    words = [
        Word(*w) for w in [(0, 7, "However"), (8, 11, "cat"), (12, 15, "and"), (16, 19, "dog")]
    ]
    found = find_connector_highlights(words, None, matcher)
    assert [(h.start, h.end, h.note) for h in found] == [
        (0, 7, "however: adversative, secondary"),
        (12, 15, "and: additive, primary"),
    ]
    # The parts of speech of the words, or of the hook, check a one-word connector
    tagged = [word._replace(pos="NOUN" if word.text == "and" else "ADV") for word in words]
    assert [h.note.split(":")[0] for h in find_connector_highlights(tagged, None, matcher)] == [
        "however"
    ]
    by_hook = find_connector_highlights(
        words, [Sent(0, 19, 4)], matcher, str, lambda w: "CCONJ" if w.text == "and" else "NOUN"
    )
    assert [h.note for h in by_hook] == [
        "Connector(sent=0, start=2, end=3, text='and', cls='additive', kind='primary')"
    ]


def test_find_connector_highlights_through_a_mark():
    class Before(Connectors):
        blocked_after: ClassVar = {"before": frozenset({"the"})}

    matcher = Before({"before": ("temporal", "primary")})
    text = "He left before, the end"
    words = [
        Word(0, 2, "He"),
        Word(3, 7, "left"),
        Word(8, 14, "before"),
        Word(16, 19, "the"),
        Word(20, 23, "end"),
    ]
    assert find_connector_highlights(words, None, matcher) == []
    found = find_connector_highlights(words, None, matcher, text=text)
    assert [(h.start, h.end) for h in found] == [(8, 14)]
    # Spaces alone are no mark, nor is the hyphen of a hyphenated word
    assert find_connector_highlights(words, None, matcher, text=text.replace(",", " ")) == []
    hyphenated = [*words[:3], Word(15, 18, "the"), Word(19, 22, "end")]
    assert (
        find_connector_highlights(hyphenated, None, matcher, text="He left before-the end") == []
    )
    # A quote between the words is no mark either
    quoted = [*words[:3], Word(16, 19, "the"), Word(20, 23, "end")]
    assert find_connector_highlights(quoted, None, matcher, text='He left before "the end"') == []
    with pytest.raises(SourceTypeError):
        find_connector_highlights(words, None, matcher, text=5)


def test_find_connector_highlights_blocked():
    matcher = Connectors({"and": ("additive", "primary")})
    words = words_of("cats and dogs and birds")
    found = find_connector_highlights(words, None, matcher, blocked=lambda w: w.start == 5)
    assert [(h.start, h.end) for h in found] == [(14, 17)]
    assert len(find_connector_highlights(words, None, matcher, blocked=lambda w: False)) == 2
    with pytest.raises(SourceTypeError, match=r"^The check of the blocked words must be callable"):
        find_connector_highlights(words, None, matcher, blocked=True)


def test_find_split_predicate_highlights():
    doc = Doc(
        spacy.blank("xx").vocab,
        words=["They", "made", "a", "decision"],
        lemmas=["they", "make", "a", "decision"],
    )
    found = find_split_predicate_highlights([(doc[1], doc[3])])
    assert found == [Highlight(5, 20, "split_predicates", "split predicate: make decision")]
    assert (
        find_split_predicate_highlights([(doc[1], doc[3])], lambda v, n: v.text)[0].note == "made"
    )
    assert find_split_predicate_highlights([]) == []


FREQUENCIES = {"s": 0.06, "t": 0.09, "z": 0.001}


def test_calc_alliteration_runs():
    # zoo and zebra repeat the rare z, the frequent t of tall tree is not enough
    words = ["zoo", "zebra", "tall", "tree"]
    assert calc_alliteration_runs(words, FREQUENCIES) == [(0, 2, "z")]
    assert calc_alliteration_runs(words, FREQUENCIES, threshold=1) == [(0, 2, "z"), (2, 4, "t")]
    # A transparent word neither breaks nor continues a run, a word without the consonant breaks it
    assert calc_alliteration_runs(["Zoo", "of", "zebra"], FREQUENCIES) == [(0, 3, "z")]
    assert calc_alliteration_runs(["zoo", "cat", "zebra"], FREQUENCIES) == []
    opaque = calc_alliteration_runs(["zoo", "of", "zebra"], FREQUENCIES, is_transparent=bool)
    assert opaque == []
    # The stem of a language: here the first letter alone, so a repetition is less likely
    first = calc_alliteration_runs(
        ["sass", "sits"], FREQUENCIES, threshold=0.01, stem=lambda w: w[0]
    )
    assert first == [(0, 2, "s")]
    assert calc_alliteration_runs(["sass", "sits"], FREQUENCIES, threshold=0.01) == []


def test_find_alliteration():
    text = "Zoo zebra. Zany cat"
    words = words_of(text)
    sents = [Sent(0, 10, 2), Sent(11, 19, 2)]
    assert find_alliteration(words, sents, FREQUENCIES) == [
        Highlight(0, 9, "alliteration", "alliteration on z")
    ]
    whole = find_alliteration(words, None, FREQUENCIES, note=lambda c: c.upper())
    assert whole == [Highlight(0, 15, "alliteration", "Z")]


class Translated(Marks):
    annotation_names: ClassVar[dict[str, str]] = {"POS": "word classes", "LEMMA": "base forms"}


def test_annotation_names():
    message = r"^The layer nouns needs a Doc with the annotations: word classes, base forms$"
    with pytest.raises(ParameterError, match=message):
        Translated(text, ["nouns"])


def test_empty_sentences_give_no_fragments():
    matcher = Connectors({"and": ("additive", "primary")})
    words = words_of("zoo and zebra")
    assert len(find_connector_highlights(words, None, matcher)) == 1
    assert find_connector_highlights(words, [], matcher) == []
    zoo = words_of("zoo of zebra")
    assert len(find_alliteration(zoo, None, FREQUENCIES)) == 1
    assert find_alliteration(zoo, [], FREQUENCIES) == []


def test_find_phrase_highlights_normalizes_every_word_alone():
    # A normalization of words, such as a lemmatizer, reads the phrases word by word
    lemmas = {"goes": "go", "went": "go"}
    words = words_of("She goes to school and went to work")
    found = find_phrase_highlights(
        words, ["goes to"], "phrases", normalize=lambda w: lemmas.get(w.lower(), w.lower())
    )
    assert [(h.start, h.end, h.note) for h in found] == [
        (4, 11, "\u00abgoes to\u00bb"),
        (23, 30, "\u00abgoes to\u00bb"),
    ]
    # A normalization that is not idempotent is applied once
    stems = find_phrase_highlights(
        words_of("glad to"), ["glad"], "phrases", lambda p: p, lambda w: w[:-1]
    )
    assert [h.note for h in stems] == ["glad"]


def test_find_phrase_highlights_reads_a_set_in_order():
    found = find_phrase_highlights(words_of("In fact"), {"in fact", "In fact"}, "phrases")
    assert [h.note for h in found] == ["\u00abIn fact\u00bb"]


@pytest.mark.parametrize("phrases", ["in fact", ["in fact", 1], {"in fact": 1}])
def test_find_phrase_highlights_checks_the_phrases(phrases):
    with pytest.raises(SourceTypeError):
        find_phrase_highlights(words_of("in fact"), phrases, "phrases")


@pytest.mark.parametrize("words", ["zoo zebra", [Word(0, 3, "zoo")]])
def test_calc_alliteration_runs_checks_the_words(words):
    with pytest.raises(SourceTypeError):
        calc_alliteration_runs(words, FREQUENCIES)


def test_finders_check_their_hooks():
    words = [Word(0, 3, "The"), Word(4, 7, "cat")]
    calls = [
        lambda: find_long_sents([], 5, note=42),
        lambda: find_complex_words(words, 3, 42),
        lambda: find_words(words, 42, "stopwords"),
        lambda: find_phrase_highlights(words, ["the cat"], "x", normalize=42),
        lambda: find_connector_highlights(words, None, ConnectorMatcher({}), pos=42),
        lambda: find_split_predicate_highlights([], note=42),
        lambda: calc_alliteration_runs(["cat", "cot"], {"c": 0.1}, stem=42),
        lambda: find_alliteration(words, None, {"c": 0.1}, is_transparent=42),
    ]
    for call in calls:
        with pytest.raises(SourceTypeError, match=r" must be callable, not int$"):
            call()


@pytest.mark.parametrize(
    ("call", "error", "message"),
    [
        (lambda: find_long_sents([], 0), ParameterError, r"^The number of words of a long"),
        (lambda: find_long_sents([], None), ParameterError, r"^The number of words of a long"),
        (lambda: find_complex_words([], 0, len), ParameterError, r"^The minimum number of syll"),
        (lambda: calc_alliteration_runs(["a"], {"c": 0.1}, 5), ParameterError, r"^The threshold"),
        (
            lambda: calc_alliteration_runs(["a"], {"c": "0.1"}),
            SourceTypeError,
            r"be numbers, not s",
        ),
        (
            lambda: calc_alliteration_runs(["a"], {"c": -0.1}),
            ParameterError,
            r"\[0, 1\], not -0.1",
        ),
        (lambda: calc_alliteration_runs(["a"], {1: 0.1}), SourceTypeError, r"^The consonant must"),
        (lambda: find_alliteration([], None, ["c"]), SourceTypeError, r"a mapping of consonants"),
    ],
)
def test_finders_check_their_numbers(call, error, message):
    with pytest.raises(error, match=message):
        call()


def test_phrase_highlights_of_a_part_normalized_to_nothing():
    words = [Word(0, 2, "in"), Word(3, 7, "fact"), Word(8, 9, ","), Word(10, 12, "it")]
    found = find_phrase_highlights(
        words, ["in fact ,", ","], "x", normalize=lambda w: w.strip(",").lower()
    )
    assert found == [Highlight(0, 7, "x", "\u00abin fact ,\u00bb")]


def test_words_of_iter_words_checked():
    class Bad(Marks):
        def iter_words(self, text):
            return [(5, 2, "cat")]

    with pytest.raises(
        SourceTypeError,
        match=r"^The iter_words of Bad must give ascending triples of integer bounds",
    ):
        Bad("The cat")
