# Exceptions

<!-- --8<-- [start:exceptions] -->
All exceptions of the library inherit the base class `AnyTSError` and a built-in Python class, and can be caught by either.

| Exception | Built-in class | When raised |
| :-------- | :------------- | :---------- |
| `AnyTSError` | `Exception` | Base class, never raised itself |
| `SourceTypeError` | `TypeError` | An argument is of an unsupported type: the source or the text, a text where a list is expected, an extractor, basic statistics of another class, a path, a hook that is not callable (a tokenizer, a lemmatizer, a measure), or a tokenizer, a sentence splitter or the `parse`, `analyze`, `syllabify`, `transcribe` or `find` of a class that returns what the core cannot use |
| `SourceError` | `ValueError` | The source has no words, sentences or texts to compute a statistic on, lacks an annotation the statistic needs, or holds values it cannot take: a negative or infinite frequency, a matrix of distances that is not one |
| `ParameterError` | `ValueError` | A parameter is out of range or not a finite number, a name (of a measure, a variant, a preset, a layer, a norm) is unknown, the labels or the axes of a plot are set incorrectly, a layer of the highlighting asks for an annotation the source lacks, or a class defines an attribute or a hook of 0.4 the core no longer reads |
| `UnknownStatError` | `ParameterError`, `KeyError` | An unknown statistic is requested by name |
| `DatasetNotFoundError` | `OSError` | The spaCy model is not installed or a dataset is not downloaded; the message gives the command that fixes it |
| `DataFileError` | `ValueError` | The archive of a dataset cannot be extracted or is unsafe, or a line of a dataset file cannot be read |
| `DownloadError` | `RuntimeError` | A file cannot be downloaded, is cut short or fails the checksum verification, its name is not a plain name, or its directory cannot be created |

The classes are available from `anyts` and from `anyts.exceptions`. A language library re-exports them under its own names as aliases, not subclasses, so its base class catches the errors of the core too.
<!-- --8<-- [end:exceptions] -->

=== "Code"

    ``` python
    from anyts import AnyTSError, ParameterError, WordsExtractor

    try:
        WordsExtractor(ngram_range=(2, 1))
    except ParameterError as e:
        print(e)

    try:
        WordsExtractor(tokenizer=42).extract("The cat sleeps.")
    except AnyTSError as e:
        print(type(e).__name__)
    ```

=== "Result"

    ```
    The lower N-gram bound is greater than the upper
    SourceTypeError
    ```

## Messages { #messages }

<!-- --8<-- [start:messages] -->
The errors of the classes of statistics (`Stats` and its subclasses), of `StatsComponent`, of the extractors `SentsExtractor`, `WordsExtractor` and `CharNgramsExtractor`, of `ConnectorMatcher` and of `HighlightedText` take their messages from the class attribute `messages`, a mapping of a key to a message, `anyts.constants.MESSAGES` in English by default, a read-only mapping shared by every class; the messages with fields in braces are format strings. A language library sets the messages of its language on its subclasses, `messages = MappingProxyType({**MESSAGES, **own})`, and they cover every error such a class raises itself; `source_type_error` of `anyts.utils` gives the error of a source of a wrong type by them. The functions `to_document`, `check_params`, `calc_windowed`, `calc_reading_time`, `find_nausea_words`, `calc_academic_nausea`, `calc_zipf_naturalness`, `split_windows` and `sentence_rhythm` take the messages as the keyword `messages`.

The shared checks of `anyts.utils` (`check_integer`, `check_number`, `check_bool`, `check_words`, `check_sequence`) take the message of a class through their keyword `message`, so a parameter of a wrong type of these classes and functions comes in the language of the class under the name of the parameter (`bool_param`, `integer_param`, `number_param`, `words_param`), and so do the arguments of `ConnectorMatcher.find`; a wrong value a hook of `to_document` gives raises `hook_bounds`. A hook of a class that returns what the core cannot use raises a `hook_*` message of the class. The checks of the lists and the scales of a subclass when it is defined, of a hook that must be callable and of the functions of the core without `messages` keep their messages in English, and so does the text of anySeg inside `document_tokens`.
<!-- --8<-- [end:messages] -->

=== "Code"

    ``` python
    from types import MappingProxyType

    from anyts.constants import MESSAGES
    from anyts.diversity_stats import DiversityStats


    class Diversity(DiversityStats):
        messages = MappingProxyType({**MESSAGES, "no_words": "Il testo non contiene parole"})


    try:
        Diversity([])
    except ValueError as e:
        print(e)
    ```

=== "Result"

    ```
    Il testo non contiene parole
    ```
