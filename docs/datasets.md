# Datasets

!!! info ""
    **anyts.datasets**

The base of a dataset and the functions that download, verify and extract its archive and filter its records.

## Dataset

<!-- --8<-- [start:Dataset] -->
An abstract dataset: a name, a dictionary of reference information `meta` and the methods a dataset implements - iteration over the records, `check_data`, `get_texts`, `get_records` and `download(force=False)`. `repr` gives the name of the class and the name of the dataset, `<repr_name>('<name>')`, and the property `info` is the name under the key `name_key` followed by `meta`.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `name` | str | `-` | Name of the dataset |
| `meta` | dict | `None` | Reference information about the dataset |
<!-- --8<-- [end:Dataset] -->

<!-- --8<-- [start:Dataset-hooks] -->
The class attributes `repr_name` and `name_key` are the name of the class in `repr` and the key of the name in `info`; a language library overrides them in a subclass.
<!-- --8<-- [end:Dataset-hooks] -->

In the core `repr_name` is `"Dataset"` and `name_key` is `"name"`.

## fetch_archive

<!-- --8<-- [start:fetch_archive] -->
Downloads the archive of a dataset, verifies it and extracts the files. The archive is verified and extracted when it is downloaded now or when `missing` says the extracted files are not all in place. An archive that fails the SHA-256 checksum, given in either case, is removed and downloaded again once, and a second failure raises `DownloadError`. The files are extracted aside, next to the archive, and replace the directory of the dataset (or a link in its place) only once the extraction is complete; the earlier directory is moved aside first and removed only once the new files are in place, so an interrupted extraction or a failed replacement leaves the earlier files as they were, and concurrent calls do not share their partial files. The name of the archive must have an extension, since the directory is named after the archive without it; otherwise `ParameterError` is raised before the download.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `url` | str | `-` | Address of the archive |
| `filepath` | str/Path | `-` | Path to the archive; the files are extracted into its directory, under the name of the archive without its extensions |
| `checksum` | str | `-` | SHA-256 checksum of the archive |
| `missing` | bool | `-` | Whether the extracted files are missing |
| `force` | bool | `False` | Download the archive even if it is already there |
| `user_agent` | str | `USER_AGENT` | User-Agent header of the request, the name of the library |
<!-- --8<-- [end:fetch_archive] -->

## download_file

<!-- --8<-- [start:download_file] -->
Downloads a file into a directory and returns its path, or an empty string if the file is already there and `force` is off. The name of the file is the last part of the path of the address, decoded; an address without one needs `filename`, and a name with a drive or a separator raises `DownloadError`. The file is written under a temporary name of its own and renamed once it is complete, so a broken, interrupted or cut download - shorter than the length the server announced - raises `DownloadError` and leaves no partial file, and concurrent downloads do not share their partial files; the server is waited for `DOWNLOAD_TIMEOUT` (60) seconds at most.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `url` | str | `-` | Address of the file |
| `dirpath` | str/Path | `-` | Directory for the downloaded file |
| `filename` | str | `None` | Name of the downloaded file; the last part of the address by default |
| `force` | bool | `False` | Download the file even if it is already there |
| `user_agent` | str | `USER_AGENT` | User-Agent header of the request, the name of the library |
<!-- --8<-- [end:download_file] -->

In the core `USER_AGENT` is `"anyTS"`; a language library passes its own name.

## extract_archive

<!-- --8<-- [start:extract_archive] -->
Extracts a ZIP or TAR archive and returns the directory with the files. Paths leading outside the directory - absolute, with a drive or a network share, or with `..` - and links are refused before anything is written, whatever the version of Python. The archive is extracted aside and put in place only once complete: a single root directory takes the name of the archive without its extensions (`corpus_v1.tar.xz` - `corpus_v1`) with its subdirectories, replacing an earlier extraction, and the files of an archive without one root go into the directory, replacing those of the same names and keeping the others; a file in the place of a directory or the other way round is refused before anything is replaced. A missing file, a file that is not an archive, a corrupted or empty archive, a directory that cannot be created and files that cannot be replaced raise `DataFileError`.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `archive_file` | str/Path | `-` | Path to the archive |
| `extract_dir` | str/Path | `None` | Directory for the extracted files; the directory of the archive by default |
<!-- --8<-- [end:extract_archive] -->

## sha256

<!-- --8<-- [start:sha256] -->
Computes the SHA-256 checksum of a file as a hexadecimal string in lower case; a missing file gives an empty string.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `path` | str/Path | `-` | Path to the file |
<!-- --8<-- [end:sha256] -->

## to_path

<!-- --8<-- [start:to_path] -->
Converts a string or a `Path` into a `Path`, expanding a leading `~` into the home directory; any other value raises `SourceTypeError`.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `path` | str/Path | `-` | Path as a string or a Path |
<!-- --8<-- [end:to_path] -->

## Filters of the records

<!-- --8<-- [start:check_limit] -->
`check_limit(limit)` checks the number of records to take: `None` or a non-negative integer, otherwise `ParameterError`.
<!-- --8<-- [end:check_limit] -->

<!-- --8<-- [start:length_filters] -->
`length_filters(min_len, max_len)` returns the predicates that keep the records whose field `text` is at least `min_len` and at most `max_len` characters long; `None` sets no bound. A bound that is not an integer or is below one, or a minimum greater than the maximum, raises `ParameterError`.
<!-- --8<-- [end:length_filters] -->

<!-- --8<-- [start:substring_filter] -->
`substring_filter(field, value, fold)` returns the predicate that keeps the records whose field holds the substring `value`. Both are folded by `fold` before the comparison, so that the differences of case and diacritics a language ignores do not count; the substring is plain text, not a regular expression, a field that is not a string does not match, and a value that is not a string raises `ParameterError`.
<!-- --8<-- [end:substring_filter] -->

In the core `fold` is `fold_diacritics`.

<!-- --8<-- [start:fold_diacritics] -->
`fold_diacritics(value)` lower-cases a string (`str.casefold`), decomposes it (NFD) and drops the combining marks, so `Galdós` and `galdos` are the same. A letter that Unicode decomposes into a base letter and a mark is folded too (`й` gives `и`); a language where such a letter is a letter of its own passes another `fold`.
<!-- --8<-- [end:fold_diacritics] -->

!!! example "Example"

    ``` python
    from anyts.datasets import fold_diacritics, length_filters, substring_filter

    records = [
        {"author": "Benito Pérez Galdós", "text": "A long text of the novel"},
        {"author": "Rubén Darío", "text": "A poem"},
    ]
    filters = [substring_filter("author", "galdos"), *length_filters(10, None)]
    [record["author"] for record in records if all(f(record) for f in filters)]
    # ['Benito Pérez Galdós']
    fold_diacritics("Pérez Galdós")
    # 'perez galdos'
    ```
