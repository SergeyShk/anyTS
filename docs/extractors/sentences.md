# Sentence extraction

!!! info ""
    **anyts.extractors.SentsExtractor**

## Description

<!-- --8<-- [start:SentsExtractor] -->
A class for extracting sentences from a text. It allows using different tokenizers and setting the minimum and maximum length of extracted sentences.
<!-- --8<-- [end:SentsExtractor] -->

## Language hooks

<!-- --8<-- [start:SentsExtractor-hooks] -->
The default tokenizer is the method `sentenize(text)`, which a language library overrides in a subclass. Here it splits the text at whitespace after `.`, `!`, `?` or `…`, optionally followed by a closing quote or bracket; it knows no abbreviations, so `e.g. this` is two sentences. A piece without words, such as the dots of a spaced ellipsis `. . .` or a lone `!`, stays with the sentence before it, or with the one after it at the start of the text. The messages of its errors come from the class attribute `messages`, `MESSAGES` by default.
<!-- --8<-- [end:SentsExtractor-hooks] -->

<!-- --8<-- [start:SentsExtractor-pipeline] -->
!!! note "Note"
    A spaCy pipeline can be passed as the tokenizer: `tokenizer=lambda text: (sent.text for sent in nlp(text).sents)`.
<!-- --8<-- [end:SentsExtractor-pipeline] -->

## Parameters

<!-- --8<-- [start:SentsExtractor-parameters] -->
| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `tokenizer` | Pattern/Callable | `None` | Tokenizer or regular expression; by default the `sentenize` method |
| `min_len` | int | `0` | Minimum length of an extracted sentence in characters, `0` for no bound |
| `max_len` | int | `0` | Maximum length of an extracted sentence in characters, `0` for no bound |

!!! note "Note"
    A regular expression as the tokenizer is a separator: the text is split with `re.split`. A blank line - a line break, optional whitespace and another line break - ends a sentence of any tokenizer: the text is split at blank lines first and every part goes to the tokenizer, so a heading or a paragraph without a final mark is a sentence of its own, and so is a part without words, such as a line of asterisks between sections, which the statistics leave out as a sentence without words. The sentences of any tokenizer are stripped of whitespace at the edges, before the length bounds, and empty ones are dropped.
<!-- --8<-- [end:SentsExtractor-parameters] -->

## Methods

### extract

<!-- --8<-- [start:SentsExtractor-extract] -->
Extracts sentences from a text.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | str | `-` | Text string |
<!-- --8<-- [end:SentsExtractor-extract] -->

An example of sentence extraction with the default tokenizer:

!!! example "Example"

    _Code_:

    ``` python
    from anyts import SentsExtractor

    SentsExtractor().extract('It rains. Does it? He said "Yes!" Then he left.')
    ```

    _Result_:

    ``` bash
    ('It rains.', 'Does it?', 'He said "Yes!"', 'Then he left.')
    ```

An example of sentence extraction from paragraphs without a final mark:

!!! example "Example"

    _Code_:

    ``` python
    from anyts import SentsExtractor

    SentsExtractor().extract("What is new\n\nFaster import\nFewer bugs\n\nThanks for reading!")
    ```

    _Result_:

    ``` bash
    ('What is new', 'Faster import\nFewer bugs', 'Thanks for reading!')
    ```

An example of sentence extraction with a regular expression as the tokenizer:

!!! example "Example"

    _Code_:

    ``` python
    import re

    from anyts import SentsExtractor

    SentsExtractor(tokenizer=re.compile(r", ")).extract("Rain today, sun tomorrow")
    ```

    _Result_:

    ``` bash
    ('Rain today', 'sun tomorrow')
    ```

## Ready sentences { #FixedSentsExtractor }

<!-- --8<-- [start:FixedSentsExtractor] -->
`FixedSentsExtractor(sents)` of `anyts.extractors` gives the sentences it was made with for any text: a class that takes a sentence extractor gets the sentences already known, and the text is not split twice. Sentences that are not a list of strings raise `SourceTypeError`.
<!-- --8<-- [end:FixedSentsExtractor] -->
