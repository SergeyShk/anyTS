from __future__ import annotations

import re
from bisect import bisect_left
from collections.abc import Callable, Iterable, Iterator, Mapping
from functools import cache
from re import Pattern
from typing import TYPE_CHECKING, Any

from .constants import MESSAGES
from .exceptions import SourceError, SourceTypeError
from .extractors import _check_spans, _sentence_spans, _word_pattern
from .utils import (
    BLANK_LINE,
    _separators,
    check_callable,
    has_sents,
    has_words,
    is_doc,
    is_document,
    source_type_error,
)

if TYPE_CHECKING:
    from anyseg import Document
    from spacy.tokens import Doc

Spans = Callable[[str], Iterable[tuple[int, int, str]]]

# The separators a word of the default tokens may end with
_WORD_SEPARATORS = "\u00ad\u200c\u200d"


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
        into sentences by sentenize, and the default tokens fill the gaps
        between those of tokenize. A blank line (BLANK_LINE) ends a paragraph
        of the document and so a sentence, of a Doc too: every part between
        blank lines goes to sentenize apart, and a sentence starts at its first
        token. Whitespace and invisible separators (the soft hyphen,
        zero-width characters, the byte order mark) at the edges of a token are
        left out, and a token of nothing else is dropped
        The default tokens are the words of WordsExtractor and every run of one
        other character; the default sentences are those of SentsExtractor

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
    for hook, what in ((tokenize, "tokenizer"), (sentenize, "sentence splitter")):
        if hook is not None:
            check_callable(hook, what)
    if is_document(source):
        return source
    if is_doc(source):
        return _doc_document(source, sentenize, messages)
    if isinstance(source, str):
        return _text_document(source, tokenize, sentenize)
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


def _doc_document(doc: Doc, sentenize: Spans | None, messages: Mapping[str, str]) -> Document:
    """Document of a Doc; one with neither sentences nor a parse gets those of sentenize"""
    from anyseg import Document
    from anyseg.spacy import from_doc

    try:
        document = from_doc(doc)
    except (TypeError, ValueError) as error:
        raise SourceError(messages["document_tokens"].format(error=error)) from error
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


def _text_document(text: str, tokenize: Spans | None, sentenize: Spans | None) -> Document:
    """Document of a string by its tokens, the default ones filling the gaps of tokenize"""
    from anyseg import Document

    starts, ends = _token_spans(text) if tokenize is None else _hook_spans(text, tokenize)
    try:
        return Document.from_tokens(
            text, starts, ends, sentence_starts=_sent_starts(text, starts, sentenize)
        )
    except ValueError as error:
        raise SourceTypeError(
            f"The tokenizer must give tokens a document can hold: {error}"
        ) from error


def _token_spans(text: str) -> tuple[list[int], list[int]]:
    """Bounds of the default tokens of a string"""
    spans = [match.span() for match in _token_pattern().finditer(text)]
    return [start for start, _ in spans], [end for _, end in spans]


def _hook_spans(text: str, tokenize: Spans) -> tuple[list[int], list[int]]:
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
    for start, end, _ in (*_check_spans(tokenize(text), text, "tokenizer"), (len(text), 0, "")):
        for gap in _token_pattern().finditer(text, position, start):
            add(*gap.span())
        if end:
            add(start, end)
            position = end
    return starts, ends


def _sent_starts(text: str, starts: list[int], sentenize: Spans | None) -> list[int]:
    """Indices of the first tokens of the sentences of every part of a text between blank lines"""
    first: list[int] = []
    sents = _iter_sents(text) if sentenize is None else _hook_sents(sentenize, text)
    for start, end, _ in sents:
        index = bisect_left(starts, start)
        if index < len(starts) and starts[index] < end and (not first or index > first[-1]):
            first.append(index)
    return first


def _hook_sents(sentenize: Spans, text: str) -> Iterator[tuple[int, int, str]]:
    """Sentences of sentenize with their positions by start, every part between blank lines apart"""
    for part_start, part in _parts(text):
        for start, end, sent in sorted(
            _check_spans(sentenize(part), part, "sentence splitter", ordered=False)
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
