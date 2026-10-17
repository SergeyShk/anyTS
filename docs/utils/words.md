# Words and tokens

!!! info ""
    **anyts.utils**

Checks of the words of a text and the counts of their letters.

## is_punctuation

<!-- --8<-- [start:is_punctuation] -->
Checks whether a token consists only of punctuation marks and symbols: the characters of the Unicode categories P (punctuation), S (symbols), M (combining marks) and Cf (invisible format characters such as the zero-width space `U+200B`, the byte order mark `U+FEFF` and the zero-width joiner `U+200D`). Multi-character tokens like `?!` and `--`, symbols like `€` and `№` and a lone invisible character that a tokenizer splits off are punctuation too, while a token with a letter or a digit is not (`e` with a combining acute accent is a word); an empty token is punctuation as well. The results are cached by token, so the function is meant for tokens, not whole texts.

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

## is_number

<!-- --8<-- [start:is_number] -->
`is_number(word, pattern)` checks whether a word is a number by a pattern matched against the whole lower-cased word, `NUMBER_PATTERN` by default, the numbers of `WordsExtractor`; a language passes its own (ordinals, Roman numerals).
<!-- --8<-- [end:is_number] -->

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

## has_words

<!-- --8<-- [start:has_words] -->
Checks whether a text, a `Doc` or a `Span` holds a word: an empty text or one of whitespace and the characters of `is_punctuation` alone holds none.

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
