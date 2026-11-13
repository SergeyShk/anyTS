import re

import pytest
import spacy
from spacy.tokens import Doc

from anyts.components import start_sents_after_blank_lines
from anyts.constants import MESSAGES
from anyts.document import document_words, to_document
from anyts.exceptions import SourceTypeError
from anyts.utils import is_document

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


def test_hooks_are_checked():
    with pytest.raises(SourceTypeError, match="tokenizer"):
        to_document(TEXT, tokenize=5)
    with pytest.raises(SourceTypeError, match="sentence splitter"):
        to_document(TEXT, sentenize="split")
    with pytest.raises(SourceTypeError, match="triples"):
        to_document(TEXT, tokenize=lambda text: [(0, 3)])
    with pytest.raises(SourceTypeError, match="ascending integer bounds"):
        to_document(TEXT, tokenize=lambda text: [(4, 7, "cat"), (0, 3, "The")])
    with pytest.raises(SourceTypeError, match="ascending integer bounds"):
        to_document(TEXT, sentenize=lambda text: [(0, 99, text)])


def test_document():
    document = to_document(TEXT)
    assert to_document(document) is document
    assert is_document(document) and not is_document(TEXT)


def test_doc_with_sentences():
    nlp = spacy.blank("en")
    nlp.add_pipe("sentencizer")
    document = to_document(nlp("One. Two! Three"))
    assert sentences(document) == ["One.", "Two!", "Three"]
    # The sentences of the Doc win over sentenize
    assert sentences(to_document(nlp("One. Two"), sentenize=semicolons)) == ["One.", "Two"]


def test_doc_without_sentences():
    """No or only partial sentence starts and no parse: the sentences of sentenize"""
    doc = spacy.blank("en")("One. Two!\n\nThree; four")
    assert sentences(to_document(doc)) == ["One.", "Two!", "Three; four"]
    assert sentences(to_document(doc, sentenize=semicolons)) == ["One. Two!", "Three;", "four"]
    partial = start_sents_after_blank_lines(spacy.blank("en")("One. Two!\n\nThree"))
    assert partial.has_annotation("SENT_START")
    assert sentences(to_document(partial)) == ["One.", "Two!", "Three"]


def test_doc_columns():
    vocab = spacy.blank("en").vocab
    doc = Doc(
        vocab,
        words=["Cats", "slept", "."],
        spaces=[True, False, False],
        lemmas=["cat", "sleep", "."],
        pos=["NOUN", "VERB", "PUNCT"],
        morphs=["Number=Plur", "Tense=Past", ""],
    )
    document = to_document(doc)
    assert document.column("lemma") == ["cat", "sleep", "."]
    assert document.column("upos") == ["NOUN", "VERB", "PUNCT"]
    assert document.column("feats") == ["Number=Plur", "Tense=Past", None]
    # A parse keeps its sentences and its tree
    parsed = Doc(
        vocab, words=["Cats", "slept", "."], heads=[1, 1, 1], deps=["nsubj", "ROOT", "punct"]
    )
    document = to_document(parsed)
    assert document.column("head") == [2, 0, 2]
    assert document.column("deprel") == ["nsubj", "root", "punct"]


def test_doc_multiword_tokens():
    nlp = spacy.blank("es", config={"nlp": {"tokenizer": {"@tokenizers": "anyseg.Tokenizer.v1"}}})
    doc = nlp("Vino del pueblo. Se fue")
    document = to_document(doc)
    assert tokens(document) == ["Vino", "del", "pueblo", ".", "Se", "fue"]
    assert [word.form for word in document.words][:4] == ["Vino", "de", "el", "pueblo"]
    assert sentences(document) == ["Vino del pueblo.", "Se fue"]
    assert document_words(document) == ("Vino", "del", "pueblo", "Se", "fue")


def test_other_sources():
    doc = spacy.blank("en")(TEXT)
    with pytest.raises(SourceTypeError, match=re.escape(MESSAGES["source_span"])):
        to_document(doc[:2])
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
    with pytest.raises(SourceTypeError, match="cannot be of type str"):
        document_words(TEXT)
