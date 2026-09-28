import re
import unicodedata
from collections.abc import Callable, Iterable, Sequence
from itertools import pairwise
from typing import NamedTuple

from spacy.tokens import Doc, Token

from ..exceptions import ParameterError, SourceTypeError
from ..extractors import _iter_words
from ..utils import _unit_word, check_integer, iter_doc_units

Tokenizer = Callable[[str], Iterable[tuple[int, int, str]]]
Lemmatizer = Callable[[str, Sequence[Token]], Iterable[str] | str]

# The end of a paragraph, and of a sentence: a final mark, closing marks and whitespace
PARAGRAPH = re.compile(r"\n[^\S\n]*\n")
BOUNDARY = re.compile(rf"[.!?…][\"'»”’)\]]*\s|{PARAGRAPH.pattern}")


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
    source: str | Doc,
    keyword: str,
    window: int = 5,
    by_lemma: bool = False,
    ignore_case: bool = True,
    tokenize: Tokenizer | None = None,
    lemmatize: Lemmatizer | None = None,
    fold: Callable[[str], str] = str.lower,
    join_hyphens: bool = False,
) -> list[Concordance]:
    """
    Building a KWIC concordance (keyword in context)

    Description:
        The occurrences of a word or a phrase are looked for among the words of
        the text by the word form, ignoring case or not, or by the lemma. The
        words of a string and of the keyword come from tokenize, those of a Doc
        from its tokens (iter_doc_units with join_hyphens), so a library passes
        the tokenizer that splits a string as its pipeline does; punctuation and
        symbols are not words. By lemma, a word matches when one of its lemmas
        (lemmatize) is one of the lemmas of the words of the keyword; the lemmas
        are folded by fold, and so are the word forms with ignore_case. The
        compared forms are in the composed form of Unicode (NFC), without soft
        hyphens. By default a word is a run of word characters, kept whole
        across its inner hyphens with join_hyphens, the lemmas of a word are the
        word itself and, for a word of a Doc with lemmas, the lemma of the
        model, and fold lower-cases
        A phrase does not run across the end of a paragraph or of a sentence -
        a boundary of a Doc anywhere between its words, or a final mark before
        whitespace without boundaries - unless the keyword has one in the same
        place. The context is window words on each side as written, with the
        punctuation between them; whitespace collapses to one space;
        occurrences do not overlap

    Arguments:
        source (str|Doc): Text or Doc object
        keyword (str): Word or phrase
        window (int): Number of words of context on each side
        by_lemma (bool): Compare lemmas instead of word forms
        ignore_case (bool): Fold the word forms before comparing them
        tokenize (callable): Words of a string as triples of the start, the end
            and the text; a run of word characters by default
        lemmatize (callable): Lemmas of a word, given its text and its tokens
            in a Doc (none for a string and the keyword); a string is one lemma
        fold (callable): Folding of a word form or a lemma before the comparison
        join_hyphens (bool): Join the parts of hyphenated words of a Doc

    Returns:
        list[Concordance]: Occurrences in the order of the text

    Raises:
        SourceTypeError: If the source is neither a string nor a Doc object, the keyword
            is not a string or a hook is not callable
        ParameterError: If the keyword has no words or the window is not an integer
            or is negative

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
    for hook, name in ((tokenize, "tokenizer"), (lemmatize, "lemmatizer")):
        if hook is not None and not callable(hook):
            raise SourceTypeError(f"The {name} must be callable, not {type(hook).__name__}")
    if not callable(fold):
        raise SourceTypeError(f"The folding must be callable, not {type(fold).__name__}")
    split = tokenize or (_iter_hyphenated_words if join_hyphens else _iter_words)
    key_words = list(split(keyword))
    if not key_words:
        raise ParameterError("The keyword is not set")
    key_gaps = [
        bool(BOUNDARY.search(keyword[end:start]))
        for (_, end, _), (start, _, _) in pairwise(key_words)
    ]
    check_integer(window, "window")
    if window < 0:
        raise ParameterError("The window cannot be negative")
    text, words, tokens = _source_words(source, split, join_hyphens)
    doc = source if isinstance(source, Doc) and source.has_annotation("SENT_START") else None
    lemmas = lemmatize or _lemmas

    def readings(word: str, word_tokens: Sequence[Token]) -> set[str]:
        word = _normalize(word)
        if not by_lemma:
            return {fold(word) if ignore_case else word}
        found = lemmas(word, word_tokens)
        if isinstance(found, str):
            return {fold(_normalize(found))}
        return {fold(_normalize(lemma)) for lemma in found}

    def crosses(index: int) -> bool:
        """Whether the phrase starting at a word runs across a boundary the keyword lacks"""
        return any(
            _boundary(text, words, tokens, doc, index + offset)
            for offset, allowed in enumerate(key_gaps, 1)
            if not allowed
        )

    met = [
        readings(word, word_tokens)
        for (_, _, word), word_tokens in zip(words, tokens, strict=True)
    ]
    target = [readings(word, ()) for _, _, word in key_words]
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
        start = words[index][0]
        end = words[last][1]
        left = text[words[max(index - window, 0)][0] : start] if window else ""
        right = text[end : words[min(last + window, len(words) - 1)][1]] if window else ""
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


def _source_words(
    source: str | Doc, split: Tokenizer, join_hyphens: bool
) -> tuple[str, list[tuple[int, int, str]], list[Sequence[Token]]]:
    """Text of a source, its words with their positions and their tokens (none for a string)"""
    if isinstance(source, Doc):
        tokens = list(iter_doc_units(source, join_hyphens))
        return source.text, [_unit_word(unit) for unit in tokens], list(tokens)
    if isinstance(source, str):
        words = list(split(source))
        return source, words, [()] * len(words)
    raise SourceTypeError("The data source is set incorrectly")


def _boundary(
    text: str,
    words: Sequence[tuple[int, int, str]],
    tokens: Sequence[Sequence[Token]],
    doc: Doc | None,
    index: int,
) -> bool:
    """
    Whether a sentence or a paragraph ends before a word

    Description:
        By the sentence boundaries of a Doc - at any token from the one after
        the previous word to the first token of the word, so that a start on an
        opening mark counts - and by the paragraph breaks; by the final marks
        before whitespace otherwise
    """
    gap = text[words[index - 1][1] : words[index][0]]
    if doc is None:
        return bool(BOUNDARY.search(gap))
    first, last = tokens[index - 1][-1].i + 1, tokens[index][0].i
    return bool(PARAGRAPH.search(gap)) or any(
        doc[position].is_sent_start for position in range(first, last + 1)
    )


def _normalize(word: str) -> str:
    """Composed form of a word (NFC) without soft hyphens"""
    return unicodedata.normalize("NFC", word).replace("\u00ad", "")


def _iter_hyphenated_words(text: str) -> list[tuple[int, int, str]]:
    """Words of the default tokenizer, those joined by a hyphen without whitespace kept whole"""
    words: list[tuple[int, int, str]] = []
    for start, end, word in _iter_words(text):
        if words and text[words[-1][1] : start] == "-":
            first = words[-1][0]
            words[-1] = (first, end, text[first:end])
        else:
            words.append((start, end, word))
    return words


def _lemmas(word: str, tokens: Sequence[Token]) -> tuple[str, ...]:
    """The word itself and, for a word of one token of a Doc with lemmas, the lemma of the model"""
    lemma = tokens[0].lemma_ if len(tokens) == 1 else ""
    return (word, lemma) if lemma else (word,)


def format_kwic(concordances: Iterable[Concordance], width: int = 40) -> str:
    """
    Formatting a concordance aligned on the keyword

    Description:
        The left context is cut from the left and aligned to the right, the
        right one is cut from the right; lines are separated by line breaks.
        The lines are taken in the composed form of Unicode (NFC), so that the
        widths count characters as they are shown

    Arguments:
        concordances (list[Concordance]): Lines of the concordance
        width (int): Width of a context in characters

    Returns:
        str: Concordance as text

    Raises:
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
    """
    print(format_kwic(concordances, width))
