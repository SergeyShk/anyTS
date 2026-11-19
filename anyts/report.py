from __future__ import annotations

import html
import io
import re
from collections.abc import Mapping, Sequence
from functools import partial
from math import isfinite
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from .constants import REPORT_TEXTS
from .exceptions import AnyTSError
from .stats import Stats, _parts_dataframe
from .utils import check_bool, check_messages

if TYPE_CHECKING:
    from anyseg import Document
    from matplotlib.figure import Figure
    from pandas import DataFrame
    from spacy.tokens import Doc

    from .visualizers.highlight import HighlightedText

# Sentences a plot of their lengths marks one by one; a longer text has its curve alone
_MARKED_SENTENCES = 300
# Style of the report, inline so that the file needs nothing else
_STYLE = """
body { font-family: system-ui, sans-serif; margin: 2rem auto; max-width: 60rem; color: #222; }
h1, h2, h3 { font-weight: 600; }
table { border-collapse: collapse; margin: 0.5rem 0 1.5rem; }
th, td { border-bottom: 1px solid #ddd; padding: 0.25rem 0.75rem; text-align: left;
  vertical-align: top; }
td.number { text-align: right; font-variant-numeric: tabular-nums; }
figure { margin: 1rem 0; }
figure svg { max-width: 100%; height: auto; }
"""


class Report:
    """
    HTML report of the statistics of a text

    Description:
        One HTML file with no outside resources: the statistics of every class
        with their descriptions and readings (describe), as print_stats, the
        chosen statistics of every sentence (by_parts), at most max_sentences of
        them, the highlighted text and plots in SVG. The text is parsed once
        (parse), and every class counts it and its sentences by compute. Every
        section is a method section_<name> that gives a fragment of HTML, in the
        order of sections; a language library sets the classes, their titles,
        the columns of the sentences, the highlighting and the texts, and
        overrides or adds sections. Every text of the source or of the statistics
        goes through escape, and the page is the same for the same text

    Arguments:
        source (str|Doc|Document): Data source
        title (str): Title of the report; that of texts by default
        stats_classes (dict[str, type[Stats]]): Classes of statistics by name; those
            of the class by default
        skip_errors (bool): Leave out a class that cannot count the source, with its
            error in errors, instead of raising it

    Attributes:
        document (Document): Document of the source
        title (str): Title of the report
        stats (dict[str, Stats]): Statistics of every class by name
        errors (dict[str, AnyTSError]): Errors of the classes left out by skip_errors

    Class attributes:
        stats_classes (dict[str, type[Stats]]): Classes of statistics by name
        titles (dict[str, str]): Headings of the classes by name; the names by default
        sentence_columns (tuple[tuple[str, str], ...]): Statistics of every sentence in
            the table of the sentences, as names of a class and of a statistic, a key
            of its flat statistics among them
        max_sentences (int): Sentences of the table, those with the highest values of
            its first statistic for a longer text; 100 by default
        highlight_class (type[HighlightedText]): Highlighting of the text, with its
            default layers; none by default
        visualizer_labels (dict[str, dict[str, str]]): Labels of the plots by visualizer,
            over VISUALIZER_LABELS
        texts (dict[str, str]): Headings and labels by key (REPORT_TEXTS), complete as
            the messages of a class of statistics
        sections (tuple[str, ...]): Sections in their order

    Raises:
        ParameterError: When a class is defined, if its texts are incomplete or have a
            field their default lacks; if skip_errors is not a bool
        SourceTypeError, SourceError: As the classes raise for the source, unless
            skip_errors

    Example:
        >>> from anyts.basic_stats import BasicStats
        >>> from anyts.report import Report
        >>> class Vowels(BasicStats):
        ...     def count_syllables(self, word):
        ...         return sum(char in "aeiou" for char in word.lower())
        >>> class VowelsReport(Report):
        ...     stats_classes = {"basic": Vowels}
        ...     sentence_columns = (("basic", "n_words"),)
        >>> page = VowelsReport("The cat sleeps. A dog barks loudly!").to_html()
        >>> page.startswith("<!DOCTYPE html>"), "<svg" in page
        (True, True)
    """

    stats_classes: ClassVar[Mapping[str, type[Stats]]] = {}
    titles: ClassVar[Mapping[str, str]] = {}
    sentence_columns: ClassVar[Sequence[tuple[str, str]]] = ()
    max_sentences: ClassVar[int] = 100
    highlight_class: ClassVar[type[HighlightedText] | None] = None
    visualizer_labels: ClassVar[Mapping[str, Mapping[str, str]]] = {}
    texts: ClassVar[Mapping[str, str]] = REPORT_TEXTS
    sections: ClassVar[Sequence[str]] = ("statistics", "sentences", "highlight", "plots")

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        check_messages(cls.texts, REPORT_TEXTS)

    def __init__(
        self,
        source: str | Doc | Document,
        title: str | None = None,
        stats_classes: Mapping[str, type[Stats]] | None = None,
        *,
        skip_errors: bool = False,
    ):
        check_bool(skip_errors, "skip_errors")
        self.document = self.parse(source)
        self.title = self.texts["title"] if title is None else title
        classes = self.stats_classes if stats_classes is None else stats_classes
        self.stats: dict[str, Stats] = {}
        self.errors: dict[str, AnyTSError] = {}
        # The statistics read once, so that a statistic computed when it is read raises here,
        # for its class
        self._values: dict[str, dict[str, Any]] = {}
        for name, cls in classes.items():
            try:
                stats = self.compute(cls, self.document)
                self._values[name] = stats.get_stats()
            except AnyTSError as error:
                if not skip_errors:
                    raise
                self.errors[name] = error
            else:
                self.stats[name] = stats

    def parse(self, source: str | Doc | Document) -> Document:
        """
        Getting the document of a data source, once for all the sections

        Description:
            to_document by default; a language library overrides it with the
            parse of its classes

        Arguments:
            source (str|Doc|Document): Data source

        Returns:
            Document: Document of anySeg
        """
        from .document import to_document

        return to_document(source)

    @classmethod
    def compute(cls, stats_class: type[Stats], document: Document) -> Stats:
        """
        Getting the statistics of a class of the document or of its sentence

        Description:
            The class of the document; DiversityStats, which takes words, of the
            words of the document (document_words). A library overrides it for a
            class that takes something else or other parameters; Command.compute
            is this one of its report, so that the command counts alike

        Arguments:
            stats_class (type[Stats]): Class of statistics
            document (Document): Document of the text or of its sentence

        Returns:
            Stats: Statistics
        """
        from .diversity_stats import DiversityStats
        from .document import document_words

        if issubclass(stats_class, DiversityStats) and (
            stats_class.__init__ is DiversityStats.__init__
        ):
            return stats_class(document_words(document))
        return stats_class(document)  # type: ignore[call-arg]

    def to_html(self) -> str:
        """
        Getting the report as one HTML page

        Returns:
            str: HTML page
        """
        body = "".join(getattr(self, f"section_{name}")() for name in self.sections)
        style = _STYLE
        if self.highlight_class is not None and "highlight" in self.sections:
            style += self.highlight_class.css()
        return (
            f'<!DOCTYPE html>\n<html lang="{escape(self.texts["lang"])}">\n<head>\n'
            f'<meta charset="utf-8">\n<title>{escape(self.title)}</title>\n'
            f"<style>{style}</style>\n</head>\n<body>\n<main>\n"
            f"<h1>{escape(self.title)}</h1>\n{body}</main>\n</body>\n</html>\n"
        )

    def save(self, path: str | Path) -> None:
        """
        Writing the report to a file in UTF-8, the encoding the page declares

        Arguments:
            path (str|Path): Path of the file
        """
        Path(path).write_text(self.to_html(), encoding="utf-8")

    def section_statistics(self) -> str:
        """
        Getting the section of the statistics: a table per class with the
        description, the value and the reading of every statistic of stats_desc,
        as print_stats, the values of a dictionary described by value_desc; the
        classes left out by skip_errors named

        Returns:
            str: Fragment of HTML
        """
        texts = self.texts
        tables = []
        if self.errors:
            tables.append(
                f"<p>{escape(texts['left_out'].format(names=', '.join(self.errors)))}</p>\n"
            )
        for name, stats in self.stats.items():
            values = self._values[name]
            rows = []
            for stat, desc in stats.stats_desc.items():
                value = values[stat]
                if isinstance(value, Mapping):
                    value = {stats.value_desc(stat, key): item for key, item in value.items()}
                rows.append(
                    f"<tr><td>{escape(desc)}</td>"
                    f'<td class="number">{escape(_number(value, texts))}</td>'
                    f"<td>{escape(stats.describe(stat) or '')}</td></tr>"
                )
            tables.append(
                f"<h3>{escape(self.titles.get(name, name))}</h3>\n<table>\n"
                f"<tr><th>{escape(texts['statistic'])}</th>"
                f"<th>{escape(texts['value'])}</th><th>{escape(texts['reading'])}</th></tr>\n"
                + "\n".join(rows)
                + "\n</table>\n"
            )
        return _section(texts["statistics"], "".join(tables)) if self.stats else ""

    def section_sentences(self) -> str:
        """
        Getting the section of the sentences: the text of every sentence with the
        statistics of sentence_columns, none without them; a text of more than
        max_sentences sentences has those with the highest values of the first
        statistic, in their order

        Returns:
            str: Fragment of HTML
        """
        texts = self.texts
        columns = [(name, stat) for name, stat in self.sentence_columns if name in self.stats]
        if not columns:
            return ""
        tables = {
            name: self._sentences_table(type(self.stats[name]))
            for name in dict.fromkeys(name for name, _ in columns)
        }
        heads = "".join(
            f"<th>{escape(type(self.stats[name]).stats_desc.get(stat, stat))}</th>"
            for name, stat in columns
        )
        first = next(iter(tables.values()))
        numbers = list(range(len(first)))
        note = ""
        if len(numbers) > self.max_sentences:
            name, stat = columns[0]
            ranked = tables[name][stat].reset_index(drop=True)
            top = ranked.sort_values(ascending=False, kind="stable", na_position="last")
            numbers = sorted(top.index[: self.max_sentences])
            note = "<p>{}</p>\n".format(
                escape(
                    texts["top_sentences"].format(
                        shown=len(numbers),
                        total=len(first),
                        stat=type(self.stats[name]).stats_desc.get(stat, stat),
                    )
                )
            )
        text = self.document.text
        bounds = first[["start", "end"]].to_numpy().tolist()
        rows = []
        for number in numbers:
            start, end = bounds[number]
            cells = "".join(
                f'<td class="number">{escape(_cell(tables[name][stat].iloc[number], texts))}</td>'
                for name, stat in columns
            )
            rows.append(
                f'<tr><td class="number">{number + 1}</td>'
                f"<td>{escape(text[start:end])}</td>{cells}</tr>"
            )
        return _section(
            texts["sentences"],
            note
            + f"<table>\n<tr><th>#</th><th>{escape(texts['sentence'])}</th>{heads}</tr>\n"
            + "\n".join(rows)
            + "\n</table>\n",
        )

    def _sentences_table(self, stats_class: type[Stats]) -> DataFrame:
        """Table of the statistics of every sentence of the document, counted by compute"""
        counted = stats_class._count_parts(
            self.document, "sentences", {}, make=partial(self.compute, stats_class)
        )
        return _parts_dataframe(
            [(number, *part) for number, part in enumerate(counted)], "sentence"
        )

    def section_highlight(self) -> str:
        """
        Getting the section of the highlighted text, with the default layers of
        highlight_class, its styles in the head of the page; none without it

        Returns:
            str: Fragment of HTML
        """
        if self.highlight_class is None:
            return ""
        return _section(
            self.texts["highlight"], self.highlight_class(self.document).to_html(css=False)
        )

    def section_plots(self) -> str:
        """
        Getting the section of the plots of plots, in SVG

        Returns:
            str: Fragment of HTML
        """
        figures = "".join(
            f"<figure>\n{_svg(figure, f'plot{number}-')}\n"
            f"<figcaption>{escape(caption)}</figcaption>\n</figure>\n"
            for number, (caption, figure) in enumerate(self.plots(), start=1)
        )
        return _section(self.texts["plots"], figures) if figures else ""

    def plots(self) -> list[tuple[str, Figure]]:
        """
        Getting the plots of the report with their captions

        Description:
            The lengths of the sentences (sentence_lengths_plot) by default, with
            the labels of visualizer_labels, a mark on every sentence of a text
            of a few hundred of them; a text without sentences has none. A
            library overrides it to add its own, made on a Figure of matplotlib,
            not of pyplot, so that a command chooses no interactive backend

        Returns:
            list[tuple[str, Figure]]: Captions and figures of matplotlib
        """
        from matplotlib.figure import Figure

        from .visualizers.sentences import sentence_lengths_plot

        figure = Figure(figsize=(9, 4))
        ax = figure.subplots()
        try:
            sentence_lengths_plot(
                self.document,
                ax=ax,
                labels=self.visualizer_labels.get("sentence_lengths_plot"),
            )
        except AnyTSError:
            return []
        if len(self.document.sentences) > _MARKED_SENTENCES:
            for line in ax.get_lines():
                line.set_marker("")
        return [(self.texts["sentence_lengths"], figure)]


def escape(value: object) -> str:
    """
    Getting a text for HTML

    Description:
        The characters & < > " ' as character references, so that a text of the
        source or of the statistics never becomes markup

    Arguments:
        value (object): Value; its str

    Returns:
        str: Text for HTML

    Example:
        >>> from anyts.report import escape
        >>> escape('<script>alert("x")</script>')
        '&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;'
    """
    return html.escape(str(value), quote=True)


def _section(heading: str, content: str) -> str:
    """Section of the report with its heading"""
    return f"<section>\n<h2>{escape(heading)}</h2>\n{content}</section>\n"


def _number(value: Any, texts: Mapping[str, str]) -> str:
    """Value of a statistic as text: a float with two decimals, a small one with two significant
    digits, an undefined one as the text of undefined, a dictionary as its pairs"""
    if isinstance(value, Mapping):
        return ", ".join(f"{key}: {_number(item, texts)}" for key, item in value.items())
    if value is None or (isinstance(value, float) and not isfinite(value)):
        return texts["undefined"]
    if isinstance(value, float):
        return f"{value:.2g}" if 0 < abs(value) < 0.1 else f"{value:.2f}"
    return str(value)


def _cell(value: Any, texts: Mapping[str, str]) -> str:
    """Value of a statistic of a sentence, undefined for a sentence without statistics"""
    from pandas import isna

    return texts["undefined"] if isna(value) else _number(value, texts)


def _svg(figure: Figure, prefix: str) -> str:
    """SVG of a figure of matplotlib, with the text as paths, so that it needs no font, the same
    for the same figure, its ids starting with the prefix, so that those of several figures of a
    page differ"""
    import matplotlib

    buffer = io.StringIO()
    with matplotlib.rc_context({"svg.fonttype": "path", "svg.hashsalt": "anyts"}):
        figure.savefig(
            buffer,
            format="svg",
            bbox_inches="tight",
            metadata={"Date": None, "Creator": None, "Format": None, "Type": None},
        )
    svg = buffer.getvalue()
    return re.sub(r'(\bid="|href="#|url\(#)', rf"\1{prefix}", svg[svg.index("<svg") :])
