from __future__ import annotations

import re
import unicodedata
from bisect import bisect_right
from collections.abc import Callable, Iterable, Sequence
from typing import TYPE_CHECKING, NamedTuple

from ..document import to_document
from ..exceptions import ParameterError, SourceTypeError
from ..utils import BLANK_LINE, check_bool, check_integer, has_words

if TYPE_CHECKING:
    from anyseg import Document, Word
    from spacy.tokens import Doc

Tokenizer = Callable[[str], Iterable[tuple[int, int, str]]]
Sentenizer = Callable[[str], Iterable[tuple[int, int, str]]]
Lemmatizer = Callable[[str, Sequence["Word"]], Iterable[str] | str]

# The end of a sentence in a keyword: a final mark, closing marks and whitespace, or a blank line
_BOUNDARY = re.compile(rf"[.!?…][\"'»”’)\]]*\s|{BLANK_LINE.pattern}")


class Concordance(NamedTuple):
    """
    Line of a concordance - an occurrence of the keyword with its context

    Attributes:
        start (int): Position of the first character of the occurrence in the text
        end (int): Position after the last character of the occurrence
        left (str): Context on the left
        keyword (str): Occurrence as written in the text
        right (str): Context on the right
    """

    start: int
    end: int
    left: str
    keyword: str
    right: str


def kwic(
    source: str | Doc | Document,
    keyword: str,
    window: int = 5,
    by_lemma: bool = False,
    ignore_case: bool = True,
    tokenize: Tokenizer | None = None,
    lemmatize: Lemmatizer | None = None,
    fold: Callable[[str], str] = str.lower,
    sentenize: Sentenizer | None = None,
) -> list[Concordance]:
    """
    Building a KWIC concordance (keyword in context)

    Description:
        Occurrences of a word or a phrase are found among the words of the
        document of the text (to_document with tokenize and sentenize) by the
        word form or by the lemma, when a word shares a lemma with its word of
        the keyword; the keyword is split the same way. The words are the
        tokens with a letter or a digit (document_words). Lemmas, and word
        forms with ignore_case, are folded by fold; forms are compared in NFC,
        without soft hyphens. A phrase does not cross the end of a sentence or
        a paragraph of the document unless the keyword has such an end in the
        same place, or a final mark before whitespace there, whatever the case
        after it. The context is window words on each side as written,
        punctuation included; whitespace collapses to one space; occurrences do
        not overlap

    Arguments:
        source (str|Doc|Document): Text, Doc or Document object
        keyword (str): Word or phrase
        window (int): Number of words of context on each side
        by_lemma (bool): Compare lemmas instead of word forms
        ignore_case (bool): Fold the word forms before comparing them
        tokenize (callable): Tokens of a string as triples of the start, the end
            and the text; the default tokens of to_document by default
        lemmatize (callable): Lemmas of a word, given its text and its words of
            Universal Dependencies (Word objects of anySeg); a string is one
            lemma; by default the word and, for a token of one word with a
            lemma, that lemma
        fold (callable): Folding of a word form or a lemma before the comparison
        sentenize (callable): Sentences of a string, of the keyword and of the
            text of a Doc without sentences, as triples of the start, the end and
            the text; those of SentsExtractor by default

    Returns:
        list[Concordance]: Occurrences in the order of the text

    Raises:
        SourceTypeError: If the source is neither a string, a Doc nor a Document
            object, the keyword is not a string, a hook is not callable, or
            tokenize or sentenize does not give triples of the text (to_document)
        SourceError: If a token of a Doc cannot be in a document (to_document)
        ParameterError: If the keyword has no words, the window is not an integer or
            is negative, or by_lemma or ignore_case is not a bool

    Example:
        >>> from anyts.corpus import kwic
        >>> text = "The cat sleeps. The cats play in the garden."
        >>> [line.keyword for line in kwic(text, "cat", window=1)]
        ['cat']
        >>> kwic(text, "cats", window=2)[0]
        Concordance(start=20, end=24, left='sleeps. The', keyword='cats', right='play in')
    """
    if not isinstance(keyword, str):
        raise SourceTypeError(f"The keyword must be a string, not {type(keyword).__name__}")
    if lemmatize is not None and not callable(lemmatize):
        raise SourceTypeError(f"The lemmatizer must be callable, not {type(lemmatize).__name__}")
    if not callable(fold):
        raise SourceTypeError(f"The folding must be callable, not {type(fold).__name__}")
    key_words = _words(to_document(keyword, tokenize, sentenize))
    if not key_words:
        raise ParameterError("The keyword is not set")
    key_gaps = [
        key_words[index].sentence != key_words[index - 1].sentence
        or bool(_BOUNDARY.search(keyword, key_words[index - 1].end, key_words[index].start))
        for index in range(1, len(key_words))
    ]
    check_integer(window, "window")
    check_bool(by_lemma, "comparison by the lemmas")
    check_bool(ignore_case, "folding of the case")
    if window < 0:
        raise ParameterError("The window cannot be negative")
    document = to_document(source, tokenize, sentenize)
    text = document.text
    words = _words(document)
    lemmas = lemmatize or _lemmas

    def readings(word: _Word | _KeyWord) -> set[str]:
        form = _normalize(word.text)
        if not by_lemma:
            return {fold(form) if ignore_case else form}
        found = lemmas(form, word.words)
        if isinstance(found, str):
            return {fold(_normalize(found))}
        return {fold(_normalize(lemma)) for lemma in found}

    def crosses(index: int) -> bool:
        """Whether the phrase starting at a word runs across a sentence end the keyword lacks"""
        return any(
            words[index + offset].sentence != words[index + offset - 1].sentence
            for offset, allowed in enumerate(key_gaps, 1)
            if not allowed
        )

    met = [readings(word) for word in words]
    target = [readings(_KeyWord(word.text)) for word in key_words]
    found = []
    index = 0
    while index <= len(words) - len(target):
        candidates = met[index : index + len(target)]
        if not all(
            wanted & seen for wanted, seen in zip(target, candidates, strict=True)
        ) or crosses(index):
            index += 1
            continue
        last = index + len(target) - 1
        start = words[index].start
        end = words[last].end
        left = text[words[max(index - window, 0)].start : start] if window else ""
        right = text[end : words[min(last + window, len(words) - 1)].end] if window else ""
        found.append(
            Concordance(
                start,
                end,
                " ".join(left.split()),
                " ".join(text[start:end].split()),
                " ".join(right.split()),
            )
        )
        index = last + 1
    return found


class _Word(NamedTuple):
    """Word of a document with its position, its sentence and its words of Universal Dependencies"""

    start: int
    end: int
    text: str
    sentence: int
    words: Sequence[Word]


class _KeyWord(NamedTuple):
    """Word of the keyword, read by its form alone"""

    text: str
    words: Sequence[Word] = ()


def _words(document: Document) -> list[_Word]:
    """Words of a document: the tokens with a letter or a digit, with the index of their sentence"""
    sentence_starts = document.sentences.starts
    return [
        _Word(
            token.start,
            token.end,
            token.text,
            bisect_right(sentence_starts, token.start) - 1,
            token.words,
        )
        for token in document.tokens
        if has_words(token.text)
    ]


def _normalize(word: str) -> str:
    """Composed form of a word (NFC) without soft hyphens"""
    return unicodedata.normalize("NFC", word).replace("\u00ad", "")


def _lemmas(word: str, words: Sequence[Word]) -> tuple[str, ...]:
    """The word itself and, for a token of one word with a lemma, that lemma"""
    lemma = words[0].lemma if len(words) == 1 else None
    return (word, lemma) if lemma else (word,)


def format_kwic(concordances: Iterable[Concordance], width: int = 40) -> str:
    """
    Formatting a concordance aligned on the keyword

    Description:
        The left context is cut from the left and aligned to the right, the
        right one is cut from the right; lines are separated by line breaks.
        The lines are taken in NFC, so the widths count characters as shown

    Arguments:
        concordances (list[Concordance]): Lines of the concordance
        width (int): Width of a context in characters

    Returns:
        str: Concordance as text

    Raises:
        SourceTypeError: If the concordances are a string or not iterable
        ParameterError: If the width of a context is not an integer or is below one

    Example:
        >>> from anyts.corpus import format_kwic, kwic
        >>> print(format_kwic(kwic("The cat sleeps and the cat eats.", "cat", window=1), width=6))
           The  cat  sleeps
           the  cat  eats
    """
    check_integer(width, "width of a context")
    if width < 1:
        raise ParameterError("The width of a context must be greater than 0")
    given: object = concordances
    if isinstance(given, str):
        raise SourceTypeError("An iterable of concordances is expected, not a string")
    if not isinstance(given, Iterable):
        raise SourceTypeError(
            f"An iterable of concordances is expected, not {type(given).__name__}"
        )
    lines = [
        [unicodedata.normalize("NFC", part) for part in (line.left, line.keyword, line.right)]
        for line in concordances
    ]
    keyword_width = max((len(keyword) for _, keyword, _ in lines), default=0)
    return "\n".join(
        f"{left[-width:]:>{width}}  {keyword:<{keyword_width}}  {right[:width]}"
        for left, keyword, right in lines
    )


def print_kwic(concordances: Iterable[Concordance], width: int = 40) -> None:
    """
    Printing a concordance aligned on the keyword

    Arguments:
        concordances (list[Concordance]): Lines of the concordance
        width (int): Width of a context in characters

    Raises:
        SourceTypeError: If the concordances are a string or not iterable
        ParameterError: If the width of a context is not an integer or is below one
    """
    print(format_kwic(concordances, width))
