# Text highlighting

!!! info ""
    **anyts.visualizers.HighlightedText**, **anyts.visualizers.Highlight**

## Description

<!-- --8<-- [start:HighlightedText] -->
The machinery of the highlighting of a text by layers, in the manner of the style checkers: every layer marks the fragments of a text that a statistic counts - long sentences, complex words, the passive. The data source can be either a text or a `Doc` object of [spaCy](https://github.com/explosion/spaCy). The result shows in Jupyter as HTML with styles and a legend; the method `to_html` returns the same markup for documentation and web applications, and the fragments are kept in the attribute `highlights` for a rendering of one's own. Fragments of different layers may overlap.
<!-- --8<-- [end:HighlightedText] -->

## Language hooks

<!-- --8<-- [start:HighlightedText-hooks] -->
The core has no layers of its own: a language library subclasses `HighlightedText` and sets its layers and their search.

| Hook | Kind | Description |
| :--: | :--: | :---------: |
| `layers_desc` | dict[str, str] | The layers in the order of drawing with their names in the legend |
| `default_layers` | tuple[str] | The layers on by default, among those the source allows |
| `layer_annotations` | dict[str, tuple[str]] | The annotations of a `Doc` a layer needs (`DEP`, `POS`, `LEMMA`...); a layer without them is available for a string too |
| `layer_styles` | dict[str, str] | The CSS declarations of every layer; the text of a layer with a background keeps a dark colour on it |
| `css_prefix` | str | The prefix of the CSS classes, `anyts` by default |
| `find(layer, words, sents, doc)` | method | The fragments of a layer: a list of `Highlight` from the words and the sentences of the text and the `Doc` (`None` for a string) |
| `iter_words(text)`, `iter_sents(text)` | methods | The words and the sentences of a string as triples of the start, the end and the text; by default those of the default tokenizers of `WordsExtractor` and `SentsExtractor` |
| `doc_words(doc)` | method | The words of a `Doc`; by default `get_doc_words` |

The sentences of a `Doc` come from its boundaries, or from `iter_sents` over its text when it has none, and the words of a sentence are those of `doc_words` or `iter_words` that start in it. `find` runs in `__init__`, so a subclass with parameters of its own stores them before it calls the `__init__` of the base; a fragment of another layer raises `ValueError`.
<!-- --8<-- [end:HighlightedText-hooks] -->

## Parameters

<!-- --8<-- [start:HighlightedText-parameters] -->
| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `source` | str/Doc | `-` | Data source (a string or a Doc object) |
| `layers` | list[str]/str | `None` | Layers of the highlighting; if not given, the default layers the source allows; `"all"` - every layer allowed |

A source that is neither a string nor a `Doc` raises `SourceTypeError`, a source without words `SourceError`; layers that are not a name or a list of names, a layer that is unknown or one that needs an annotation the source lacks raise `ParameterError`.
<!-- --8<-- [end:HighlightedText-parameters] -->

## Attributes

<!-- --8<-- [start:HighlightedText-attributes] -->
| Attribute | Type | Description |
| :-------: | :--: | :---------: |
| `text` | str | Text of the data source |
| `layers` | tuple[str] | Layers turned on, in the order of drawing |
| `highlights` | tuple[Highlight] | Highlighted fragments, sorted by their start and then by descending end |
| `counts` | dict[str, int] | Number of fragments of every layer |
<!-- --8<-- [end:HighlightedText-attributes] -->

<!-- --8<-- [start:Highlight] -->
A `Highlight` fragment is an immutable object with the fields `start` and `end` (positions in the text), `layer` (the layer) and `note` (the explanation for the tooltip).
<!-- --8<-- [end:Highlight] -->

## Methods

### to_html

<!-- --8<-- [start:HighlightedText-to_html] -->
Returns the HTML markup of the highlighted text: a `div` of the class `<prefix>-highlight` with the legend and its counts and the text, where the highlighted segments are wrapped in a `span` of the classes `<prefix>-hl` and `<prefix>-hl-<layer>`, the notes going to the attribute `title`; `<prefix>` is the prefix of the CSS classes. Overlapping fragments of different layers give segments with several classes, in the order of drawing. Line breaks (`\n`, `\r\n`, `\r`) are kept as character references, one per break, so the markup can be put into Markdown.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `legend` | bool | `True` | Add the legend with the counts of the fragments |
| `css` | bool | `True` | Add the styles of the layers |
<!-- --8<-- [end:HighlightedText-to_html] -->

### css

<!-- --8<-- [start:HighlightedText-css] -->
The class method `css()` returns the styles `to_html` adds: the container, the legend and the text under the classes of `css_prefix`, the declarations of `layer_styles` for every layer, and a dark colour of the text on the layers with a background.
<!-- --8<-- [end:HighlightedText-css] -->

## Helpers of the layers

<!-- --8<-- [start:Word] -->
`Word(start, end, text, pos=None, lemma=None)` - a word with its position in the text and, when known, its part of speech and lemma.
<!-- --8<-- [end:Word] -->

<!-- --8<-- [start:Sent] -->
`Sent(start, end, n_words)` - a sentence with its position and number of words.
<!-- --8<-- [end:Sent] -->

<!-- --8<-- [start:get_doc_words] -->
`get_doc_words(doc)` - the words of `iter_doc_tokens` with their positions, and with the part of speech and the lemma when the `Doc` has both.
<!-- --8<-- [end:get_doc_words] -->

<!-- --8<-- [start:iter_doc_sents] -->
`iter_doc_sents(doc)` - the sentences of the boundaries of a `Doc` as triples of the start, the end and the text; the whitespace tokens at the edges of a sentence are left out, and a sentence of whitespace alone is skipped.
<!-- --8<-- [end:iter_doc_sents] -->

<!-- --8<-- [start:get_text_sents] -->
`get_text_sents(spans, words)` - the sentences given by their positions with their numbers of words; a word belongs to the sentence of its first character.
<!-- --8<-- [end:get_text_sents] -->

<!-- --8<-- [start:group_words_by_sents] -->
`group_words_by_sents(words, sents)` - the words of every sentence; the words out of the sentences are skipped.
<!-- --8<-- [end:group_words_by_sents] -->

<!-- --8<-- [start:tokens_span] -->
`tokens_span(tokens)` - the positions of the fragment that covers some tokens, without the punctuation and the whitespace at its edges.
<!-- --8<-- [end:tokens_span] -->

<!-- --8<-- [start:split_segments] -->
`split_segments(length, highlights)` - the segments of a text with the same set of fragments: their bounds are the starts and the ends of all the fragments, and overlapping or nested fragments give segments with several layers.
<!-- --8<-- [end:split_segments] -->

## Usage example

A layer of the long sentences in a subclass.

!!! example "Example"

    ``` python
    from anyts.visualizers import Highlight, HighlightedText


    class Highlighter(HighlightedText):
        layers_desc = {"long_sents": "long sentence"}
        default_layers = ("long_sents",)
        layer_styles = {"long_sents": "background: #fef9c3;"}
        css_prefix = "demo"

        def find(self, layer, words, sents, doc):
            return [
                Highlight(sent.start, sent.end, layer, f"{sent.n_words} words")
                for sent in sents
                if sent.n_words >= 8
            ]


    ht = Highlighter("The cat sleeps. The dog barks at the cat that sleeps on the mat.")
    ht.highlights
    # (Highlight(start=16, end=64, layer='long_sents', note='11 words'),)
    ht.to_html(legend=False, css=False)
    # '<div class="demo-highlight"><div class="demo-highlight-text">The cat sleeps. <span class="demo-hl demo-hl-long_sents" title="11 words">The dog barks at the cat that sleeps on the mat.</span></div></div>'
    ```
