# Word extraction

``` {.python .signature}
WordsExtractor(tokenizer=None, filter_punct=True, filter_nums=False, use_lexemes=False, stopwords=None, lowercase=False, ngram_range=(1, 1), min_len=0, max_len=0)
```

<!-- --8<-- [start:WordsExtractor] -->
A class for extracting words from a text.

Raises:

- `ParameterError` - an `ngram_range` that is not a pair of integers or whose lower bound is below one or above the upper one, a length bound that is not an integer, a negative bound, a minimum above the maximum, a switch that is not a `bool`;
- `SourceTypeError` - stop words that are not a collection of strings.
<!-- --8<-- [end:WordsExtractor] -->

=== "Code"

    ``` python
    from anyts import WordsExtractor

    text = "Better 100 friends than 100 dollars"

    we = WordsExtractor(lowercase=True, stopwords=["than"], filter_nums=True, ngram_range=(1, 2))
    we.extract(text)
    ```

=== "Result"

    ```
    ('better', 'friends', 'dollars', 'better_friends', 'friends_dollars')
    ```

## Parameters

<!-- --8<-- [start:WordsExtractor-parameters] -->
| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `tokenizer` | `Pattern` / `Callable` | `None` | Tokenizer or regular expression; by default the `tokenize` method |
| `filter_punct` | `bool` | `True` | Filter punctuation marks |
| `filter_nums` | `bool` | `False` | Filter numbers matched by `number_pattern` |
| `use_lexemes` | `bool` | `False` | Use word lemmas of the `lemmatize` method |
| `stopwords` | `Collection[str]` | `None` | Stop words, compared case-insensitively |
| `lowercase` | `bool` | `False` | Convert words to lower case |
| `ngram_range` | `tuple[int, int]` | `(1, 1)` | Lower and upper bound of the N-gram size |
| `min_len` | `int` | `0` | Minimum length of an extracted word in characters, `0` for no bound |
| `max_len` | `int` | `0` | Maximum length of an extracted word in characters, `0` for no bound |

!!! note "Note"
    A regular expression as the tokenizer is a separator for `re.split`. The filters are applied in order: punctuation, numbers, lemmatization, lower case, stop words, word length. A punctuation mark is a token of marks and symbols only, multi-character ones included: `?!`, `--`, `…`, `€` (`anyts.utils.is_punctuation`). Empty and whitespace tokens are dropped before the filters. N-grams join the words with `_`.
<!-- --8<-- [end:WordsExtractor-parameters] -->

## Methods

<!-- --8<-- [start:WordsExtractor-extract] -->
`extract(text)` extracts words from a text.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `str` | - | Text string |

A text that is not a string and a tokenizer that cannot be called or does not return strings raise `SourceTypeError`.
<!-- --8<-- [end:WordsExtractor-extract] -->

<!-- --8<-- [start:WordsExtractor-get_most_common] -->
`get_most_common(n=10)` returns the top words of the text as a list of (word, frequency) pairs, the most frequent first.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `n` | `int` | `10` | Number of top words |

A number that is not an integer of at least one raises `ParameterError`.

!!! warning "Warning"
    The method must be called after words have been extracted with `extract`.
<!-- --8<-- [end:WordsExtractor-get_most_common] -->

=== "Code"

    ``` python
    we = WordsExtractor(lowercase=True)
    we.extract("The cat saw the dog and the bird")
    we.get_most_common(2)
    ```

=== "Result"

    ```
    ('the', 'cat', 'saw', 'the', 'dog', 'and', 'the', 'bird')
    [('the', 3), ('cat', 1)]
    ```

## Ready words { #FixedWordsExtractor }

<!-- --8<-- [start:FixedWordsExtractor] -->
``` {.python .signature}
FixedWordsExtractor(words)
```

A `WordsExtractor` that gives the words it was made with for any text, so a class that takes a word extractor gets known words without tokenizing the text again.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `words` | `list[str]` | - | Words |

Words that are not a list of strings raise `SourceTypeError`.
<!-- --8<-- [end:FixedWordsExtractor] -->

=== "Code"

    ``` python
    from anyts.extractors import FixedWordsExtractor

    FixedWordsExtractor(["It", "rains"]).extract("any text")
    ```

=== "Result"

    ```
    ('It', 'rains')
    ```

## For library developers { #hooks }

<details class="library-hooks" markdown>
<summary>Language hooks of a subclass</summary>

<!-- --8<-- [start:WordsExtractor-hooks] -->
A language library overrides these hooks in a subclass:

| Hook | Kind | Description |
| :--- | :--- | :---------- |
| `tokenize(text)` | method | Tokenizer when `tokenizer` is not given; by default a word character `\w` followed by word characters, combining marks, zero-width joiners and non-joiners and soft hyphens, so that a word in NFD, in Devanagari or in Persian with `U+200C` stays whole |
| `lemmatize(word)` | method | Lemma of a word for `use_lexemes=True`; the word itself by default |
| `number_pattern` | class attribute | Pattern of a number for `filter_nums=True`, matched against the whole lower-cased word; by default a signed number with separators and an optional percent sign: `-5`, `1990-1995`, `1,500.50`, `12/03/2020`, `3:30`, `10%` |
| `messages` | class attribute | Messages of the errors of the parameters, of the text and of the tokenizer; `MESSAGES` by default |
<!-- --8<-- [end:WordsExtractor-hooks] -->

=== "Code"

    ``` python
    import re

    from anyts import WordsExtractor


    class EnglishWords(WordsExtractor):
        number_pattern = re.compile(r"\d+(?:st|nd|rd|th)?")

        def tokenize(self, text):
            return text.split()


    EnglishWords(filter_nums=True).extract("The 3rd time")
    ```

=== "Result"

    ```
    ('The', 'time')
    ```

</details>
