# Exceptions

!!! info ""
    **anyts.exceptions**

<!-- --8<-- [start:exceptions] -->
All exceptions of the library inherit the base class `AnyTSError` and a built-in Python class, so they can be caught by either, and `except ValueError` keeps working.

| Exception | Built-in class | When raised |
| :-------- | :------------- | :---------- |
| `AnyTSError` | `Exception` | Base class, never raised itself |
| `SourceTypeError` | `TypeError` | The source or the text is of an unsupported type; a text is passed where a list of words is expected; the tokenizer is not callable or returns a non-iterable object; the stop words are a string |
| `SourceError` | `ValueError` | The source has no words, sentences or texts to compute a statistic on, or lacks an annotation the statistic needs |
| `ParameterError` | `ValueError` | A length, window, threshold or number of items is out of range, or the name of a measure, variant or preset is unknown |
| `UnknownStatError` | `ParameterError`, `KeyError` | An unknown statistic is requested by name |
| `DatasetNotFoundError` | `OSError` | The spaCy model is not installed or a dataset is not downloaded; the message gives the command that fixes it |
| `DataFileError` | `ValueError` | The archive of a dataset cannot be extracted or is unsafe, or a line of a dataset file cannot be read |
| `DownloadError` | `RuntimeError` | A file cannot be downloaded or fails the checksum verification |

The classes are available from `anyts` and from `anyts.exceptions`. A language library re-exports them under its own names as aliases, not subclasses, so its base class catches the errors of the core too.
<!-- --8<-- [end:exceptions] -->

!!! example "Example"

    ``` python
    from anyts import AnyTSError, ParameterError, WordsExtractor

    try:
        WordsExtractor(ngram_range=(2, 1))
    except ParameterError as e:
        print(e)
    # The lower N-gram bound is greater than the upper

    try:
        WordsExtractor(tokenizer=42).extract("The cat sleeps.")
    except AnyTSError as e:
        print(type(e).__name__)
    # SourceTypeError
    ```
