# Any Texts Statistics (anyTS)
#
# Copyright (C) 2026
# Author: Sergey Shkarin <kouki.sergey@gmail.com>
# URL: <https://github.com/SergeyShk/anyTS>

import logging
from importlib.metadata import PackageNotFoundError, version

from .diversity_stats import DiversityStats
from .exceptions import (
    AnyTSError,
    DataFileError,
    DatasetNotFoundError,
    DownloadError,
    ParameterError,
    SourceError,
    SourceTypeError,
    UnknownStatError,
)
from .extractors import CharNgramsExtractor, SentsExtractor, WordsExtractor

logging.getLogger(__name__).addHandler(logging.NullHandler())

try:
    __version__ = version("anyts")
except PackageNotFoundError:
    __version__ = "0.0.0"
__description__ = (
    "The language-independent core of text statistics libraries. Requires Python 3.11+"
)
__author__ = "Sergey Shkarin"
__author_email__ = "kouki.sergey@gmail.com"

__all__ = [
    "AnyTSError",
    "CharNgramsExtractor",
    "DataFileError",
    "DatasetNotFoundError",
    "DiversityStats",
    "DownloadError",
    "ParameterError",
    "SentsExtractor",
    "SourceError",
    "SourceTypeError",
    "UnknownStatError",
    "WordsExtractor",
    "__version__",
]
