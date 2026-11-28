# Command line

A language library gives its users a command over its classes of statistics, so that the statistics of a text need no Python code. The core has the frame of such a command, `Command`: a library names the command, its classes and the parse of a text in its language. The core has no command of its own, since it does not know the language of a text.

## Command { #Command }

<!-- --8<-- [start:Command] -->
``` {.python .signature}
Command()
```

The command line of the statistics of a language library. Its command `stats` reads texts from files, or from the standard input without them or for `-`, parses every text once (`parse`) and prints the statistics of the classes of `stats_classes`:

| Option | Default | Description |
| :----- | :------ | :---------- |
| `files` | the standard input | Text files |
| `-s`, `--stats` | the classes of `default_stats` | Classes of statistics, by name and separated by commas; with `-p`, those of `default_stats` that count such parts by default |
| `-p`, `--parts` | - | `sentences`, `lines` or `paragraphs`: a row per part ([`by_parts`](https://sergeyshk.github.io/anyTS/stats/stats/#by_parts)); a class of `-s` that counts no such parts is an error |
| `-f`, `--format` | `table` | `table` - the table of `print_stats` of every class, or of the parts; `json` - the flat statistics of every class by text, `get_stats(flat=True)`, or the records of the parts, with `nan` and infinities as `null`; `csv` - a row per text, or per part of a text, with a column `<class>.<statistic>` for every statistic and 0 for a count of a distribution a text lacks ([`stats_dataframe`](https://sergeyshk.github.io/anyTS/stats/stats/#stats_dataframe)) |
| `-o`, `--output` | the standard output | File of the output, written only by a result: without one an existing file keeps its text and a new one is not left; the standard output for `-`. A table, written as every text is counted, refuses one of its texts after the first |
| `-e`, `--encoding` | `utf-8-sig` | Encoding of the files: UTF-8, a byte order mark left out, by default; the output is in UTF-8 |

The standard input is read as a file, its line breaks and its byte order mark alike, and a table is printed as every text is counted.

Its command `download`, of a library with `datasets`, downloads the datasets its classes need, those named or every one, again with `--force`, and names each on the standard output.

Its command `report` writes the [HTML report](https://sergeyshk.github.io/anyTS/report/) of a text, from a file or from the standard input, to `-o` or to the standard output, with the classes of `-s` and the title of `-t`, `--title`; its statistics, those of its table of sentences too, are counted as by `stats`, and a class that cannot count the text is left out of it.

`run(argv=None)` runs the command with the arguments, those of the command line by default, and returns the exit code: 0; 1 when a file cannot be read or written, a class cannot count a text or a dataset cannot be downloaded, whose error goes to the standard error while the others are counted, and when the reader of the output stops, as `head`, without a message; 2 for wrong arguments, an unknown encoding among them, with the help of `argparse`, and without a command, with the help of the command; 130 when interrupted. `-V`, `--version` prints the versions of the library and of the core.

Raises `ParameterError` when a subclass is defined with texts that `check_messages` rejects against `CLI_TEXTS`, or with `default_stats` that names a class not in `stats_classes`.
<!-- --8<-- [end:Command] -->

A library defines its command, with the parse of its classes and the help in its language, and makes `run` the entry point of a script of its package. Here the classes are those of the core, and the parse is `to_document`:

``` python
import sys

from anyts.basic_stats import BasicStats
from anyts.cli import Command
from anyts.constants import CLI_TEXTS
from anyts.document import to_document


class Vowels(BasicStats):
    def count_syllables(self, word):
        return sum(char in "aeiou" for char in word.lower())


class VowelsCommand(Command):
    prog = "vowels"
    stats_classes = {"basic": Vowels}
    texts = {**CLI_TEXTS, "description": "Statistics of English texts"}

    def parse(self, text):
        return to_document(text)


def main():
    sys.exit(VowelsCommand().run())
```

``` bash
vowels stats text.txt
vowels stats -f json chapter1.txt chapter2.txt
vowels stats -p sentences -f csv -o sentences.csv text.txt
cat text.txt | vowels stats -f json
vowels report text.txt -t "My text" -o report.html
```

## For library developers { #hooks }

<details class="library-hooks" markdown>
<summary>Hooks of a command</summary>

<!-- --8<-- [start:Command-hooks] -->
A command of a library subclasses `Command`:

| Hook | Kind | Description |
| :--- | :--- | :---------- |
| `prog` | class attribute | Name of the command; `anyts` by default |
| `stats_classes` | class attribute | Classes of statistics by their name in `--stats`; none by default |
| `default_stats` | class attribute | Names of the classes counted without `--stats`; `None` - every class, by default |
| `datasets` | class attribute | Datasets of the command `download` by name, as their classes, made without arguments; none by default |
| `version` | class attribute | Version of the library, which `-V`, `--version` prints with that of the core; `None` - no such option, by default |
| `texts` | class attribute | Texts of the help, of its headings and usage, and of the errors by key, `CLI_TEXTS` by default: complete, as the messages of a class of statistics. The other errors of `argparse`, as an invalid choice, come from its translation by `gettext` |
| `parse(text)` | method | Document of a text, once for all the classes; `to_document` by default, overridden with the parse of the classes of the library. It may read `args` and `names`, as to parse with a model only for the classes that need it, and raises `SourceError` for a text it cannot parse, so that the other texts are counted |
| `compute(stats_class, document)` | method | Statistics of a class of a document or of its part; `compute` of `report_class` by default, so that a library overrides that of its report and the commands count alike |
| `report_class` | class attribute | Report of the command `report`, made of the document of `parse` and the classes of `-s`; `Report` by default |
| `arguments(parser, command)` | method | Adds the options of the library to the parser of the command `stats` or `report`; none by default |
| `subcommands(commands)` | method | Adds the commands of the library with `commands.add_parser(name, help=..., texts=self.texts)`; none by default |
| `command_<name>(args)` | method | Runs the command `name` and returns its exit code: `command_stats`, `command_report` and those of the library |
| `args`, `names` | attributes | Arguments of the command line and names of the classes of `-s`, set by `run` before the command |
| `parser()` | method | `ArgumentParser` of the command |
<!-- --8<-- [end:Command-hooks] -->

</details>
