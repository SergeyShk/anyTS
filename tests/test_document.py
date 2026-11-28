import pickle
import random
import re

import pytest
from anyseg import Document

from anyts import document as document_module
from anyts.constants import MESSAGES
from anyts.document import document_part, document_words, get_tree, to_document
from anyts.exceptions import ParameterError, SourceError, SourceTypeError
from anyts.extractors import split_paragraphs
from anyts.utils import is_document
from tests.documents import parsed

TEXT = "The cat sat. It slept!\n\nThe end"


def tokens(document):
    return [token.text for token in document.tokens]


def sentences(document):
    return [sentence.text for sentence in document.sentences]


def words(text):
    """Words of a text alone, with their positions"""
    return [(m.start(), m.end(), m.group()) for m in re.finditer(r"\w+", text)]


def semicolons(text):
    """Sentences of a text at its semicolons"""
    return [(m.start(), m.end(), m.group()) for m in re.finditer(r"[^;]+", text)]


def test_string():
    document = to_document(TEXT)
    assert tokens(document) == ["The", "cat", "sat", ".", "It", "slept", "!", "The", "end"]
    assert sentences(document) == ["The cat sat.", "It slept!", "The end"]
    assert [paragraph.text for paragraph in document.paragraphs] == [
        "The cat sat. It slept!",
        "The end",
    ]


def test_string_tokens():
    # A run of one mark is a token, a combining mark stays in its word
    text = "Hi... «yes»?! áb -- 5%"
    assert tokens(to_document(text)) == [
        "Hi", "...", "«", "yes", "»", "?", "!", "áb", "--", "5", "%",
    ]  # fmt: skip
    # Invisible separators are in no token; a soft hyphen inside a word stays
    text = "﻿The​ cat­ sl­ept ⁠"
    assert tokens(to_document(text)) == ["The", "cat", "sl­ept"]
    assert tokens(to_document("")) == tokens(to_document(" \n​ ")) == []
    # A character of no class is a token of its own
    assert tokens(to_document("a  b")) == ["a", "", "b"]


def test_tokenize():
    # The default tokens fill the gaps between those of the tokenizer
    document = to_document("Hi, you there.", tokenize=words)
    assert tokens(document) == ["Hi", ",", "you", "there", "."]
    # Invisible separators at the edges of a token are left out, a token of them alone dropped
    text = "a­ ​ b"
    spans = [(0, 2, "a­"), (3, 4, "​"), (5, 6, "b")]
    assert tokens(to_document(text, tokenize=lambda _: spans)) == ["a", "b"]
    # A token may hold a space
    assert tokens(to_document("3 000 cats", tokenize=lambda _: [(0, 5, "3 000")])) == [
        "3 000",
        "cats",
    ]


def thirds(text):
    """Sentences of a text: its first three characters and the rest"""
    return [(0, 3, text[:3]), (3, len(text), text[3:])] if len(text) > 3 else [(0, 3, text)]


def test_sentenize():
    # A sentence without a token of its own adds no start
    document = to_document("One two; three; ;", sentenize=semicolons)
    assert sentences(document) == ["One two;", "three; ;"]
    # A sentence that starts inside a token starts at the next one; a blank line ends a sentence
    document = to_document("Onetwo three\n\nfour", sentenize=thirds)
    assert sentences(document) == ["Onetwo", "three", "four"]
    # The sentences may come in any order: only their starts count
    backwards = to_document("One. Two. Three.", sentenize=lambda text: semicolons(text)[::-1])
    assert sentences(backwards) == ["One. Two. Three."]
    reversed_thirds = to_document("Onetwo three", sentenize=lambda text: thirds(text)[::-1])
    assert sentences(reversed_thirds) == ["Onetwo", "three"]


def test_hooks_of_spans():
    """The spans of anySeg are hooks as they are, as triples with start, end and text are"""
    from anyseg import Segmenter

    segmenter = Segmenter("ru")
    text = "Ёж идёт домой. Т. е. всё.\n\nКот спит."
    document = to_document(text, tokenize=segmenter.tokenize, sentenize=segmenter.sentenize)
    assert sentences(document) == ["Ёж идёт домой.", "Т. е. всё.", "Кот спит."]
    assert tokens(document) == [span.text for span in segmenter.tokenize(text)]


def test_hooks_are_checked():
    with pytest.raises(SourceTypeError, match=r"^The tokenize must be callable, not int$"):
        to_document(TEXT, tokenize=5)
    with pytest.raises(SourceTypeError, match=r"^The sentenize must be callable, not str$"):
        to_document(TEXT, sentenize="split")
    with pytest.raises(SourceTypeError, match=r"^The tokenize must give triples .+ not \(0, 3\)$"):
        to_document(TEXT, tokenize=lambda text: [(0, 3)])
    with pytest.raises(SourceTypeError, match=r"ascending for tokenize, not \(0, 3, 'The'\)$"):
        to_document(TEXT, tokenize=lambda text: [(4, 7, "cat"), (0, 3, "The")])
    with pytest.raises(SourceTypeError, match=r"^The sentenize must give triples"):
        to_document(TEXT, sentenize=lambda text: [(0, 99, text)])
    with pytest.raises(SourceTypeError, match=r"^The sentenize must give triples .+ not 5$"):
        to_document(TEXT, sentenize=lambda text: 5)
    own = {**MESSAGES, "hook_bounds": "Own {hook}: {span}"}
    with pytest.raises(SourceTypeError, match=r"^Own tokenize: \(0, 3\)$"):
        to_document(TEXT, tokenize=lambda text: [(0, 3)], messages=own)
    with pytest.raises(SourceTypeError, match=r"^Own sentenize: 5$"):
        to_document("One two", sentenize=lambda text: 5, messages=own)


def test_document():
    document = to_document(TEXT)
    assert to_document(document) is document
    assert is_document(document) and not is_document(TEXT)


def test_tree_for_one_use():
    """A tree of a document is built anew every time, and the one of _tree_once is broken after
    its use"""
    document = parsed(["Cats", "sleep"], [1, 1], ["nsubj", "ROOT"])
    assert get_tree(document) is not get_tree(document)
    with document_module._tree_once(document) as tree:
        cats, sleep = tree.words
        assert cats.head is sleep
    assert cats.head is None
    assert sleep.children == ()
    assert not hasattr(cats, "tree")


def test_word_at_a_position():
    """The word at a position or of a span, none at whitespace, and the first word of a multiword
    token"""
    tree = get_tree(to_document("Cats  sleep\n\nDogs bark"))
    assert [tree.word_at(position) for position in (0, 4, 6, 11, 13, 18)] == [
        tree.words[0],
        None,
        tree.words[1],
        None,
        tree.words[2],
        tree.words[3],
    ]
    assert tree.word_at(3).form == "Cats"
    assert tree.word_at(4, 7) is tree.words[1]
    assert tree.word_at(4, 6) is None
    assert tree.word_at(6, 6) is tree.words[1]
    assert tree.word_at(-1) is None
    assert tree.word_at(len(tree.text)) is None
    # The token of the document leaves out the separators at the edges of a piece of the text
    tree = get_tree(to_document("\ufeffThe cat sat on the \u200bmat."))
    assert [word.form for word in tree.words] == ["The", "cat", "sat", "on", "the", "mat", "."]
    assert tree.word_at(0) is None
    assert tree.word_at(19, 23) is tree.words[5]
    tree = get_tree(Document.from_tokens("al cine", [0, 3], [2, 7], words={0: ["a", "el"]}))
    assert [word.form for word in tree.words] == ["a", "el", "cine"]
    assert tree.word_at(1) is tree.words[0]


def test_other_sources():
    with pytest.raises(SourceTypeError, match="cannot be of type int"):
        to_document(5)
    own = {**MESSAGES, "source_type": "Own {type}"}
    with pytest.raises(SourceTypeError, match="Own list"):
        to_document([TEXT], messages=own)


def test_document_words():
    assert document_words(to_document("Well, the cat sat - 100% €5!")) == (
        "Well",
        "the",
        "cat",
        "sat",
        "100",
        "5",
    )
    assert document_words(to_document("?! ...")) == ()
    with pytest.raises(SourceTypeError, match=r"^A Document of anySeg is expected, not str: make"):
        document_words(TEXT)


def test_blank_lines():
    """A blank line ends a paragraph of the document, as BLANK_LINE and split_paragraphs have it"""
    text = "The page ends in the middle of a\n\x0csentence that goes on."
    assert sentences(to_document(text)) == [
        "The page ends in the middle of a",
        "sentence that goes on.",
    ]
    generator = random.Random(0)
    alphabet = (
        "ab .\n\r\x0b\x0c\x85\u2028\u2029\u00ad\u2060\u200b\u200c\u200d\ufeff\t \x01\x7f\xa0"
        "\u200e\u200f\u2066\u061c"
    )
    for _ in range(2000):
        text = "".join(generator.choice(alphabet) for _ in range(generator.randint(0, 12)))
        paragraphs = [paragraph.text for paragraph in to_document(text).paragraphs]
        assert paragraphs == split_paragraphs(text), repr(text)


def test_words_of_no_class():
    """A token of private use or unassigned characters is no word"""
    document = to_document("\uf0b7 First item.\n\uf0b7 Second item \u0378 x\ue000")
    assert tokens(document)[:3] == ["\uf0b7", "First", "item"]
    assert document_words(document) == ("First", "item", "Second", "item", "x")


def test_tokens_over_a_blank_line():
    text = "One two. Three four.\n\nFive six."
    with pytest.raises(SourceTypeError, match="cannot make a document: token 4: runs over"):
        to_document(text, tokenize=lambda t: [(14, 24, t[14:24])])
    own = {**MESSAGES, "document_tokens": "Own {error}"}
    with pytest.raises(SourceTypeError, match=r"^Own token 4"):
        to_document(text, tokenize=lambda t: [(14, 24, t[14:24])], messages=own)


def test_tree():
    document = Document.from_tokens(
        "Vino del pueblo. Se fue",
        [0, 5, 9, 15, 17, 20],
        [4, 8, 15, 16, 19, 23],
        sentence_starts=[0, 4],
        words={1: ["de", "el"]},
    )
    document.set_columns(
        upos=["VERB", "ADP", "DET", "NOUN", "PUNCT", "PRON", "VERB"],
        feats=["Mood=Ind", None, "Gender=Masc", "Gender=Masc", None, None, "Mood=Ind"],
        head=[0, 4, 4, 1, 1, 2, 0],
        deprel=["root", "case", "det", "obl", "punct", "obj", "root"],
    )
    tree = get_tree(document)
    vino, de, el, pueblo, mark, se, fue = tree.words
    assert tree.sentences == ((vino, de, el, pueblo, mark), (se, fue))
    assert (de.start, de.end) == (el.start, el.end) == (5, 8)
    assert pueblo.children == (de, el) and de.head is pueblo and vino.head is None
    assert (se.sentence, se.head) == (1, fue)
    assert el.feats is pueblo.feats and vino.feats == {"Mood": "Ind"} and de.feats == {}
    clone = pickle.loads(pickle.dumps(el))
    assert clone.head.form == "pueblo" and clone.tree.sentences[1][1].children[0].form == "Se"
    empty = pickle.loads(pickle.dumps(get_tree(to_document(""))))
    assert empty.words == empty.sentences == ()
    with pytest.raises(SourceTypeError, match=r"^A Document of anySeg is expected, not str: make"):
        get_tree("Vino del pueblo")


@pytest.mark.parametrize(
    ("text", "tokens"),
    [
        ("Hola \u200emundo.", ["Hola", "mundo", "."]),
        ("Hola mundo\u200f.", ["Hola", "mundo", "."]),
        ("Вто\u2060рой день.", ["Вто\u2060рой", "день", "."]),
        ("pa\u200egina\u200f\u200e web", ["pa\u200egina", "web"]),
    ],
)
def test_marks_of_the_direction_of_text(text, tokens):
    """A mark of the direction of text or a word joiner is never a token: between words it is
    in neither, inside a word part of it, as in anySeg"""
    assert [token.text for token in to_document(text).tokens] == tokens


def parsed_text():
    """A document of two paragraphs of three sentences with a parse, lemmas and features"""
    return parsed(
        words=["Cats", "sleep", ".", "Dogs", "bark", "loudly", ".", "\n\n", "Birds", "sing", "."],
        spaces=[True, False, True, True, True, False, False, False, True, False, False],
        heads=[1, 1, 1, 4, 4, 4, 4, 6, 9, 9, 9],
        deps=[
            "nsubj",
            "ROOT",
            "punct",
            "nsubj",
            "ROOT",
            "advmod",
            "punct",
            "dep",
            "nsubj",
            "ROOT",
            "punct",
        ],
        pos=[
            "NOUN",
            "VERB",
            "PUNCT",
            "NOUN",
            "VERB",
            "ADV",
            "PUNCT",
            "SPACE",
            "NOUN",
            "VERB",
            "PUNCT",
        ],
        lemmas=["cat", "sleep", ".", "dog", "bark", "loudly", ".", "\n\n", "bird", "sing", "."],
        morphs=["Number=Plur", "", "", "Number=Plur", "", "", "", "", "Number=Plur", "", ""],
    )


def test_document_part_of_a_sentence():
    """A part keeps the tokens, the words with their columns and the heads of its sentence, at
    positions from its start"""
    document = to_document(parsed_text())
    part = document_part(document, 13, 14)
    assert part.text == "Dogs bark loudly."
    assert list(zip(part.tokens.starts, part.tokens.ends, strict=True)) == [
        (0, 4),
        (5, 9),
        (10, 16),
        (16, 17),
    ]
    words = get_tree(part).words
    assert [(w.form, w.lemma, w.upos, w.deprel) for w in words] == [
        ("Dogs", "dog", "NOUN", "nsubj"),
        ("bark", "bark", "VERB", "root"),
        ("loudly", "loudly", "ADV", "advmod"),
        (".", ".", "PUNCT", "punct"),
    ]
    assert [w.head.form if w.head else None for w in words] == ["bark", None, "bark", "bark"]
    assert words[0].feats == {"Number": "Plur"}


def test_document_part_of_several_sentences():
    """A span takes the sentences it overlaps whole, across a blank line with its paragraphs"""
    document = to_document(parsed_text())
    part = document_part(document, 3, 33)
    assert [sentence.text for sentence in part.sentences] == [
        "Cats sleep.",
        "Dogs bark loudly.",
        "Birds sing.",
    ]
    assert [paragraph.text for paragraph in part.paragraphs] == [
        "Cats sleep. Dogs bark loudly.",
        "Birds sing.",
    ]
    assert document_part(document, 0, len(document.text)).text == document.text
    # A document without columns gives a part without them
    plain = document_part(to_document("One two. Three four."), 9, 10)
    assert plain.text == "Three four."
    assert plain.column("lemma") == [None, None, None]


def test_document_part_keeps_multiword_tokens():
    document = Document.from_tokens(
        "Vino. Salió del pueblo.",
        [0, 4, 6, 12, 16, 22],
        [4, 5, 11, 15, 22, 23],
        sentence_starts=[0, 2],
        words={3: ["de", "el"]},
    )
    document.set_columns(upos=[None, None, None, "ADP", "DET", None, None])
    part = document_part(document, 7, 8)
    assert part.text == "Salió del pueblo."
    assert [word.form for word in part.words] == ["Salió", "de", "el", "pueblo", "."]
    assert part.column("upos") == [None, "ADP", "DET", None, None]


@pytest.mark.parametrize(
    ("arguments", "error", "message"),
    [
        (("The cat.", 0, 3), SourceTypeError, "^A Document of anySeg is expected, not str: make"),
        ((None, 0.5, 3), ParameterError, "^The start must be an integer, not float$"),
        ((None, 0, "3"), ParameterError, "^The end must be an integer, not str$"),
        ((None, 3, 3), ParameterError, "^The part must lie within the text of 20 characters"),
        ((None, -1, 3), ParameterError, "not -1 and 3$"),
        ((None, 0, 21), ParameterError, "not 0 and 21$"),
        ((None, 8, 9), SourceError, "^The part from 8 to 9 overlaps no sentence$"),
    ],
)
def test_document_part_errors(arguments, error, message):
    document = to_document("The cat. The dog.   ")
    source, start, end = arguments
    with pytest.raises(error, match=message):
        document_part(document if source is None else source, start, end)
