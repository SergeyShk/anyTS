# Sentence extraction

!!! info ""
    **anyts.extractors.SentsExtractor**

## Description

<!-- --8<-- [start:SentsExtractor] -->
A class for extracting sentences from a text. It allows using different tokenizers and setting the minimum and maximum length of extracted sentences.
<!-- --8<-- [end:SentsExtractor] -->

## Language hooks

<!-- --8<-- [start:SentsExtractor-hooks] -->
The default tokenizer is the method `sentenize(text)`, which a language library overrides in a subclass. Here it splits the text at whitespace after `.`, `!`, `?` or `…`, optionally followed by a closing quote or bracket; it knows no abbreviations, so `e.g. this` is two sentences.
<!-- --8<-- [end:SentsExtractor-hooks] -->

!!! note "Note"
    A spaCy pipeline can be passed as the tokenizer: `tokenizer=lambda text: (sent.text for sent in nlp(text).sents)`.

## Parameters

<!-- --8<-- [start:SentsExtractor-parameters] -->
| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `tokenizer` | Pattern/Callable | `None` | Tokenizer or regular expression; by default the `sentenize` method |
| `min_len` | int | `0` | Minimum length of an extracted sentence, `0` for no bound |
| `max_len` | int | `0` | Maximum length of an extracted sentence, `0` for no bound |

!!! note "Note"
    A regular expression as the tokenizer is a separator: the text is split with `re.split`. Empty and whitespace-only sentences are dropped.
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
