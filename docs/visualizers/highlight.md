# Text highlighting

!!! info ""
    **anyts.visualizers.HighlightedText**, **anyts.visualizers.Highlight**; the helpers of the layers are in **anyts.visualizers.highlight**

## Description

<!-- --8<-- [start:HighlightedText] -->
Highlighting of a text by layers, in the manner of the style checkers: every layer marks the fragments of a text that a statistic counts - long sentences, complex words, the passive. The data source is a text or a `Doc` object of [spaCy](https://github.com/explosion/spaCy). The result shows in Jupyter as HTML with styles and a legend; `to_html` returns the markup, and `highlights` keeps the fragments for a rendering of one's own. Fragments of different layers may overlap.
<!-- --8<-- [end:HighlightedText] -->

## Language hooks

<!-- --8<-- [start:HighlightedText-hooks] -->
The core has no layers of its own: a language library subclasses `HighlightedText` and sets its layers and their search.

| Hook | Kind | Description |
| :--: | :--: | :---------: |
| `layers_desc` | class attribute | The layers in the order of drawing with their names in the legend, `dict[str, str]` |
| `default_layers` | class attribute | The layers on by default, among those the source allows, `tuple[str]` |
| `layer_annotations` | class attribute | The annotations of a `Doc` a layer needs (`DEP`, `POS`, `LEMMA`...), `dict[str, tuple[str]]`; a layer without them is available for a string too |
| `layer_styles` | class attribute | The CSS declarations of every layer, `dict[str, str]`; the text of a layer with a background keeps a dark colour on it |
| `css_prefix` | class attribute | The prefix of the CSS classes, `str` |
| `find(layer, words, sents, doc)` | method | The fragments of a layer: a list of `Highlight` from the words and the sentences of the text and the `Doc` (`None` for a string) |
| `iter_words(text)`, `iter_sents(text)` | methods | The words and the sentences of a string as triples of the start, the end and the text; by default those of the default tokenizers of `WordsExtractor` and `SentsExtractor` |
| `doc_words(doc)` | method | The words of a `Doc`; by default `get_doc_words` |
| `annotation_names` | class attribute | Names of the annotations in the message of a layer a source does not allow, `dict[str, str]`; English by default |
| `messages` | class attribute | Messages of the errors by key; `MESSAGES` by default |

The sentences of a `Doc` come from its boundaries, or from `iter_sents` over its text when it has none or partial ones (`has_sents`). `iter_sents` gets the parts of a text between blank lines one by one, so a blank line always ends a sentence; a sentence holds the words of `doc_words` or `iter_words` that start in it. `find` runs in `__init__`: a subclass stores its own parameters, checked by `check_params`, before calling the `__init__` of the base, and may find its layers with the finders of the layers. A fragment of another layer, an empty one or one outside the text raises `ParameterError`; a `find` that does not return `Highlight` objects, and an `iter_words` or an `iter_sents` whose triples are not ascending integer bounds inside the text with the text of each, `SourceTypeError`.
<!-- --8<-- [end:HighlightedText-hooks] -->

In the core the layers are empty and `css_prefix` is `anyts`.

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
Returns the HTML markup of the highlighted text: a `div` of the class `<prefix>-highlight` with the legend, its counts and the text, where a highlighted segment is a `span` of the classes `<prefix>-hl` and `<prefix>-hl-<layer>` with the notes in its `title`; `<prefix>` is `css_prefix`. Overlapping fragments of different layers give segments with several classes, in the order of drawing. Line breaks (`\n`, `\r\n`, `\r`) become character references, one per break, so the markup can go into Markdown.

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
`get_doc_words(doc)` - the words of `iter_doc_tokens` with their positions, a byte order mark at the start of the text left out, with the part of speech and the lemma when the `Doc` has them.
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

## Finders of the layers { #finders }

<!-- --8<-- [start:highlight-finders] -->
The layers the languages share are found by functions that take the language as parameters: the notes of the fragments (callables where they read a number, so a language writes its plural forms; English by default), the counts of syllables, the normalized forms of the words, the stems, the matcher of the connectors. A subclass calls them from its `find`. A value that cannot be called for a parameter that takes a function, such as `count_syllables`, `normalize` or `stem`, raises `SourceTypeError`.
<!-- --8<-- [end:highlight-finders] -->

<!-- --8<-- [start:find_long_sents] -->
`find_long_sents(sents, long_sent_word_factor, note)` - the layer `long_sents`: the sentences of that number of words or more, the note by their number of words. A `long_sent_word_factor` that is not an integer of at least one raises `ParameterError`.
<!-- --8<-- [end:find_long_sents] -->

<!-- --8<-- [start:find_complex_words] -->
`find_complex_words(words, complex_syl_factor, count_syllables, note)` - the layer `complex_words`: the words of that number of syllables of `count_syllables` or more, the note by their number of syllables. A `complex_syl_factor` that is not an integer of at least one raises `ParameterError`.
<!-- --8<-- [end:find_complex_words] -->

<!-- --8<-- [start:find_words] -->
`find_words(words, is_match, layer, note)` - a layer of single words, such as stopwords, rare words or verbal nouns: the words of the check `is_match` of a language, with one note.
<!-- --8<-- [end:find_words] -->

<!-- --8<-- [start:find_phrase_highlights] -->
`find_phrase_highlights(words, phrases, layer, note, normalize)` - a layer of the phrases of a list, such as compound prepositions, clichés or parentheticals. The phrases are matched by the normalized forms of their words, each normalized alone as in the text (`find_phrases`). A mapping gives their variants - contractions, forms of verbs - with the phrase each stands for; of the variants that normalize alike the first wins. A set of phrases is read in order (`in_order`). A fragment spans the phrase in the text; its note reads the phrase of the list, in quotes by default. Phrases that are not a collection of strings or a mapping of strings raise `SourceTypeError`.
<!-- --8<-- [end:find_phrase_highlights] -->

<!-- --8<-- [start:find_connector_highlights] -->
`find_connector_highlights(words, sents, matcher, note, pos, text)` - the layer `connectors`: the connectors of a `ConnectorMatcher` of the language inside every sentence, in the whole text when the sentences are `None`; a one-word connector is checked by its part of speech when a word of the sentence has one - its own, or that of the hook `pos`. With the `text`, a character of `is_punctuation` between two words is a punctuation mark, which the rules of the matcher do not read through; the hyphen that joins two parts of a word is none. The note gives the class and the kind of the connector by default.
<!-- --8<-- [end:find_connector_highlights] -->

<!-- --8<-- [start:find_split_predicate_highlights] -->
`find_split_predicate_highlights(pairs, note)` - the layer `split_predicates`: a fragment for every pair of a light verb and its noun a language finds, from the first word of the pair to the last; the note reads their lemmas by default.
<!-- --8<-- [end:find_split_predicate_highlights] -->

<!-- --8<-- [start:calc_alliteration_runs] -->
`calc_alliteration_runs(words, frequencies, threshold, stem, is_transparent)` - the runs of two or more neighbouring words with a consonant of `frequencies` in the stem of each (the stem of a language leaves out the endings that repeat by agreement) and a probability below the threshold (`anyts.constants.ALLITERATION_THRESHOLD`, 0.001). The probability under an independent spread of the consonants is the product over the words of $1 - (1 - f)^n$, $f$ the frequency of the consonant and $n$ the length of the stem. A transparent word - by default one shorter than `ALLITERATION_MIN_WORD_LEN` (3) letters, a stopword for a language - neither breaks nor continues a run; the words are taken in lower case. Words that are not a list of strings and frequencies that are not a mapping of strings to numbers raise `SourceTypeError`, and a frequency outside [0, 1] or a threshold outside (0, 1] `ParameterError`.
<!-- --8<-- [end:calc_alliteration_runs] -->

<!-- --8<-- [start:find_alliteration] -->
`find_alliteration(words, sents, frequencies, threshold, stem, is_transparent, note)` - the layer `alliteration`: the runs of `calc_alliteration_runs` inside every sentence, in the whole text when the sentences are `None`, the note by the consonant. The frequencies and the threshold raise the errors of `calc_alliteration_runs`.
<!-- --8<-- [end:find_alliteration] -->

<!-- --8<-- [start:HighlightedText-check_params] -->
`check_params(long_sent_word_factor, complex_syl_factor, alliteration_threshold, *, messages)` checks the parameters of the highlighting: a number of words or syllables that is not an integer of at least one, or a threshold outside the interval (0, 1], raises `ParameterError`.
<!-- --8<-- [end:HighlightedText-check_params] -->

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
