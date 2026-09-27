class AnyTSError(Exception):
    """
    Base exception of the library

    Description:
        Every exception of the library also inherits ValueError, TypeError,
        OSError or RuntimeError and can be caught by it
    """


class SourceTypeError(AnyTSError, TypeError):
    """
    Wrong type of the data source

    Description:
        The source or the text is of an unsupported type, a text is passed for
        a list of words, the tokenizer is not callable or returns a non-iterable
        object
    """


class SourceError(AnyTSError, ValueError):
    """
    Unusable data source

    Description:
        The source has no words, sentences or texts to compute a statistic on,
        or lacks an annotation the statistic needs
    """


class ParameterError(AnyTSError, ValueError):
    """
    Invalid parameter

    Description:
        A length, window, threshold or number of items is out of range, or the
        name of a measure, variant or preset is unknown
    """


class UnknownStatError(ParameterError, KeyError):
    """Unknown name of a statistic"""

    # Without the quotes that KeyError.__str__ adds to the message
    __str__ = Exception.__str__


class DatasetNotFoundError(AnyTSError, OSError):
    """
    Model or dataset is not installed

    Description:
        The spaCy model is not installed or the dataset files are missing from
        the data directory; the message shows the command that brings them
    """


class DataFileError(AnyTSError, ValueError):
    """
    Dataset file cannot be read

    Description:
        The archive cannot be extracted, has no files or has paths outside its
        directory, or a line of a dataset file cannot be read
    """


class DownloadError(AnyTSError, RuntimeError):
    """
    Download failed

    Description:
        The file cannot be downloaded, its directory cannot be created, or it
        failed the checksum verification
    """
