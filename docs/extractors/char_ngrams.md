# Character N-gram extraction

!!! info ""
    **anyts.extractors.CharNgramsExtractor**

## Description

<!-- --8<-- [start:CharNgramsExtractor] -->
A class for extracting character N-grams from a text - sequences of N characters taken with a sliding window over the string. Character N-grams are a standard feature of stylometry and authorship attribution (Stamatatos 2009) and can replace words in measures such as Burrows's Delta.

Whitespace runs are collapsed into a single space, punctuation marks are kept. With `within_words=True` N-grams do not cross word boundaries: the text is split into words by the tokenizer, punctuation is dropped, and words shorter than N yield no N-grams.
<!-- --8<-- [end:CharNgramsExtractor] -->

## Language hooks

<!-- --8<-- [start:CharNgramsExtractor-hooks] -->
The default word tokenizer for `within_words` is the method `tokenize(text)`, which a language library overrides in a subclass. Here it is the default tokenizer of `WordsExtractor`: a word character `\w` followed by word characters, combining marks, zero-width joiners and non-joiners and soft hyphens, so `don't` gives the words `don` and `t`. The messages of its errors come from the class attribute `messages`, `MESSAGES` by default.
<!-- --8<-- [end:CharNgramsExtractor-hooks] -->

## Parameters

<!-- --8<-- [start:CharNgramsExtractor-parameters] -->
| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `n` | int | `2` | N-gram length in characters |
| `lowercase` | bool | `False` | Convert the text to lower case |
| `within_words` | bool | `False` | Take N-grams only inside words |
| `tokenizer` | Pattern/Callable | `None` | Word tokenizer for `within_words` or a regular expression; by default the `tokenize` method |

An `n` that is not an integer of at least one raises `ParameterError`.
<!-- --8<-- [end:CharNgramsExtractor-parameters] -->

## Methods

### extract

<!-- --8<-- [start:CharNgramsExtractor-extract] -->
Extracts N-grams from a text.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | str | `-` | Text string |

A text that is not a string raises `SourceTypeError`, and so does, with `within_words`, a tokenizer that cannot be called or does not return strings.
<!-- --8<-- [end:CharNgramsExtractor-extract] -->

!!! example "Example"

    _Code_:

    ``` python
    from anyts import CharNgramsExtractor

    text = "The cat slept  on the sill, and the dog - on the floor."

    CharNgramsExtractor(n=3, lowercase=True).extract(text)[:6]
    ```

    _Result_:

    ``` bash
    ('the', 'he ', 'e c', ' ca', 'cat', 'at ')
    ```

N-grams inside words only:

!!! example "Example"

    _Code_:

    ``` python
    CharNgramsExtractor(n=4, lowercase=True, within_words=True).extract(text)
    ```

    _Result_:

    ``` bash
    ('slep', 'lept', 'sill', 'floo', 'loor')
    ```

### get_most_common

<!-- --8<-- [start:CharNgramsExtractor-get_most_common] -->
Returns the top N-grams of the text as a list of (N-gram, frequency) pairs, the most frequent first; a number that is not an integer of at least one raises `ParameterError`.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `n` | int | `10` | Number of top N-grams |

!!! warning "Warning"
    The method must be called after N-grams have been extracted with `extract`.
<!-- --8<-- [end:CharNgramsExtractor-get_most_common] -->

!!! example "Example"

    _Code_:

    ``` python
    ce = CharNgramsExtractor(n=3, lowercase=True)
    ce.extract(text)
    ce.get_most_common(2)
    ```

    _Result_:

    ``` bash
    [('the', 4), ('he ', 4)]
    ```
