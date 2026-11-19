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
| `-s`, `--stats` | every class | Classes of statistics, by name and separated by commas |
| `-p`, `--parts` | - | `sentences` or `paragraphs`: a row per part ([`by_parts`](https://sergeyshk.github.io/anyTS/stats/stats/#by_parts)); a class that counts no such parts is an error |
| `-f`, `--format` | `table` | `table` - the table of `print_stats` of every class, or of the parts; `json` - the flat statistics of every class by text, `get_stats(flat=True)`, or the records of the parts, with `nan` and infinities as `null`; `csv` - a row per text, or per part of a text, with a column `<class>.<statistic>` for every statistic and 0 for a count of a distribution a text lacks ([`stats_dataframe`](https://sergeyshk.github.io/anyTS/stats/stats/#stats_dataframe)) |
| `-o`, `--output` | the standard output | File of the output |
| `-e`, `--encoding` | `utf-8` | Encoding of the files and of the output |

Its command `report` writes the [HTML report](https://sergeyshk.github.io/anyTS/report/) of a text, from a file or from the standard input, to `-o` or to the standard output, with the classes of `-s` and the title of `-t`, `--title`. `-e` is the encoding of the file, and the report is in UTF-8, which it declares. A class that cannot count the text is left out of the report, and its error goes to the standard error with the exit code 1.

`run(argv=None)` runs the command with the arguments, those of the command line by default, and returns the exit code: 0; 1 when a file cannot be read or written or a class cannot count a text, whose error goes to the standard error while the other texts and classes are counted; 2 for wrong arguments, with the help of `argparse`.

Raises `ParameterError` when a subclass is defined with texts that `check_messages` rejects against `CLI_TEXTS`.
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
| `texts` | class attribute | Texts of the help and of the errors by key, `CLI_TEXTS` by default: complete, as the messages of a class of statistics |
| `parse(text)` | method | Document of a text, once for all the classes; `to_document` by default, overridden with the parse of the classes of the library |
| `compute(cls, document)` | method | Statistics of a class of a document; `DiversityStats` of the words of the document (`document_words`) |
| `report_class` | class attribute | Report of the command `report`, made of the document of `parse` and the classes of `-s`; `Report` by default |
| `parser()` | method | `ArgumentParser` of the command |
<!-- --8<-- [end:Command-hooks] -->

</details>
