# Utilities

!!! info ""
    **anyts.utils**

Helper functions shared by the extractors and the statistics.

## is_punctuation

<!-- --8<-- [start:is_punctuation] -->
Checks whether a token consists only of punctuation marks and symbols: the characters of the Unicode categories P (punctuation), S (symbols), M (combining marks) and Cf (invisible format characters such as the zero-width space `U+200B`, the byte order mark `U+FEFF` and the zero-width joiner `U+200D`). Multi-character tokens like `?!` and `--`, symbols like `€` and `№` and a lone invisible character that a tokenizer splits off are punctuation too, while a token with a letter or a digit is not (`e` with a combining acute accent is a word); an empty token is punctuation as well.

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

## check_sequence

<!-- --8<-- [start:check_sequence] -->
Checks that an argument is a sequence and not a text or an iterator: a string, a `Doc`, a `Span`, an iterator or an object that cannot be iterated raises `SourceTypeError`, since a string would be iterated character by character and an iterator would be exhausted by the first pass over it; so does a table - a two-dimensional array or a `DataFrame`. A set or a mapping holds every item once, in no order of the text, and raises the error too, unless `ordered=False` - for a collection whose order and repeats do not matter, such as stop words.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `value` | object | `-` | Value to check |
| `what` | str | `"words"` | What is expected, for the message of the error |
| `ordered` | bool | `True` | Whether the order and the repeats of the items matter |
<!-- --8<-- [end:check_sequence] -->

## check_words

<!-- --8<-- [start:check_words] -->
Checks that an argument is a list of words: it passes `check_sequence` and every item is a string, so that a list of spaCy tokens, which would count every token as a lexeme of its own, raises `SourceTypeError`.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `value` | Iterable | `-` | Value to check |
| `what` | str | `"words"` | What is expected, for the message of the error |
| `ordered` | bool | `True` | Whether the order and the repeats of the words matter |
<!-- --8<-- [end:check_words] -->

## check_integer

<!-- --8<-- [start:check_integer] -->
Checks that a parameter is an integer: a `bool` or a `float`, even a whole one like `5.0`, raises `ParameterError`, since it would fail only later, as an index or a count.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `value` | object | `-` | Value to check |
| `what` | str | `-` | Name of the parameter, for the message of the error |
<!-- --8<-- [end:check_integer] -->

## check_number

<!-- --8<-- [start:check_number] -->
Checks that a parameter is a real number: a `bool`, a string or `None` raises `ParameterError` instead of failing later in a comparison.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `value` | object | `-` | Value to check |
| `what` | str | `-` | Name of the parameter, for the message of the error |
<!-- --8<-- [end:check_number] -->

## check_counts

<!-- --8<-- [start:check_counts] -->
Checks that an argument is a counter - a mapping of words to their frequencies, such as a `Counter`: a value that is not a mapping, a word that is not a string or a frequency that is not a number raises `SourceTypeError`.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `value` | object | `-` | Value to check |
<!-- --8<-- [end:check_counts] -->

## merge_labels

<!-- --8<-- [start:merge_labels] -->
Merges the labels given for a plot over its default ones: a label that is not given keeps its default, so a single label can be changed alone. A default with fields in braces, such as `"Moving average ({window})"`, is a format string: a label given for it may use only those fields, and a literal brace in it is doubled (`{{`); the other labels are taken as they are. A format label is tried on sample values of its fields, of the types the plot gives them, so that a format spec the values do not take (`{window:s}` for a number) fails before a figure is created. Labels that are not a mapping of strings, have a key the plot does not know, a field their default does not have or a format spec their values do not take raise `ParameterError`.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `defaults` | dict[str, str] | `-` | Default labels by key |
| `labels` | dict[str, str] | `-` | Labels given; `None` - the default ones |
| `**samples` | object | `-` | Values of the fields of the format labels, for trying the labels given |
<!-- --8<-- [end:merge_labels] -->

The defaults of the visualizers of the core are `anyts.constants.VISUALIZER_LABELS`, by the name of the function.

!!! example "Example"

    ``` python
    from anyts.utils import merge_labels

    merge_labels({"title": "Plot", "xlabel": "x"}, {"title": "My plot"})
    # {'title': 'My plot', 'xlabel': 'x'}
    ```

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
Yields the words of `iter_doc_units` as tuples: the position of the first character, the position after the last character and the text of the word. A byte order mark glued to the start of a word, as in a file read with `utf-8` instead of `utf-8-sig`, is dropped.

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
