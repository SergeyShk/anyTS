from __future__ import annotations

import html
import re
from collections.abc import Callable, Collection, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise
from numbers import Real
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, ClassVar, NamedTuple

from ..constants import ALLITERATION_MIN_WORD_LEN, ALLITERATION_THRESHOLD, MESSAGES
from ..exceptions import ParameterError, SourceError, SourceTypeError
from ..extractors import SentsExtractor, _iter_words, iter_part_sents
from ..syntax_stats import get_words
from ..utils import (
    _unit_word,
    check_callable,
    check_integer,
    check_messages,
    check_number,
    check_word,
    check_words,
    find_phrases,
    has_sents,
    in_order,
    is_doc,
    iter_doc_tokens,
)

if TYPE_CHECKING:
    from spacy.tokens import Doc, Token

    from ..cohesion_stats import Connector, ConnectorMatcher

# Line breaks of Unix, Windows and old Mac texts
LINE_BREAK = re.compile(r"\r\n?|\n")
# What an annotation of a Doc gives a layer, for the message of an unavailable layer
ANNOTATION_NAMES = {
    "DEP": "a dependency parse",
    "LEMMA": "the lemmas",
    "POS": "the parts of speech",
    "TAG": "the tags",
    "MORPH": "the morphological features",
    "ENT_IOB": "the named entities",
}


class Word(NamedTuple):
    """
    Word of a text with its position

    Attributes:
        start (int): Position of the first character
        end (int): Position after the last character
        text (str): Text of the word
        pos (str): Part of speech, if known
        lemma (str): Lemma, if known
    """

    start: int
    end: int
    text: str
    pos: str | None = None
    lemma: str | None = None


class Sent(NamedTuple):
    """
    Sentence of a text with its position

    Attributes:
        start (int): Position of the first character
        end (int): Position after the last character
        n_words (int): Number of words
    """

    start: int
    end: int
    n_words: int


@dataclass(frozen=True)
class Highlight:
    """
    Highlighted fragment of a text

    Arguments:
        start (int): Position of the first character of the fragment
        end (int): Position after the last character of the fragment
        layer (str): Layer of the highlighting
        note (str): Explanation of the fragment for the tooltip
    """

    start: int
    end: int
    layer: str
    note: str = ""


def check_params(
    long_sent_word_factor: int,
    complex_syl_factor: int,
    alliteration_threshold: float,
    *,
    messages: Mapping[str, str] = MESSAGES,
) -> None:
    """
    Checking the parameters of the highlighting

    Arguments:
        long_sent_word_factor (int): Minimum number of words of a long sentence
        complex_syl_factor (int): Minimum number of syllables of a complex word
        alliteration_threshold (float): Probability threshold of the alliteration
        messages (dict[str, str]): Messages of the errors by key (MESSAGES)

    Raises:
        ParameterError: If a number is not an integer of at least one, or the
            threshold does not lie in the interval (0, 1]
    """
    _check_factor(long_sent_word_factor, "long_sent_word_factor", messages)
    _check_factor(complex_syl_factor, "complex_syl_factor", messages)
    _check_threshold(alliteration_threshold, messages)


def _check_factor(value: int, key: str, messages: Mapping[str, str] = MESSAGES) -> None:
    """Checking the least number of words or syllables of a layer, its message by key"""
    what = {
        "long_sent_word_factor": "number of words of a long sentence",
        "complex_syl_factor": "number of syllables of a complex word",
    }[key]
    check_integer(value, what)
    if value < 1:
        raise ParameterError(messages[key])


def _check_threshold(value: float, messages: Mapping[str, str] = MESSAGES) -> None:
    """Checking the probability threshold of the alliteration"""
    check_number(value, "threshold of the alliteration")
    if not 0 < value <= 1:
        raise ParameterError(messages["alliteration_threshold"])


class HighlightedText:
    """
    Base of the highlighting of a text by layers, in the manner of the style checkers

    Description:
        A layer marks the fragments of a text that a statistic counts. A
        language library subclasses the class, sets the class attributes
            layers_desc - the layers in the order of drawing with their legends
            default_layers - the layers on by default
            layer_annotations - the annotations of a Doc a layer needs (DEP, POS,
                LEMMA...); a layer without them is available for a string too
            layer_styles - the CSS declarations of the layers
            css_prefix - the prefix of the CSS classes
            annotation_names - the names of the annotations in the message of
                an unavailable layer
            messages - the messages of the errors by key
        and implements find, overriding iter_words, iter_sents and doc_words
        when needed. The sentences of a Doc come from its boundaries
        (iter_doc_sents), or from iter_sents over its text without them or with
        partial ones (has_sents); iter_sents gets the parts of a text between
        blank lines one by one, so a blank line ends a sentence as in
        SentsExtractor. The words of a sentence are those that start in it.
        Fragments of different layers may overlap. The result shows in Jupyter
        as HTML with a legend (to_html)

    Arguments:
        source (str|Doc): Data source (a string or a Doc object)
        layers (list[str]|str): Layers of the highlighting; the layers of
            default_layers the source allows if not set; "all" - every layer the
            source allows

    Attributes:
        text (str): Text of the source
        layers (tuple[str]): Layers turned on, in the order of drawing
        highlights (tuple[Highlight]): Highlighted fragments by start, then by descending end
        counts (dict[str, int]): Number of fragments of every layer

    Methods:
        to_html: Getting the HTML markup of the highlighted text
        css: Getting the styles of the layers

    Raises:
        SourceTypeError: If the source is neither a string nor a Doc
        SourceError: If the source has no words
        ParameterError: If a layer is unknown or not allowed by the source, the
            layers are not a list of names, or find gives a fragment of another
            layer or one outside the text
    """

    layers_desc: ClassVar[Mapping[str, str]] = MappingProxyType({})
    default_layers: ClassVar[Sequence[str]] = ()
    layer_annotations: ClassVar[Mapping[str, Sequence[str]]] = MappingProxyType({})
    layer_styles: ClassVar[Mapping[str, str]] = MappingProxyType({})
    css_prefix: ClassVar[str] = "anyts"
    annotation_names: ClassVar[Mapping[str, str]] = MappingProxyType(ANNOTATION_NAMES)
    messages: ClassVar[Mapping[str, str]] = MESSAGES

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        check_messages(cls.messages)

    def __init__(self, source: str | Doc, layers: Sequence[str] | str | None = None):
        doc = None
        if is_doc(source):
            doc = source
            self.text = source.text
            words = self.doc_words(source)
            spans = (
                iter_doc_sents(source)
                if has_sents(source)
                else iter_part_sents(self.iter_sents, self.text)
            )
            sents = get_text_sents(spans, words)
        elif isinstance(source, str):
            self.text = source
            words = [Word(start, end, text) for start, end, text in self.iter_words(source)]
            sents = get_text_sents(iter_part_sents(self.iter_sents, source), words)
        else:
            raise SourceTypeError(self.messages["source_type"])
        if not words:
            raise SourceError(self.messages["no_words"])
        available = [
            layer
            for layer in self.layers_desc
            if all(
                doc is not None and doc.has_annotation(annotation)
                for annotation in self.layer_annotations.get(layer, ())
            )
        ]
        self.layers = self._select_layers(layers, available)
        highlights = []
        for layer in self.layers:
            found = self.find(layer, words, sents, doc)
            if not isinstance(found, Iterable):
                raise SourceTypeError(self._find_error(found))
            for h in found:
                if not isinstance(h, Highlight):
                    raise SourceTypeError(self._find_error(h))
                if h.layer != layer:
                    raise ParameterError(
                        self.messages["fragment_layer"].format(found=h.layer, layer=layer)
                    )
                if not 0 <= h.start < h.end <= len(self.text):
                    raise ParameterError(
                        self.messages["fragment_outside"].format(
                            layer=layer, start=h.start, end=h.end
                        )
                    )
                highlights.append(h)
        self.highlights = tuple(sorted(highlights, key=lambda h: (h.start, -h.end)))

    def iter_words(self, text: str) -> Iterable[tuple[int, int, str]]:
        """
        Extracting the words of a string with their positions

        Description:
            By default the words of the default tokenizer of WordsExtractor;
            a language library overrides the method

        Arguments:
            text (str): Text string

        Returns:
            iterable[tuple[int, int, str]]: Position of the first character,
                position after the last character and text of each word
        """
        return _iter_words(text)

    def iter_sents(self, text: str) -> Iterator[tuple[int, int, str]]:
        """
        Extracting the sentences of a string with their positions

        Description:
            By default the sentences of the default tokenizer of SentsExtractor;
            a language library overrides the method

        Arguments:
            text (str): Text string

        Returns:
            iterator[tuple[int, int, str]]: Position of the first character,
                position after the last character and text of each sentence
        """
        position = 0
        for sent in SentsExtractor().extract(text):
            start = text.index(sent, position)
            position = start + len(sent)
            yield start, position, sent

    def doc_words(self, doc: Doc) -> list[Word]:
        """
        Extracting the words of a Doc object with their positions

        Description:
            By default get_doc_words; a language library overrides the method

        Arguments:
            doc (Doc): Doc object

        Returns:
            list[Word]: Words with their positions
        """
        return get_doc_words(doc)

    def find(
        self, layer: str, words: Sequence[Word], sents: Sequence[Sent], doc: Doc | None
    ) -> list[Highlight]:
        """
        Finding the fragments of a layer

        Description:
            A language library implements the method for its layers; it runs in
            __init__, so a subclass stores its own parameters before calling the
            __init__ of the base

        Arguments:
            layer (str): Layer of the highlighting
            words (list[Word]): Words of the text with their positions
            sents (list[Sent]): Sentences of the text with their positions
            doc (Doc): Doc object of the source; None for a string

        Returns:
            list[Highlight]: Fragments of the layer, of this layer only
        """
        raise NotImplementedError

    def _find_error(self, value: object) -> str:
        """Message of a result of find that is not fragments of the highlighting"""
        return self.messages["hook_result"].format(
            hook="find",
            cls=type(self).__name__,
            expected="Highlight objects",
            type=type(value).__name__,
        )

    @classmethod
    def _select_layers(
        cls, layers: Sequence[str] | str | None, available: Sequence[str]
    ) -> tuple[str, ...]:
        """
        Selecting the layers of the highlighting

        Arguments:
            layers (list[str]|str): Layers asked for; the layers of default_layers
                among the available ones if not set, "all" - every available layer
            available (list[str]): Layers the data source allows

        Returns:
            tuple[str]: Layers in the order of drawing

        Raises:
            ParameterError: If a layer is unknown or not allowed by the source, or
                the layers are not a list of names
        """
        messages = cls.messages
        if layers is None:
            return tuple(layer for layer in cls.default_layers if layer in available)
        if isinstance(layers, str):
            if layers == "all":
                return tuple(available)
            layers = [layers]
        try:
            layers = list(layers)
        except TypeError as e:
            raise ParameterError(messages["layers_type"]) from e
        for layer in layers:
            if not isinstance(layer, str) or layer not in cls.layers_desc:
                raise ParameterError(messages["unknown_layer"].format(layer=layer))
            if layer not in available:
                needs = [
                    cls.annotation_names.get(annotation, annotation)
                    for annotation in cls.layer_annotations.get(layer, ())
                ]
                if not needs:
                    raise ParameterError(messages["layer_unavailable"].format(layer=layer))
                raise ParameterError(
                    messages["layer_annotations"].format(layer=layer, annotations=", ".join(needs))
                )
        return tuple(layer for layer in cls.layers_desc if layer in layers)

    @classmethod
    def css(cls) -> str:
        """
        Getting the styles of the layers

        Description:
            The CSS classes are named by css_prefix; the text of a layer with a
            background (layer_styles) keeps a dark colour on it

        Returns:
            str: CSS
        """
        p = cls.css_prefix
        lines = [
            f".{p}-highlight {{ line-height: 1.7; }}",
            f".{p}-highlight-legend {{ display: flex; flex-wrap: wrap; gap: 0.4em 1.2em; "
            "margin-bottom: 0.8em; font-size: 0.9em; }",
            f".{p}-highlight-legend .{p}-hl {{ padding: 0 0.3em; }}",
            f".{p}-highlight-count {{ opacity: 0.6; margin-left: 0.3em; }}",
            f".{p}-highlight-text {{ white-space: pre-wrap; }}",
        ]
        painted = [layer for layer, style in cls.layer_styles.items() if "background" in style]
        if painted:
            selectors = ", ".join(f".{p}-highlight .{p}-hl.{p}-hl-{layer}" for layer in painted)
            lines.append(f"{selectors} {{ color: #1f2328; border-radius: 2px; }}")
        lines.extend(f".{p}-hl-{layer} {{ {style} }}" for layer, style in cls.layer_styles.items())
        return "\n".join(lines) + "\n"

    @property
    def counts(self) -> dict[str, int]:
        return {
            layer: sum(1 for h in self.highlights if h.layer == layer) for layer in self.layers
        }

    def to_html(self, legend: bool = True, css: bool = True) -> str:
        """
        Getting the HTML markup of the highlighted text

        Description:
            A div of the class <prefix>-highlight with the legend and the text,
            where a highlighted segment is a span of the classes <prefix>-hl and
            <prefix>-hl-<layer> with the notes in its title. Line breaks become
            character references, so the markup can go into Markdown with no
            blank line inside the block

        Arguments:
            legend (bool): Add the legend with the counts of the fragments
            css (bool): Add the styles of the layers

        Returns:
            str: HTML markup
        """
        p = self.css_prefix
        parts = [f'<div class="{p}-highlight">']
        if css:
            parts.append(f"<style>{self.css()}</style>")
        if legend:
            items = "".join(
                f'<span><span class="{p}-hl {p}-hl-{layer}">'
                f"{html.escape(self.layers_desc[layer], quote=False)}</span>"
                f'<span class="{p}-highlight-count">{count}</span></span>'
                for layer, count in self.counts.items()
            )
            parts.append(f'<div class="{p}-highlight-legend">{items}</div>')
        parts.append(f'<div class="{p}-highlight-text">{self._render_text()}</div></div>')
        return "".join(parts)

    def _repr_html_(self) -> str:
        return self.to_html()

    def __repr__(self) -> str:
        return f"{type(self).__name__}(counts={self.counts})"

    def _render_text(self) -> str:
        p = self.css_prefix
        chunks = []
        for start, end, active in split_segments(len(self.text), self.highlights):
            chunk = LINE_BREAK.sub("&#10;", html.escape(self.text[start:end]))
            if active:
                active.sort(key=lambda h: self.layers.index(h.layer))
                classes = " ".join(f"{p}-hl-{h.layer}" for h in active)
                notes = "; ".join(dict.fromkeys(h.note for h in active if h.note))
                title = f' title="{html.escape(notes)}"' if notes else ""
                chunk = f'<span class="{p}-hl {classes}"{title}>{chunk}</span>'
            chunks.append(chunk)
        return "".join(chunks)


def get_doc_words(doc: Doc) -> list[Word]:
    """
    Extracting the words of a Doc object with their positions

    Description:
        The words of iter_doc_tokens, a byte order mark at the start left out,
        with the part of speech and the lemma when the Doc has them

    Arguments:
        doc (Doc): Doc object

    Returns:
        list[Word]: Words with their positions
    """
    has_pos, has_lemma = doc.has_annotation("POS"), doc.has_annotation("LEMMA")
    return [
        Word(
            *_unit_word([token]),
            token.pos_ if has_pos else None,
            token.lemma_ if has_lemma else None,
        )
        for token in iter_doc_tokens(doc)
    ]


def iter_doc_sents(doc: Doc) -> Iterator[tuple[int, int, str]]:
    """
    Extracting the sentences of a Doc object with their positions

    Description:
        The sentences of its boundaries; the whitespace tokens at the edges of a
        sentence are left out of its positions, and a sentence of whitespace
        alone is skipped

    Arguments:
        doc (Doc): Doc object with the sentence boundaries

    Returns:
        iterator[tuple[int, int, str]]: Position of the first character,
            position after the last character and text of each sentence
    """
    text = doc.text
    for sent in doc.sents:
        tokens = [token for token in sent if not token.is_space]
        if tokens:
            start = min(token.idx for token in tokens)
            end = max(token.idx + len(token) for token in tokens)
            yield start, end, text[start:end]


def get_text_sents(spans: Iterable[tuple[int, int, str]], words: Sequence[Word]) -> list[Sent]:
    """
    Counting the words of the sentences of a text

    Description:
        A word belongs to the sentence of its first character; the words and
        the sentences are ordered by position

    Arguments:
        spans (iterable[tuple[int, int, str]]): Sentences with their positions
            (the start, the position after the end and the text)
        words (list[Word]): Words of the text with their positions

    Returns:
        list[Sent]: Sentences with their positions and numbers of words

    Example:
        >>> from anyts.visualizers.highlight import Word, get_text_sents
        >>> words = [Word(0, 5, "Hello"), Word(7, 12, "world"), Word(14, 17, "Bye")]
        >>> get_text_sents([(0, 13, "Hello, world."), (14, 18, "Bye.")], words)
        [Sent(start=0, end=13, n_words=2), Sent(start=14, end=18, n_words=1)]
    """
    ordered = list(words)
    sents = []
    index = 0
    for start, end, _ in spans:
        n_words = 0
        while index < len(ordered) and ordered[index].start < end:
            n_words += ordered[index].start >= start
            index += 1
        sents.append(Sent(start, end, n_words))
    return sents


def group_words_by_sents(words: Sequence[Word], sents: Sequence[Sent]) -> list[list[Word]]:
    """
    Grouping the words by sentences

    Description:
        The words and the sentences must be ordered by position; a word belongs
        to the sentence of its first character, the words out of the sentences
        are skipped

    Arguments:
        words (list[Word]): Words with their positions
        sents (list[Sent]): Sentences with their positions

    Returns:
        list[list[Word]]: Words of every sentence
    """
    ordered = list(sents)
    groups: list[list[Word]] = [[] for _ in ordered]
    index = 0
    for word in words:
        while index < len(ordered) and ordered[index].end <= word.start:
            index += 1
        if index < len(ordered) and ordered[index].start <= word.start:
            groups[index].append(word)
    return groups


def tokens_span(tokens: Iterable[Token]) -> tuple[int, int]:
    """
    Computing the positions of the fragment of a text that covers some words

    Description:
        The punctuation marks and the whitespace tokens are left out

    Arguments:
        tokens (Doc|Span|list[Token]): Sequence of tokens with a word

    Returns:
        tuple[int, int]: Position of the first character and position after the last one
    """
    words = get_words(tokens)
    return min(token.idx for token in words), max(token.idx + len(token) for token in words)


def split_segments(
    length: int, highlights: Sequence[Highlight]
) -> Iterator[tuple[int, int, list[Highlight]]]:
    """
    Splitting a text into segments with the same set of fragments

    Description:
        The bounds of the segments are the starts and the ends of all the
        fragments; overlapping and nested fragments of different layers give
        segments with several layers

    Arguments:
        length (int): Length of the text
        highlights (list[Highlight]): Fragments

    Returns:
        iterator[tuple[int, int, list[Highlight]]]: Positions of a segment and
            the fragments that cover it

    Example:
        >>> from anyts.visualizers.highlight import Highlight, split_segments
        >>> highlights = [Highlight(0, 4, "a"), Highlight(2, 6, "b")]
        >>> [(start, end, [h.layer for h in active]) for start, end, active in split_segments(8, highlights)]
        [(0, 2, ['a']), (2, 4, ['a', 'b']), (4, 6, ['b']), (6, 8, [])]
    """
    bounds = sorted({0, length, *(h.start for h in highlights), *(h.end for h in highlights)})
    pending = sorted(highlights, key=lambda h: h.start)
    active: list[Highlight] = []
    index = 0
    for start, end in pairwise(bounds):
        while index < len(pending) and pending[index].start <= start:
            active.append(pending[index])
            index += 1
        active = [h for h in active if h.end > start]
        yield start, end, list(active)


def find_long_sents(
    sents: Iterable[Sent],
    long_sent_word_factor: int,
    note: Callable[[int], str] | None = None,
) -> list[Highlight]:
    """
    Finding the long sentences

    Arguments:
        sents (list[Sent]): Sentences with their positions and numbers of words
        long_sent_word_factor (int): Minimum number of words of a long sentence
        note (Callable[[int], str]): Note of a sentence by its number of words; in
            English if not set

    Returns:
        list[Highlight]: Fragments of the layer long_sents

    Raises:
        ParameterError: If the number of words is not an integer of at least one
        SourceTypeError: If note is not callable
    """
    _check_factor(long_sent_word_factor, "long_sent_word_factor")
    _check_hooks((note, "note"))
    note = note or (lambda n: f"long sentence, {_plural(n, 'word')}")
    return [
        Highlight(sent.start, sent.end, "long_sents", note(sent.n_words))
        for sent in sents
        if sent.n_words >= long_sent_word_factor
    ]


def _check_hooks(*hooks: tuple[object, str]) -> None:
    """Checking that every hook of a finder that is set can be called"""
    for hook, what in hooks:
        if hook is not None:
            check_callable(hook, what)


def _plural(n: int, noun: str) -> str:
    """Number with an English noun in the singular or the plural"""
    return f"{n} {noun}" if n == 1 else f"{n} {noun}s"


def find_complex_words(
    words: Iterable[Word],
    complex_syl_factor: int,
    count_syllables: Callable[[str], int],
    note: Callable[[int], str] | None = None,
) -> list[Highlight]:
    """
    Finding the complex words

    Arguments:
        words (list[Word]): Words with their positions
        complex_syl_factor (int): Minimum number of syllables of a complex word
        count_syllables (Callable[[str], int]): Number of the syllables of a word
        note (Callable[[int], str]): Note of a word by its number of syllables; in
            English if not set

    Returns:
        list[Highlight]: Fragments of the layer complex_words

    Raises:
        ParameterError: If the number of syllables is not an integer of at least one
        SourceTypeError: If count_syllables or note is not callable
    """
    _check_factor(complex_syl_factor, "complex_syl_factor")
    _check_hooks((count_syllables, "count of the syllables"), (note, "note"))
    note = note or (lambda n: f"complex word, {_plural(n, 'syllable')}")
    highlights = []
    for word in words:
        n_syllables = count_syllables(word.text)
        if n_syllables >= complex_syl_factor:
            highlights.append(Highlight(word.start, word.end, "complex_words", note(n_syllables)))
    return highlights


def find_words(
    words: Iterable[Word], is_match: Callable[[Word], bool], layer: str, note: str = ""
) -> list[Highlight]:
    """
    Finding the words of a layer one by one

    Description:
        For the layers of single words - stopwords, rare words, verbal nouns -
        whose check of a word belongs to a language

    Arguments:
        words (list[Word]): Words with their positions, parts of speech and lemmas
        is_match (Callable[[Word], bool]): Whether a word is a fragment of the layer
        layer (str): Layer of the highlighting
        note (str): Note of every fragment

    Returns:
        list[Highlight]: Fragments of the layer

    Raises:
        SourceTypeError: If is_match is not callable
    """
    _check_hooks((is_match, "check of a word"))
    return [Highlight(word.start, word.end, layer, note) for word in words if is_match(word)]


def find_phrase_highlights(
    words: Sequence[Word],
    phrases: Mapping[str, str] | Collection[str],
    layer: str,
    note: Callable[[str], str] | None = None,
    normalize: Callable[[str], str] = str.lower,
) -> list[Highlight]:
    """
    Finding the phrases of a list

    Description:
        The phrases are matched by the normalized forms of their words, each
        normalized alone as in the text (find_phrases). A mapping gives
        variants of the phrases - contractions, forms of verbs - with the
        phrase each stands for; of the variants that normalize alike the first
        wins. A set is read in order (in_order). A fragment covers the words
        from the first to the last, and the note reads the phrase of the list

    Arguments:
        words (list[Word]): Words with their positions
        phrases (list[str]|set[str]|dict[str, str]): Phrases, words separated by spaces, or
            their variants with the phrase of each
        layer (str): Layer of the highlighting
        note (Callable[[str], str]): Note of a fragment by its phrase; the phrase in
            quotes if not set
        normalize (Callable[[str], str]): Normalized form of a word

    Returns:
        list[Highlight]: Fragments of the layer

    Raises:
        SourceTypeError: If the phrases are not a list of strings or a mapping of
            strings, or note or normalize is not callable
    """
    _check_hooks((note, "note"), (normalize, "normalization"))
    note = note or (lambda phrase: f"\u00ab{phrase}\u00bb")
    check_words(phrases, "phrases", ordered=False)
    if isinstance(phrases, Mapping):
        check_words(list(phrases.values()), "phrases")
        pairs: Iterable[tuple[str, str]] = phrases.items()
    else:
        pairs = ((phrase, phrase) for phrase in in_order(phrases))
    forms: dict[str, str] = {}
    for variant, phrase in pairs:
        # A part may normalize to nothing or to several words, as find_phrases splits it
        if form := " ".join(" ".join(normalize(part) for part in variant.split()).split()):
            forms.setdefault(form, phrase)
    normalized = [normalize(word.text) for word in words]
    highlights = []
    for start, end in find_phrases(normalized, forms, str):
        phrase = forms[" ".join(normalized[start:end])]
        highlights.append(Highlight(words[start].start, words[end - 1].end, layer, note(phrase)))
    return highlights


def find_connector_highlights(
    words: Sequence[Word],
    sents: Sequence[Sent] | None,
    matcher: ConnectorMatcher,
    note: Callable[[Connector], str] | None = None,
    pos: Callable[[Word], str | None] | None = None,
) -> list[Highlight]:
    """
    Finding the connectors

    Description:
        The connectors of a matcher are looked for inside every sentence, in
        the whole text without the sentences, a one-word one checked by its
        part of speech when a word of the sentence has one

    Arguments:
        words (list[Word]): Words with their positions and parts of speech
        sents (list[Sent]): Sentences with their positions; None for the whole text
        matcher (ConnectorMatcher): Matcher of the connectors of a language
        note (Callable[[Connector], str]): Note of a connector; its class and kind if
            not set
        pos (Callable[[Word], str|None]): Part of speech of a word for the matcher;
            that of the word if not set

    Returns:
        list[Highlight]: Fragments of the layer connectors

    Raises:
        SourceTypeError: If note or pos is not callable
    """
    _check_hooks((note, "note"), (pos, "part of speech"))
    note = note or (lambda connector: f"{connector.text}: {connector.cls}, {connector.kind}")
    groups = [list(words)] if sents is None else group_words_by_sents(words, sents)
    highlights: list[Highlight] = []
    for group in groups:
        tags = [word.pos if pos is None else pos(word) for word in group]
        texts = [word.text for word in group]
        highlights.extend(
            Highlight(
                group[connector.start].start,
                group[connector.end - 1].end,
                "connectors",
                note(connector),
            )
            for connector in matcher.find(texts, 0, tags if any(tags) else None)
        )
    return highlights


def find_split_predicate_highlights(
    pairs: Iterable[tuple[Token, Token]], note: Callable[[Token, Token], str] | None = None
) -> list[Highlight]:
    """
    Finding the split predicates

    Description:
        The pairs of a light verb and its noun of a language; a fragment covers
        the words from the first to the last of the pair

    Arguments:
        pairs (list[tuple[Token, Token]]): Verb and noun of every split predicate
        note (Callable[[Token, Token], str]): Note of a pair; its lemmas if not set

    Returns:
        list[Highlight]: Fragments of the layer split_predicates

    Raises:
        SourceTypeError: If note is not callable
    """
    _check_hooks((note, "note"))
    note = note or (
        lambda verb, noun: f"split predicate: {verb.lemma_.lower()} {noun.lemma_.lower()}"
    )
    highlights = []
    for verb, noun in pairs:
        start, end = tokens_span([verb, noun])
        highlights.append(Highlight(start, end, "split_predicates", note(verb, noun)))
    return highlights


def calc_alliteration_runs(
    words: Sequence[str],
    frequencies: Mapping[str, float],
    threshold: float = ALLITERATION_THRESHOLD,
    stem: Callable[[str], Sequence[str]] = list,
    is_transparent: Callable[[str], bool] | None = None,
) -> list[tuple[int, int, str]]:
    """
    Finding the repetitions of a consonant in neighbouring words

    Description:
        A run of two or more neighbouring words with the same consonant in the
        stem of each; the stem of a language leaves out the endings that repeat
        by agreement. The probability of a run under an independent spread of
        the consonants is the product over its words of 1 - (1 - f)^n, with f
        the frequency of the consonant and n the length of the stem; a run is
        alliteration when it is below the threshold. Transparent words - by
        default shorter than ALLITERATION_MIN_WORD_LEN letters, such as
        stopwords for a language - neither break nor continue a run. The words
        are taken in lower case

    Arguments:
        words (list[str]): Words of a sentence
        frequencies (dict[str, float]): Consonants to look for with their frequencies
        threshold (float): Probability threshold
        stem (Callable[[str], list[str]]): Sounds or letters of the stem of a word;
            the letters of the word if not set
        is_transparent (Callable[[str], bool]): Whether a word neither breaks nor
            continues a run

    Returns:
        list[tuple[int, int, str]]: Positions of the first word and after the last
            word of every run and its consonant, in the order of the text

    Raises:
        SourceTypeError: If the words are not a list of strings (check_words), the
            frequencies not a mapping of consonants to numbers, or stem or
            is_transparent is not callable
        ParameterError: If a frequency does not lie in the interval [0, 1] or the
            threshold in (0, 1]
    """
    check_words(words)
    _check_frequencies(frequencies)
    _check_threshold(threshold)
    _check_hooks((stem, "stem"), (is_transparent, "check of a transparent word"))
    lowered = [word.lower() for word in words]
    if is_transparent is None:
        transparent = [len(word) < ALLITERATION_MIN_WORD_LEN for word in lowered]
    else:
        transparent = [is_transparent(word) for word in lowered]
    stems = [stem(word) for word in lowered]
    runs = []
    for consonant in sorted(frequencies):
        frequency = frequencies[consonant]
        start = None
        stop = 0
        probability = 1.0
        for i, word_stem in enumerate(stems):
            if transparent[i]:
                continue
            if consonant in word_stem:
                if start is None:
                    start, probability = i, 1.0
                stop = i + 1
                probability *= 1 - (1 - frequency) ** len(word_stem)
            elif start is not None:
                if stop - start >= 2 and probability < threshold:
                    runs.append((start, stop, consonant))
                start = None
        if start is not None and stop - start >= 2 and probability < threshold:
            runs.append((start, stop, consonant))
    return sorted(runs)


def _check_frequencies(frequencies: object) -> None:
    """Checking the frequencies of the consonants of the alliteration"""
    if not isinstance(frequencies, Mapping):
        raise SourceTypeError(
            f"The frequencies must be a mapping of consonants, not {type(frequencies).__name__}"
        )
    for consonant, frequency in frequencies.items():
        check_word(consonant, "consonant")
        if isinstance(frequency, bool) or not isinstance(frequency, Real):
            raise SourceTypeError(
                f"The frequencies must be numbers, not {type(frequency).__name__}"
            )
        if not 0 <= float(frequency) <= 1:
            raise ParameterError(
                f"The frequency of a consonant must lie in the interval [0, 1], not {frequency}"
            )


def find_alliteration(
    words: Sequence[Word],
    sents: Sequence[Sent] | None,
    frequencies: Mapping[str, float],
    threshold: float = ALLITERATION_THRESHOLD,
    stem: Callable[[str], Sequence[str]] = list,
    is_transparent: Callable[[str], bool] | None = None,
    note: Callable[[str], str] | None = None,
) -> list[Highlight]:
    """
    Finding the alliterations

    Description:
        The repetitions of calc_alliteration_runs are looked for inside the
        sentences, in the whole text without them

    Arguments:
        words (list[Word]): Words with their positions
        sents (list[Sent]): Sentences with their positions; None for the whole text
        frequencies (dict[str, float]): Consonants to look for with their frequencies
        threshold (float): Probability threshold
        stem (Callable[[str], list[str]]): Sounds or letters of the stem of a word
        is_transparent (Callable[[str], bool]): Whether a word neither breaks nor
            continues a run
        note (Callable[[str], str]): Note of a run by its consonant; in English if
            not set

    Returns:
        list[Highlight]: Fragments of the layer alliteration

    Raises:
        SourceTypeError: If the frequencies are not a mapping of consonants to
            numbers, or a hook is not callable
        ParameterError: If a frequency does not lie in the interval [0, 1] or the
            threshold in (0, 1]
    """
    _check_frequencies(frequencies)
    _check_threshold(threshold)
    _check_hooks((stem, "stem"), (is_transparent, "check of a transparent word"), (note, "note"))
    note = note or (lambda consonant: f"alliteration on {consonant}")
    groups = [list(words)] if sents is None else group_words_by_sents(words, sents)
    highlights = []
    for group in groups:
        runs = calc_alliteration_runs(
            [word.text for word in group], frequencies, threshold, stem, is_transparent
        )
        for start, stop, consonant in runs:
            highlights.append(
                Highlight(group[start].start, group[stop - 1].end, "alliteration", note(consonant))
            )
    return highlights
