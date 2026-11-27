import re
import sys
from io import BytesIO, TextIOWrapper
from typing import ClassVar

import pytest

from anyts.basic_stats import BasicStats
from anyts.cli import Command
from anyts.constants import MESSAGES, REPORT_TEXTS
from anyts.exceptions import ParameterError, SourceError
from anyts.morph_stats import MorphStats
from anyts.readability_stats import ReadabilityStats
from anyts.report import Report, escape
from anyts.style_stats import StyleStats
from anyts.visualizers import sentence_lengths
from anyts.visualizers.highlight import Highlight, HighlightedText


class Vowels(BasicStats):
    def count_syllables(self, word):
        return sum(char in "aeiou" for char in word.lower())


class Readability(ReadabilityStats):
    basic_stats_class = Vowels


class LongWords(HighlightedText):
    layers_desc: ClassVar[dict[str, str]] = {"long": "Long words"}
    default_layers: ClassVar[tuple[str, ...]] = ("long",)

    def find(self, layer, words, sents, document):
        return [Highlight(word.start, word.end, layer) for word in words if len(word.text) > 5]


class VowelsReport(Report):
    stats_classes: ClassVar[dict[str, type]] = {"basic": Vowels, "readability": Readability}
    sentence_columns: ClassVar[tuple[tuple[str, str], ...]] = (
        ("basic", "n_words"),
        ("readability", "flesch_kincaid_grade"),
    )
    highlight_class = LongWords


TEXT = 'The cat <script>alert("x")</script> sleeps.\n\n***\n\nA dog barks loudly & happily!'


def rows(page, heading):
    """Cells of the rows of the first table after a heading"""
    table = page[page.index(heading) :]
    table = table[: table.index("</table>")]
    return [
        re.findall(r"<td[^>]*>(.*?)</td>", row) for row in re.findall(r"<tr>(.*?)</tr>", table)
    ][1:]


def test_statistics_are_those_of_the_classes():
    report = VowelsReport(TEXT)
    page = report.to_html()
    found = {cells[0]: cells[1:] for cells in rows(page, "<h3>basic</h3>")}
    basic = report.stats["basic"]
    assert found[escape(basic.stats_desc["n_words"])] == [str(basic.n_words), ""]
    assert found[escape(basic.stats_desc["letters_entropy"])][0] == f"{basic.letters_entropy:.2f}"
    readability = report.stats["readability"]
    found_grade = {cells[0]: cells[1:] for cells in rows(page, "<h3>readability</h3>")}
    stat = "flesch_kincaid_grade"
    assert found_grade[escape(readability.stats_desc[stat])] == [
        f"{getattr(readability, stat):.2f}",
        escape(readability.describe(stat) or ""),
    ]


def test_sentences_are_those_of_by_parts():
    """The sentences with words, numbered as on the plot of their lengths: *** is left out"""
    page = VowelsReport(TEXT).to_html()
    parts = Vowels.by_parts(TEXT)
    grades = Readability.by_parts(TEXT)["flesch_kincaid_grade"]
    found = rows(page, "<h2>Sentences</h2>")
    assert [cells[0] for cells in found] == ["1", "2"]
    assert found[0][1] == escape(TEXT[parts.loc[0, "start"] : parts.loc[0, "end"]])
    assert [cells[2] for cells in found] == [str(int(parts.loc[0, "n_words"])), "5"]
    assert found[1][3] == f"{grades.loc[2]:.2f}"
    assert len(sentence_lengths(TEXT)) == len(found)


def test_text_is_escaped_and_needs_nothing_else():
    page = VowelsReport(TEXT, title='<b>"Title"</b>').to_html()
    assert "<script>" not in page and "&lt;script&gt;alert(&quot;x&quot;)" in page
    assert "<title>&lt;b&gt;&quot;Title&quot;&lt;/b&gt;</title>" in page
    assert "&amp; happily" in page
    references = re.findall(r'(?:src|href)="([^"]*)"', page)
    assert references and all(reference.startswith("#") for reference in references)
    assert all(url.startswith("#") for url in re.findall(r"url\(([^)]*)\)", page))
    assert "<link" not in page and "<script" not in page


def test_sections():
    page = VowelsReport(TEXT).to_html()
    assert [re.sub("<[^>]+>", "", h) for h in re.findall(r"<h2>.*?</h2>", page)] == [
        "Statistics",
        "Sentences",
        "Highlighted text",
        "Plots",
    ]
    assert 'class="hl-highlight"' in page or "-hl-long" in page
    assert page.count("<svg") == 1


def test_a_report_of_a_library():
    """A library reorders the sections, adds its own and translates the texts"""

    class Own(VowelsReport):
        sections: ClassVar[tuple[str, ...]] = ("words", "statistics")
        texts: ClassVar[dict[str, str]] = {
            **REPORT_TEXTS,
            "lang": "ru",
            "statistics": "Статистики",
        }

        def section_words(self):
            return f"<p>{escape(len(self.document.words))}</p>\n"

    page = Own(TEXT, stats_classes={"basic": Vowels}).to_html()
    assert '<html lang="ru">' in page and "<h2>Статистики</h2>" in page
    assert page.index("<p>") < page.index("<h2>Статистики</h2>")
    assert "<h3>readability</h3>" not in page
    with pytest.raises(ParameterError, match="lack the keys"):
        type("Partial", (Report,), {"texts": {"title": "Отчёт"}})


def test_a_report_without_classes_and_sentences(tmp_path):
    """No class, no sentence columns, no highlighting and no sentences: the sections are empty or
    left out"""
    report = Report("")
    path = tmp_path / "report.html"
    report.save(path)
    page = path.read_text(encoding="utf-8")
    assert page == report.to_html()
    assert "<h2>" not in page and "<svg" not in page


class Prototype(Command):
    prog = "proto"
    stats_classes: ClassVar[dict[str, type]] = {"basic": Vowels, "readability": Readability}
    report_class = VowelsReport


def test_report_command(tmp_path, capsys, monkeypatch):
    source, output = tmp_path / "text.txt", tmp_path / "text.html"
    source.write_text(TEXT, encoding="utf-8")
    assert (
        Prototype().run(["report", str(source), "-o", str(output), "-t", "Text", "-s", "basic"])
        == 0
    )
    page = output.read_text(encoding="utf-8")
    assert "<title>Text</title>" in page
    assert "<h3>basic</h3>" in page and "<h3>readability</h3>" not in page
    monkeypatch.setattr(sys, "stdin", TextIOWrapper(BytesIO(b"The cat sleeps.")))
    assert Prototype().run(["report"]) == 0
    assert capsys.readouterr().out.startswith("<!DOCTYPE html>")


def test_report_command_errors(tmp_path, capsys):
    assert Prototype().run(["report", str(tmp_path / "missing.txt")]) == 1
    assert capsys.readouterr().err.startswith(f"proto: {tmp_path / 'missing.txt'}: ")
    empty = tmp_path / "empty.txt"
    empty.write_text("", encoding="utf-8")
    assert Prototype().run(["report", str(empty)]) == 1
    assert capsys.readouterr().err == f"proto: {empty}: The data source has no words\n"


def test_values_are_those_of_get_stats():
    """A statistic of the table is that of get_stats: the counts of MorphStats, not the values of
    every word its attributes keep"""
    import spacy
    from spacy.tokens import Doc

    doc = Doc(
        spacy.blank("en").vocab,
        words=["Cats", "sleep", "and", "eat", "."],
        pos=["NOUN", "VERB", "CCONJ", "VERB", "PUNCT"],
        morphs=["Number=Plur", "Tense=Pres", "", "Tense=Pres", ""],
    )

    class Morph(Report):
        stats_classes: ClassVar[dict[str, type]] = {"morph": MorphStats}

    report = Morph(doc)
    found = {cells[0]: cells[1] for cells in rows(report.to_html(), "<h3>morph</h3>")}
    stats = report.stats["morph"]
    # The values from the most frequent, described as print_stats describes them
    desc = stats.value_desc
    assert found[escape(stats.stats_desc["pos"])] == escape(
        f"{desc('pos', 'VERB')}: 2, {desc('pos', 'NOUN')}: 1, {desc('pos', 'CCONJ')}: 1"
    )
    assert found[escape(stats.stats_desc["number"])] == escape(
        f"{stats.unknown_value}: 3, {desc('number', 'Plur')}: 1"
    )


def test_the_statistics_are_read_once_for_the_sentences():
    """The statistics of every sentence are read once, and none of the whole text"""
    reads = []

    class Counted(Vowels):
        stats_desc: ClassVar[dict[str, str]] = {**Vowels.stats_desc, "slow": "Slow"}

        @property
        def slow(self):
            reads.append(self.n_words)
            return self.n_words

    class Slow(Report):
        stats_classes: ClassVar[dict[str, type]] = {"counted": Counted}
        sentence_columns: ClassVar[tuple[tuple[str, str], ...]] = (("counted", "slow"),)
        sections: ClassVar[tuple[str, ...]] = ("sentences",)

    text = " ".join(["The cat sleeps."] * 40)
    report = Slow(text)
    reads.clear()
    page = report.to_html()
    assert [cells[2] for cells in rows(page, "<h2>Sentences</h2>")] == ["3"] * 40
    assert reads == [3] * 40


class Fussy(Vowels):
    """A class that cannot count a text with fewer than five words"""

    def __init__(self, source):
        super().__init__(source)
        if self.n_words < 5:
            raise SourceError("Too few words")


def test_skip_errors():
    class Two(Report):
        stats_classes: ClassVar[dict[str, type]] = {"basic": Vowels, "fussy": Fussy}

    with pytest.raises(SourceError, match=r"^Too few words$"):
        Two("The cat sleeps.")
    report = Two("The cat sleeps.", skip_errors=True)
    assert list(report.stats) == ["basic"] and str(report.errors["fussy"]) == "Too few words"
    page = report.to_html()
    assert "<h3>fussy</h3>" not in page and "<p>Not counted: fussy</p>" in page

    class Titled(Two):
        titles: ClassVar[dict[str, str]] = {"fussy": "Fussy statistics"}

    assert (
        "<p>Not counted: Fussy statistics</p>"
        in Titled("The cat sleeps.", skip_errors=True).to_html()
    )
    with pytest.raises(ParameterError):
        Two("The cat sleeps.", skip_errors="yes")


class Partly(Command):
    prog = "proto"
    stats_classes: ClassVar[dict[str, type]] = {"basic": Vowels, "fussy": Fussy}


def test_report_command_leaves_out_a_class(tmp_path, capsys):
    """A class that cannot count the text is left out with its error and the exit code 1; the
    report of the others is written"""
    source, output = tmp_path / "text.txt", tmp_path / "text.html"
    source.write_text("The cat sleeps.", encoding="utf-8")
    assert Partly().run(["report", str(source), "-o", str(output)]) == 1
    assert capsys.readouterr().err == f"proto: {source}, fussy: Too few words\n"
    page = output.read_text(encoding="utf-8")
    assert "<h3>basic</h3>" in page and "<h3>fussy</h3>" not in page


def test_report_command_writes_utf_8(tmp_path):
    """The encoding of the option is that of the file; the report is in UTF-8, which it declares"""
    source, output = tmp_path / "text.txt", tmp_path / "text.html"
    source.write_text("Кот спит. Où est le chat?", encoding="cp1251", errors="replace")
    assert Prototype().run(["report", str(source), "-e", "cp1251", "-o", str(output)]) == 0
    page = output.read_bytes().decode("utf-8")
    assert '<meta charset="utf-8">' in page and "Кот спит." in page


@pytest.mark.parametrize("command", ["stats", "report"])
def test_an_output_that_cannot_be_written(tmp_path, capsys, command):
    source = tmp_path / "text.txt"
    source.write_text("The cat sleeps.", encoding="utf-8")
    output = tmp_path / "missing" / "out"
    assert Prototype().run([command, str(source), "-o", str(output)]) == 1
    assert capsys.readouterr().err.startswith(f"proto: {output}: ")


def test_rows_are_those_of_print_stats():
    """The statistics of stats_desc, as print_stats, not the distributions of BasicStats; the
    classes under their titles"""

    class Titled(VowelsReport):
        titles: ClassVar[dict[str, str]] = {"basic": "Basic <statistics>"}

    page = Titled(TEXT).to_html()
    found = [cells[0] for cells in rows(page, "<h3>Basic &lt;statistics&gt;</h3>")]
    assert found == [escape(desc) for desc in Vowels.stats_desc.values()]
    assert "<h3>readability</h3>" in page


def test_numbers():
    """A small float keeps two significant digits, and an undefined value is the text of
    undefined"""

    class Small(Vowels):
        stats_desc: ClassVar[dict[str, str]] = {
            **Vowels.stats_desc,
            "small": "Small",
            "none": "None",
        }
        small = 0.0033
        none = None

    class SmallReport(Report):
        stats_classes: ClassVar[dict[str, type]] = {"small": Small}

    found = {cells[0]: cells[1] for cells in rows(SmallReport(TEXT).to_html(), "<h3>small</h3>")}
    assert (found["Small"], found["None"]) == ("0.0033", "-")


def test_max_sentences():
    """A longer text has the sentences with the highest values of the first column, in order"""

    class Top(VowelsReport):
        max_sentences = 2
        sections: ClassVar[tuple[str, ...]] = ("sentences",)

    text = "A cat. The big dog barks. It sleeps now. Birds sing in the old tree."
    page = Top(text).to_html()
    assert [cells[:3] for cells in rows(page, "<h2>Sentences</h2>")] == [
        ["2", "The big dog barks.", "4"],
        ["4", "Birds sing in the old tree.", "6"],
    ]
    assert "The 2 sentences of 4 with the highest" in page


def test_the_page_is_the_same_for_the_same_text():
    class Two(VowelsReport):
        def plots(self):
            return super().plots() + super().plots()

    page = Two(TEXT).to_html()
    assert page == Two(TEXT).to_html()
    assert "<dc:date>" not in page
    ids = re.findall(r'\bid="([^"]+)"', page)
    assert len(ids) == len(set(ids))
    assert re.findall(r"url\(#([^)]+)\)", page)
    assert all(found in ids for found in re.findall(r"url\(#([^)]+)\)", page))


def test_the_styles_of_the_highlighting_are_in_the_head():
    page = VowelsReport(TEXT).to_html()
    head, body = page.split("</head>")
    assert LongWords.css() in head and LongWords.css() not in body


def test_no_interactive_backend(tmp_path):
    """A report chooses no backend of matplotlib that could open a window"""
    import os
    import subprocess

    script = tmp_path / "report.py"
    script.write_text(
        "import sys\n"
        "from anyts.basic_stats import BasicStats\n"
        "from anyts.report import Report\n"
        "class Vowels(BasicStats):\n"
        "    def count_syllables(self, word):\n"
        "        return 1\n"
        "class Basic(Report):\n"
        "    stats_classes = {'basic': Vowels}\n"
        "Basic('The cat sleeps. A dog barks.').to_html()\n"
        "print(sorted(name for name in sys.modules if name.startswith('matplotlib.backends.backend_')))\n",
        encoding="utf-8",
    )
    environment = {key: value for key, value in os.environ.items() if key != "MPLBACKEND"}
    found = subprocess.run(
        [sys.executable, str(script)], capture_output=True, text=True, env=environment, check=True
    )
    # The backends that write files, and none of a window
    assert set(eval(found.stdout)) <= {
        f"matplotlib.backends.backend_{name}" for name in ("agg", "mixed", "svg")
    }


def test_the_command_report_does_not_load_pyplot(tmp_path):
    """The command report draws on a Figure, without the state of pyplot"""
    import subprocess

    source = tmp_path / "text.txt"
    source.write_text("The cat sleeps. A dog barks loudly!", encoding="utf-8")
    code = (
        "import sys\n"
        "from anyts.basic_stats import BasicStats\n"
        "from anyts.cli import Command\n"
        "from anyts.report import Report\n"
        "class Vowels(BasicStats):\n"
        "    def count_syllables(self, word):\n"
        "        return 1\n"
        "class Basic(Report):\n"
        "    stats_classes = {'basic': Vowels}\n"
        "    sentence_columns = (('basic', 'n_words'),)\n"
        "class Proto(Command):\n"
        "    prog = 'proto'\n"
        "    stats_classes = {'basic': Vowels}\n"
        "    report_class = Basic\n"
        f"code = Proto().run(['report', {str(source)!r}, '-o', {str(tmp_path / 'text.html')!r}])\n"
        "print(code, 'matplotlib.pyplot' in sys.modules)\n"
    )
    found = subprocess.run(
        [sys.executable, "-I", "-c", code], capture_output=True, text=True, check=True
    )
    assert found.stdout == "0 False\n"
    assert "<svg" in (tmp_path / "text.html").read_text(encoding="utf-8")


def test_plot_of_many_sentences():
    """A plot of the lengths of a few hundred sentences marks every sentence, of more none"""

    def markers(count):
        report = VowelsReport(" ".join(["The cat sleeps."] * count))
        [(_, figure)] = report.plots()
        ax = figure.axes[0]
        lines = [*ax.get_lines(), *ax.get_legend().get_lines()]
        return {line.get_marker() for line in lines} - {"None", ""}

    assert markers(300) == {"."}
    assert markers(301) == set()


def test_messages_of_a_report():
    """The errors of the arguments of a report come from its messages"""

    class Translated(Report):
        messages: ClassVar[dict[str, str]] = {
            **MESSAGES,
            "bool_param": "Wrong {param}: {type}",
            "report_stats_classes": "Classes: {type}",
        }

    with pytest.raises(ParameterError, match=r"^Wrong skip_errors: str$"):
        Translated(TEXT, skip_errors="yes")
    for classes, name in (
        (("basic",), "tuple"),
        ({"basic": object()}, "object"),
        ({"x": int}, "int"),
        ({"basic": None}, "NoneType"),
    ):
        with pytest.raises(ParameterError, match=rf"^Classes: {name}$"):
            Translated(TEXT, stats_classes=classes)


def test_the_other_classes_count_only_the_sentences_shown():
    """For a longer text, the classes after the first count the sentences of the table only"""
    counted = []

    class Counting(Report):
        stats_classes: ClassVar[dict[str, type]] = {"basic": Vowels, "style": StyleStats}
        sentence_columns: ClassVar[tuple[tuple[str, str], ...]] = (
            ("basic", "n_words"),
            ("style", "water"),
        )
        max_sentences = 2

        @classmethod
        def compute(cls, stats_class, document):
            if stats_class is StyleStats:
                counted.append(document.text)
            return super().compute(stats_class, document)

    report = Counting("One. Two words. Three words here. Four words are here now.")
    counted.clear()
    table = rows(report.section_sentences(), "<table>")
    assert counted == ["Three words here.", "Four words are here now."]
    assert [row[0] for row in table] == ["3", "4"]
    assert all(cell != "-" for row in table for cell in row)


def test_the_statistics_of_a_report_keep_their_tree():
    """The tree the classes of a report share stays whole for the statistics it keeps"""
    import spacy
    from spacy.tokens import Doc

    from anyts import document as document_module
    from anyts.document import to_document
    from anyts.syntax_stats import SyntaxStats

    doc = Doc(
        spacy.blank("en").vocab,
        words=["Cats", "sleep", "."],
        heads=[1, 1, 1],
        deps=["nsubj", "ROOT", "punct"],
        pos=["NOUN", "VERB", "PUNCT"],
        lemmas=["cat", "sleep", "."],
    )
    document = to_document(doc)
    # A document no conversion keeps, as that of a text
    document_module._slot().clear()

    class Trees(Report):
        stats_classes: ClassVar[dict[str, type]] = {"syntax": SyntaxStats}

    report = Trees(document)
    cats, sleep = report.stats["syntax"].sents[0]
    assert cats.head is sleep
