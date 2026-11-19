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
    assert capsys.readouterr().err == f"proto: {files[1]}, parse: broken\n"


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
