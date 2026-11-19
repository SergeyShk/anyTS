from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from math import isfinite
from pathlib import Path
from typing import IO, TYPE_CHECKING, Any, ClassVar

from .constants import CLI_TEXTS
from .exceptions import AnyTSError
from .stats import Stats
from .utils import check_messages

if TYPE_CHECKING:
    from anyseg import Document
    from pandas import DataFrame

# Outputs of the command
_FORMATS = ("table", "json", "csv")
# Name of the standard input among the files
_STDIN = "-"


class Command:
    """
    Command line of the statistics of a language library

    Description:
        The command stats reads texts from files or from the standard input,
        parses every text once (parse) and prints the statistics of the classes
        of stats_classes: a table, JSON with the flat statistics of every class
        by text, or CSV with a row per text; with --parts, a row per sentence or
        paragraph (by_parts). A text a class cannot count is reported on the
        standard error and the others are counted, with the exit code 1. A
        language library subclasses it and calls run from the entry point of its
        command

    Class attributes:
        prog (str): Name of the command
        stats_classes (dict[str, type[Stats]]): Classes of statistics by their
            name in --stats
        texts (dict[str, str]): Texts of the help and of the errors by key (CLI_TEXTS),
            complete as the messages of a class of statistics (check_messages)

    Raises:
        ParameterError: When a class is defined, if its texts are incomplete or have a
            field their default lacks

    Example:
        >>> from anyts.basic_stats import BasicStats
        >>> from anyts.cli import Command
        >>> class Vowels(BasicStats):
        ...     def count_syllables(self, word):
        ...         return sum(char in "aeiou" for char in word.lower())
        >>> class Stats(Command):
        ...     prog = "vowels"
        ...     stats_classes = {"basic": Vowels}
        >>> import pathlib, tempfile
        >>> path = pathlib.Path(tempfile.mkdtemp()) / "cat.txt"
        >>> _ = path.write_text("The cat sleeps.")
        >>> Stats().run(["stats", "--format", "json", str(path)])  # doctest: +ELLIPSIS
        {"...cat.txt": {"basic": {"c_letters_3": 2, ..., "n_words": 3, ...}}}
        0
    """

    prog: ClassVar[str] = "anyts"
    stats_classes: ClassVar[Mapping[str, type[Stats]]] = {}
    texts: ClassVar[Mapping[str, str]] = CLI_TEXTS

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        check_messages(cls.texts, CLI_TEXTS)

    def parse(self, text: str) -> Document:
        """
        Getting the document of a text, once for all the classes

        Description:
            to_document by default; a language library overrides it with the
            parse of its classes, so that a text is segmented and annotated once

        Arguments:
            text (str): Text

        Returns:
            Document: Document of anySeg
        """
        from .document import to_document

        return to_document(text)

    def compute(self, cls: type[Stats], document: Document) -> Stats:
        """
        Getting the statistics of a class of a document

        Description:
            The class of the document; DiversityStats, which takes words, of the
            words of the document (document_words). A library overrides it for a
            class that takes something else

        Arguments:
            cls (type[Stats]): Class of statistics
            document (Document): Document of the text

        Returns:
            Stats: Statistics
        """
        from .diversity_stats import DiversityStats
        from .document import document_words

        if issubclass(cls, DiversityStats):
            return cls(document_words(document))
        return cls(document)  # type: ignore[call-arg]

    def parser(self) -> argparse.ArgumentParser:
        """
        Getting the parser of the arguments of the command

        Returns:
            ArgumentParser: Parser with the command stats
        """
        texts = self.texts
        parser = argparse.ArgumentParser(prog=self.prog, description=texts["description"])
        commands = parser.add_subparsers(dest="command", required=True)
        stats = commands.add_parser("stats", help=texts["stats_command"])
        self._add_input(stats)
        stats.add_argument(
            "-s",
            "--stats",
            help=texts["stats_option"].format(names=", ".join(self.stats_classes)),
        )
        stats.add_argument(
            "-p", "--parts", choices=("sentences", "paragraphs"), help=texts["parts_option"]
        )
        stats.add_argument(
            "-f", "--format", choices=_FORMATS, default="table", help=texts["format_option"]
        )
        return parser

    def run(self, argv: Sequence[str] | None = None) -> int:
        """
        Running the command

        Arguments:
            argv (list[str]): Arguments; those of the command line by default

        Returns:
            int: Exit code: 0, 1 if a text could not be read or counted, 2 for wrong
                arguments
        """
        parser = self.parser()
        try:
            args = parser.parse_args(argv)
            names = self._names(parser, args.stats)
            if args.parts:
                for name in names:
                    if args.parts not in self.stats_classes[name].part_kinds:
                        parser.error(self.texts["no_parts"].format(name=name, parts=args.parts))
        except SystemExit as ended:
            # The help and the wrong arguments, which argparse ends with sys.exit
            return int(ended.code or 0)
        failed = False
        results: dict[str, dict[str, Any]] = {}
        for source in args.files or [_STDIN]:
            try:
                text = self._read(source, args.encoding)
            except (OSError, UnicodeDecodeError) as error:
                self._error(self.texts["file_error"].format(source=source, error=error))
                failed = True
                continue
            try:
                document = self.parse(text)
            except AnyTSError as error:
                self._error(
                    self.texts["stats_error"].format(source=source, name="parse", error=error)
                )
                failed = True
                continue
            results[source] = {}
            for name in names:
                cls = self.stats_classes[name]
                try:
                    results[source][name] = (
                        cls._count_parts(document, args.parts, {})
                        if args.parts
                        else self.compute(cls, document)
                    )
                except AnyTSError as error:
                    self._error(
                        self.texts["stats_error"].format(source=source, name=name, error=error)
                    )
                    failed = True
        with self._output(args.output, args.encoding) as output:
            self._write(results, args.format, (args.parts or "sentences")[:-1], output)
        return 1 if failed else 0

    def _add_input(self, parser: argparse.ArgumentParser) -> None:
        """Arguments of the files, of the output and of the encoding"""
        texts = self.texts
        parser.add_argument("files", nargs="*", help=texts["files"])
        parser.add_argument("-o", "--output", help=texts["output_option"])
        parser.add_argument("-e", "--encoding", default="utf-8", help=texts["encoding_option"])

    def _names(self, parser: argparse.ArgumentParser, option: str | None) -> list[str]:
        """Names of the classes of --stats, every class without it"""
        if option is None:
            return list(self.stats_classes)
        names = [name.strip() for name in option.split(",") if name.strip()]
        for name in names:
            if name not in self.stats_classes:
                parser.error(
                    self.texts["unknown_stats"].format(
                        name=name, names=", ".join(self.stats_classes)
                    )
                )
        return names

    def _read(self, source: str, encoding: str) -> str:
        """Text of a file or of the standard input"""
        if source == _STDIN:
            return sys.stdin.read()
        return Path(source).read_text(encoding=encoding)

    def _error(self, message: str) -> None:
        """Message of an error on the standard error"""
        print(f"{self.prog}: {message}", file=sys.stderr)

    def _output(self, path: str | None, encoding: str) -> Any:
        """The file of the output or the standard output, which stays open"""
        from contextlib import nullcontext

        if path is None:
            return nullcontext(sys.stdout)
        return Path(path).open("w", encoding=encoding)

    def _write(
        self, results: Mapping[str, Mapping[str, Any]], fmt: str, part: str, output: IO[str]
    ) -> None:
        """Statistics in the format; part names the index of the parts"""
        if fmt == "json":
            data = {
                source: {name: _json_value(value, part) for name, value in found.items()}
                for source, found in results.items()
            }
            output.write(json.dumps(data, ensure_ascii=False, allow_nan=False) + "\n")
        elif fmt == "csv":
            _table(results, part).to_csv(output)
        else:
            self._print(results, part, output)

    def _print(self, results: Mapping[str, Mapping[str, Any]], part: str, output: IO[str]) -> None:
        """Tables of the statistics of every text and class, with a heading where there are
        several"""
        from contextlib import redirect_stdout

        many = len(results) > 1
        for source, found in results.items():
            for name, value in found.items():
                if many or len(found) > 1:
                    output.write(f"{source}: {name}\n" if many else f"{name}\n")
                if isinstance(value, Stats):
                    with redirect_stdout(output):
                        value.print_stats()
                else:
                    output.write(_parts(value, part).to_string() + "\n")
                output.write("\n")


def _parts(counted: Sequence[tuple[int, int, Stats | None]], part: str) -> DataFrame:
    """Table of the parts of one text"""
    from .stats import _parts_dataframe

    return _parts_dataframe([(number, *found) for number, found in enumerate(counted)], part)


def _json_value(value: Any, part: str) -> Any:
    """Flat statistics, or records of the parts, for JSON: nan and infinities as null"""
    if isinstance(value, Stats):
        return _finite(value.get_stats(flat=True))
    return [_finite(record) for record in _parts(value, part).reset_index().to_dict("records")]


def _finite(stats: Mapping[str, Any]) -> dict[str, Any]:
    """Values for JSON: nan and infinities as None"""
    return {
        str(key): None if isinstance(value, float) and not isfinite(value) else value
        for key, value in stats.items()
    }


def _table(results: Mapping[str, Mapping[str, Any]], part: str) -> DataFrame:
    """One table of the texts, or of their parts, with the columns of every class named by it:
    a value of a dictionary statistic a text or a part lacks is 0 across all of them"""
    from pandas import DataFrame, concat

    from .stats import _parts_dataframe, stats_dataframe

    names = list(dict.fromkeys(name for found in results.values() for name in found))
    columns: list[DataFrame] = []
    for name in names:
        found = {source: value[name] for source, value in results.items() if name in value}
        if all(isinstance(value, Stats) for value in found.values()):
            frame = stats_dataframe(list(found.values()), index=list(found))
            frame.index.name = "source"
        else:
            frame = _parts_dataframe(
                [
                    ((source, number), *counted)
                    for source, value in found.items()
                    for number, counted in enumerate(value)
                ],
                ("source", part),
            )
            if not columns:
                columns.append(frame[["start", "end"]])
            frame = frame.drop(columns=["start", "end"])
        columns.append(frame.add_prefix(f"{name}."))
    return concat(columns, axis=1) if columns else DataFrame()
