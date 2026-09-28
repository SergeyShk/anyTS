import hashlib
import logging
import os
import shutil
import tarfile
import unicodedata
import urllib.parse
import urllib.request
import zipfile
from abc import ABCMeta, abstractmethod
from collections.abc import Callable, Iterator
from pathlib import Path, PureWindowsPath
from typing import Any, ClassVar

from .exceptions import DataFileError, DownloadError, ParameterError, SourceTypeError
from .utils import check_integer

logger = logging.getLogger(__name__)

Filter = Callable[[dict[str, Any]], bool]
Filters = list[Filter]

# Seconds a download waits for the server to answer
DOWNLOAD_TIMEOUT = 60

# User-Agent header of the downloads
USER_AGENT = "anyTS"

# Whether tarfile has the data filter (Python 3.11.4+)
TAR_DATA_FILTER = hasattr(tarfile, "data_filter")


class Dataset(metaclass=ABCMeta):
    """
    Abstract dataset

    Description:
        The class attributes repr_name and name_key are the name of the class
        in repr and the key of the name of the dataset in info

    Arguments:
        name (str): Name of the dataset
        meta (dict): Reference information about the dataset

    Methods:
        check_data: Checking that the directories and files of the dataset are in place
        get_texts: Getting the texts (without the headers) of the dataset
        get_records: Getting the records (with the headers) of the dataset
        download: Downloading the dataset from the network
    """

    __test__ = False
    repr_name: ClassVar[str] = "Dataset"
    name_key: ClassVar[str] = "name"

    @abstractmethod
    def __init__(self, name: str, meta: dict[str, str] | None = None) -> None:
        self.name = name
        self.meta = meta or {}

    def __repr__(self) -> str:
        return f"{self.repr_name}('{self.name}')"

    @property
    def info(self) -> dict[str, str]:
        """
        Name of the dataset and its reference information
        """
        return {self.name_key: self.name, **self.meta}

    @abstractmethod
    def __iter__(self) -> Iterator[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def check_data(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_texts(self, *args: Any) -> Iterator[str]:
        raise NotImplementedError

    @abstractmethod
    def get_records(self, *args: Any) -> Iterator[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def download(self, force: bool = False) -> None:
        raise NotImplementedError


def fetch_archive(
    url: str,
    filepath: Path,
    checksum: str,
    missing: bool,
    force: bool = False,
    user_agent: str = USER_AGENT,
) -> None:
    """
    Downloading the archive of a dataset, verifying it and extracting the files

    Description:
        The archive is verified and extracted when it is downloaded now or the
        extracted files are missing. An archive that fails the SHA-256 checksum
        is removed and downloaded again once. The extracted files replace the
        directory of the dataset only once the extraction is complete

    Arguments:
        url (str): Address of the archive
        filepath (Path): Path to the archive; the files are extracted into its directory
        checksum (str): SHA-256 checksum of the archive
        missing (bool): Whether the extracted files are missing
        force (bool): Download the archive even if it is already there
        user_agent (str): User-Agent header of the request

    Raises:
        ParameterError: If the name of the archive has no extension
        DownloadError: If the archive cannot be downloaded or fails the checksum twice
        DataFileError: If the verified archive cannot be extracted or its files
            cannot replace the directory of the dataset
    """
    stem = _stem(filepath.name)
    if stem == filepath.name:
        raise ParameterError(f"The name of the archive {filepath.name} has no extension")
    downloaded = download_file(
        url=url,
        dirpath=filepath.parent,
        filename=filepath.name,
        force=force,
        user_agent=user_agent,
    )
    if not downloaded and not missing:
        return
    if sha256(filepath) != checksum:
        filepath.unlink(missing_ok=True)
        download_file(
            url=url,
            dirpath=filepath.parent,
            filename=filepath.name,
            force=True,
            user_agent=user_agent,
        )
        if sha256(filepath) != checksum:
            filepath.unlink(missing_ok=True)
            raise DownloadError(
                f"The file {filepath} failed the checksum verification and was removed, "
                "download it again"
            )
    target = filepath.parent / stem
    partial = filepath.parent / (stem + ".part")
    shutil.rmtree(partial, ignore_errors=True)
    try:
        extracted = Path(extract_archive(filepath, partial))
        try:
            if target.is_symlink() or target.is_file():
                target.unlink()
            elif target.exists():
                shutil.rmtree(target)
            extracted.rename(target)
        except OSError as e:
            raise DataFileError(f"Cannot replace the directory {target}") from e
    finally:
        shutil.rmtree(partial, ignore_errors=True)


def check_limit(limit: int | None) -> None:
    """
    Checking the number of records

    Arguments:
        limit (int): Number of records; None - no limit

    Raises:
        ParameterError: If the number of records is not an integer or is negative
    """
    if limit is not None:
        check_integer(limit, "number of records")
    if limit is not None and limit < 0:
        raise ParameterError(f"The number of records must not be negative - {limit}")


def fold_diacritics(value: str) -> str:
    """
    Folding the case and the diacritics of a string

    Description:
        The string is lower-cased with str.casefold and decomposed (NFD), and
        the combining marks are dropped, so "Galdós" and "galdos" are the same;
        a letter that is a base letter with a mark in Unicode is folded too
        ("й" gives "и")

    Arguments:
        value (str): String

    Returns:
        str: Folded string

    Example:
        >>> from anyts.datasets import fold_diacritics
        >>> fold_diacritics("Pérez Galdós")
        'perez galdos'
    """
    decomposed = unicodedata.normalize("NFD", value.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def substring_filter(
    field: str, value: str, fold: Callable[[str], str] = fold_diacritics
) -> Filter:
    """
    Filter of the records by a substring of a field

    Description:
        The substring and the field are compared after the folding, by default
        regardless of case and diacritics; the substring is plain text, not a
        regular expression

    Arguments:
        field (str): Name of the field of a record
        value (str): Substring to look for
        fold (callable): Folding of a string before the comparison

    Returns:
        Filter: Predicate on a record

    Raises:
        ParameterError: If the value is not a string

    Example:
        >>> from anyts.datasets import substring_filter
        >>> substring_filter("author", "galdos")({"author": "Benito Pérez Galdós"})
        True
    """
    if not isinstance(value, str):
        raise ParameterError(f"The {field} must be a string, not {type(value).__name__}")
    needle = fold(value)
    return lambda record: needle in fold(record[field])


def length_filters(min_len: int | None, max_len: int | None) -> Filters:
    """
    Filters of the records by the length of the text

    Arguments:
        min_len (int): Minimum length of the text in characters; None - no bound
        max_len (int): Maximum length of the text in characters; None - no bound

    Returns:
        Filters: List of predicates on a record

    Raises:
        ParameterError: If the minimum or the maximum length is not an integer or
            is below one, or the minimum length is greater than the maximum one
    """
    filters: Filters = []
    if min_len is not None:
        check_integer(min_len, "minimum length of the text")
        if min_len < 1:
            raise ParameterError("The minimum length of the text must be greater than 0")
        filters.append(lambda record: len(record["text"]) >= min_len)
    if max_len is not None:
        check_integer(max_len, "maximum length of the text")
        if max_len < 1:
            raise ParameterError("The maximum length of the text must be greater than 0")
        filters.append(lambda record: len(record["text"]) <= max_len)
    if min_len is not None and max_len is not None and min_len > max_len:
        raise ParameterError("The minimum length of the text is greater than the maximum one")
    return filters


def to_path(path: str | Path) -> Path:
    """
    Converting the string form of a path into a Path

    Arguments:
        path (str|Path): Path as a string or a Path

    Returns:
        Path: Path object

    Raises:
        SourceTypeError: If the value is neither a string nor a Path
    """
    if isinstance(path, str):
        return Path(path)
    if isinstance(path, Path):
        return path
    raise SourceTypeError("The path must be a string or a Path")


def download_file(
    url: str,
    dirpath: str | Path,
    filename: str | None = None,
    force: bool = False,
    user_agent: str = USER_AGENT,
) -> str:
    """
    Downloading a file from the network

    Description:
        A broken download leaves no partial file; the server is waited for
        DOWNLOAD_TIMEOUT seconds at most

    Arguments:
        url (str): Address of the file
        dirpath (str|Path): Directory for the downloaded file
        filename (str): Name of the downloaded file; the last part of the address by default
        force (bool): Download the file even if it is already there
        user_agent (str): User-Agent header of the request

    Returns:
        str: Path to the downloaded file; an empty string if it was already there

    Raises:
        DownloadError: If the directory cannot be created, the address names no
            file and no name is given, the name is not a plain name of a file, or
            the file cannot be downloaded
    """
    dirpath = to_path(dirpath)
    try:
        dirpath.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise DownloadError(f"Cannot create the directory {dirpath}") from e
    if not filename:
        filename = Path(urllib.parse.unquote(urllib.parse.urlparse(url).path)).name
    if not filename:
        raise DownloadError(f"The address {url} names no file: give the name of the file")
    if _is_outside(filename) or PureWindowsPath(filename).name != filename:
        raise DownloadError(f"The name of the file {filename} is not a plain name")
    filepath = dirpath.resolve() / filename
    if filepath.is_file() and not force:
        logger.info("The file %s is already downloaded", filepath)
        return ""
    partial = filepath.with_name(filepath.name + ".part")
    try:
        logger.info("Downloading the file %s", url)
        request = urllib.request.Request(url, headers={"User-Agent": user_agent})
        with (
            urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT) as response,
            partial.open("wb") as out_file,
        ):
            shutil.copyfileobj(response, out_file)
        partial.replace(filepath)
    except Exception as e:
        raise DownloadError(f"Cannot download the file {url}") from e
    finally:
        partial.unlink(missing_ok=True)
    logger.info("The file is downloaded: %s", filepath)
    return str(filepath)


def _is_outside(member: str) -> bool:
    """
    Whether the path of an archive member leads outside the directory of extraction

    Description:
        Read as a Windows path, so that both separators, drives and network
        shares are seen: any anchor (a leading separator, a drive, a share) or
        a part ..
    """
    path = PureWindowsPath(member)
    return bool(path.anchor) or ".." in path.parts


def _stem(name: str) -> str:
    """Name of a file without all its extensions: corpus_v1.tar.xz - corpus_v1"""
    while (stem := Path(name).stem) != name:
        name = stem
    return name


def extract_archive(archive_file: str | Path, extract_dir: str | Path | None = None) -> str:
    """
    Extracting the files of a ZIP or TAR archive

    Description:
        Paths leading outside the directory (absolute, with a drive or with
        ..) and links are refused. A root directory that differs from the
        name of the archive without its extensions is renamed to it,
        replacing an earlier extraction

    Arguments:
        archive_file (str|Path): Path to the archive
        extract_dir (str|Path): Directory for the extracted files; the directory of the archive by default

    Returns:
        str: Path to the directory with the extracted files

    Raises:
        DataFileError: If the file is missing or is not a ZIP or TAR archive, the archive is
            corrupted, empty, has paths outside the directory or links, or the
            directory cannot be created
    """
    archive_path = to_path(archive_file).resolve()
    if not archive_path.is_file():
        raise DataFileError(f"The archive {archive_path} is not found")
    extract_path = to_path(extract_dir) if extract_dir else archive_path.parent
    try:
        extract_path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise DataFileError(f"Cannot create the directory {extract_path}") from e
    # A TAR that ends with a ZIP member passes is_zipfile too
    is_tar = tarfile.is_tarfile(archive_path)
    if not is_tar and not zipfile.is_zipfile(archive_path):
        raise DataFileError(f"The file {archive_path} is not a ZIP or TAR archive")
    refused = f"The archive {archive_path} has paths outside the directory or links"

    def check(member: tarfile.TarInfo, path: str) -> tarfile.TarInfo:
        if _is_outside(member.name) or not (member.isfile() or member.isdir()):
            raise DataFileError(refused)
        return tarfile.data_filter(member, path) if TAR_DATA_FILTER else member

    logger.info("Extracting the archive %s", archive_path)
    try:
        if is_tar:
            with tarfile.open(archive_path, mode="r") as tar_file:
                if TAR_DATA_FILTER:
                    tar_file.extractall(extract_path, filter=check)
                else:
                    for member in tar_file:
                        tar_file.extract(check(member, str(extract_path)), extract_path)
                # After the extraction, so that the stream is read once
                members = tar_file.getnames()
        else:
            with zipfile.ZipFile(archive_path, mode="r") as zip_file:
                members = zip_file.namelist()
                if any(_is_outside(member) for member in members):
                    raise DataFileError(refused)
                zip_file.extractall(extract_path)
    except (OSError, zipfile.BadZipFile, tarfile.TarError) as e:
        raise DataFileError(f"Cannot extract the archive {archive_path}") from e
    if not members:
        raise DataFileError(f"The archive {archive_path} has no files")
    src_basename = os.path.commonpath(members)
    if src_basename and not (extract_path / src_basename).is_dir():
        src_basename = str(Path(src_basename).parent)
    if not src_basename or src_basename == ".":
        return str(extract_path)
    dest_basename = _stem(archive_path.name)
    if src_basename != dest_basename:
        destination = extract_path / dest_basename
        if destination.is_dir():
            shutil.rmtree(destination)
        return str(shutil.move(extract_path / src_basename, destination))
    return str(extract_path / src_basename)


def sha256(path: Path) -> str:
    """
    Computing the SHA-256 checksum of a file

    Arguments:
        path (Path): Path to the file

    Returns:
        str: Hexadecimal checksum; an empty string for a missing file
    """
    if not path.is_file():
        return ""
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()
