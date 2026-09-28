import html
import re
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise
from types import MappingProxyType
from typing import ClassVar, NamedTuple

from spacy.tokens import Doc, Token

from ..exceptions import ParameterError, SourceError, SourceTypeError
from ..extractors import SentsExtractor, _iter_words
from ..syntax import get_words
from ..utils import iter_doc_tokens

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


class HighlightedText:
    """
    Base of the highlighting of a text by layers, in the manner of the style checkers

    Description:
        A layer marks the fragments of a text that a statistic counts. The
        layers and their search belong to a language library, which subclasses
        the class and sets:
            layers_desc - the layers in the order of drawing with their legends
            default_layers - the layers on by default
            layer_annotations - the annotations of a Doc a layer needs (DEP, POS,
                LEMMA...); a layer without them is available for a string too
            layer_styles - the CSS declarations of the layers
            css_prefix - the prefix of the CSS classes
            find - the fragments of a layer
            iter_words, iter_sents - the words and the sentences of a string with
                their positions, doc_words - the words of a Doc
        The sentences of a Doc come from its boundaries (iter_doc_sents), or
        from iter_sents over its text without them; the words of a sentence are
        those of doc_words or iter_words that start in it. The fragments are
        sorted by their start and then by descending end; fragments of
        different layers may overlap. The result shows in Jupyter as HTML with
        a legend (to_html)

    Arguments:
        source (str|Doc): Data source (a string or a Doc object)
        layers (list[str]|str): Layers of the highlighting; the layers of
            default_layers the source allows if not set; "all" - every layer the
            source allows

    Attributes:
        text (str): Text of the source
        layers (tuple[str]): Layers turned on, in the order of drawing
        highlights (tuple[Highlight]): Highlighted fragments in the order of the text
        counts (dict[str, int]): Number of fragments of every layer

    Methods:
        to_html: Getting the HTML markup of the highlighted text
        css: Getting the styles of the layers

    Raises:
        SourceTypeError: If the source is neither a string nor a Doc
        SourceError: If the source has no words
        ParameterError: If a layer is unknown or not allowed by the source, or
            the layers are not a list of names
        ValueError: If find gives a fragment of another layer
    """

    layers_desc: ClassVar[Mapping[str, str]] = MappingProxyType({})
    default_layers: ClassVar[Sequence[str]] = ()
    layer_annotations: ClassVar[Mapping[str, Sequence[str]]] = MappingProxyType({})
    layer_styles: ClassVar[Mapping[str, str]] = MappingProxyType({})
    css_prefix: ClassVar[str] = "anyts"

    def __init__(self, source: str | Doc, layers: Sequence[str] | str | None = None):
        doc = None
        if isinstance(source, Doc):
            doc = source
            self.text = source.text
            words = self.doc_words(source)
            spans = (
                iter_doc_sents(source)
                if source.has_annotation("SENT_START")
                else self.iter_sents(self.text)
            )
            sents = get_text_sents(spans, words)
        elif isinstance(source, str):
            self.text = source
            words = [Word(start, end, text) for start, end, text in self.iter_words(source)]
            sents = get_text_sents(self.iter_sents(source), words)
        else:
            raise SourceTypeError("The data source is set incorrectly")
        if not words:
            raise SourceError("The data source has no words")
        available = [
            layer
            for layer in self.layers_desc
            if all(
                doc is not None and doc.has_annotation(annotation)
                for annotation in self.layer_annotations.get(layer, ())
            )
        ]
        self.layers = self.select_layers(layers, available)
        highlights = []
        for layer in self.layers:
            for h in self.find(layer, words, sents, doc):
                if h.layer != layer:
                    raise ValueError(f"A fragment of the layer {h.layer} is found for {layer}")
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

    @classmethod
    def select_layers(
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
        if layers is None:
            return tuple(layer for layer in cls.default_layers if layer in available)
        if isinstance(layers, str):
            if layers == "all":
                return tuple(available)
            layers = [layers]
        try:
            layers = list(layers)
        except TypeError as e:
            raise ParameterError("The layers must be a list of names or a string") from e
        for layer in layers:
            if not isinstance(layer, str) or layer not in cls.layers_desc:
                raise ParameterError(f"Unknown layer of the highlighting: {layer}")
            if layer not in available:
                needs = [
                    ANNOTATION_NAMES.get(annotation, annotation)
                    for annotation in cls.layer_annotations.get(layer, ())
                ]
                if not needs:
                    raise ParameterError(f"The layer {layer} is not available")
                listed = (
                    ", ".join(needs[:-1]) + " and " + needs[-1] if len(needs) > 1 else needs[0]
                )
                raise ParameterError(f"The layer {layer} needs a Doc with {listed}")
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
        The words of iter_doc_tokens, with the part of speech and the lemma when
        the Doc has both

    Arguments:
        doc (Doc): Doc object

    Returns:
        list[Word]: Words with their positions
    """
    tagged = doc.has_annotation("POS") and doc.has_annotation("LEMMA")
    return [
        Word(
            token.idx,
            token.idx + len(token),
            token.text,
            token.pos_ if tagged else None,
            token.lemma_ if tagged else None,
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
    for sent in doc.sents:
        tokens = [token for token in sent if not token.is_space]
        if tokens:
            start = min(token.idx for token in tokens)
            end = max(token.idx + len(token) for token in tokens)
            yield start, end, doc.text[start:end]


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
    sents = []
    index = 0
    for start, end, _ in spans:
        n_words = 0
        while index < len(words) and words[index].start < end:
            n_words += words[index].start >= start
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
    groups: list[list[Word]] = [[] for _ in sents]
    index = 0
    for word in words:
        while index < len(sents) and sents[index].end <= word.start:
            index += 1
        if index < len(sents) and sents[index].start <= word.start:
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
