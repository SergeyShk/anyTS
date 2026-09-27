# Word extraction

!!! info ""
    **anyts.extractors.WordsExtractor**

## Description

<!-- --8<-- [start:WordsExtractor] -->
A class for extracting words from a text. It allows using different tokenizers, filtering stop words, numbers and punctuation, lemmatizing, building N-grams, and setting the minimum and maximum length of extracted words.
<!-- --8<-- [end:WordsExtractor] -->

## Language hooks

<!-- --8<-- [start:WordsExtractor-hooks] -->
The language enters the extractor through three hooks that a language library overrides in a subclass:

| Hook | Kind | Default | Used for |
| :--: | :--: | :-----: | :------: |
| `tokenize(text)` | method | runs of word characters `\w+` | the tokenizer when `tokenizer` is not given |
| `lemmatize(word)` | method | the word itself | `use_lexemes=True` |
| `number_pattern` | class attribute | a signed number with separators and an optional percent sign: `-5`, `1990-1995`, `1,500.50`, `12/03/2020`, `3:30`, `10%` | `filter_nums=True`, matched against the whole lower-cased word |
<!-- --8<-- [end:WordsExtractor-hooks] -->

!!! example "Example"

    ``` python
    import re

    from anyts import WordsExtractor


    class EnglishWords(WordsExtractor):
        number_pattern = re.compile(r"\d+(?:st|nd|rd|th)?")

        def tokenize(self, text):
            return text.split()


    EnglishWords(filter_nums=True).extract("The 3rd time")
    ```

    _Result_:

    ``` bash
    ('The', 'time')
    ```

## Parameters

<!-- --8<-- [start:WordsExtractor-parameters] -->
| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `tokenizer` | Pattern/Callable | `None` | Tokenizer or regular expression; by default the `tokenize` method |
| `filter_punct` | bool | `True` | Filter punctuation marks |
| `filter_nums` | bool | `False` | Filter numbers matched by `number_pattern` |
| `use_lexemes` | bool | `False` | Use word lemmas of the `lemmatize` method |
| `stopwords` | Collection[str] | `None` | Stop words, compared case-insensitively |
| `lowercase` | bool | `False` | Convert words to lower case |
| `ngram_range` | Tuple[int, int] | `(1, 1)` | Lower and upper bound of the N-gram size |
| `min_len` | int | `0` | Minimum length of an extracted word, `0` for no bound |
| `max_len` | int | `0` | Maximum length of an extracted word, `0` for no bound |

!!! note "Note"
    A regular expression as the tokenizer is a separator: the text is split with `re.split`. The filters are applied in order: punctuation, numbers, lemmatization, lower case, stop words, word length. A lower-case stop word list also filters a capitalized word at the start of a sentence. A punctuation mark is a token consisting entirely of marks and symbols (the Unicode categories P and S), including multi-character ones: `?!`, `--`, `…`, `€`. Empty tokens are dropped before the filters. N-grams join the words with `_`.
<!-- --8<-- [end:WordsExtractor-parameters] -->

## Methods

### extract

<!-- --8<-- [start:WordsExtractor-extract] -->
Extracts words from a text.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | str | `-` | Text string |
<!-- --8<-- [end:WordsExtractor-extract] -->

An example of word extraction with bigrams as tokens, after filtering numbers and stop words:

!!! example "Example"

    _Code_:

    ``` python
    from anyts import WordsExtractor

    text = "Better 100 friends than 100 dollars"

    we = WordsExtractor(lowercase=True, stopwords=["than"], filter_nums=True, ngram_range=(1, 2))
    we.extract(text)
    ```

    _Result_:

    ``` bash
    ('better', 'friends', 'dollars', 'better_friends', 'friends_dollars')
    ```

### get_most_common

<!-- --8<-- [start:WordsExtractor-get_most_common] -->
Returns a counter of the top words of the text. It takes the number of top words to return as a parameter.

!!! warning "Warning"
    The method must be called after words have been extracted with `extract`.
<!-- --8<-- [end:WordsExtractor-get_most_common] -->

!!! example "Example"

    _Code_:

    ``` python
    from anyts import WordsExtractor

    we = WordsExtractor(lowercase=True)
    we.extract("The cat saw the dog and the bird")
    we.get_most_common(2)
    ```

    _Result_:

    ``` bash
    [('the', 3), ('cat', 1)]
    ```
