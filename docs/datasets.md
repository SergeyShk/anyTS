# Datasets

The base of a dataset and the functions that download, verify and extract its archive and filter its records.

## Dataset

``` {.python .signature}
Dataset(name, meta=None)
```

<!-- --8<-- [start:Dataset] -->
An abstract dataset: a name, a dictionary of reference information `meta` and the methods a dataset implements - iteration over the records, `check_data`, `get_texts`, `get_records` and `download(force=False)`. `repr` gives the name of the class and the name of the dataset, `<repr_name>('<name>')`, and the property `info` is the name under the key `name_key` followed by `meta`.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `name` | `str` | - | Name of the dataset |
| `meta` | `dict` | `None` | Reference information about the dataset |
<!-- --8<-- [end:Dataset] -->

## Fetching an archive { #fetch_archive }

<!-- --8<-- [start:fetch_archive] -->
``` {.python .signature}
fetch_archive(url, filepath, checksum, missing, force=False, user_agent='anyTS')
```

Downloads the archive of a dataset; when it is just downloaded or `missing` says the extracted files are not all in place, verifies it and extracts the files. The SHA-256 checksum may be in upper or lower case; an archive that fails it is removed and downloaded again once. The files are extracted aside, next to the archive, and replace the directory of the dataset (or a link in its place) only once complete, the earlier directory removed only once they are in place: an interrupted extraction or a failed replacement leaves the earlier files intact, and concurrent calls do not share partial files. The name of the archive needs an extension, since the directory is named after the archive without it.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `url` | `str` | - | Address of the archive |
| `filepath` | `str` / `Path` | - | Path to the archive; the files are extracted into its directory, under the name of the archive without its extensions |
| `checksum` | `str` | - | SHA-256 checksum of the archive |
| `missing` | `bool` | - | Whether the extracted files are missing |
| `force` | `bool` | `False` | Download the archive even if it is already there |
| `user_agent` | `str` | `USER_AGENT` | User-Agent header of the request, the name of the library |

A name of the archive without an extension raises `ParameterError` before the download, an archive that cannot be downloaded or fails the checksum twice `DownloadError`, an archive that cannot be extracted or files that cannot replace the directory of the dataset `DataFileError`, and a path of the archive that is neither a string nor a `Path` `SourceTypeError`.
<!-- --8<-- [end:fetch_archive] -->

## Downloading a file { #download_file }

<!-- --8<-- [start:download_file] -->
``` {.python .signature}
download_file(url, dirpath, filename=None, force=False, user_agent='anyTS')
```

Downloads a file into a directory and returns its path, or an empty string if the file is already there and `force` is off. The name of the file is the decoded last part of the path of the address; an address without one needs `filename`. The file is written under a temporary name and renamed once complete: a broken, interrupted or cut download (shorter than the announced length) leaves no partial file, and concurrent downloads do not share partial files. The server is waited for at most `DOWNLOAD_TIMEOUT` (60) seconds.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `url` | `str` | - | Address of the file |
| `dirpath` | `str` / `Path` | - | Directory for the downloaded file |
| `filename` | `str` | `None` | Name of the downloaded file; the last part of the address by default |
| `force` | `bool` | `False` | Download the file even if it is already there |
| `user_agent` | `str` | `USER_AGENT` | User-Agent header of the request, the name of the library |

A directory that cannot be created, an address without a name of a file and no `filename`, a name that is not a plain name of a file, such as one with a drive or a separator, and a broken, interrupted or cut download raise `DownloadError`, and a directory that is neither a string nor a `Path` `SourceTypeError`.
<!-- --8<-- [end:download_file] -->

A language library passes its own name as `user_agent`.

## Extracting an archive { #extract_archive }

<!-- --8<-- [start:extract_archive] -->
``` {.python .signature}
extract_archive(archive_file, extract_dir=None)
```

Extracts a ZIP or TAR archive and returns the directory with the files. Paths leading outside the directory (absolute, with a drive or a network share, or with `..`) and links are refused before anything is written, on any version of Python. The archive is extracted aside and put in place once complete: a single root directory takes the name of the archive without its extensions (`corpus_v1.tar.xz` - `corpus_v1`), replacing an earlier extraction; otherwise the files go into the directory, replacing those of the same names and keeping the others. A file in the place of a directory or the other way round, or in the place of the archive itself, is refused before anything is replaced.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `archive_file` | `str` / `Path` | - | Path to the archive |
| `extract_dir` | `str` / `Path` | `None` | Directory for the extracted files; the directory of the archive by default |

A refused path, link or file, a missing file, a file that is not an archive, a corrupted or empty archive, a directory that cannot be created and files that cannot be replaced raise `DataFileError`, and a path that is neither a string nor a `Path` `SourceTypeError`.
<!-- --8<-- [end:extract_archive] -->

## Checksum of a file { #sha256 }

<!-- --8<-- [start:sha256] -->
``` {.python .signature}
sha256(path)
```

Computes the SHA-256 checksum of a file as a hexadecimal string in lower case; a missing file gives an empty string.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `path` | `str` / `Path` | - | Path to the file |

A path that is neither a string nor a `Path` raises `SourceTypeError`.
<!-- --8<-- [end:sha256] -->

## Conversion into a path { #to_path }

<!-- --8<-- [start:to_path] -->
``` {.python .signature}
to_path(path)
```

Converts a string or a `Path` into a `Path`, expanding a leading `~`, alone or before a separator, into the home directory.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `path` | `str` / `Path` | - | Path as a string or a Path |

Any other value raises `SourceTypeError`.
<!-- --8<-- [end:to_path] -->

## Filters of the records

<!-- --8<-- [start:check_limit] -->
``` {.python .signature}
check_limit(limit)
```

Checks the number of records to take: `None` or a non-negative integer.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `limit` | `int` | - | Number of records; `None` - no limit |

Any other value raises `ParameterError`.
<!-- --8<-- [end:check_limit] -->

<!-- --8<-- [start:length_filters] -->
``` {.python .signature}
length_filters(min_len, max_len)
```

Returns the predicates that keep the records whose field `text` is at least `min_len` and at most `max_len` characters long.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `min_len` | `int` | - | Minimum length of the text in characters; `None` - no bound |
| `max_len` | `int` | - | Maximum length of the text in characters; `None` - no bound |

A bound that is not an integer or is below one, or a minimum greater than the maximum, raises `ParameterError`.
<!-- --8<-- [end:length_filters] -->

``` {.python .signature}
substring_filter(field, value, fold=fold_diacritics)
```

<!-- --8<-- [start:substring_filter] -->
Returns the predicate that keeps the records whose field holds the substring `value`. Both are folded by `fold`, so the differences of case and diacritics a language ignores do not count. The substring is plain text, not a regular expression; a field that is not a string does not match. A value that is not a string raises `ParameterError`, and a `fold` that cannot be called `SourceTypeError`.
<!-- --8<-- [end:substring_filter] -->

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `field` | `str` | - | Name of the field of a record |
| `value` | `str` | - | Substring to look for |
| `fold` | `Callable` | `fold_diacritics` | Folding of a string before the comparison |

<!-- --8<-- [start:fold_diacritics] -->
``` {.python .signature}
fold_diacritics(value)
```

Lower-cases a string (`str.casefold`), decomposes it (NFD) and drops the combining marks, so `Galdós` and `galdos` are the same. A letter that Unicode decomposes into a base letter and a mark is folded too (`й` gives `и`); a language where such a letter is a letter of its own passes another `fold`.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `value` | `str` | - | String |
<!-- --8<-- [end:fold_diacritics] -->

=== "Code"

    ``` python
    from anyts.datasets import fold_diacritics, length_filters, substring_filter

    records = [
        {"author": "Benito Pérez Galdós", "text": "A long text of the novel"},
        {"author": "Rubén Darío", "text": "A poem"},
    ]
    filters = [substring_filter("author", "galdos"), *length_filters(10, None)]
    [record["author"] for record in records if all(f(record) for f in filters)]
    fold_diacritics("Pérez Galdós")
    ```

=== "Result"

    ```
    ['Benito Pérez Galdós']
    'perez galdos'
    ```

## For library developers { #hooks }

<details class="library-hooks" markdown>
<summary>Language hooks of a subclass</summary>

<!-- --8<-- [start:Dataset-hooks] -->
The class attributes `repr_name` and `name_key` are the name of the class in `repr` and the key of the name in `info`; a subclass overrides them.
<!-- --8<-- [end:Dataset-hooks] -->

In the core `repr_name` is `"Dataset"` and `name_key` is `"name"`.

</details>
