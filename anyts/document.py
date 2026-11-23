from __future__ import annotations

import re
import threading
import weakref
from bisect import bisect_left, bisect_right
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from functools import cache, partial
from re import Pattern
from typing import TYPE_CHECKING, Any, NamedTuple, cast

from .constants import MESSAGES
from .exceptions import ParameterError, SourceError, SourceTypeError
from .extractors import _check_spans, _sentence_spans, _word_pattern
from .utils import (
    _IN_WORD_MARKS,
    BLANK_LINE,
    LINE_BREAK,
    _messages,
    _separators,
    check_callable,
    check_integer,
    has_words,
    is_doc,
    is_document,
    source_type_error,
)

if TYPE_CHECKING:
    from anyseg import Document
    from spacy.tokens import Doc

Spans = Callable[[str], Iterable[tuple[int, int, str]]]

# Columns of the words a part of a document keeps
_PART_COLUMNS = ("lemma", "upos", "xpos", "feats", "head", "deprel", "deps", "misc")
# The separators a word of the default tokens may end with
_WORD_SEPARATORS = "\u00ad\u200c\u200d" + _IN_WORD_MARKS


class _Converted:
    """The last Doc a thread converted, the stamp of its annotations, the sentenize of the
    conversion (None for a Doc with its sentences), its document and the tree of the document,
    once one is asked"""

    __slots__ = ("doc", "document", "sentenize", "stamp", "tree")

    def __init__(
        self,
        doc: weakref.ref[Doc],
        stamp: tuple[bytes, str, tuple[int, ...] | None],
        sentenize: Spans | None,
        document: Document,
    ):
        self.doc = doc
        self.stamp = stamp
        self.sentenize = sentenize
        self.document = document
        self.tree: Tree | None = None


class _Slot(list[_Converted]):
    """Slot of the last conversion of a thread, which the weak reference of its Doc finds"""

    __slots__ = ("__weakref__",)


class _Shared:
    """The document the classes of a command or a report count and its tree, once one is asked"""

    __slots__ = ("document", "tree")

    def __init__(self, document: Document):
        self.document = document
        self.tree: Tree | None = None


# The slot of the last conversion of every thread
_local = threading.local()


def to_document(
    source: str | Doc | Document,
    tokenize: Spans | None = None,
    sentenize: Spans | None = None,
    *,
    messages: Mapping[str, str] = MESSAGES,
) -> Document:
    """
    Getting the document of a data source in the model of anySeg

    Description:
        A Document of anySeg is returned as it is. A Doc of spaCy keeps its
        tokens, their columns (lemma, part of speech, features, head and
        relation) and its sentences (anyseg.spacy.from_doc), those of a hook
        (user_hooks["sents"]) of a Doc without a parse too; a multiword token
        of anySeg whose words have no columns of their own is one word with the
        columns and the head of the token, as the pipeline annotated it. A Doc
        with no or only partial sentence starts (a token whose is_sent_start is
        unset), as before the parser, senter or sentencizer, and without a parse
        or a hook gets those of sentenize on its text. A string is split into
        tokens by tokenize and into sentences by sentenize, and the default
        tokens fill the gaps between those of tokenize. A blank line
        (BLANK_LINE) ends a paragraph of the document and so a sentence, of a
        Doc too: every part between blank lines goes to sentenize apart, and a
        sentence starts at its first token. Whitespace and invisible separators
        (the soft hyphen, zero-width characters, the byte order mark) at the
        edges of a token are left out, and a token of nothing else is dropped.
        The default tokens are the words of WordsExtractor and every run of one
        other character; the default sentences are those of SentsExtractor.
        The document of the Doc a thread converted last is kept while the Doc
        lives with the same tokens and annotations, and the same sentenize for
        a Doc without its sentences, so the classes of statistics of one Doc
        convert it once: the same Document comes back, and it is not to be changed

    Arguments:
        source (str|Doc|Document): Data source
        tokenize (Callable[[str], Iterable[tuple[int, int, str]]]): Tokens of a
            string with their positions
        sentenize (Callable[[str], Iterable[tuple[int, int, str]]]): Sentences of a
            string with their positions, in any order
        messages (dict[str, str]): Messages of the errors by key (MESSAGES)

    Returns:
        Document: Document

    Raises:
        SourceTypeError: If the source is neither a string, a Doc nor a Document
            object, tokenize or sentenize is not callable, either does not give
            triples of integer bounds inside the text and a string, those of
            tokenize ascending, or a token of tokenize runs over a blank line
        SourceError: If a token of the Doc runs over a blank line or its words in
            token._.anyseg_words cannot be in a document

    Example:
        >>> from anyts.document import to_document
        >>> document = to_document("The cat sat. It slept!\\n\\nThe end")
        >>> [token.text for token in document.tokens][:4]
        ['The', 'cat', 'sat', '.']
        >>> [sentence.text for sentence in document.sentences]
        ['The cat sat.', 'It slept!', 'The end']
    """
    messages = _messages(messages)
    for hook, what in ((tokenize, "tokenize"), (sentenize, "sentenize")):
        if hook is not None:
            check_callable(hook, what, message=messages["callable_param"])
    if is_document(source):
        return source
    if is_doc(source):
        return _cached_document(source, sentenize, messages)
    if isinstance(source, str):
        return _text_document(source, tokenize, sentenize, messages)
    raise source_type_error(messages, source)


def document_words(document: Document) -> tuple[str, ...]:
    """
    Getting the words of a document

    Description:
        The tokens with a letter or a digit (has_words), as written: no
        punctuation mark, symbol or character of no class, such as the bullet
        of private use in a text from a PDF, is a word. A multiword token is one
        word

    Arguments:
        document (Document): Document of anySeg

    Returns:
        tuple[str]: Words

    Raises:
        SourceTypeError: If the document is not a Document object

    Example:
        >>> from anyts.document import document_words, to_document
        >>> document_words(to_document("Well, the cat sat - 100%!"))
        ('Well', 'the', 'cat', 'sat', '100')
    """
    if not is_document(document):
        raise SourceTypeError(MESSAGES["source_type"].format(type=type(document).__name__))
    text = document.text
    tokens = document.tokens
    return tuple(
        word
        for word in (
            text[start:end] for start, end in zip(tokens.starts, tokens.ends, strict=True)
        )
        if has_words(word)
    )


def document_part(
    document: Document, start: int, end: int, *, messages: Mapping[str, str] | None = None
) -> Document:
    """
    Getting the document of a part of a document

    Description:
        The part is made of the sentences the span of the text from start to
        end overlaps, whole, so that their trees stay whole: a sentence, a
        paragraph or a fragment of several of them. Its text runs from the first
        token of the first sentence to the last token of the last one, and the
        positions count from there; the tokens, the words with their columns,
        the sentences and the paragraphs are those of the document, and a head
        stays as it is, since the head of a word is in its own sentence

    Arguments:
        document (Document): Document of anySeg
        start (int): Position of the first character of the span in the text
        end (int): Position after its last character
        messages (dict[str, str]): Messages of the errors by key, in place of those of
            the library

    Returns:
        Document: Document of the part

    Raises:
        SourceTypeError: If the document is not a Document object
        ParameterError: If start or end is not an integer, or the span is not within
            the text with start before end
        SourceError: If the span overlaps no sentence, as one of whitespace between two

    Example:
        >>> from anyts.document import document_part, to_document
        >>> document = to_document("The cat sleeps. The dog barks.")
        >>> document_part(document, 20, 21).text
        'The dog barks.'
    """
    messages = _messages(messages)
    if not is_document(document):
        raise source_type_error(messages, document)
    for value, what in ((start, "start"), (end, "end")):
        check_integer(value, what, message=messages["integer_param"])
    size = len(document.text)
    if not 0 <= start < end <= size:
        raise ParameterError(messages["part_bounds"].format(size=size, start=start, end=end))
    reader = _PartReader(document)
    sentences = reader.sentences_in(start, end)
    if not sentences:
        raise SourceError(messages["no_words"])
    return reader.part(sentences[0], sentences[-1])


def _document_parts(document: Document, kind: str) -> Iterator[tuple[int, int, Document]]:
    """Positions of every sentence, line or paragraph of a document in its text, with its document
    (document_part), the columns read once"""
    reader = _PartReader(document)
    for first, last in reader.ranges(kind):
        yield *reader.bounds(first, last), reader.part(first, last)


class _PartReader:
    """The tokens, the words and the columns of a document read once, to make documents of its
    parts"""

    __slots__ = (
        "columns",
        "document",
        "ends",
        "first_tokens",
        "first_words",
        "forms",
        "multiword",
        "starts",
    )

    def __init__(self, document: Document) -> None:
        self.document = document
        tokens = document.tokens
        self.starts = list(tokens.starts)
        self.ends = list(tokens.ends)
        self.first_tokens = [bisect_left(self.starts, s) for s in document.sentences.starts]
        self.first_tokens.append(len(self.starts))
        sizes = [1] * len(self.starts)
        self.forms: dict[int, list[str]] = {}
        for token in document.multiword_tokens:
            self.forms[token.index] = [word.form for word in token.words]
            sizes[token.index] = len(token.words)
        # The indices of the multiword tokens in order, to find those of a part
        self.multiword = sorted(self.forms)
        self.first_words = [0]
        for size in sizes:
            self.first_words.append(self.first_words[-1] + size)
        self.columns = {name: document.column(name) for name in _PART_COLUMNS}

    def sentences_in(self, start: int, end: int) -> list[int]:
        """Indices of the sentences whose tokens the span overlaps"""
        found = []
        for index in range(len(self.first_tokens) - 1):
            first, last = self.first_tokens[index], self.first_tokens[index + 1] - 1
            if first <= last and self.starts[first] < end and self.ends[last] > start:
                found.append(index)
        return found

    def ranges(self, kind: str) -> list[tuple[int, int]]:
        """First and last sentences of every sentence, line or paragraph"""
        count = len(self.first_tokens) - 1
        if kind == "sentences":
            return [(index, index) for index in range(count)]
        if kind == "lines" and count:
            # A line ends before a sentence with a line break between it and the one before
            text = self.document.text
            firsts = [
                index
                for index in range(1, count)
                if LINE_BREAK.search(
                    text,
                    self.ends[self.first_tokens[index] - 1],
                    self.starts[self.first_tokens[index]],
                )
            ]
            return list(
                zip([0, *firsts], [*(first - 1 for first in firsts), count - 1], strict=True)
            )
        ranges = []
        for paragraph in self.document.paragraphs:
            indices = [sentence.index for sentence in paragraph.sentences]
            ranges.append((indices[0], indices[-1]))
        return ranges

    def bounds(self, first: int, last: int) -> tuple[int, int]:
        """Start of the first token of the first sentence and end of the last token of the last"""
        return self.starts[self.first_tokens[first]], self.ends[self.first_tokens[last + 1] - 1]

    def part(self, first: int, last: int) -> Document:
        """Document of the sentences from first to last"""
        from anyseg import Document

        token_first, token_end = self.first_tokens[first], self.first_tokens[last + 1]
        offset, end = self.bounds(first, last)
        part = Document.from_tokens(
            self.document.text[offset:end],
            [position - offset for position in self.starts[token_first:token_end]],
            [position - offset for position in self.ends[token_first:token_end]],
            sentence_starts=[
                self.first_tokens[index] - token_first for index in range(first, last + 1)
            ],
            words={
                index - token_first: self.forms[index]
                for index in self.multiword[
                    bisect_left(self.multiword, token_first) : bisect_left(
                        self.multiword, token_end
                    )
                ]
            }
            or None,
        )
        word_first, word_end = self.first_words[token_first], self.first_words[token_end]
        values = {name: column[word_first:word_end] for name, column in self.columns.items()}
        kept = {name: value for name, value in values.items() if any(v is not None for v in value)}
        part.set_columns(**cast(dict[str, Any], kept))
        return part


class TreeWord:
    """
    Word of the dependency tree of a document

    Description:
        A word of Universal Dependencies of a document with its columns and its
        place in the tree: the word it hangs on, None at the head of a sentence,
        and the words hanging on it in the order of the text. The words of a
        multiword token share its positions. Made by get_tree

    Attributes:
        index (int): Position among the words of the document
        form (str): Form of the word
        lemma (str|None): Lemma
        upos (str|None): Part of speech of Universal Dependencies
        xpos (str|None): Tag of the language
        feats (Mapping[str, str]): Features of Universal Dependencies by name, the
            values of a feature of several joined by commas (Int,Rel); the words of
            one set of features share one mapping
        deprel (str|None): Relation to the head
        head (TreeWord|None): Word it hangs on, None at the head of a sentence
        children (tuple[TreeWord]): Words hanging on it
        sentence (int): Position of its sentence among the sentences of the document
        start (int): Position of the first character of its token
        end (int): Position after the last character of its token
        tree (Tree): Tree of the document
    """

    __slots__ = (
        "children",
        "deprel",
        "end",
        "feats",
        "form",
        "head",
        "index",
        "lemma",
        "sentence",
        "start",
        "tree",
        "upos",
        "xpos",
    )

    index: int
    form: str
    lemma: str | None
    upos: str | None
    xpos: str | None
    feats: Mapping[str, str]
    deprel: str | None
    head: TreeWord | None
    children: tuple[TreeWord, ...]
    sentence: int
    start: int
    end: int
    tree: Tree

    def __repr__(self) -> str:
        return f"TreeWord({self.index}, {self.form!r}, {self.upos}, {self.deprel})"

    def __reduce__(self) -> tuple[Any, ...]:
        # A word is its tree and its position, so that pickle and copy follow no chain of links
        return _tree_word, (self.tree, self.index)


class Tree(NamedTuple):
    """
    Dependency tree of a document

    Attributes:
        text (str): Text of the document
        words (tuple[TreeWord]): Words of the document, punctuation marks included
        sentences (tuple[tuple[TreeWord]]): Words of every sentence

    Methods:
        word_at: Word at a position of the text
    """

    text: str
    words: tuple[TreeWord, ...]
    sentences: tuple[tuple[TreeWord, ...], ...]

    def word_at(self, position: int, end: int | None = None) -> TreeWord | None:
        """
        Getting the word at a position or a span of the text

        Description:
            The word whose token covers the position, or with end the first one
            whose token overlaps the span from the position to end; the first
            word of a multiword token, or None where no word stands, as at
            whitespace. The word of a token of spaCy is
            word_at(token.idx, token.idx + len(token)), since its position among
            the words differs from token.i where a Doc has tokens of whitespace,
            and the token of the document leaves out the separators at the edges
            of the token, such as a byte order mark

        Arguments:
            position (int): Position of a character of the text
            end (int): Position after the span; the character at the position alone
                by default

        Returns:
            TreeWord|None: Word at the position or of the span
        """
        limit = position + 1 if end is None else max(end, position + 1)
        index = bisect_right(self.words, position, key=lambda word: word.end)
        if index < len(self.words) and self.words[index].start < limit:
            return self.words[index]
        return None

    def __reduce__(self) -> tuple[Any, ...]:
        # The columns and the positions of the heads, linked again on loading
        rows = [
            (
                word.form,
                word.lemma,
                word.upos,
                word.xpos,
                word.feats,
                word.deprel,
                word.head.index if word.head is not None else None,
                word.sentence,
                word.start,
                word.end,
            )
            for word in self.words
        ]
        return _restore_tree, (self.text, rows)


def get_tree(document: Document) -> Tree:
    """
    Getting the dependency tree of a document

    Description:
        The words of Universal Dependencies of the document with the columns
        lemma, upos, xpos, feats, head and deprel, linked by their heads within
        their sentences: a word without a head (0 or None) heads its sentence.
        The tree of the document of the Doc a thread converted last
        (to_document), and of the document the command and the report count, is
        built once and shared by the classes, and it is not to be changed; a tree
        holds cycles of references, which the garbage collector of Python frees

    Arguments:
        document (Document): Document of anySeg

    Returns:
        Tree: Tree of the document

    Raises:
        SourceTypeError: If the document is not a Document object

    Example:
        >>> import spacy
        >>> from spacy.tokens import Doc
        >>> from anyts.document import get_tree, to_document
        >>> doc = Doc(
        ...     spacy.blank("en").vocab,
        ...     words=["Cats", "sleep"],
        ...     heads=[1, 1],
        ...     deps=["nsubj", "ROOT"],
        ...     pos=["NOUN", "VERB"],
        ... )
        >>> cats, sleep = get_tree(to_document(doc)).words
        >>> cats.head is sleep, sleep.head, sleep.children
        (True, None, (TreeWord(0, 'Cats', NOUN, nsubj),))
    """
    if not is_document(document):
        raise SourceTypeError(MESSAGES["source_type"].format(type=type(document).__name__))
    shared: _Shared | None = getattr(_local, "shared", None)
    if shared is not None and shared.document is document and shared.tree is not None:
        return shared.tree
    converted = next((item for item in _slot() if item.document is document), None)
    if converted is not None and converted.tree is not None:
        tree = converted.tree
    else:
        tree = _built_tree(document)
        if converted is not None:
            converted.tree = tree
    if shared is not None and shared.document is document:
        shared.tree = tree
    return tree


def _built_tree(document: Document) -> Tree:
    """Tree of a document, built anew"""
    column = document.column
    tokens = document.tokens
    sizes = {token.index: len(token.words) for token in document.multiword_tokens}
    starts: list[int] = []
    ends: list[int] = []
    for index, (start, end) in enumerate(zip(tokens.starts, tokens.ends, strict=True)):
        size = sizes.get(index, 1)
        starts.extend([start] * size)
        ends.extend([end] * size)
    sentence_starts = document.sentences.starts
    features: dict[str | None, Mapping[str, str]] = {}
    words: list[TreeWord] = []
    firsts: list[int] = []
    rows = zip(
        column("form"),
        column("lemma"),
        column("upos"),
        column("xpos"),
        column("feats"),
        column("deprel"),
        starts,
        ends,
        strict=True,
    )
    for index, (form, lemma, upos, xpos, feats, deprel, start, end) in enumerate(rows):
        word = TreeWord()
        word.index = index
        word.form = form
        word.lemma = lemma
        word.upos = upos
        word.xpos = xpos
        if (found := features.get(feats)) is None:
            found = features[feats] = _feature_dict(feats)
        word.feats = found
        word.deprel = deprel
        word.start = start
        word.end = end
        word.sentence = bisect_right(sentence_starts, start) - 1
        if word.sentence == len(firsts):
            firsts.append(index)
        words.append(word)
    heads = [
        firsts[word.sentence] + head - 1 if head else None
        for word, head in zip(words, column("head"), strict=True)
    ]
    return _linked_tree(document.text, words, heads, len(firsts))


def _linked_tree(
    text: str, words: list[TreeWord], heads: Sequence[int | None], n_sentences: int
) -> Tree:
    """Tree of words with their columns, linked by the positions of their heads"""
    children: list[list[TreeWord]] = [[] for _ in words]
    for word, head in zip(words, heads, strict=True):
        word.head = words[head] if head is not None else None
        if head is not None:
            children[head].append(word)
    sentences: list[list[TreeWord]] = [[] for _ in range(n_sentences)]
    for word in words:
        word.children = tuple(children[word.index])
        sentences[word.sentence].append(word)
    tree = Tree(text, tuple(words), tuple(map(tuple, sentences)))
    for word in words:
        word.tree = tree
    return tree


def _restore_tree(text: str, rows: Sequence[tuple[Any, ...]]) -> Tree:
    """Tree of the columns Tree.__reduce__ gives"""
    words = []
    heads = []
    for index, (form, lemma, upos, xpos, feats, deprel, head, sentence, start, end) in enumerate(
        rows
    ):
        word = TreeWord()
        word.index = index
        word.form = form
        word.lemma = lemma
        word.upos = upos
        word.xpos = xpos
        word.feats = feats
        word.deprel = deprel
        word.sentence = sentence
        word.start = start
        word.end = end
        words.append(word)
        heads.append(head)
    return _linked_tree(text, words, heads, words[-1].sentence + 1 if words else 0)


def _tree_word(tree: Tree, index: int) -> TreeWord:
    """Word of a tree by its position, for TreeWord.__reduce__"""
    return tree.words[index]


def _feature_dict(feats: str | None) -> dict[str, str]:
    """Features of a word in the CoNLL-U format as a dictionary, a part without a value left out"""
    return dict(pair.split("=", 1) for pair in feats.split("|") if "=" in pair) if feats else {}


@contextmanager
def _tree_once(document: Document) -> Iterator[Tree]:
    """Tree of a document (get_tree) for one use: a tree no slot keeps is broken after it, so that
    it goes at once rather than with the garbage collector"""
    tree = get_tree(document)
    try:
        yield tree
    finally:
        if not _kept(tree):
            _break(tree)


@contextmanager
def _sharing_tree(document: Document) -> Iterator[None]:
    """The tree of a document built once for the classes that count it inside, and broken after
    them as _tree_once breaks it"""
    previous: _Shared | None = getattr(_local, "shared", None)
    shared = _local.shared = _Shared(document)
    try:
        yield
    finally:
        _local.shared = previous
        if shared.tree is not None and not any(
            converted.tree is shared.tree for converted in _slot()
        ):
            _break(shared.tree)


def _kept(tree: Tree) -> bool:
    """Whether a slot or the shared document keeps a tree"""
    shared: _Shared | None = getattr(_local, "shared", None)
    return (shared is not None and shared.tree is tree) or any(
        converted.tree is tree for converted in _slot()
    )


def _break(tree: Tree) -> None:
    """Breaking the cycles of the references of a tree, so that it goes at once rather than with
    the garbage collector"""
    for word in tree.words:
        word.head = None
        word.children = ()
        del word.tree


def _parsed(owner: Any, source: str | Doc | Document) -> Document:
    """Document of the parse hook of an object, checked to be a Document"""
    document = owner.parse(source)
    if not is_document(document):
        raise SourceTypeError(
            owner.messages["hook_document"].format(
                hook="parse", cls=type(owner).__name__, type=type(document).__name__
            )
        )
    return document


def _source_text(source: str | Doc | Document, messages: Mapping[str, str]) -> str:
    """Text of a string, a Doc or a Document object"""
    if isinstance(source, str):
        return source
    if is_doc(source) or is_document(source):
        return source.text
    raise source_type_error(messages, source)


def _cached_document(doc: Doc, sentenize: Spans | None, messages: Mapping[str, str]) -> Document:
    """Document of a Doc, the one of the last conversion while the Doc and its annotations are
    the same"""
    stamp = _doc_stamp(doc)
    if _has_sentences(doc):
        sentenize = None
    slot = _slot()
    for converted in slot:
        if (
            converted.doc() is doc
            and converted.stamp == stamp
            and converted.sentenize == sentenize
        ):
            return converted.document
    document = _doc_document(doc, sentenize, messages)
    # The slot is found by a weak reference too, so that a thread that ends frees it at once
    forget = partial(_forget, weakref.ref(slot))
    slot[:] = [_Converted(weakref.ref(doc, forget), stamp, sentenize, document)]
    return document


def _slot() -> _Slot:
    """The slot of the last conversion of the calling thread"""
    slot: _Slot | None = getattr(_local, "converted", None)
    if slot is None:
        slot = _local.converted = _Slot()
    return slot


def _forget(slot_ref: weakref.ref[_Slot], ref: weakref.ref[Doc]) -> None:
    """Dropping the document and the tree of a Doc that is gone from its slot, unless the slot is
    gone too: its thread may end while the callbacks of the Doc run"""
    if (slot := slot_ref()) is not None:
        slot[:] = [converted for converted in slot if converted.doc is not ref]


def _doc_stamp(doc: Doc) -> tuple[bytes, str, tuple[int, ...] | None]:
    """The tokens of a Doc and the annotations its document reads: the columns, the sentence
    starts, the words of the multiword tokens of anySeg and the starts of the sentences of a
    hook"""
    from anyseg.spacy import given_words
    from spacy.attrs import DEP, HEAD, LEMMA, MORPH, ORTH, POS, SENT_START, SPACY, TAG

    columns = doc.to_array([ORTH, SPACY, LEMMA, POS, TAG, MORPH, HEAD, DEP, SENT_START])
    hooked = tuple(span.start_char for span in doc.sents) if "sents" in doc.user_hooks else None
    return columns.tobytes(), repr(list(given_words(doc).items())), hooked


def _doc_document(doc: Doc, sentenize: Spans | None, messages: Mapping[str, str]) -> Document:
    """Document of a Doc: a multiword token whose words have no columns of their own is one word,
    as the pipeline annotated it, and a Doc without its sentences takes those of sentenize"""
    from anyseg.spacy import from_doc

    try:
        document = from_doc(doc, split_unannotated=False)
    except (TypeError, ValueError) as error:
        raise SourceError(messages["document_tokens"].format(error=error)) from error
    if _has_sentences(doc) or "sents" in doc.user_hooks:
        return document
    starts = _sent_starts(document.text, document.tokens.starts, sentenize, messages)
    return document.with_sentences(starts)


def _has_sentences(doc: Doc) -> bool:
    """Whether a Doc has its sentences: is_sent_start set at every token, a hook of the sentences
    or a parse"""
    return doc.has_annotation("SENT_START", require_complete=True) or doc.has_annotation("DEP")


def _text_document(
    text: str, tokenize: Spans | None, sentenize: Spans | None, messages: Mapping[str, str]
) -> Document:
    """Document of a string by its tokens, the default ones filling the gaps of tokenize"""
    from anyseg import Document

    starts, ends = (
        _token_spans(text) if tokenize is None else _hook_spans(text, tokenize, messages)
    )
    try:
        return Document.from_tokens(
            text, starts, ends, sentence_starts=_sent_starts(text, starts, sentenize, messages)
        )
    except ValueError as error:
        raise SourceTypeError(messages["document_tokens"].format(error=error)) from error


def _token_spans(text: str) -> tuple[list[int], list[int]]:
    """Bounds of the default tokens of a string"""
    spans = [match.span() for match in _token_pattern().finditer(text)]
    return [start for start, _ in spans], [end for _, end in spans]


def _hook_spans(
    text: str, tokenize: Spans, messages: Mapping[str, str]
) -> tuple[list[int], list[int]]:
    """Bounds of the tokens of tokenize without the separators at their edges, gaps filled"""
    starts: list[int] = []
    ends: list[int] = []
    separators = _separators()

    def add(start: int, end: int) -> None:
        token = text[start:end]
        stripped = token.lstrip(separators)
        if stripped:
            start += len(token) - len(stripped)
            starts.append(start)
            ends.append(start + len(stripped.rstrip(separators)))

    position = 0
    spans = _check_spans(
        tokenize(text), text, "tokenizer", error=_spans_error("tokenize", messages)
    )
    for start, end, _ in (*spans, (len(text), 0, "")):
        for gap in _token_pattern().finditer(text, position, start):
            add(*gap.span())
        if end:
            add(start, end)
            position = end
    return starts, ends


def _spans_error(hook: str, messages: Mapping[str, str]) -> Callable[[object], str]:
    """Message of a wrong value a hook of the spans gives"""
    return lambda span: messages["hook_bounds"].format(hook=hook, span=repr(span))


def _sent_starts(
    text: str, starts: list[int], sentenize: Spans | None, messages: Mapping[str, str]
) -> list[int]:
    """Indices of the first tokens of the sentences of every part of a text between blank lines"""
    first: list[int] = []
    sents = _iter_sents(text) if sentenize is None else _hook_sents(sentenize, text, messages)
    for start, end, _ in sents:
        index = bisect_left(starts, start)
        if index < len(starts) and starts[index] < end and (not first or index > first[-1]):
            first.append(index)
    return first


def _hook_sents(
    sentenize: Spans, text: str, messages: Mapping[str, str]
) -> Iterator[tuple[int, int, str]]:
    """Sentences of sentenize with their positions by start, every part between blank lines apart"""
    error = _spans_error("sentenize", messages)
    for part_start, part in _parts(text):
        for start, end, sent in sorted(
            _check_spans(sentenize(part), part, "sentence splitter", ordered=False, error=error)
        ):
            yield part_start + start, part_start + end, sent


def _iter_sents(text: str) -> Iterator[tuple[int, int, str]]:
    """Sentences of SentsExtractor with their positions, every part between blank lines apart"""
    separators = _separators()
    for part_start, part in _parts(text):
        for start, end in _sentence_spans(part):
            sent = part[start:end]
            stripped = sent.strip(separators)
            if stripped:
                first = part_start + start + len(sent) - len(sent.lstrip(separators))
                yield first, first + len(stripped), stripped


def _parts(text: str) -> Iterator[tuple[int, str]]:
    """Parts of a text between blank lines with their starts"""
    bounds = [0, *(bound for match in BLANK_LINE.finditer(text) for bound in match.span())]
    for start, end in zip(bounds[::2], [*bounds[1::2], len(text)], strict=True):
        yield start, text[start:end]


@cache
def _token_pattern() -> Pattern[str]:
    """Pattern of a default token: a word without the separators it ends with, or a run of one other character"""
    separators = re.escape(_separators())
    word = f"{_word_pattern().pattern}(?<![{_WORD_SEPARATORS}])"
    return re.compile(rf"{word}|([^\w{separators}])\1*")
