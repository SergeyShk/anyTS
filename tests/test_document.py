import gc
import pickle
import random
import re

import pytest
import spacy
from anyseg import Document
from spacy.tokens import Doc

from anyts import document as document_module
from anyts.constants import MESSAGES
from anyts.document import document_words, get_tree, to_document
from anyts.exceptions import SourceError, SourceTypeError
from anyts.extractors import split_paragraphs
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
    # The sentences may come in any order: only their starts count
    backwards = to_document("One. Two. Three.", sentenize=lambda text: semicolons(text)[::-1])
    assert sentences(backwards) == ["One. Two. Three."]
    reversed_thirds = to_document("Onetwo three", sentenize=lambda text: thirds(text)[::-1])
    assert sentences(reversed_thirds) == ["Onetwo", "three"]


def test_hooks_are_checked():
    with pytest.raises(SourceTypeError, match="tokenizer"):
        to_document(TEXT, tokenize=5)
    with pytest.raises(SourceTypeError, match="sentence splitter"):
        to_document(TEXT, sentenize="split")
    with pytest.raises(SourceTypeError, match="triples"):
        to_document(TEXT, tokenize=lambda text: [(0, 3)])
    with pytest.raises(SourceTypeError, match="ascending integer bounds"):
        to_document(TEXT, tokenize=lambda text: [(4, 7, "cat"), (0, 3, "The")])
    with pytest.raises(SourceTypeError, match="must give integer bounds inside"):
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
    partial = spacy.blank("en")("One. Two!\n\nThree")
    partial[-1].is_sent_start = True
    assert partial.has_annotation("SENT_START")
    assert sentences(to_document(partial)) == ["One.", "Two!", "Three"]


def test_doc_converted_once():
    """The last Doc converted keeps its document while its tokens and annotations stay"""
    nlp = spacy.blank("en")
    doc = nlp("One. Two!")
    document = to_document(doc)
    assert to_document(doc) is document
    # Another sentenize, a new annotation and a Doc between them convert it again
    assert to_document(doc, sentenize=semicolons) is not document
    assert to_document(doc, sentenize=semicolons) is to_document(doc, sentenize=semicolons)
    document = to_document(doc)
    doc[0].lemma_ = "one"
    changed = to_document(doc)
    assert changed is not document and changed.column("lemma")[0] == "one"
    to_document(nlp("Three"))
    assert to_document(doc) is not changed
    # A hook of the sentences is an annotation too
    document = to_document(doc)
    doc.user_hooks["sents"] = lambda whole: [whole[:]]
    assert to_document(doc) is not document
    assert [sentence.text for sentence in to_document(doc).sentences] == ["One. Two!"]
    # A Doc with its sentences takes no sentenize
    parsed = Doc(nlp.vocab, words=["Cats", "sleep"], heads=[1, 1], deps=["nsubj", "ROOT"])
    assert to_document(parsed, sentenize=semicolons) is to_document(parsed)
    # The words of a multiword token of anySeg are part of the annotations
    doc = nlp("Vino del pueblo")
    plain = to_document(doc)
    doc[1]._.anyseg_words = [{"form": "de", "upos": "ADP"}, {"form": "el", "upos": "DET"}]
    assert [word.form for word in to_document(doc).words] == ["Vino", "de", "el", "pueblo"]
    assert len(plain.words) == 3
    doc.user_data[("._.", "anyseg_words", None, None)] = "a value of the whole Doc"
    assert len(to_document(doc).words) == 4
    # Docs of one text are other Docs, and a Doc that is gone takes its document with it
    first, second = nlp("Four"), nlp("Four")
    assert to_document(first) is not to_document(second)
    del first, second
    gc.collect()
    assert document_module._last_converted == []


def test_sentences_of_a_hook():
    """A Doc without a parse whose sentences come from a hook keeps them, each paragraph too"""
    doc = spacy.blank("en")("One two three. Four five six. Seven eight\n\nNine")

    def by_period(whole):
        start = 0
        for token in whole:
            if token.text == "." or token.text.startswith("\n"):
                yield whole[start : token.i + 1]
                start = token.i + 1
        yield whole[start:]

    doc.user_hooks["sents"] = by_period
    assert sentences(to_document(doc)) == [
        "One two three.",
        "Four five six.",
        "Seven eight",
        "Nine",
    ]
    # Another hook is another document
    doc.user_hooks["sents"] = lambda whole: [whole[:]]
    assert sentences(to_document(doc)) == ["One two three. Four five six. Seven eight", "Nine"]


def test_multiword_tokens_without_columns_of_their_words():
    """A multiword token whose words have no columns of their own is one word, with the columns
    and the head the pipeline gave the token; words with their columns stay words"""
    vocab = spacy.blank("es").vocab
    doc = Doc(
        vocab,
        words=["Vino", "del", "pueblo", "."],
        heads=[0, 2, 0, 0],
        deps=["ROOT", "case", "obl", "punct"],
        pos=["VERB", "ADP", "NOUN", "PUNCT"],
        lemmas=["venir", "del", "pueblo", "."],
    )
    import anyseg.spacy  # noqa: F401 - the extension token._.anyseg_words

    doc[1]._.anyseg_words = [{"form": "de"}, {"form": "el"}]
    words = get_tree(to_document(doc)).words
    assert [(word.form, word.lemma, word.upos, word.deprel) for word in words] == [
        ("Vino", "venir", "VERB", "root"),
        ("del", "del", "ADP", "case"),
        ("pueblo", "pueblo", "NOUN", "obl"),
        (".", ".", "PUNCT", "punct"),
    ]
    assert [word.head.form if word.head else None for word in words] == [
        None,
        "pueblo",
        "Vino",
        "Vino",
    ]
    doc[1]._.anyseg_words = ({"form": "de"}, {"form": "el"})
    assert [word.form for word in to_document(doc).words] == ["Vino", "del", "pueblo", "."]
    doc[1]._.anyseg_words = [{"form": "de", "upos": "ADP"}, {"form": "el", "upos": "DET"}]
    assert [word.upos for word in to_document(doc).words] == [
        "VERB",
        "ADP",
        "DET",
        "NOUN",
        "PUNCT",
    ]


def test_multiword_tokens_merged_in_one_pass(monkeypatch):
    """The merge of multiword tokens reads every column of the document once"""
    from anyseg.spacy import from_doc

    vocab = spacy.blank("es").vocab
    doc = Doc(vocab, words=["al", "del"] * 3, heads=[0] * 6, deps=["ROOT"] * 6)
    import anyseg.spacy  # noqa: F401 - the extension token._.anyseg_words

    for token in doc:
        token._.anyseg_words = [{"form": "a"}, {"form": "el"}]
    document = from_doc(doc)
    names = []
    column = Document.column

    def counted(self, name):
        names.append(name)
        return column(self, name)

    monkeypatch.setattr(Document, "column", counted)
    merged = document_module._merged(document, {token.index for token in document.tokens})
    assert len(names) == len(set(names))
    monkeypatch.undo()
    assert [word.form for word in merged.words] == ["al", "del"] * 3


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
    # Without columns of their own the words of del are the token, as the pipeline sees it
    assert [word.form for word in document.words][:3] == ["Vino", "del", "pueblo"]
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


def test_blank_lines():
    """A blank line ends a paragraph of the document, as BLANK_LINE and split_paragraphs have it"""
    text = "The page ends in the middle of a\n\x0csentence that goes on."
    assert sentences(to_document(text)) == [
        "The page ends in the middle of a",
        "sentence that goes on.",
    ]
    nlp = spacy.blank("en")
    nlp.add_pipe("sentencizer")
    document = to_document(nlp("Title of the text\n\nThe body goes on. It ends."))
    assert sentences(document) == ["Title of the text", "The body goes on.", "It ends."]
    generator = random.Random(0)
    alphabet = (
        "ab .\n\r\x0b\x0c\x85\u2028\u2029\u00ad\u2060\u200b\u200c\u200d\ufeff\t \x01\x7f\xa0"
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
    doc = spacy.blank("en")("Mr. John\n\nSmith came home.")
    with doc.retokenize() as retokenizer:
        retokenizer.merge(doc[1:4])
    with pytest.raises(
        SourceError, match="cannot make a document: token 1: runs over a paragraph"
    ):
        to_document(doc)
    own = {**MESSAGES, "document_tokens": "Own {error}"}
    with pytest.raises(SourceError, match=r"^Own token 1"):
        to_document(doc, messages=own)
    text = "One two. Three four.\n\nFive six."
    with pytest.raises(SourceTypeError, match="tokens a document can hold: token 4: runs over"):
        to_document(text, tokenize=lambda t: [(14, 24, t[14:24])])


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
    with pytest.raises(SourceTypeError, match="cannot be of type str"):
        get_tree("Vino del pueblo")
