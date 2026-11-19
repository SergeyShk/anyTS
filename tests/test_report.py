import re
import sys
from io import BytesIO, TextIOWrapper
from typing import ClassVar

import pytest

from anyts.basic_stats import BasicStats
from anyts.cli import Command
from anyts.constants import REPORT_TEXTS
from anyts.exceptions import ParameterError, SourceError
from anyts.morph_stats import MorphStats
from anyts.readability_stats import ReadabilityStats
from anyts.report import Report, escape
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
    page = VowelsReport(TEXT).to_html()
    parts = Vowels.by_parts(TEXT)
    grades = Readability.by_parts(TEXT)["flesch_kincaid_grade"]
    found = rows(page, "<h2>Sentences</h2>")
    assert [cells[0] for cells in found] == ["1", "2", "3"]
    assert found[0][1] == escape(TEXT[parts.loc[0, "start"] : parts.loc[0, "end"]])
    assert [cells[2] for cells in found] == [str(int(parts.loc[0, "n_words"])), "-", "5"]
    assert found[2][3] == f"{grades.loc[2]:.2f}"


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
        words=["Cats", "sleep", "."],
        pos=["NOUN", "VERB", "PUNCT"],
        morphs=["Number=Plur", "Tense=Pres", ""],
    )

    class Morph(Report):
        stats_classes: ClassVar[dict[str, type]] = {"morph": MorphStats}

    report = Morph(doc)
    found = {cells[0]: cells[1] for cells in rows(report.to_html(), "<h3>morph</h3>")}
    stats = report.stats["morph"]
    assert found[escape(stats.stats_desc["pos"])] == escape("NOUN: 1, VERB: 1")
    assert found[escape(stats.stats_desc["number"])] == escape("Plur: 1, None: 1")


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
    assert "<h3>fussy</h3>" not in report.to_html()
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
