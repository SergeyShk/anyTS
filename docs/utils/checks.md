# Input checks

!!! info ""
    **anyts.utils**

Input checks shared by the functions and classes of the core; their messages are in English.

## check_sequence

<!-- --8<-- [start:check_sequence] -->
Checks that an argument is a sequence and not a text or an iterator. A string (of characters or bytes), a `Doc`, a `Span`, an iterator, an object that cannot be iterated or has no length, and a table - a two-dimensional array or a `DataFrame` - raise `SourceTypeError`: a string would be iterated by characters, and an iterator exhausted by the first pass. A set or a mapping holds every item once, in no order of the text, and raises the error too unless `ordered=False`, for a collection such as stop words.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `value` | object | `-` | Value to check |
| `what` | str | `"words"` | What is expected, for the message of the error |
| `ordered` | bool | `True` | Whether the order and the repeats of the items matter |
<!-- --8<-- [end:check_sequence] -->

## check_words

<!-- --8<-- [start:check_words] -->
Checks that an argument is a list of words: it passes `check_sequence` and every item is a string, so a list of spaCy tokens raises `SourceTypeError`.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `value` | Iterable | `-` | Value to check |
| `what` | str | `"words"` | What is expected, for the message of the error |
| `ordered` | bool | `True` | Whether the order and the repeats of the words matter |
<!-- --8<-- [end:check_words] -->

## check_word

<!-- --8<-- [start:check_word] -->
Checks that an argument of a function of a single word, such as the syllables of a language, is a word: a value that is not a string raises `SourceTypeError`.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `value` | object | `-` | Value to check |
| `what` | str | `"word"` | What is expected, for the message of the error |
<!-- --8<-- [end:check_word] -->

## check_counts

<!-- --8<-- [start:check_counts] -->
Checks that an argument is a counter - a mapping of words to their frequencies, such as a `Counter`: a value that is not a mapping, a word that is not a string or a frequency that is not a number raises `SourceTypeError`, and a negative, `nan` or infinite frequency `SourceError`.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `value` | object | `-` | Value to check |
<!-- --8<-- [end:check_counts] -->

## check_integer

<!-- --8<-- [start:check_integer] -->
Checks that a parameter is an integer: a `bool` or a `float`, even a whole one like `5.0`, raises `ParameterError`.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `value` | object | `-` | Value to check |
| `what` | str | `-` | Name of the parameter, for the message of the error |
<!-- --8<-- [end:check_integer] -->

## check_number

<!-- --8<-- [start:check_number] -->
Checks that a parameter is a finite real number: a `bool`, a string, `None`, `nan` or an infinity raises `ParameterError`.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `value` | object | `-` | Value to check |
| `what` | str | `-` | Name of the parameter, for the message of the error |
<!-- --8<-- [end:check_number] -->

## check_callable

<!-- --8<-- [start:check_callable] -->
Checks that an argument is a function, such as a hook a function of the core takes as a parameter: a value that cannot be called raises `SourceTypeError`.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `value` | object | `-` | Value to check |
| `what` | str | `-` | Name of the argument, for the message of the error |
<!-- --8<-- [end:check_callable] -->
