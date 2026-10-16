# Exceptions

!!! info ""
    **anyts.exceptions**

<!-- --8<-- [start:exceptions] -->
All exceptions of the library inherit the base class `AnyTSError` and a built-in Python class, so they can be caught by either, and `except ValueError` keeps working.

| Exception | Built-in class | When raised |
| :-------- | :------------- | :---------- |
| `AnyTSError` | `Exception` | Base class, never raised itself |
| `SourceTypeError` | `TypeError` | An argument is of an unsupported type: the source or the text, a text where a list is expected, an extractor, basic statistics of another class, a path, a hook that is not callable (a tokenizer, a lemmatizer, a measure) or returns what the core cannot use |
| `SourceError` | `ValueError` | The source has no words, sentences or texts to compute a statistic on, lacks an annotation the statistic needs, or holds values it cannot take: a negative or infinite frequency, a matrix of distances that is not one |
| `ParameterError` | `ValueError` | A parameter is out of range or not a finite number, a name (of a measure, a variant, a preset, a layer, a norm) is unknown, the labels or the axes of a plot are set incorrectly, or a layer of the highlighting asks for an annotation the source lacks |
| `UnknownStatError` | `ParameterError`, `KeyError` | An unknown statistic is requested by name |
| `DatasetNotFoundError` | `OSError` | The spaCy model is not installed or a dataset is not downloaded; the message gives the command that fixes it |
| `DataFileError` | `ValueError` | The archive of a dataset cannot be extracted or is unsafe, or a line of a dataset file cannot be read |
| `DownloadError` | `RuntimeError` | A file cannot be downloaded, is cut short or fails the checksum verification, its name is not a plain name, or its directory cannot be created |

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

## Messages { #messages }

<!-- --8<-- [start:messages] -->
The messages of the errors of the classes of statistics (`Stats` and its subclasses), of `StatsComponent`, of the extractors `SentsExtractor`, `WordsExtractor` and `CharNgramsExtractor` and of `ConnectorMatcher` come from their class attribute `messages`, a mapping of a key to a message; the messages with fields in braces are format strings. By default it is `anyts.constants.MESSAGES`, in English. A language library sets the messages of its language on its subclasses, `messages = {**MESSAGES, **own}`, and its users get them for a source without words, an extractor of another type, an unknown preset or statistic, a parameter out of range, the bounds of the lengths, the N-grams and the top of an extractor, a text that is not a string or a wrong tokenizer, and a dictionary of connectors of a wrong form or wrong parts of speech: every error such a class raises itself. The functions `check_params`, `calc_windowed` and `calc_reading_time`, which these classes call, take the messages as the keyword `messages`.

The shared checks of `anyts.utils` (`check_integer`, `check_number`, `check_words`, `check_sequence`), which these classes call too, and the other functions of the core keep their messages in English.
<!-- --8<-- [end:messages] -->

!!! example "Example"

    ``` python
    from anyts.constants import MESSAGES
    from anyts.diversity_stats import DiversityStats


    class Diversity(DiversityStats):
        messages = {**MESSAGES, "no_words": "Il testo non contiene parole"}


    try:
        Diversity([])
    except ValueError as e:
        print(e)
    # Il testo non contiene parole
    ```
