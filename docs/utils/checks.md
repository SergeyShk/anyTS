# Input checks

!!! info ""
    **anyts.utils**

The checks of the input that the functions and the classes of the core share; their messages are in English.

## check_sequence

<!-- --8<-- [start:check_sequence] -->
Checks that an argument is a sequence and not a text or an iterator: a string (of characters or bytes), a `Doc`, a `Span`, an iterator or an object that cannot be iterated raises `SourceTypeError`, since a string would be iterated character by character and an iterator would be exhausted by the first pass over it; so does a table - a two-dimensional array or a `DataFrame`. A set or a mapping holds every item once, in no order of the text, and raises the error too, unless `ordered=False` - for a collection whose order and repeats do not matter, such as stop words.

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

## check_counts

<!-- --8<-- [start:check_counts] -->
Checks that an argument is a counter - a mapping of words to their frequencies, such as a `Counter`: a value that is not a mapping, a word that is not a string or a frequency that is not a number raises `SourceTypeError`, and a negative, `nan` or infinite frequency `SourceError`.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `value` | object | `-` | Value to check |
<!-- --8<-- [end:check_counts] -->

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
Checks that a parameter is a finite real number: a `bool`, a string, `None`, `nan` or an infinity raises `ParameterError` instead of failing later in a comparison.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `value` | object | `-` | Value to check |
| `what` | str | `-` | Name of the parameter, for the message of the error |
<!-- --8<-- [end:check_number] -->
