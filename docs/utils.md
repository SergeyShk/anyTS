# Utilities

!!! info ""
    **anyts.utils**

Helper functions shared by the extractors and the statistics.

## is_punctuation

<!-- --8<-- [start:is_punctuation] -->
Checks whether a token consists only of punctuation marks and symbols: the characters of the Unicode categories P (punctuation) and S (symbols). Multi-character tokens like `?!` and `--` and symbols like `€` and `№` are punctuation too; an empty token is punctuation as well.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `token` | str | `-` | Token |
<!-- --8<-- [end:is_punctuation] -->

!!! example "Example"

    ``` python
    from anyts.utils import is_punctuation

    is_punctuation("?!"), is_punctuation("€"), is_punctuation("no.")
    # (True, True, False)
    ```

## count_letters

<!-- --8<-- [start:count_letters] -->
Counts the letters of a word: the characters of any alphabet (`str.isalpha`), without digits, hyphens and marks. The results are cached by word form, so the function is meant for words, not whole texts.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `word` | str | `-` | Word form |
<!-- --8<-- [end:count_letters] -->

!!! example "Example"

    ``` python
    from anyts.utils import count_letters

    count_letters("well-known"), count_letters("3rd")
    # (9, 2)
    ```

## safe_divide

<!-- --8<-- [start:safe_divide] -->
Divides two numbers and returns `default` for a zero denominator.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `num` | float/int | `-` | Numerator |
| `den` | float/int | `-` | Denominator |
| `default` | float/int | `0` | Value returned for a zero denominator |
<!-- --8<-- [end:safe_divide] -->

## has_words

<!-- --8<-- [start:has_words] -->
Checks whether a text, a `Doc` or a `Span` holds a word: an empty text or one of whitespace and punctuation alone holds none.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `source` | str/Doc/Span | `-` | Text, Doc or Span object |
<!-- --8<-- [end:has_words] -->

!!! example "Example"

    ``` python
    from anyts.utils import has_words

    has_words("The cat sleeps"), has_words("?!"), has_words("")
    # (True, False, False)
    ```

## check_sequence

<!-- --8<-- [start:check_sequence] -->
Checks that an argument is a sequence of strings and not a text: a string, a `Doc` or a `Span` raises `SourceTypeError`, since a string would be iterated character by character.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `value` | object | `-` | Value to check |
| `what` | str | `"words"` | What is expected, for the message of the error |
<!-- --8<-- [end:check_sequence] -->

## iter_doc_tokens

<!-- --8<-- [start:iter_doc_tokens] -->
Yields the tokens of the words of a `Doc` or a `Span`: whitespace tokens and the tokens of `is_punctuation`, symbols like `%` and `€` included, are skipped.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `source` | Doc/Span | `-` | Doc or Span object |
<!-- --8<-- [end:iter_doc_tokens] -->

## iter_doc_units

<!-- --8<-- [start:iter_doc_units] -->
Yields the words of a `Doc` or a `Span` as lists of tokens: one token each, as in `iter_doc_tokens`. With `join_hyphens=True` a word that the tokenizer split at its hyphens (`well-known` into `well`, `-`, `known`) is joined back when no whitespace separates its parts; a language library whose own tokenizer keeps such words whole turns it on, so that a string and a `Doc` give the same words.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `source` | Doc/Span | `-` | Doc or Span object |
| `join_hyphens` | bool | `False` | Join the parts of hyphenated words |
<!-- --8<-- [end:iter_doc_units] -->

## iter_doc_words

<!-- --8<-- [start:iter_doc_words] -->
Yields the words of `iter_doc_units` as tuples: the position of the first character, the position after the last character and the text of the word.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `source` | Doc/Span | `-` | Doc or Span object |
| `join_hyphens` | bool | `False` | Join the parts of hyphenated words |
<!-- --8<-- [end:iter_doc_words] -->

!!! example "Example"

    ``` python
    import spacy

    from anyts.utils import iter_doc_words

    doc = spacy.blank("xx")("A well-known cat")
    [word for _, _, word in iter_doc_words(doc)]
    # ['A', 'well', 'known', 'cat']
    list(iter_doc_words(doc, join_hyphens=True))
    # [(0, 1, 'A'), (2, 12, 'well-known'), (13, 16, 'cat')]
    ```
