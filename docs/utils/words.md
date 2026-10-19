# Words and tokens

Checks of the words of a text and the counts of their letters.

## Punctuation { #is_punctuation }

<!-- --8<-- [start:is_punctuation] -->
``` {.python .signature}
is_punctuation(token)
```

Checks whether a token consists only of punctuation marks and symbols: the characters of the Unicode categories P (punctuation), S (symbols), M (combining marks) and Cf (invisible format characters such as the zero-width space `U+200B`, the byte order mark `U+FEFF` and the zero-width joiner `U+200D`). So `?!`, `--`, `€`, `№`, a lone invisible character and an empty token are punctuation, and a token with a letter or a digit is not (`e` with a combining acute accent is a word). The results are cached by token, so the function is meant for tokens, not whole texts.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `token` | `str` | - | Token |
<!-- --8<-- [end:is_punctuation] -->

=== "Code"

    ``` python
    from anyts.utils import is_punctuation

    is_punctuation("?!"), is_punctuation("€"), is_punctuation("no.")
    ```

=== "Result"

    ```
    (True, True, False)
    ```

## Numbers { #is_number }

<!-- --8<-- [start:is_number] -->
``` {.python .signature}
is_number(word, pattern=NUMBER_PATTERN)
```

Checks whether a word is a number by a pattern matched against the whole lower-cased word; a language passes its own (ordinals, Roman numerals).

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `word` | `str` | - | Word |
| `pattern` | `Pattern` | `NUMBER_PATTERN` | Pattern of a number; by default the numbers of `WordsExtractor` |
<!-- --8<-- [end:is_number] -->

=== "Code"

    ``` python
    import re

    from anyts.utils import is_number

    is_number("2020"), is_number("10%"), is_number("3rd"), is_number("XIV", re.compile(r"[ivxlcdm]+"))
    ```

=== "Result"

    ```
    (True, True, False, True)
    ```

## Letters { #count_letters }

<!-- --8<-- [start:count_letters] -->
``` {.python .signature}
count_letters(word)
```

Counts the letters of a word: the characters of any alphabet (`str.isalpha`), without digits, hyphens and marks. The results are cached by word form, so the function is meant for words, not whole texts.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `word` | `str` | - | Word form |
<!-- --8<-- [end:count_letters] -->

=== "Code"

    ``` python
    from anyts.utils import count_letters

    count_letters("well-known"), count_letters("3rd")
    ```

=== "Result"

    ```
    (9, 2)
    ```

## Texts with words { #has_words }

<!-- --8<-- [start:has_words] -->
``` {.python .signature}
has_words(source)
```

Checks whether a text, a `Doc` or a `Span` holds a word: an empty text or one of whitespace and the characters of `is_punctuation` alone holds none.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `source` | `str` / `Doc` / `Span` | - | Text, Doc or Span object |
<!-- --8<-- [end:has_words] -->

=== "Code"

    ``` python
    from anyts.utils import has_words

    has_words("The cat sleeps"), has_words("?!"), has_words("")
    ```

=== "Result"

    ```
    (True, False, False)
    ```

## Marks between the words of a text { #find_marks }

<!-- --8<-- [start:find_marks] -->
``` {.python .signature}
find_marks(text, words)
```

Finds the punctuation marks between the words of a text: the words are found in the text in their order, a word inside a longer one not counting, and a word with a character of `is_punctuation` between it and the word before gets its position; the hyphen that joins two parts of a word is no mark. A word the text does not hold is passed over. The positions go to `ConnectorMatcher.find`, whose rules do not read a word across a mark.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `str` | - | Text |
| `words` | `list[str]` | - | Words of the text in their order |

A text that is not a string and words that are not a list of strings raise `SourceTypeError`.
<!-- --8<-- [end:find_marks] -->

=== "Code"

    ``` python
    from anyts.utils import find_marks

    sorted(find_marks("So, it is late - very late", ["So", "it", "is", "late", "very", "late"]))
    ```

=== "Result"

    ```
    [1, 4]
    ```
