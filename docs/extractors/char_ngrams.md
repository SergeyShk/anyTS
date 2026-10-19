# Character N-gram extraction

``` {.python .signature}
CharNgramsExtractor(n=2, lowercase=False, within_words=False, tokenizer=None)
```

<!-- --8<-- [start:CharNgramsExtractor] -->
A class for extracting character N-grams from a text - sequences of N characters taken with a sliding window over the string. Character N-grams are a standard feature of stylometry and authorship attribution (Stamatatos 2009) and can replace words in measures such as Burrows's Delta.

Whitespace runs are collapsed into a single space, punctuation marks are kept. With `within_words=True` N-grams do not cross word boundaries: the text is split into words by the tokenizer, punctuation is dropped, and words shorter than N yield no N-grams.

Raises:

- `ParameterError` - an `n` that is not an integer of at least one.
<!-- --8<-- [end:CharNgramsExtractor] -->

=== "Code"

    ``` python
    from anyts import CharNgramsExtractor

    text = "The cat slept  on the sill, and the dog - on the floor."

    ce = CharNgramsExtractor(n=3, lowercase=True)
    ce.extract(text)[:6]
    CharNgramsExtractor(n=4, lowercase=True, within_words=True).extract(text)
    ```

=== "Result"

    ```
    ('the', 'he ', 'e c', ' ca', 'cat', 'at ')
    ('slep', 'lept', 'sill', 'floo', 'loor')
    ```

## Parameters

<!-- --8<-- [start:CharNgramsExtractor-parameters] -->
| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `n` | `int` | `2` | N-gram length in characters |
| `lowercase` | `bool` | `False` | Convert the text to lower case |
| `within_words` | `bool` | `False` | Take N-grams only inside words |
| `tokenizer` | `Pattern` / `Callable` | `None` | Word tokenizer for `within_words` or a regular expression; by default the `tokenize` method |
<!-- --8<-- [end:CharNgramsExtractor-parameters] -->

## Methods

<!-- --8<-- [start:CharNgramsExtractor-extract] -->
`extract(text)` extracts N-grams from a text.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `str` | - | Text string |

A text that is not a string raises `SourceTypeError`, and so does, with `within_words`, a tokenizer that cannot be called or does not return strings.
<!-- --8<-- [end:CharNgramsExtractor-extract] -->

<!-- --8<-- [start:CharNgramsExtractor-get_most_common] -->
`get_most_common(n=10)` returns the top N-grams of the text as a list of (N-gram, frequency) pairs, the most frequent first.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `n` | `int` | `10` | Number of top N-grams |

A number that is not an integer of at least one raises `ParameterError`.

!!! warning "Warning"
    The method must be called after N-grams have been extracted with `extract`.
<!-- --8<-- [end:CharNgramsExtractor-get_most_common] -->

=== "Code"

    ``` python
    ce.get_most_common(2)
    ```

=== "Result"

    ```
    [('the', 4), ('he ', 4)]
    ```

## For library developers { #hooks }

<details class="library-hooks" markdown>
<summary>Language hooks of a subclass</summary>

<!-- --8<-- [start:CharNgramsExtractor-hooks] -->
The default word tokenizer for `within_words` is the method `tokenize(text)`, which a language library overrides in a subclass. In the core it is the default tokenizer of `WordsExtractor`: a word character `\w` followed by word characters, combining marks, zero-width joiners and non-joiners and soft hyphens, so `don't` gives the words `don` and `t`. The messages of its errors come from the class attribute `messages`, `MESSAGES` by default.
<!-- --8<-- [end:CharNgramsExtractor-hooks] -->

</details>
