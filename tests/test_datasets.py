import hashlib
import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from anyts import datasets
from anyts.datasets import (
    Dataset,
    check_limit,
    download_file,
    extract_archive,
    fetch_archive,
    fold_diacritics,
    length_filters,
    sha256,
    substring_filter,
    to_path,
)
from anyts.exceptions import DataFileError, DownloadError, ParameterError, SourceTypeError


class IncompleteDataset(Dataset):
    def __init__(self, name, meta):
        super().__init__(name, meta)


class MinimalDataset(Dataset):
    def __init__(self, name, meta=None):
        super().__init__(name, meta)

    def __iter__(self):
        return super().__iter__()

    def check_data(self):
        return super().check_data()

    def get_texts(self, *args):
        return super().get_texts()

    def get_records(self, *args):
        return super().get_records()

    def download(self, force=False):
        return super().download()


class NamedDataset(MinimalDataset):
    repr_name = "Corpus"
    name_key = "title"


@pytest.fixture(scope="module")
def dataset():
    return MinimalDataset("test", {"a": "1", "b": "2"})


def test_repr(dataset):
    assert repr(dataset) == "Dataset('test')"
    assert repr(NamedDataset("test")) == "Corpus('test')"


def test_info(dataset):
    assert dataset.info == {"name": "test", "a": "1", "b": "2"}
    assert list(dataset.info) == ["name", "a", "b"]
    assert MinimalDataset("empty").info == {"name": "empty"}
    assert NamedDataset("test", {"a": "1"}).info == {"title": "test", "a": "1"}


def test_abstract():
    with pytest.raises(TypeError):
        IncompleteDataset("", {})


@pytest.mark.parametrize(
    "name", ["__iter__", "check_data", "get_texts", "get_records", "download"]
)
def test_methods(dataset, name):
    with pytest.raises(NotImplementedError):
        getattr(dataset, name)()


def test_check_limit():
    check_limit(None)
    check_limit(0)
    with pytest.raises(ParameterError, match=r"^The number of records must not be negative"):
        check_limit(-1)
    with pytest.raises(ParameterError, match=r"must be an integer, not float$"):
        check_limit(1.5)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("pérez galdós", "perez galdos"),
        ("GALDÓS", "galdos"),
        ("Straße", "strasse"),
        ("Ñandú", "nandu"),
        ("", ""),
    ],
)
def test_fold_diacritics(value, expected):
    assert fold_diacritics(value) == expected


@pytest.mark.parametrize("value", ["galdos", "GALDÓS", "Pérez", "perez galdos", "Galdó"])
def test_substring_filter(value):
    assert substring_filter("author", value)({"author": "Benito Pérez Galdós"})


def test_substring_filter_miss():
    predicate = substring_filter("country", "españa")
    assert predicate({"country": "España"})
    assert not predicate({"country": "Argentina"})
    # Characters of regular expressions are plain characters
    assert not substring_filter("title", ".")({"title": "Azul"})
    assert substring_filter("title", ".")({"title": "Azul..."})


def test_substring_filter_fold():
    exact = substring_filter("author", "Galdós", fold=str)
    assert exact({"author": "Benito Pérez Galdós"})
    assert not exact({"author": "Benito Perez Galdos"})


def test_substring_filter_type():
    with pytest.raises(ParameterError, match=r"^The author must be a string, not int$"):
        substring_filter("author", 5)


def test_length_filters():
    records = [{"text": "a" * size} for size in (1, 5, 10)]
    filters = length_filters(2, 9)
    assert [len(r["text"]) for r in records if all(f(r) for f in filters)] == [5]
    assert length_filters(None, None) == []


@pytest.mark.parametrize(
    ("min_len", "max_len"), [(0, None), (None, 0), (-1, None), (10, 5), (2.0, None), (None, "9")]
)
def test_length_filters_errors(min_len, max_len):
    with pytest.raises(ParameterError):
        length_filters(min_len, max_len)


def test_to_path():
    assert to_path("/usr/local/") == Path("/usr/local/")
    path = Path("/usr/local/")
    assert to_path(path) is path


@pytest.mark.parametrize("path", [666, ["a", "b"], {"a": "b"}])
def test_to_path_type_error(path):
    with pytest.raises(SourceTypeError, match=r"^The path must be a string or a Path$"):
        to_path(path)


@pytest.fixture
def online(monkeypatch):
    """The network replaced by an answer with fixed bytes; the requests are recorded"""
    requests = []

    def fake_urlopen(request, timeout=None):
        requests.append((request.full_url, request.get_header("User-agent"), timeout))
        return io.BytesIO(b"data")

    monkeypatch.setattr(datasets.urllib.request, "urlopen", fake_urlopen)
    return requests


def test_download_file(tmp_path, online):
    url = "https://example.com/files/data%20v1.txt"
    assert download_file(url, tmp_path) == str(tmp_path / "data v1.txt")
    assert (tmp_path / "data v1.txt").read_bytes() == b"data"
    assert download_file(url, tmp_path) == ""
    assert download_file(url, str(tmp_path), filename="copy.txt") == str(tmp_path / "copy.txt")
    assert download_file(url, tmp_path, force=True, user_agent="library") == str(
        tmp_path / "data v1.txt"
    )
    assert sorted(path.name for path in tmp_path.iterdir()) == ["copy.txt", "data v1.txt"]
    assert online == [
        (url, "anyTS", datasets.DOWNLOAD_TIMEOUT),
        (url, "anyTS", datasets.DOWNLOAD_TIMEOUT),
        (url, "library", datasets.DOWNLOAD_TIMEOUT),
    ]


@pytest.mark.parametrize(
    ("url", "name"),
    [
        ("https://example.com/files/data+v1.zip", "data+v1.zip"),
        ("https://example.com/files/a%23b.txt?download=1#top", "a#b.txt"),
    ],
)
def test_download_file_name(tmp_path, online, url, name):
    assert download_file(url, tmp_path) == str(tmp_path / name)


def test_download_file_without_a_name(tmp_path, online):
    with pytest.raises(DownloadError, match="names no file"):
        download_file("https://example.com/", tmp_path)
    for url, name in (
        ("https://example.com/files/C:data.zip", None),
        ("https://example.com/a", "../a"),
        ("https://example.com/a%00b.zip", None),
        ("https://example.com/a", "a\x00b.zip"),
    ):
        with pytest.raises(DownloadError, match="is not a plain name"):
            download_file(url, tmp_path, filename=name)
    with pytest.raises(DownloadError, match="is not a plain name"):
        download_file("https://example.com/a", tmp_path, filename="sub\\a.zip")
    assert online == []


def test_download_file_interrupted(tmp_path, monkeypatch):
    class InterruptedResponse(io.BytesIO):
        def read(self, size=-1):
            if self.tell():
                raise KeyboardInterrupt
            return super().read(4)

    monkeypatch.setattr(
        datasets.urllib.request,
        "urlopen",
        lambda *args, **kwargs: InterruptedResponse(b"data" * 4),
    )
    with pytest.raises(KeyboardInterrupt):
        download_file("https://example.com/data.zip", tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_download_file_partial_cleanup(tmp_path, monkeypatch):
    class BrokenResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, size=-1):
            raise OSError("connection reset")

    monkeypatch.setattr(
        datasets.urllib.request, "urlopen", lambda *args, **kwargs: BrokenResponse()
    )
    with pytest.raises(DownloadError, match=r"^Cannot download the file"):
        download_file("https://example.com/data.zip", tmp_path, force=True)
    assert list(tmp_path.iterdir()) == []


def test_download_file_mkdir_error(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("not a directory", encoding="utf-8")
    with pytest.raises(DownloadError, match=r"^Cannot create the directory"):
        download_file("https://example.com/data.zip", blocker / "data")


def test_extract_archive_traversal(tmp_path):
    payload = tmp_path / "payload.txt"
    payload.write_text("evil", encoding="utf-8")
    archive = tmp_path / "evil.tar"
    with tarfile.open(archive, mode="w") as tar_file:
        tar_file.add(payload, arcname="../evil.txt")
    with pytest.raises(DataFileError):
        extract_archive(archive, tmp_path / "out")
    assert not (tmp_path / "evil.txt").exists()
    zipped = tmp_path / "evil.zip"
    with zipfile.ZipFile(zipped, "w") as zip_file:
        zip_file.writestr("../evil.txt", "evil")
    with pytest.raises(DataFileError, match="outside the directory"):
        extract_archive(zipped, tmp_path / "zip_out")
    assert not (tmp_path / "evil.txt").exists()
    assert not (tmp_path / "zip_out" / "evil.txt").exists()
    broken = tmp_path / "broken.zip"
    with zipfile.ZipFile(broken, "w") as zip_file:
        zip_file.writestr("good.txt", "good")
    broken.write_bytes(b"\x00" * 4 + broken.read_bytes()[4:])
    with pytest.raises(DataFileError, match=r"^Cannot extract the archive"):
        extract_archive(broken, tmp_path / "broken_out")


def _tar(path: Path, members: dict[str, str]) -> bytes:
    """A TAR.XZ archive of text members, written to the path; its bytes"""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:xz") as archive:
        for name, content in members.items():
            data = content.encode("utf-8")
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
    path.write_bytes(buffer.getvalue())
    return buffer.getvalue()


@pytest.fixture
def tar_archive(tmp_path):
    path = tmp_path / "corpus_v1.tar.xz"
    _tar(path, {"corpus/prose/a.txt": "text", "corpus/metadata.tsv": "text"})
    return path


def test_extract_archive_zip(tmp_path):
    path = tmp_path / "words.zip"
    with zipfile.ZipFile(path, mode="w") as archive:
        archive.writestr("words/first", "the\na\n")
        archive.writestr("words/second", "of\n")
    extract_dir = tmp_path / "extract"
    assert extract_archive(path, extract_dir=extract_dir) == str(extract_dir / "words")
    assert (extract_dir / "words" / "first").is_file()


def test_extract_archive_tar_renames_root(tar_archive):
    extracted = extract_archive(tar_archive)
    assert extracted == str(tar_archive.parent / "corpus_v1")
    assert (Path(extracted) / "prose" / "a.txt").is_file()
    # A second extraction replaces the renamed directory instead of nesting a copy in it
    assert extract_archive(str(tar_archive)) == extracted
    assert not (Path(extracted) / "corpus").exists()


def test_extract_archive_missing(tmp_path):
    with pytest.raises(DataFileError, match=r"is not found$"):
        extract_archive(tmp_path / "missing.zip")


def test_extract_archive_not_an_archive(tmp_path):
    not_an_archive = tmp_path / "words.tar.xz"
    not_an_archive.write_text("the\na\n", encoding="utf-8")
    with pytest.raises(DataFileError, match=r"is not a ZIP or TAR archive$"):
        extract_archive(not_an_archive)


def test_extract_archive_mkdir_error(tar_archive):
    blocker = tar_archive.parent / "file"
    blocker.write_text("not a directory", encoding="utf-8")
    with pytest.raises(DataFileError, match=r"^Cannot create the directory"):
        extract_archive(tar_archive, blocker / "out")


def test_extract_archive_single_file(tmp_path):
    nested = tmp_path / "nested.zip"
    with zipfile.ZipFile(nested, "w") as zip_file:
        zip_file.writestr("corpus-abc/corpus.xml", "<items />")
    extracted = Path(extract_archive(nested, tmp_path))
    assert extracted == tmp_path / "nested"
    assert (extracted / "corpus.xml").read_text() == "<items />"
    flat = tmp_path / "flat.zip"
    with zipfile.ZipFile(flat, "w") as zip_file:
        zip_file.writestr("corpus.xml", "<items />")
    assert extract_archive(flat, tmp_path / "flat") == str(tmp_path / "flat")
    assert (tmp_path / "flat" / "corpus.xml").read_text() == "<items />"


def test_extract_archive_same_root(tmp_path):
    path = tmp_path / "words.zip"
    with zipfile.ZipFile(path, mode="w") as archive:
        archive.writestr("words/a/first", "the\n")
        archive.writestr("words/b/second", "of\n")
    assert extract_archive(path, tmp_path / "out") == str(tmp_path / "out" / "words")


def test_extract_archive_dotted_names(tmp_path):
    archive = tmp_path / "dotted.zip"
    with zipfile.ZipFile(archive, "w") as zip_file:
        zip_file.writestr("dotted-abc/README.md", "readme")
        zip_file.writestr("dotted-abc/a/What....txt", "text")
        zip_file.writestr("dotted-abc/a/normal.txt", "text")
    extracted = Path(extract_archive(archive, tmp_path))
    assert extracted == tmp_path / "dotted"
    assert sorted(path.name for path in extracted.joinpath("a").iterdir()) == [
        "What....txt",
        "normal.txt",
    ]


def test_extract_archive_empty(tmp_path):
    empty_tar = tmp_path / "empty.tar.xz"
    with tarfile.open(empty_tar, mode="w:xz"):
        pass
    with pytest.raises(DataFileError, match="has no files"):
        extract_archive(empty_tar, tmp_path / "tar_out")
    empty_zip = tmp_path / "empty.zip"
    with zipfile.ZipFile(empty_zip, "w"):
        pass
    with pytest.raises(DataFileError, match="has no files"):
        extract_archive(empty_zip, tmp_path / "zip_out")


def test_extract_archive_without_the_data_filter(tar_archive, tmp_path, monkeypatch):
    # Python 3.11 before 3.11.4 has no filter: the members are checked by hand
    monkeypatch.setattr(datasets, "TAR_DATA_FILTER", False)
    extracted = extract_archive(tar_archive, tmp_path / "out")
    assert (Path(extracted) / "prose" / "a.txt").read_text(encoding="utf-8") == "text"
    payload = tmp_path / "payload.txt"
    payload.write_text("evil", encoding="utf-8")
    outside = tmp_path / "outside.tar"
    with tarfile.open(outside, mode="w") as tar_file:
        tar_file.add(payload, arcname="../evil.txt")
    with pytest.raises(DataFileError, match="outside"):
        extract_archive(outside, tmp_path / "outside_out")
    assert not (tmp_path / "evil.txt").exists()
    linked = tmp_path / "linked.tar"
    with tarfile.open(linked, mode="w") as tar_file:
        link = tarfile.TarInfo("corpus/link")
        link.type = tarfile.SYMTYPE
        link.linkname = "/etc/passwd"
        tar_file.addfile(link)
    with pytest.raises(DataFileError, match="links"):
        extract_archive(linked, tmp_path / "linked_out")
    assert not (tmp_path / "linked_out" / "corpus" / "link").exists()


@pytest.mark.parametrize(
    ("member", "outside"),
    [
        ("/x", True),
        ("//x", True),
        ("C:/x", True),
        ("C:x", True),
        ("\\\\server\\share\\x", True),
        ("\\x", True),
        ("../x", True),
        ("a\\..\\b", True),
        ("corpus/a.txt", False),
        ("corpus/", False),
        ("What....txt", False),
    ],
)
def test_is_outside(member, outside):
    assert datasets._is_outside(member) is outside


def _tar_member(archive: tarfile.TarFile, name: str, data: bytes = b"text") -> None:
    info = tarfile.TarInfo(name)
    info.size = len(data)
    archive.addfile(info, io.BytesIO(data))


@pytest.mark.parametrize("data_filter", [True, False])
def test_extract_archive_absolute_member(tmp_path, monkeypatch, data_filter):
    if data_filter and not datasets.TAR_DATA_FILTER:
        pytest.skip("tarfile has no data filter")
    monkeypatch.setattr(datasets, "TAR_DATA_FILTER", data_filter)
    victim = tmp_path / "victim"
    victim.mkdir()
    (victim / "mine.txt").write_text("mine", encoding="utf-8")
    archive = tmp_path / "corpus.tar"
    with tarfile.open(archive, mode="w") as tar_file:
        _tar_member(tar_file, (victim / "a.txt").as_posix())
    with pytest.raises(DataFileError, match="outside the directory or links"):
        extract_archive(archive, tmp_path / "out")
    assert (victim / "mine.txt").read_text(encoding="utf-8") == "mine"
    assert not (victim / "a.txt").exists()


@pytest.mark.parametrize("name", ["//abs/a.txt", "C:/data/a.txt", "\\\\server\\share\\a.txt"])
def test_extract_archive_absolute_zip_member(tmp_path, name):
    archive = tmp_path / "corpus.zip"
    with zipfile.ZipFile(archive, "w") as zip_file:
        zip_file.writestr(name, "text")
    with pytest.raises(DataFileError, match="outside the directory or links"):
        extract_archive(archive, tmp_path / "out")


@pytest.mark.parametrize("data_filter", [True, False])
def test_extract_archive_refuses_inner_links(tmp_path, monkeypatch, data_filter):
    if data_filter and not datasets.TAR_DATA_FILTER:
        pytest.skip("tarfile has no data filter")
    monkeypatch.setattr(datasets, "TAR_DATA_FILTER", data_filter)
    for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
        archive = tmp_path / f"corpus{kind!r}.tar"
        with tarfile.open(archive, mode="w") as tar_file:
            _tar_member(tar_file, "corpus/a.txt")
            link = tarfile.TarInfo("corpus/link.txt")
            link.type = kind
            link.linkname = "a.txt" if kind == tarfile.SYMTYPE else "corpus/a.txt"
            tar_file.addfile(link)
        with pytest.raises(DataFileError, match="outside the directory or links"):
            extract_archive(archive, tmp_path / "out")
        assert not (tmp_path / "out" / "corpus" / "link.txt").exists()


def test_extract_archive_tar_ending_with_a_zip(tmp_path):
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, "w") as zip_file:
        zip_file.writestr("inner/readme.txt", "readme")
    archive = tmp_path / "corpus_v1.tar"
    with tarfile.open(archive, mode="w") as tar_file:
        _tar_member(tar_file, "corpus_v1/a.txt")
        _tar_member(tar_file, "corpus_v1/extra.zip", inner.getvalue())
    assert zipfile.is_zipfile(archive)
    extracted = Path(extract_archive(archive, tmp_path / "out"))
    assert sorted(path.name for path in extracted.iterdir()) == ["a.txt", "extra.zip"]


def test_sha256(tmp_path):
    path = tmp_path / "data.txt"
    path.write_bytes(b"anyTS")
    assert sha256(path) == hashlib.sha256(b"anyTS").hexdigest()
    assert sha256(tmp_path / "missing.txt") == ""


MEMBERS = {"corpus_v1/a.txt": "first", "corpus_v1/b/c.txt": "second"}


@pytest.fixture
def remote(tmp_path, monkeypatch):
    """The archive of a dataset behind a fake download_file; the calls are recorded"""
    source = tmp_path / "remote.tar.xz"
    archive = _tar(source, MEMBERS)
    calls = []

    def fake_download(url, dirpath, filename=None, force=False, user_agent=None):
        calls.append((force, user_agent))
        path = Path(dirpath) / filename
        if path.is_file() and not force:
            return ""
        path.write_bytes(source.read_bytes())
        return str(path)

    monkeypatch.setattr(datasets, "download_file", fake_download)
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir / "corpus_v1.tar.xz", hashlib.sha256(archive).hexdigest(), source, calls


def _fetch(filepath, checksum, force=False, missing=None, **kwargs):
    root = filepath.parent / "corpus_v1"
    if missing is None:
        missing = not (root / "a.txt").is_file() or not (root / "b" / "c.txt").is_file()
    fetch_archive(
        "https://example.com/corpus_v1.tar.xz", filepath, checksum, missing, force, **kwargs
    )
    return root


def test_fetch_archive(remote):
    filepath, checksum, _, calls = remote
    root = _fetch(filepath, checksum)
    assert (root / "a.txt").read_text(encoding="utf-8") == "first"
    assert (root / "b" / "c.txt").read_text(encoding="utf-8") == "second"
    assert calls == [(False, "anyTS")]
    assert sorted(path.name for path in filepath.parent.iterdir()) == [
        "corpus_v1",
        "corpus_v1.tar.xz",
    ]


def test_fetch_archive_keeps_extracted_files(remote):
    filepath, checksum, _, calls = remote
    root = _fetch(filepath, checksum)
    (root / "a.txt").write_text("changed", encoding="utf-8")
    _fetch(filepath, checksum)
    assert calls == [(False, "anyTS"), (False, "anyTS")]
    assert (root / "a.txt").read_text(encoding="utf-8") == "changed"


def test_fetch_archive_restores_missing_files(remote):
    filepath, checksum, _, calls = remote
    root = _fetch(filepath, checksum)
    (root / "stray.txt").write_text("stray", encoding="utf-8")
    (root / "b" / "c.txt").unlink()
    _fetch(filepath, checksum)
    assert calls == [(False, "anyTS"), (False, "anyTS")]
    assert (root / "b" / "c.txt").read_text(encoding="utf-8") == "second"
    assert not (root / "stray.txt").exists()


def test_fetch_archive_force(remote):
    filepath, checksum, _, calls = remote
    _fetch(filepath, checksum)
    _fetch(filepath, checksum, force=True, user_agent="library")
    assert calls == [(False, "anyTS"), (True, "library")]


def test_fetch_archive_replaces_broken_archive(remote):
    filepath, checksum, source, calls = remote
    filepath.write_bytes(b"\x00" * 40)
    root = _fetch(filepath, checksum)
    assert calls == [(False, "anyTS"), (True, "anyTS")]
    assert filepath.read_bytes() == source.read_bytes()
    assert (root / "a.txt").is_file()


def test_fetch_archive_checksum_error(remote):
    filepath, _, _, calls = remote
    with pytest.raises(DownloadError, match="failed the checksum verification"):
        _fetch(filepath, "0" * 64)
    assert calls == [(False, "anyTS"), (True, "anyTS")]
    assert not filepath.exists()
    assert not (filepath.parent / "corpus_v1").exists()


def test_fetch_archive_without_an_extension(remote):
    filepath, checksum, _, calls = remote
    with pytest.raises(ParameterError, match="has no extension"):
        _fetch(filepath.with_name("corpus_v1"), checksum)
    assert calls == []


def test_fetch_archive_replaces_a_link(remote):
    filepath, checksum, _, _ = remote
    elsewhere = filepath.parent.parent / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "a.txt").write_text("elsewhere", encoding="utf-8")
    try:
        (filepath.parent / "corpus_v1").symlink_to(elsewhere, target_is_directory=True)
    except OSError:
        pytest.skip("symbolic links are not available")
    root = _fetch(filepath, checksum, missing=True)
    assert not root.is_symlink()
    assert (root / "b" / "c.txt").is_file()
    assert (elsewhere / "a.txt").read_text(encoding="utf-8") == "elsewhere"


def test_fetch_archive_cannot_replace(remote, monkeypatch):
    filepath, checksum, _, _ = remote
    _fetch(filepath, checksum)

    rmtree = datasets.shutil.rmtree

    def failing(path, ignore_errors=False):
        if not ignore_errors:
            raise PermissionError(path)
        rmtree(path, ignore_errors=True)

    monkeypatch.setattr(datasets.shutil, "rmtree", failing)
    with pytest.raises(DataFileError, match=r"^Cannot replace the directory"):
        _fetch(filepath, checksum, missing=True)


def test_fetch_archive_interrupted_extraction(remote, monkeypatch):
    filepath, checksum, _, _ = remote
    root = _fetch(filepath, checksum)
    (root / "a.txt").write_text("earlier", encoding="utf-8")
    (root / "b" / "c.txt").unlink()

    def broken_extract(archive_file, extract_dir=None):
        # The first members are written, then the extraction stops
        folder = Path(extract_dir) / "corpus_v1" / "b"
        folder.mkdir(parents=True)
        (folder / "c.txt").write_text("second", encoding="utf-8")
        raise KeyboardInterrupt

    extract = datasets.extract_archive
    monkeypatch.setattr(datasets, "extract_archive", broken_extract)
    with pytest.raises(KeyboardInterrupt):
        _fetch(filepath, checksum)
    # The earlier directory stays as it was and the partial one is gone
    assert (root / "a.txt").read_text(encoding="utf-8") == "earlier"
    assert not (filepath.parent / "corpus_v1.part").exists()
    monkeypatch.setattr(datasets, "extract_archive", extract)
    _fetch(filepath, checksum)
    assert (root / "a.txt").read_text(encoding="utf-8") == "first"
    assert (root / "b" / "c.txt").is_file()
