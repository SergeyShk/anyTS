import json
import sys
from io import BytesIO, StringIO, TextIOWrapper
from typing import ClassVar

import pandas as pd
import pytest

from anyts.basic_stats import BasicStats
from anyts.cli import Command
from anyts.constants import CLI_TEXTS
from anyts.diversity_stats import DiversityStats
from anyts.document import document_words, to_document
from anyts.exceptions import ParameterError, SourceError
from anyts.report import Report
from anyts.style_stats import StyleStats
from anyts.syntax_stats import SyntaxStats


class Vowels(BasicStats):
    def count_syllables(self, word):
        return sum(char in "aeiou" for char in word.lower())


class Prototype(Command):
    """The command of a library over the classes of the core"""

    prog = "proto"
    stats_classes: ClassVar[dict[str, type]] = {
        "basic": Vowels,
        "diversity": DiversityStats,
        "style": StyleStats,
        "syntax": SyntaxStats,
    }


FIRST = "The cat sleeps. A dog barks loudly!\n\nA bird sings."
SECOND = "One more text here."


@pytest.fixture
def files(tmp_path):
    first, second = tmp_path / "first.txt", tmp_path / "second.txt"
    first.write_text(FIRST, encoding="utf-8")
    second.write_text(SECOND, encoding="utf-8")
    return str(first), str(second)


def run(capsys, *argv):
    code = Prototype().run(["stats", *argv])
    out, err = capsys.readouterr()
    return code, out, err


def finite(stats):
    return {
        key: None if isinstance(value, float) and value != value else value
        for key, value in stats.items()
    }


def test_json_is_the_flat_statistics(capsys, files):
    """JSON gives get_stats(flat=True) of every class by text, nan as null"""
    code, out, err = run(capsys, "-s", "basic,diversity,style", "-f", "json", *files)
    assert (code, err) == (0, "")
    data = json.loads(out)
    assert list(data) == list(files)
    document = to_document(FIRST)
    assert data[files[0]]["basic"] == Vowels(document).get_stats(flat=True)
    assert data[files[0]]["diversity"] == finite(
        DiversityStats(document_words(document)).get_stats(flat=True)
    )
    assert data[files[0]]["style"] == finite(StyleStats(document).get_stats(flat=True))


def stdin(text, encoding="utf-8"):
    return TextIOWrapper(BytesIO(text.encode(encoding)), encoding="utf-8")


def test_standard_input(capsys, monkeypatch):
    monkeypatch.setattr(sys, "stdin", stdin(SECOND))
    code, out, _ = run(capsys, "-s", "basic", "-f", "json")
    assert code == 0
    assert json.loads(out)["-"]["basic"]["n_words"] == 4
    monkeypatch.setattr(sys, "stdin", stdin(SECOND))
    code, out, _ = run(capsys, "-s", "basic", "-f", "json", "-")
    assert json.loads(out)["-"]["basic"]["n_words"] == 4
    # The encoding of the option, not that of the locale
    monkeypatch.setattr(sys, "stdin", stdin("Кот спит у окна.", "cp1251"))
    code, out, _ = run(capsys, "-s", "basic", "-f", "json", "-e", "cp1251")
    assert json.loads(out)["-"]["basic"]["n_letters"] == 12


def test_csv_of_several_texts(capsys, files):
    """A row per text, the columns named by their class; a count a text lacks is 0"""
    code, out, _ = run(capsys, "-s", "basic,style", "-f", "csv", *files)
    assert code == 0
    table = pd.read_csv(StringIO(out), index_col="source")
    assert list(table.index) == list(files)
    assert table.loc[files[1], "basic.n_words"] == 4
    assert table.loc[files[1], "basic.c_letters_1"] == 0
    assert "style.water" in table.columns


def test_parts(capsys, files):
    """With --parts a row per sentence or paragraph of every text, in CSV and JSON"""
    code, out, _ = run(capsys, "-s", "basic,style", "-p", "sentences", "-f", "csv", *files)
    assert code == 0
    table = pd.read_csv(StringIO(out), index_col=["source", "sentence"])
    assert len(table) == 4
    assert table.loc[(files[0], 1), ["start", "end", "basic.n_words"]].tolist() == [16, 35, 4]
    assert table.loc[(files[1], 0), "basic.c_letters_1"] == 0
    code, out, _ = run(capsys, "-s", "basic", "-p", "paragraphs", "-f", "json", files[0])
    records = json.loads(out)[files[0]]["basic"]
    assert [(record["paragraph"], record["n_sents"]) for record in records] == [(0, 2), (1, 1)]


def test_tables(capsys, files):
    code, out, _ = run(capsys, "-s", "basic", files[1])
    assert code == 0
    assert out.startswith("    Statistic") or "Sentences" in out.splitlines()[2]
    assert "basic" not in out
    _, out, _ = run(capsys, "-s", "basic,style", *files)
    assert f"{files[0]}: basic" in out and f"{files[1]}: style" in out
    _, out, _ = run(capsys, "-s", "basic", "-p", "sentences", files[0])
    assert out.splitlines()[1].startswith("sentence")


def test_output_file_and_encoding(capsys, tmp_path):
    source = tmp_path / "cp1251.txt"
    source.write_text("Кот спит.", encoding="cp1251")
    output = tmp_path / "out.json"
    code, out, _ = run(
        capsys, "-s", "basic", "-f", "json", "-e", "cp1251", "-o", str(output), str(source)
    )
    assert (code, out) == (0, "")
    assert json.loads(output.read_text(encoding="cp1251"))[str(source)]["basic"]["n_words"] == 2


def test_a_text_that_fails(capsys, files, tmp_path):
    """A file that cannot be read and a class that cannot count a text are reported, the rest
    is counted, with the exit code 1"""
    missing = str(tmp_path / "missing.txt")
    code, out, err = run(capsys, "-s", "basic,syntax", "-f", "json", files[1], missing)
    assert code == 1
    assert json.loads(out) == {files[1]: {"basic": Vowels(SECOND).get_stats(flat=True)}}
    assert err.splitlines()[0].startswith(f"proto: {files[1]}, syntax: ")
    assert err.splitlines()[1].startswith(f"proto: {missing}: ")


def test_a_text_that_cannot_be_parsed(capsys, files):
    class Failing(Prototype):
        def parse(self, text):
            raise ParameterError("broken")

    code = Failing().run(["stats", "-s", "basic", files[1]])
    assert code == 1
    assert capsys.readouterr().err == f"proto: {files[1]}: broken\n"


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        (
            ["stats", "-s", "lexical"],
            "unknown statistics lexical; available: basic, diversity, style, syntax",
        ),
        (["stats", "-s", "diversity", "-p", "sentences"], "diversity counts no sentences"),
        (["stats", "-f", "xml"], "invalid choice: 'xml'"),
        ([], "the following arguments are required: command"),
    ],
)
def test_wrong_arguments(capsys, argv, message):
    assert Prototype().run(argv) == 2
    assert message in capsys.readouterr().err


def test_help(capsys):
    assert Prototype().run(["stats", "--help"]) == 0
    help_text = " ".join(capsys.readouterr().out.split())
    assert "Classes of statistics, by name and separated by commas: basic, diversity" in help_text


def test_texts_of_a_library(capsys):
    class Translated(Prototype):
        texts: ClassVar[dict[str, str]] = {**CLI_TEXTS, "no_parts": "{name} не считает {parts}"}

    assert Translated().run(["stats", "-s", "diversity", "-p", "sentences"]) == 2
    assert "diversity не считает sentences" in capsys.readouterr().err
    with pytest.raises(ParameterError, match="lack the keys"):
        type("Partial", (Command,), {"texts": {"description": "Статистика"}})


class SourceDiversity(DiversityStats):
    """DiversityStats of a library, which takes a source and finds its words itself"""

    def __init__(self, source):
        super().__init__(document_words(to_document(source)))


class Lazy(Vowels):
    """A statistic computed when it is read, which fails for a text with no long word"""

    stats_desc: ClassVar[dict[str, str]] = {**Vowels.stats_desc, "longest": "Longest word"}

    @property
    def longest(self):
        if not self.n_long_words:
            raise SourceError("No long words")
        return self.n_long_words


class Library(Command):
    prog = "library"
    stats_classes: ClassVar[dict[str, type]] = {
        "syntax": SyntaxStats,
        "basic": Vowels,
        "diversity": SourceDiversity,
        "lazy": Lazy,
    }


def test_diversity_of_a_library(capsys, files):
    """A DiversityStats with its own constructor gets the document, the core one its words"""
    assert Library().run(["stats", "-s", "diversity", "-f", "json", files[0]]) == 0
    data = json.loads(capsys.readouterr().out)
    assert (
        data[files[0]]["diversity"]["ttr"]
        == DiversityStats(document_words(to_document(FIRST))).ttr
    )


def test_a_statistic_that_fails_when_read(capsys, tmp_path):
    """It is reported for its text, and the other texts and classes are counted; a part keeps its
    row without statistics"""
    plain, wordy = tmp_path / "plain.txt", tmp_path / "wordy.txt"
    plain.write_text("The cat sleeps.", encoding="utf-8")
    wordy.write_text("Wonderful creatures. A cat.", encoding="utf-8")
    code = Library().run(["stats", "-s", "basic,lazy", "-f", "json", str(plain), str(wordy)])
    out, err = capsys.readouterr()
    assert code == 1
    data = json.loads(out)
    assert set(data[str(plain)]) == {"basic"} and set(data[str(wordy)]) == {"basic", "lazy"}
    assert err == f"library: {plain}, lazy: No long words\n"
    code = Library().run(["stats", "-s", "lazy", "-p", "sentences", "-f", "json", str(wordy)])
    records = json.loads(capsys.readouterr().out)[str(wordy)]["lazy"]
    assert code == 0
    assert [record["longest"] for record in records] == [2, None]


def test_positions_of_the_parts_of_a_failed_class(capsys, files):
    """The positions of the parts come from any class that counted the text"""
    code = Library().run(["stats", "-s", "syntax,basic", "-p", "sentences", "-f", "csv", *files])
    out, err = capsys.readouterr()
    assert code == 1 and "syntax" in err
    table = pd.read_csv(StringIO(out), index_col=["source", "sentence"])
    assert table[["start", "end"]].dtypes.tolist() == ["int64", "int64"]
    assert table.loc[(files[1], 0), ["start", "end"]].tolist() == [0, 19]


def test_parts_without_stats(capsys, files):
    """Without --stats, --parts takes the classes that count such parts"""
    code, out, err = run(capsys, "-p", "sentences", "-f", "json", files[1])
    # SyntaxStats needs a parse the core does not make, DiversityStats counts no sentences
    assert code == 1 and err.startswith(f"proto: {files[1]}, syntax: ")
    assert set(json.loads(out)[files[1]]) == {"basic", "style"}

    class Diverse(Command):
        prog = "diverse"
        stats_classes: ClassVar[dict[str, type]] = {"diversity": DiversityStats}

    assert Diverse().run(["stats", "-p", "lines", files[1]]) == 2
    assert "diverse: error: no class counts lines" in capsys.readouterr().err


def test_lines(capsys, files):
    code, out, _ = run(capsys, "-s", "basic", "-p", "lines", "-f", "json", files[0])
    records = json.loads(out)[files[0]]["basic"]
    assert code == 0
    assert [(record["line"], record["n_sents"]) for record in records] == [(0, 2), (1, 1)]
    assert all(isinstance(record["n_words"], int) for record in records)


def test_output_is_utf_8(capsys, tmp_path):
    """-e is the encoding of the files: the output is in UTF-8, the descriptions of the
    statistics outside the encoding of the files among them"""
    source = tmp_path / "cp1251.txt"
    source.write_text("Кот спит на окне. Кот любит окно.", encoding="cp1251")
    output = tmp_path / "out.txt"
    code, out, _ = run(capsys, "-s", "diversity", "-e", "cp1251", "-o", str(output), str(source))
    assert (code, out) == (0, "")
    assert "Honoré's R" in output.read_text(encoding="utf-8")
    code, out, _ = run(capsys, "-s", "diversity", "-e", "cp1251", "-o", "-", str(source))
    assert code == 0 and "Honoré's R" in out


def test_csv_line_ends(capsys, files, tmp_path):
    output = tmp_path / "out.csv"
    assert run(capsys, "-s", "basic", "-f", "csv", "-o", str(output), *files)[0] == 0
    data = output.read_bytes()
    assert b"\r\r" not in data and data.count(b"\n") == 3


@pytest.mark.parametrize("encoding", ["cp-1251", "utf9"])
def test_unknown_encoding(capsys, files, encoding):
    code, _, err = run(capsys, "-e", encoding, files[1])
    assert code == 2
    assert f"proto stats: error: argument -e/--encoding: unknown encoding {encoding}" in err


def test_a_file_in_another_encoding(capsys, tmp_path):
    source = tmp_path / "cp1251.txt"
    source.write_text("Кот спит.", encoding="cp1251")
    code, _, err = run(capsys, "-s", "basic", str(source))
    assert code == 1
    assert err.startswith(f"proto: {source}: 'utf-8' codec can't decode")
    assert err.endswith("; give its encoding with -e\n")


def test_standard_input_reads_as_a_file(capsys, monkeypatch, tmp_path):
    """The line breaks and the byte order mark of the standard input are read as in a file"""
    data = "﻿The cat sleeps.\r\n\r\nA dog barks.".encode()
    source = tmp_path / "crlf.txt"
    source.write_bytes(data)
    _, from_file, _ = run(capsys, "-s", "basic", "-p", "paragraphs", "-f", "json", str(source))
    monkeypatch.setattr(sys, "stdin", TextIOWrapper(BytesIO(data)))
    _, from_stdin, _ = run(capsys, "-s", "basic", "-p", "paragraphs", "-f", "json")
    assert json.loads(from_file)[str(source)] == json.loads(from_stdin)["-"]
    assert json.loads(from_file)[str(source)]["basic"][0]["start"] == 0


class Filtered(Report):
    """A report whose classes leave the numbers out of their words"""

    sentence_columns: ClassVar[tuple[tuple[str, str], ...]] = (("basic", "n_words"),)
    sections: ClassVar[tuple[str, ...]] = ("sentences",)

    @classmethod
    def compute(cls, stats_class, document):
        if issubclass(stats_class, Vowels):
            return stats_class(document, filter_nums=True)
        return super().compute(stats_class, document)


class FilteredCommand(Prototype):
    report_class = Filtered


def test_compute_counts_the_text_its_parts_and_the_report(capsys, tmp_path):
    """compute of the report counts the whole text, its parts and the report alike"""
    source = tmp_path / "numbers.txt"
    source.write_text("In 2024 we had 15 cats. And 3 dogs.", encoding="utf-8")
    command = FilteredCommand()
    assert command.run(["stats", "-s", "basic", "-f", "json", str(source)]) == 0
    whole = json.loads(capsys.readouterr().out)[str(source)]["basic"]["n_words"]
    assert command.run(["stats", "-s", "basic", "-p", "sentences", "-f", "json", str(source)]) == 0
    parts = json.loads(capsys.readouterr().out)[str(source)]["basic"]
    assert whole == sum(record["n_words"] for record in parts) == 6
    assert command.run(["report", "-s", "basic", str(source)]) == 0
    page = capsys.readouterr().out
    cells = [cell.split("<")[0] for cell in page.split('<td class="number">')[1:]]
    assert cells == ["1", "4", "2", "2"]


class Options(Prototype):
    """A command with an option of its own that parse reads, and a command of its own"""

    def arguments(self, parser, command):
        if command == "stats":
            parser.add_argument("--upper", action="store_true")

    def subcommands(self, commands):
        commands.add_parser("names", help="Print the names of the classes", texts=self.texts)

    def parse(self, text):
        return super().parse(text.upper() if self.args.upper else text)

    def command_names(self, args):
        print(", ".join(self.names))
        return 0


def test_options_and_commands_of_a_library(capsys, files):
    command = Options()
    assert command.run(["stats", "-s", "basic", "-f", "json", "--upper", files[1]]) == 0
    assert json.loads(capsys.readouterr().out)[files[1]]["basic"]["n_words"] == 4
    assert command.run(["names"]) == 0
    assert capsys.readouterr().out == "basic, diversity, style, syntax\n"


def test_texts_of_argparse(capsys):
    texts = {
        **CLI_TEXTS,
        "usage": "использование: ",
        "commands": "команды",
        "positionals": "аргументы",
        "options": "параметры",
        "help_option": "показать справку",
        "files_metavar": "файлы",
        "error": "{prog}: ошибка: {message}",
    }

    class Translated(Prototype):
        pass

    Translated.texts = texts
    assert Translated().run(["stats", "--help"]) == 0
    help_text = capsys.readouterr().out
    for text in ("использование: proto stats", "аргументы:", "параметры:", "показать справку"):
        assert text in help_text
    assert "[файлы ...]" in help_text
    assert Translated().run(["--help"]) == 0
    assert "команды:" in capsys.readouterr().out
    assert Translated().run(["stats", "-f", "xml"]) == 2
    assert "proto stats: ошибка: argument -f/--format: invalid choice" in capsys.readouterr().err


def test_interrupted(capsys, files, monkeypatch):
    def interrupt(self, text):
        raise KeyboardInterrupt

    monkeypatch.setattr(Prototype, "parse", interrupt)
    assert run(capsys, files[1])[0] == 130


def test_closed_output(tmp_path):
    """A reader of the output that stops, as head, ends the command quietly with the code 1"""
    import subprocess

    script = tmp_path / "command.py"
    script.write_text(
        "import sys\n"
        "from anyts.basic_stats import BasicStats\n"
        "from anyts.cli import Command\n"
        "class Vowels(BasicStats):\n"
        "    def count_syllables(self, word):\n"
        "        return 1\n"
        "class Big(Command):\n"
        "    prog = 'big'\n"
        "    stats_classes = {'basic': Vowels}\n"
        "sys.exit(Big().run())\n",
        encoding="utf-8",
    )
    text = tmp_path / "text.txt"
    text.write_text("The cat sleeps. " * 2000, encoding="utf-8")
    process = subprocess.Popen(
        [sys.executable, str(script), "stats", "-p", "sentences", str(text)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdout is not None
    process.stdout.read(10)
    process.stdout.close()
    _, err = process.communicate()
    assert process.returncode == 1
    assert err == b""


class ClosedOutput:
    """A standard output whose reader has stopped, on a descriptor of a pipe"""

    def __init__(self, descriptor):
        self.descriptor = descriptor
        self.buffer = self

    def write(self, data):
        raise BrokenPipeError

    def flush(self):
        pass

    def fileno(self):
        return self.descriptor


@pytest.mark.parametrize("command", ["stats", "report"])
def test_closed_output_in_process(monkeypatch, files, command):
    import os

    reader, writer = os.pipe()
    try:
        monkeypatch.setattr(sys, "stdout", ClosedOutput(writer))
        assert Prototype().run([command, "-s", "basic", files[1]]) == 1
    finally:
        os.close(reader)
        os.close(writer)
