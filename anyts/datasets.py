import errno
import hashlib
import logging
import os
import shutil
import tarfile
import unicodedata
import urllib.parse
import urllib.request
import uuid
import zipfile
from abc import ABCMeta, abstractmethod
from collections.abc import Callable, Iterator
from pathlib import Path, PurePosixPath, PureWindowsPath
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

# The starts of a path that expandusers turns into the home directory
_HOME = tuple(f"~{sep}" for sep in (os.sep, os.altsep) if sep)


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
    filepath: str | Path,
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
        directory of the dataset only once the extraction is complete, and the
        earlier directory is removed only once they are in place; concurrent
        calls do not share their partial files

    Arguments:
        url (str): Address of the archive
        filepath (str|Path): Path to the archive; the files are extracted into its directory
        checksum (str): SHA-256 checksum of the archive, in either case
        missing (bool): Whether the extracted files are missing
        force (bool): Download the archive even if it is already there
        user_agent (str): User-Agent header of the request

    Raises:
        ParameterError: If the name of the archive has no extension
        DownloadError: If the archive cannot be downloaded or fails the checksum twice
        DataFileError: If the verified archive cannot be extracted or its files
            cannot replace the directory of the dataset
    """
    filepath = to_path(filepath)
    checksum = checksum.lower()
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
    partial = _partial(target)
    try:
        partial.mkdir()
        extracted = Path(extract_archive(filepath, partial))
        _replace(extracted, target)
    except OSError as e:
        raise DataFileError(f"Cannot replace the directory {target}") from e
    finally:
        shutil.rmtree(partial, ignore_errors=True)


def _partial(path: Path) -> Path:
    """Path next to the given one, unique to the call, for its partial file or directory"""
    return path.with_name(f".{path.name}.{uuid.uuid4().hex[:12]}.part")


def _replace(source: Path, target: Path) -> None:
    """
    Putting a file or a directory in place of another one

    Description:
        The earlier target is moved aside and removed only once the source is
        in place; it is put back when the source cannot take its place. A target
        that a concurrent call moves away or puts in place meanwhile is taken as
        it is
    """
    aside = _partial(target)
    backup: Path | None = aside
    try:
        target.rename(aside)
    except FileNotFoundError:
        backup = None
    try:
        source.rename(target)
    except OSError as error:
        if _taken(error, target):
            return
        if backup is not None:
            try:
                backup.rename(target)
            except OSError as restore_error:
                if _taken(restore_error, target):
                    return
                raise
            backup = None
        raise
    finally:
        if backup is not None:
            if backup.is_dir() and not backup.is_symlink():
                shutil.rmtree(backup, ignore_errors=True)
            else:
                backup.unlink(missing_ok=True)


def _taken(error: OSError, target: Path) -> bool:
    """Whether a rename failed because a concurrent call has put its target in place"""
    return error.errno in (errno.EEXIST, errno.ENOTEMPTY) or target.exists()


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
        regular expression, and a field that is not a string does not match

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
    return lambda record: isinstance(text := record[field], str) and needle in fold(text)


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

    Description:
        A leading ~, alone or before a separator, is expanded into the home
        directory

    Arguments:
        path (str|Path): Path as a string or a Path

    Returns:
        Path: Path object

    Raises:
        SourceTypeError: If the value is neither a string nor a Path
    """
    if isinstance(path, str | Path):
        text = str(path)
        return Path(path).expanduser() if text == "~" or text.startswith(_HOME) else Path(path)
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
        A broken or cut download, shorter than the Content-Length of the
        answer, leaves no partial file, and concurrent downloads do not share
        their partial files; the server is waited for DOWNLOAD_TIMEOUT seconds
        at most

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
    if "\x00" in filename or _is_outside(filename) or PureWindowsPath(filename).name != filename:
        raise DownloadError(f"The name of the file {filename} is not a plain name")
    filepath = dirpath.resolve() / filename
    if filepath.is_file() and not force:
        logger.info("The file %s is already downloaded", filepath)
        return ""
    partial = _partial(filepath)
    try:
        logger.info("Downloading the file %s", url)
        request = urllib.request.Request(url, headers={"User-Agent": user_agent})
        with (
            urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT) as response,
            partial.open("xb") as out_file,
        ):
            shutil.copyfileobj(response, out_file)
            length = response.headers.get("Content-Length", "")
            if length.isdigit() and out_file.tell() != int(length):
                raise DownloadError(
                    f"Cannot download the file {url}: received {out_file.tell()} of {length} bytes"
                )
        partial.replace(filepath)
    except DownloadError:
        raise
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
        ..) and links are refused. The archive is extracted aside and put in
        place only once complete: a single root directory takes the name of
        the archive without its extensions, replacing an earlier extraction;
        the files of an archive without one root go into the directory,
        replacing those of the same names and keeping the others, once none of
        them would replace a directory or the other way round

    Arguments:
        archive_file (str|Path): Path to the archive
        extract_dir (str|Path): Directory for the extracted files; the directory of the archive by default

    Returns:
        str: Path to the directory with the extracted files

    Raises:
        DataFileError: If the file is missing or is not a ZIP or TAR archive, the archive is
            corrupted, empty, has paths outside the directory or links, its files
            would replace it or put a file in the place of a directory or the
            other way round, or the directory cannot be created or its files
            replaced
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
    stem = _stem(archive_path.name)
    partial = _partial(extract_path / stem)
    try:
        partial.mkdir()
        members = _extract(archive_path, is_tar, partial)
        roots = {parts[0] for member in members if (parts := PurePosixPath(member).parts)}
        if len(roots) == 1 and (partial / (root := roots.pop())).is_dir():
            destination = extract_path / stem
            _check_not_the_archive(destination, archive_path)
            _replace(partial / root, destination)
            return str(destination)
        entries = [
            (entry, extract_path / entry.relative_to(partial))
            for entry in sorted(partial.rglob("*"))
        ]
        for entry, destination in entries:
            _check_merge(entry, destination, archive_path)
        for entry, destination in entries:
            if entry.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                _replace(entry, destination)
        return str(extract_path)
    except OSError as e:
        raise DataFileError(f"Cannot extract the archive {archive_path}") from e
    finally:
        shutil.rmtree(partial, ignore_errors=True)


def _check_merge(entry: Path, destination: Path, archive_path: Path) -> None:
    """Refusing a file or a directory of the archive that would replace one of the other kind"""
    if entry.is_file():
        _check_not_the_archive(destination, archive_path)
    if destination.exists() and entry.is_dir() != destination.is_dir():
        kind = "directory" if entry.is_dir() else "file"
        raise DataFileError(
            f"The archive {archive_path} would put a {kind} in the place of {destination}"
        )


def _check_not_the_archive(destination: Path, archive_path: Path) -> None:
    """Refusing a file of the archive that would take the place of the archive itself"""
    if destination.resolve() == archive_path:
        raise DataFileError(
            f"The files of the archive {archive_path} would replace it: give the archive "
            "an extension or extract it into another directory"
        )


def _extract(archive_path: Path, is_tar: bool, extract_path: Path) -> list[str]:
    """
    Extracting the members of an archive; the names of the members

    Description:
        A TAR member is checked as it is extracted, so that the archive is read
        once; a refused member stops the extraction, and the caller removes
        what was written
    """
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
    return members


def sha256(path: str | Path) -> str:
    """
    Computing the SHA-256 checksum of a file

    Arguments:
        path (str|Path): Path to the file

    Returns:
        str: Hexadecimal checksum in lower case; an empty string for a missing file
    """
    path = to_path(path)
    if not path.is_file():
        return ""
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()
