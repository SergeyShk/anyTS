from __future__ import annotations

import re
import unicodedata
from bisect import bisect_left
from collections.abc import Callable, Iterable, Iterator, Mapping
from functools import cache
from re import Pattern
from typing import TYPE_CHECKING

from .constants import MESSAGES
from .exceptions import SourceTypeError
from .extractors import SentsExtractor, _check_spans, _iter_part_sents, _word_pattern
from .utils import (
    check_callable,
    has_sents,
    is_doc,
    is_document,
    is_punctuation,
    source_type_error,
)

if TYPE_CHECKING:
    from anyseg import Document
    from spacy.tokens import Doc

Spans = Callable[[str], Iterable[tuple[int, int, str]]]

# What separates the tokens of a document and is in none of them, as in anySeg
_INVISIBLE_SEPARATORS = "­​‌‍⁠﻿"


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
        relation) and its sentences (anyseg.spacy.from_doc); a Doc with no or
        only partial sentence starts (has_sents) and no parse gets those of
        sentenize on its text. A string is split into tokens by tokenize and
        into sentences by sentenize. Every part between blank lines goes to
        sentenize apart, and a sentence starts at its first token. Whitespace
        and invisible separators (the soft hyphen, zero-width characters, the
        byte order mark) at the edges of a token are left out, and a token of
        nothing else is dropped
        The default tokens are the words of WordsExtractor and every run of a
        punctuation mark (is_punctuation); the default sentences are those of
        SentsExtractor

    Arguments:
        source (str|Doc|Document): Data source
        tokenize (Callable[[str], Iterable[tuple[int, int, str]]]): Tokens of a
            string with their positions
        sentenize (Callable[[str], Iterable[tuple[int, int, str]]]): Sentences of a
            string with their positions
        messages (dict[str, str]): Messages of the errors by key (MESSAGES)

    Returns:
        Document: Document

    Raises:
        SourceTypeError: If the source is neither a string, a Doc nor a Document
            object, tokenize or sentenize is not callable, or either does not give
            ascending triples of integer bounds inside the text and a string

    Example:
        >>> from anyts.document import to_document
        >>> document = to_document("The cat sat. It slept!\\n\\nThe end")
        >>> [token.text for token in document.tokens][:4]
        ['The', 'cat', 'sat', '.']
        >>> [sentence.text for sentence in document.sentences]
        ['The cat sat.', 'It slept!', 'The end']
    """
    for hook, what in ((tokenize, "tokenizer"), (sentenize, "sentence splitter")):
        if hook is not None:
            check_callable(hook, what)
    if is_document(source):
        return source
    if is_doc(source):
        return _doc_document(source, sentenize or _iter_sents)
    if isinstance(source, str):
        return _text_document(source, tokenize or _iter_tokens, sentenize or _iter_sents)
    raise source_type_error(messages, source)


def document_words(document: Document) -> tuple[str, ...]:
    """
    Getting the words of a document

    Description:
        The tokens that are no punctuation marks (is_punctuation), as written:
        a multiword token is one word

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
        if not is_punctuation(word)
    )


def _source_text(source: str | Doc | Document, messages: Mapping[str, str]) -> str:
    """Text of a string, a Doc or a Document object"""
    if isinstance(source, str):
        return source
    if is_doc(source) or is_document(source):
        return source.text
    raise source_type_error(messages, source)


def _doc_document(doc: Doc, sentenize: Spans) -> Document:
    """Document of a Doc; one with neither sentences nor a parse gets those of sentenize"""
    from anyseg import Document
    from anyseg.spacy import from_doc

    document = from_doc(doc)
    if has_sents(doc) or doc.has_annotation("DEP"):
        return document
    tokens = document.tokens
    starts = _sent_starts(document.text, tokens.starts, sentenize)
    words = {
        token.index: [word.form for word in token.words] for token in document.multiword_tokens
    }
    rebuilt = Document.from_tokens(
        document.text, tokens.starts, tokens.ends, sentence_starts=starts, words=words or None
    )
    column = document.column
    rebuilt.set_columns(
        lemma=column("lemma"),
        upos=column("upos"),
        xpos=column("xpos"),
        feats=column("feats"),
        misc=column("misc"),
    )
    return rebuilt


def _text_document(text: str, tokenize: Spans, sentenize: Spans) -> Document:
    """Document of a string by its tokens, the default ones filling the gaps between them"""
    from anyseg import Document

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
    for start, end, _ in (*_check_spans(tokenize(text), text, "tokenizer"), (len(text), 0, "")):
        for gap in _token_pattern().finditer(text, position, start):
            add(*gap.span())
        if end:
            add(start, end)
            position = end
    return Document.from_tokens(
        text, starts, ends, sentence_starts=_sent_starts(text, starts, sentenize)
    )


def _sent_starts(text: str, starts: list[int], sentenize: Spans) -> list[int]:
    """Indices of the first tokens of the sentences of every part of a text between blank lines"""
    first: list[int] = []
    for start, end, _ in _iter_part_sents(sentenize, text):
        index = bisect_left(starts, start)
        if index < len(starts) and starts[index] < end and (not first or index > first[-1]):
            first.append(index)
    return first


def _iter_tokens(text: str) -> Iterator[tuple[int, int, str]]:
    """Tokens of the default tokenizer of to_document: words and runs of one other character"""
    return (
        (match.start(), match.end(), match.group()) for match in _token_pattern().finditer(text)
    )


def _iter_sents(text: str) -> Iterator[tuple[int, int, str]]:
    """Sentences of the default rule of SentsExtractor with their positions"""
    position = 0
    for sent in SentsExtractor().sentenize(text):
        stripped = sent.strip()
        if stripped:
            start = text.index(stripped, position)
            position = start + len(stripped)
            yield start, position, stripped


@cache
def _token_pattern() -> Pattern[str]:
    """Pattern of a token of the default tokenizer: a word, or a run of one other character"""
    separators = re.escape(_separators())
    return re.compile(rf"{_word_pattern().pattern}|([^\w{separators}])\1*")


@cache
def _separators() -> str:
    """Characters that separate tokens: whitespace, control characters and invisible separators"""
    return (
        "".join(
            char
            for char in map(chr, range(0x3001))
            if char.isspace() or unicodedata.category(char) == "Cc"
        )
        + _INVISIBLE_SEPARATORS
    )
