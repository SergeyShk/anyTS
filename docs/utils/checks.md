# Input checks

Input checks shared by the functions and classes of the core; their messages are in English.

## Sequences { #check_sequence }

<!-- --8<-- [start:check_sequence] -->
``` {.python .signature}
check_sequence(value, what='words', ordered=True)
```

Checks that an argument is a sequence and not a text or an iterator: a string would be iterated by characters, and an iterator exhausted by the first pass. A set or a mapping holds every item once, in no order of the text, so it passes only with `ordered=False`, for a collection such as stop words.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `value` | `object` | - | Value to check |
| `what` | `str` | `"words"` | What is expected, for the message of the error |
| `ordered` | `bool` | `True` | Whether the order and the repeats of the items matter |

A string (of characters or bytes), a `Doc`, a `Span`, an iterator, an object that cannot be iterated or has no length, a table - a two-dimensional array or a `DataFrame` - and, unless `ordered=False`, a set or a mapping raise `SourceTypeError`.
<!-- --8<-- [end:check_sequence] -->

=== "Code"

    ``` python
    from anyts.utils import check_sequence

    check_sequence(["the", "cat"])
    check_sequence({"the", "cat"}, "stop words", ordered=False)
    check_sequence("the cat")
    ```

=== "Result"

    ```
    Traceback (most recent call last):
      ...
    anyts.exceptions.SourceTypeError: A list of words is expected, not a string
    ```

## Lists of words { #check_words }

<!-- --8<-- [start:check_words] -->
``` {.python .signature}
check_words(value, what='words', ordered=True)
```

Checks that an argument is a list of words: it passes `check_sequence` and every item is a string.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `value` | `Iterable` | - | Value to check |
| `what` | `str` | `"words"` | What is expected, for the message of the error |
| `ordered` | `bool` | `True` | Whether the order and the repeats of the words matter |

A value that fails `check_sequence` or holds an item that is not a string, such as a spaCy token, raises `SourceTypeError`.
<!-- --8<-- [end:check_words] -->

=== "Code"

    ``` python
    import spacy

    from anyts.utils import check_words

    check_words(["the", "cat"])
    check_words(list(spacy.blank("xx")("the cat")))
    ```

=== "Result"

    ```
    Traceback (most recent call last):
      ...
    anyts.exceptions.SourceTypeError: The words must be strings, not Token
    ```

## Words { #check_word }

<!-- --8<-- [start:check_word] -->
``` {.python .signature}
check_word(value, what='word')
```

Checks that an argument of a function of a single word, such as the syllables of a language, is a word, a string.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `value` | `object` | - | Value to check |
| `what` | `str` | `"word"` | What is expected, for the message of the error |

A value that is not a string raises `SourceTypeError`.
<!-- --8<-- [end:check_word] -->

=== "Code"

    ``` python
    from anyts.utils import check_word

    check_word("cat")
    check_word(["cat"])
    ```

=== "Result"

    ```
    Traceback (most recent call last):
      ...
    anyts.exceptions.SourceTypeError: The word must be a string, not list
    ```

## Counters { #check_counts }

<!-- --8<-- [start:check_counts] -->
``` {.python .signature}
check_counts(value)
```

Checks that an argument is a counter - a mapping of words to their frequencies, such as a `Counter`.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `value` | `object` | - | Value to check |

A value that is not a mapping, a word that is not a string or a frequency that is not a number raises `SourceTypeError`, and a negative, `nan` or infinite frequency `SourceError`.
<!-- --8<-- [end:check_counts] -->

=== "Code"

    ``` python
    from collections import Counter

    from anyts.utils import check_counts

    check_counts(Counter(["the", "cat", "the"]))
    check_counts({"the": "2"})
    check_counts({"the": -2})
    ```

=== "Result"

    ```
    Traceback (most recent call last):
      ...
    anyts.exceptions.SourceTypeError: The frequencies must be numbers, not str
    Traceback (most recent call last):
      ...
    anyts.exceptions.SourceError: The frequencies must be finite and not negative, not -2
    ```

## Integers { #check_integer }

<!-- --8<-- [start:check_integer] -->
``` {.python .signature}
check_integer(value, what)
```

Checks that a parameter is an integer.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `value` | `object` | - | Value to check |
| `what` | `str` | - | Name of the parameter, for the message of the error |

A value that is not an integer, a `bool` or a `float` included, even a whole one like `5.0`, raises `ParameterError`.
<!-- --8<-- [end:check_integer] -->

=== "Code"

    ``` python
    from anyts.utils import check_integer

    check_integer(5, "window size")
    check_integer(5.0, "window size")
    ```

=== "Result"

    ```
    Traceback (most recent call last):
      ...
    anyts.exceptions.ParameterError: The window size must be an integer, not float
    ```

## Bools { #check_bool }

<!-- --8<-- [start:check_bool] -->
``` {.python .signature}
check_bool(value, what)
```

Checks that a parameter is a `bool`.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `value` | `object` | - | Value to check |
| `what` | `str` | - | Name of the parameter, for the message of the error |

A value that is not a `bool`, `0`, `1` and `"yes"` included, raises `ParameterError`.
<!-- --8<-- [end:check_bool] -->

=== "Code"

    ``` python
    from anyts.utils import check_bool

    check_bool(True, "normalization")
    check_bool("yes", "normalization")
    ```

=== "Result"

    ```
    Traceback (most recent call last):
      ...
    anyts.exceptions.ParameterError: The normalization must be a bool, not str
    ```

## Numbers { #check_number }

<!-- --8<-- [start:check_number] -->
``` {.python .signature}
check_number(value, what)
```

Checks that a parameter is a finite real number.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `value` | `object` | - | Value to check |
| `what` | `str` | - | Name of the parameter, for the message of the error |

A value that is not a finite real number - a `bool`, a string, `None`, `nan`, an infinity - raises `ParameterError`.
<!-- --8<-- [end:check_number] -->

=== "Code"

    ``` python
    from anyts.utils import check_number

    check_number(0.95, "confidence level")
    check_number("0.95", "confidence level")
    check_number(float("nan"), "confidence level")
    ```

=== "Result"

    ```
    Traceback (most recent call last):
      ...
    anyts.exceptions.ParameterError: The confidence level must be a number, not str
    Traceback (most recent call last):
      ...
    anyts.exceptions.ParameterError: The confidence level must be a finite number, not nan
    ```

## Functions { #check_callable }

<!-- --8<-- [start:check_callable] -->
``` {.python .signature}
check_callable(value, what)
```

Checks that an argument is a function, such as a hook a function of the core takes as a parameter.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `value` | `object` | - | Value to check |
| `what` | `str` | - | Name of the argument, for the message of the error |

A value that cannot be called raises `SourceTypeError`.
<!-- --8<-- [end:check_callable] -->

=== "Code"

    ``` python
    from anyts.utils import check_callable

    check_callable(str.lower, "normalization")
    check_callable("lower", "normalization")
    ```

=== "Result"

    ```
    Traceback (most recent call last):
      ...
    anyts.exceptions.SourceTypeError: The normalization must be callable, not str
    ```
