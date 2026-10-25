# Text highlighting

``` {.python .signature}
HighlightedText(source, layers=None)
```

<!-- --8<-- [start:HighlightedText] -->
Highlighting of a text by layers, in the manner of the style checkers: every layer marks the fragments of a text that a statistic counts - long sentences, complex words, the passive. The data source is a text or a `Doc` object of [spaCy](https://github.com/explosion/spaCy). The result shows in Jupyter as HTML with styles and a legend; `to_html` returns the markup, and `highlights` keeps the fragments for a rendering of one's own. Fragments of different layers may overlap.

Raises:

- `SourceTypeError` - a source that is neither a string nor a `Doc`;
- `SourceError` - a source without words;
- `ParameterError` - layers that are not a name or a list of names, a layer that is unknown or one that needs an annotation the source lacks.
<!-- --8<-- [end:HighlightedText] -->

A layer of the long sentences in a subclass.

=== "Code"

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
    ```

=== "Result"

    ```
    (Highlight(start=16, end=64, layer='long_sents', note='11 words'),)
    ```

## Parameters

<!-- --8<-- [start:HighlightedText-parameters] -->
| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `source` | `str` / `Doc` | - | Data source (a string or a Doc object) |
| `layers` | `list[str]` / `str` | `None` | Layers of the highlighting; if not given, the default layers the source allows; `"all"` - every layer allowed |
<!-- --8<-- [end:HighlightedText-parameters] -->

## Attributes

<!-- --8<-- [start:HighlightedText-attributes] -->
| Attribute | Type | Description |
| :-------- | :--- | :---------- |
| `text` | `str` | Text of the data source |
| `layers` | `tuple[str]` | Layers turned on, in the order of drawing |
| `highlights` | `tuple[Highlight]` | Highlighted fragments, sorted by their start and then by descending end |
| `counts` | `dict[str, int]` | Number of fragments of every layer |
<!-- --8<-- [end:HighlightedText-attributes] -->

<!-- --8<-- [start:Highlight] -->
``` {.python .signature}
Highlight(start, end, layer, note='')
```

A fragment of the highlighting: an immutable object with the parameters as its fields.

| Field | Type | Default | Description |
| :---- | :--- | :------ | :---------- |
| `start` | `int` | - | Position of the first character of the fragment in the text |
| `end` | `int` | - | Position after the last character of the fragment |
| `layer` | `str` | - | Layer of the highlighting |
| `note` | `str` | `''` | Explanation of the fragment for the tooltip |
<!-- --8<-- [end:Highlight] -->

## Methods

<!-- --8<-- [start:HighlightedText-to_html] -->
`to_html(legend=True, css=True)` returns the HTML markup of the highlighted text: a `div` of the class `<prefix>-highlight` with the legend, its counts and the text, where a highlighted segment is a `span` of the classes `<prefix>-hl` and `<prefix>-hl-<layer>` with the notes in its `title`; `<prefix>` is `css_prefix`. Overlapping fragments of different layers give segments with several classes, in the order of drawing. Line breaks (`\n`, `\r\n`, `\r`) become character references, one per break, so the markup can go into Markdown.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `legend` | `bool` | `True` | Add the legend with the counts of the fragments |
| `css` | `bool` | `True` | Add the styles of the layers |
<!-- --8<-- [end:HighlightedText-to_html] -->

<!-- --8<-- [start:HighlightedText-css] -->
The class method `css()` returns the styles `to_html` adds: the container, the legend and the text under the classes of `css_prefix`, the declarations of `layer_styles` for every layer, and a dark colour of the text on the layers with a background.
<!-- --8<-- [end:HighlightedText-css] -->

=== "Code"

    ``` python
    ht.to_html(legend=False, css=False)
    ```

=== "Result"

    ```
    '<div class="demo-highlight"><div class="demo-highlight-text">The cat sleeps. <span class="demo-hl demo-hl-long_sents" title="11 words">The dog barks at the cat that sleeps on the mat.</span></div></div>'
    ```

## Helpers of the layers

The helpers and the finders of the layers are in `anyts.visualizers.highlight`.

<!-- --8<-- [start:Word] -->
``` {.python .signature}
Word(start, end, text, pos=None, lemma=None)
```

A word with its position in the text and, when known, its part of speech and lemma.
<!-- --8<-- [end:Word] -->

<!-- --8<-- [start:Sent] -->
``` {.python .signature}
Sent(start, end, n_words)
```

A sentence with its position and number of words.
<!-- --8<-- [end:Sent] -->

<!-- --8<-- [start:get_doc_words] -->
``` {.python .signature}
get_doc_words(doc)
```

The words of `iter_doc_tokens` with their positions, a byte order mark at the start of the text left out, with the part of speech and the lemma when the `Doc` has them.
<!-- --8<-- [end:get_doc_words] -->

<!-- --8<-- [start:iter_doc_sents] -->
``` {.python .signature}
iter_doc_sents(doc)
```

The sentences of the boundaries of a `Doc` as triples of the start, the end and the text; the whitespace tokens at the edges of a sentence are left out, and a sentence of whitespace alone is skipped.
<!-- --8<-- [end:iter_doc_sents] -->

<!-- --8<-- [start:get_text_sents] -->
``` {.python .signature}
get_text_sents(spans, words)
```

The sentences given by their positions with their numbers of words; a word belongs to the sentence of its first character.
<!-- --8<-- [end:get_text_sents] -->

<!-- --8<-- [start:group_words_by_sents] -->
``` {.python .signature}
group_words_by_sents(words, sents)
```

The words of every sentence; the words out of the sentences are skipped.
<!-- --8<-- [end:group_words_by_sents] -->

<!-- --8<-- [start:tokens_span] -->
``` {.python .signature}
tokens_span(tokens)
```

The positions of the fragment that covers some tokens, without the punctuation and the whitespace at its edges.
<!-- --8<-- [end:tokens_span] -->

<!-- --8<-- [start:split_segments] -->
``` {.python .signature}
split_segments(length, highlights)
```

The segments of a text with the same set of fragments: their bounds are the starts and the ends of all the fragments, and overlapping or nested fragments give segments with several layers.
<!-- --8<-- [end:split_segments] -->

## Finders of the layers { #finders }

<!-- --8<-- [start:highlight-finders] -->
The layers the languages share are found by functions that take the language as parameters: the notes of the fragments (callables where they read a number, so a language writes its plural forms; English by default), the counts of syllables, the normalized forms of the words, the stems, the matcher of the connectors. A subclass calls them from its `find`. A value that cannot be called for a parameter that takes a function, such as `count_syllables`, `normalize` or `stem`, raises `SourceTypeError`.
<!-- --8<-- [end:highlight-finders] -->

### Long sentences { #find_long_sents }

<!-- --8<-- [start:find_long_sents] -->
``` {.python .signature}
find_long_sents(sents, long_sent_word_factor, note=None)
```

The layer `long_sents`: the sentences of `long_sent_word_factor` words or more.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `sents` | `list[Sent]` | - | Sentences with their positions and numbers of words |
| `long_sent_word_factor` | `int` | - | Minimum number of words of a long sentence |
| `note` | `Callable[[int], str]` | `None` | Note of a sentence by its number of words |

A `long_sent_word_factor` that is not an integer of at least one raises `ParameterError`.
<!-- --8<-- [end:find_long_sents] -->

### Complex words { #find_complex_words }

<!-- --8<-- [start:find_complex_words] -->
``` {.python .signature}
find_complex_words(words, complex_syl_factor, count_syllables, note=None)
```

The layer `complex_words`: the words of `complex_syl_factor` syllables of `count_syllables` or more.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `words` | `list[Word]` | - | Words with their positions |
| `complex_syl_factor` | `int` | - | Minimum number of syllables of a complex word |
| `count_syllables` | `Callable[[str], int]` | - | Number of the syllables of a word |
| `note` | `Callable[[int], str]` | `None` | Note of a word by its number of syllables |

A `complex_syl_factor` that is not an integer of at least one raises `ParameterError`.
<!-- --8<-- [end:find_complex_words] -->

### Single words { #find_words }

<!-- --8<-- [start:find_words] -->
``` {.python .signature}
find_words(words, is_match, layer, note='')
```

A layer of single words, such as stopwords, rare words or verbal nouns: the words the check `is_match` of a language accepts.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `words` | `list[Word]` | - | Words with their positions, parts of speech and lemmas |
| `is_match` | `Callable[[Word], bool]` | - | Whether a word is a fragment of the layer |
| `layer` | `str` | - | Layer of the highlighting |
| `note` | `str` | `''` | Note of every fragment |
<!-- --8<-- [end:find_words] -->

### Phrases { #find_phrase_highlights }

<!-- --8<-- [start:find_phrase_highlights] -->
``` {.python .signature}
find_phrase_highlights(words, phrases, layer, note=None, normalize=str.lower)
```

A layer of the phrases of a list, such as compound prepositions, clichés or parentheticals. The phrases are matched by the normalized forms of their words, each normalized alone as in the text (`find_phrases`). A mapping gives their variants - contractions, forms of verbs - with the phrase each stands for; of the variants that normalize alike the first wins. A set of phrases is read in order (`in_order`). A fragment spans the phrase in the text; its note reads the phrase of the list, in quotes by default.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `words` | `list[Word]` | - | Words with their positions |
| `phrases` | `list[str]` / `dict[str, str]` | - | Phrases, words separated by spaces, or their variants with the phrase of each |
| `layer` | `str` | - | Layer of the highlighting |
| `note` | `Callable[[str], str]` | `None` | Note of a fragment by its phrase |
| `normalize` | `Callable[[str], str]` | `str.lower` | Normalized form of a word |

Phrases that are not a collection of strings or a mapping of strings raise `SourceTypeError`.
<!-- --8<-- [end:find_phrase_highlights] -->

### Connectors { #find_connector_highlights }

<!-- --8<-- [start:find_connector_highlights] -->
``` {.python .signature}
find_connector_highlights(words, sents, matcher, note=None, pos=None, text=None, blocked=None)
```

The layer `connectors`: the connectors of a `ConnectorMatcher` of the language inside every sentence, in the whole text when the sentences are `None`; a one-word connector is checked by its part of speech when a word of the sentence has one - its own, or that of the hook `pos`. With the `text`, a character of `is_punctuation` between two words is a punctuation mark, which the rules of the matcher do not read through; a quote, an apostrophe and the hyphen that joins two parts of a word are none. No connector starts at a word the hook `blocked` rules out, such as one its parse makes no connector. The note gives the text, the class and the kind of the connector by default.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `words` | `list[Word]` | - | Words with their positions and parts of speech |
| `sents` | `list[Sent]` | - | Sentences with their positions |
| `matcher` | `ConnectorMatcher` | - | Matcher of the connectors of a language |
| `note` | `Callable[[Connector], str]` | `None` | Note of a connector |
| `pos` | `Callable[[Word], str]` | `None` | Part of speech of a word for the matcher |
| `text` | `str` | `None` | Text of the words, for the punctuation marks between them |
| `blocked` | `Callable[[Word], bool]` | `None` | Whether no connector starts at a word |

A hook that cannot be called or a `text` that is not a string raises `SourceTypeError`.
<!-- --8<-- [end:find_connector_highlights] -->

### Split predicates { #find_split_predicate_highlights }

<!-- --8<-- [start:find_split_predicate_highlights] -->
``` {.python .signature}
find_split_predicate_highlights(pairs, note=None)
```

The layer `split_predicates`: a fragment for every pair of a light verb and its noun a language finds, from the first word of the pair to the last; the note reads their lemmas by default.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `pairs` | `list[tuple[Token, Token]]` | - | Light verb and noun of every split predicate |
| `note` | `Callable[[Token, Token], str]` | `None` | Note of a pair |
<!-- --8<-- [end:find_split_predicate_highlights] -->

### Runs of alliteration { #calc_alliteration_runs }

<!-- --8<-- [start:calc_alliteration_runs] -->
``` {.python .signature}
calc_alliteration_runs(words, frequencies, threshold=0.001, stem=list, is_transparent=None)
```

The runs of two or more neighbouring words with a consonant of `frequencies` in the stem of each (the stem of a language leaves out the endings that repeat by agreement) and a probability below the threshold. The probability under an independent spread of the consonants is the product over the words of $1 - (1 - f)^n$, $f$ the frequency of the consonant and $n$ the length of the stem. A transparent word - by default one shorter than `ALLITERATION_MIN_WORD_LEN` (3) letters, a stopword for a language - neither breaks nor continues a run; the words are taken in lower case. A run is a triple of the index of its first word, the index after its last word and its consonant, in the order of the text.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `words` | `list[str]` | - | Words of a sentence |
| `frequencies` | `dict[str, float]` | - | Consonants to look for with their frequencies |
| `threshold` | `float` | `0.001` | Probability threshold (`anyts.constants.ALLITERATION_THRESHOLD`) |
| `stem` | `Callable[[str], list[str]]` | `list` | Sounds or letters of the stem of a word; the letters of the word by default |
| `is_transparent` | `Callable[[str], bool]` | `None` | Whether a word neither breaks nor continues a run |

Words that are not a list of strings and frequencies that are not a mapping of strings to numbers raise `SourceTypeError`, and a frequency outside [0, 1] or a threshold outside (0, 1] `ParameterError`.
<!-- --8<-- [end:calc_alliteration_runs] -->

### Alliteration { #find_alliteration }

<!-- --8<-- [start:find_alliteration] -->
``` {.python .signature}
find_alliteration(words, sents, frequencies, threshold=0.001, stem=list, is_transparent=None, note=None)
```

The layer `alliteration`: the runs of `calc_alliteration_runs` inside every sentence, in the whole text when the sentences are `None`.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `words` | `list[Word]` | - | Words with their positions |
| `sents` | `list[Sent]` | - | Sentences with their positions |
| `frequencies` | `dict[str, float]` | - | Consonants to look for with their frequencies, as in `calc_alliteration_runs` |
| `threshold` | `float` | `0.001` | Probability threshold (`anyts.constants.ALLITERATION_THRESHOLD`) |
| `stem` | `Callable[[str], list[str]]` | `list` | Sounds or letters of the stem of a word; the letters of the word by default |
| `is_transparent` | `Callable[[str], bool]` | `None` | Whether a word neither breaks nor continues a run |
| `note` | `Callable[[str], str]` | `None` | Note of a run by its consonant |

The frequencies and the threshold raise the errors of `calc_alliteration_runs`.
<!-- --8<-- [end:find_alliteration] -->

## For library developers { #hooks }

<details class="library-hooks" markdown>
<summary>Language hooks of a subclass</summary>

<!-- --8<-- [start:HighlightedText-hooks] -->
The core has no layers of its own: a language library subclasses `HighlightedText` and sets its layers and their search.

| Hook | Kind | Description |
| :--- | :--- | :---------- |
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

<!-- --8<-- [start:HighlightedText-check_params] -->
``` {.python .signature}
check_params(long_sent_word_factor, complex_syl_factor, alliteration_threshold, *, messages=MESSAGES)
```

Checks the parameters of the highlighting: a number of words or syllables that is not an integer of at least one, or a threshold outside the interval (0, 1], raises `ParameterError`.
<!-- --8<-- [end:HighlightedText-check_params] -->

</details>
