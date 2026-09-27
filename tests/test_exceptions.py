import logging

import pytest

import anyts
from anyts import AnyTSError, SentsExtractor, WordsExtractor
from anyts.exceptions import (
    DataFileError,
    DatasetNotFoundError,
    DownloadError,
    ParameterError,
    SourceError,
    SourceTypeError,
    UnknownStatError,
)


@pytest.mark.parametrize(
    "exception, builtin",
    [
        (SourceTypeError, TypeError),
        (SourceError, ValueError),
        (ParameterError, ValueError),
        (UnknownStatError, KeyError),
        (DatasetNotFoundError, OSError),
        (DataFileError, ValueError),
        (DownloadError, RuntimeError),
    ],
)
def test_hierarchy(exception, builtin):
    assert issubclass(exception, AnyTSError)
    assert issubclass(exception, builtin)
    assert getattr(anyts, exception.__name__) is exception
    assert exception.__name__ in anyts.__all__


def test_unknown_stat_error():
    assert issubclass(UnknownStatError, ParameterError)
    assert str(UnknownStatError("unknown")) == "unknown"
    assert str(KeyError("unknown")) == "'unknown'"


def test_builtin_compatibility():
    with pytest.raises(ValueError):
        WordsExtractor(min_len=3, max_len=2)
    with pytest.raises(TypeError):
        WordsExtractor(tokenizer=42).extract("The cat sleeps.")  # type: ignore[arg-type]
    with pytest.raises(AnyTSError):
        SentsExtractor(min_len=3, max_len=2)


def test_logging():
    assert any(isinstance(h, logging.NullHandler) for h in logging.getLogger("anyts").handlers)
