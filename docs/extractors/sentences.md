# Sentence extraction

``` {.python .signature}
SentsExtractor(tokenizer=None, min_len=0, max_len=0)
```

<!-- --8<-- [start:SentsExtractor] -->
A class for extracting sentences from a text.

Raises:

- `ParameterError` - a length bound that is not an integer, a negative bound, a minimum above the maximum.
<!-- --8<-- [end:SentsExtractor] -->

=== "Code"

    ``` python
    from anyts import SentsExtractor

    SentsExtractor().extract('It rains. Does it? He said "Yes!" Then he left.')
    ```

=== "Result"

    ```
    ('It rains.', 'Does it?', 'He said "Yes!"', 'Then he left.')
    ```

## Parameters

<!-- --8<-- [start:SentsExtractor-parameters] -->
| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `tokenizer` | `Pattern` / `Callable` | `None` | Tokenizer or regular expression; by default the `sentenize` method |
| `min_len` | `int` | `0` | Minimum length of an extracted sentence in characters, `0` for no bound |
| `max_len` | `int` | `0` | Maximum length of an extracted sentence in characters, `0` for no bound |

!!! note "Note"
    A regular expression as the tokenizer is a separator for `re.split`. A blank line - a line break, optional whitespace and another line break - ends a sentence of any tokenizer: the text is split at blank lines first and every part goes to the tokenizer, so a heading or a paragraph without a final mark is a sentence of its own, and so is a part without words, such as a line of asterisks, which the statistics leave out. The sentences are stripped of whitespace at the edges before the length bounds, and empty ones are dropped.
<!-- --8<-- [end:SentsExtractor-parameters] -->

<!-- --8<-- [start:SentsExtractor-pipeline] -->
!!! note "Note"
    A spaCy pipeline can be passed as the tokenizer: `tokenizer=lambda text: (sent.text for sent in nlp(text).sents)`.
<!-- --8<-- [end:SentsExtractor-pipeline] -->

## Methods

<!-- --8<-- [start:SentsExtractor-extract] -->
`extract(text)` extracts sentences from a text.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `str` | - | Text string |

A text that is not a string and a tokenizer that cannot be called or does not return strings raise `SourceTypeError`.
<!-- --8<-- [end:SentsExtractor-extract] -->

=== "Code"

    ``` python
    import re

    SentsExtractor().extract("What is new\n\nFaster import\nFewer bugs\n\nThanks for reading!")
    SentsExtractor(tokenizer=re.compile(r", ")).extract("Rain today, sun tomorrow")
    ```

=== "Result"

    ```
    ('What is new', 'Faster import\nFewer bugs', 'Thanks for reading!')
    ('Rain today', 'sun tomorrow')
    ```

## Sentences of the parts of a text { #iter_part_sents }

<!-- --8<-- [start:iter_part_sents] -->
``` {.python .signature}
iter_part_sents(iter_sents, text)
```

Runs the splitter `iter_sents` on every part of a text between blank lines (`BLANK_LINE`) and gives the sentences at their positions in the whole text, so that a blank line ends a sentence whatever the splitter, as in `SentsExtractor`.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `iter_sents` | `Callable` | - | Splitter giving the start, the end and the text of every sentence of a string |
| `text` | `str` | - | Text string |

A text that is not a string raises `SourceTypeError`, and so does an `iter_sents` that cannot be called or does not give the sentences of a part in order, as triples of integer bounds within it and a string.
<!-- --8<-- [end:iter_part_sents] -->

=== "Code"

    ``` python
    import re

    from anyts.extractors import iter_part_sents


    def periods(text):
        return [(m.start(), m.end(), m.group()) for m in re.finditer(r"[^.\s][^.]*\.?", text)]


    list(iter_part_sents(periods, "One. Two\n\nThree."))
    ```

=== "Result"

    ```
    [(0, 4, 'One.'), (5, 8, 'Two'), (10, 16, 'Three.')]
    ```

## Ready sentences { #FixedSentsExtractor }

<!-- --8<-- [start:FixedSentsExtractor] -->
``` {.python .signature}
FixedSentsExtractor(sents)
```

A `SentsExtractor` that gives the sentences it was made with for any text, so a class that takes a sentence extractor gets known sentences without splitting the text again.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `sents` | `list[str]` | - | Sentences |

Sentences that are not a list of strings raise `SourceTypeError`.
<!-- --8<-- [end:FixedSentsExtractor] -->

=== "Code"

    ``` python
    from anyts.extractors import FixedSentsExtractor

    FixedSentsExtractor(["It rains.", "Yes!"]).extract("any text")
    ```

=== "Result"

    ```
    ('It rains.', 'Yes!')
    ```

## For library developers { #hooks }

<details class="library-hooks" markdown>
<summary>Language hooks of a subclass</summary>

<!-- --8<-- [start:SentsExtractor-hooks] -->
The default tokenizer is the method `sentenize(text)`, which a language library overrides in a subclass. In the core it splits the text at whitespace after `.`, `!`, `?` or `…`, optionally followed by a closing quote or bracket; it knows no abbreviations, so `e.g. this` is two sentences. A piece without words, such as the dots of a spaced ellipsis `. . .` or a lone `!`, stays with the sentence before it, or with the one after it at the start of the text. The messages of its errors come from the class attribute `messages`, `MESSAGES` by default.
<!-- --8<-- [end:SentsExtractor-hooks] -->

</details>
