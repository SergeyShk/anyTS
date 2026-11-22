from __future__ import annotations

import argparse
import codecs
import contextlib
import io
import json
import os
import sys
from collections.abc import Callable, Mapping, Sequence
from functools import partial
from math import isfinite
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from .constants import CLI_TEXTS
from .exceptions import AnyTSError, ParameterError
from .report import Report
from .stats import Stats, StatsRow, _stats_row
from .utils import check_messages

if TYPE_CHECKING:
    from anyseg import Document
    from pandas import DataFrame

    from .datasets import Dataset

# Outputs of the command
_FORMATS = ("table", "json", "csv")
# Parts of the command stats
_PARTS = ("sentences", "lines", "paragraphs")
# Name of the standard input among the files and of the standard output for --output
_STDIN = "-"
# Encoding of the files by default: UTF-8, a byte order mark left out
_ENCODING = "utf-8-sig"


class Command:
    """
    Command line of the statistics of a language library

    Description:
        The command stats reads texts from files or from the standard input,
        parses every text once (parse) and prints the statistics of the classes
        of stats_classes: a table, JSON with the flat statistics of every class
        by text, or CSV with a row per text; with --parts, a row per sentence,
        line or paragraph (by_parts). The command report writes the HTML report
        of a text (report_class), and download the datasets of datasets. A text
        a class cannot count is reported on the standard error and the others
        are counted, with the exit code 1. Every command is a method
        command_<name>; a language library subclasses the class, adds options
        (arguments) and commands (subcommands), and calls run from the entry
        point of its command

    Attributes:
        args (argparse.Namespace): Arguments of the command line, set by run before
            the command, so that parse may read them
        names (list[str]): Names of the classes of the command, those of --stats

    Class attributes:
        prog (str): Name of the command
        stats_classes (dict[str, type[Stats]]): Classes of statistics by their
            name in --stats
        default_stats (tuple[str, ...]|None): Names of the classes counted without
            --stats; None - every class
        datasets (dict[str, Callable[[], Dataset]]): Datasets of the command download
            by name, as their classes; none by default, and no such command
        texts (dict[str, str]): Texts of the help and of the errors by key (CLI_TEXTS),
            complete as the messages of a class of statistics (check_messages)
        report_class (type[Report]): Report of the command report, made of the document
            of parse and the classes of --stats

    Raises:
        ParameterError: When a class is defined, if its texts are incomplete or have a
            field their default lacks, or default_stats names a class that is not in
            stats_classes

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
    default_stats: ClassVar[Sequence[str] | None] = None
    datasets: ClassVar[Mapping[str, Callable[[], Dataset]]] = {}
    texts: ClassVar[Mapping[str, str]] = CLI_TEXTS
    report_class: ClassVar[type[Report]] = Report

    args: argparse.Namespace
    names: list[str]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        check_messages(cls.texts, CLI_TEXTS)
        if cls.default_stats is not None:
            unknown = [name for name in cls.default_stats if name not in cls.stats_classes]
            if unknown:
                raise ParameterError(
                    f"default_stats of {cls.__name__} must be names of stats_classes, "
                    f"not {', '.join(unknown)}"
                )

    def parse(self, text: str) -> Document:
        """
        Getting the document of a text, once for all the classes

        Description:
            to_document by default; a language library overrides it with the
            parse of its classes, so that a text is segmented and annotated once,
            and may read the arguments (args) and the classes of the command
            (names), as to parse with a model only for the classes that need it.
            A text it cannot parse raises SourceError, so that the other texts are
            counted

        Arguments:
            text (str): Text

        Returns:
            Document: Document of anySeg
        """
        from .document import to_document

        return to_document(text)

    def compute(self, stats_class: type[Stats], document: Document) -> Stats:
        """
        Getting the statistics of a class of a document or of its part

        Description:
            compute of report_class by default, so that the command stats, its
            parts and the command report count alike: a library overrides that of
            its report

        Arguments:
            stats_class (type[Stats]): Class of statistics
            document (Document): Document of the text or of its part

        Returns:
            Stats: Statistics
        """
        return self.report_class.compute(stats_class, document)

    def parser(self) -> argparse.ArgumentParser:
        """
        Getting the parser of the arguments of the command

        Description:
            The commands stats and report with the options of arguments, download
            with datasets, and the commands of subcommands; the headings, the
            usage, the help option and the errors of the command come from texts,
            the other errors of argparse from its translation (gettext)

        Returns:
            ArgumentParser: Parser of the commands
        """
        texts = self.texts
        parser = _Parser(prog=self.prog, description=texts["description"], texts=texts)
        commands = parser.add_subparsers(
            dest="command", required=True, title=texts["commands"], parser_class=_Parser
        )
        stats = commands.add_parser("stats", help=texts["stats_command"], texts=texts)
        stats.add_argument("files", nargs="*", metavar=texts["files_metavar"], help=texts["files"])
        self._add_options(stats, "")
        stats.add_argument("-p", "--parts", choices=_PARTS, help=texts["parts_option"])
        stats.add_argument(
            "-f", "--format", choices=_FORMATS, default="table", help=texts["format_option"]
        )
        self.arguments(stats, "stats")
        report = commands.add_parser("report", help=texts["report_command"], texts=texts)
        report.add_argument(
            "file", nargs="?", default=_STDIN, metavar=texts["file_metavar"], help=texts["file"]
        )
        self._add_options(report, "report_")
        report.add_argument(
            "-t", "--title", metavar=texts["title_metavar"], help=texts["title_option"]
        )
        self.arguments(report, "report")
        if self.datasets:
            download = commands.add_parser("download", help=texts["download_command"], texts=texts)
            download.add_argument(
                "names",
                nargs="*",
                metavar=texts["datasets_metavar"],
                help=texts["datasets_option"].format(names=", ".join(self.datasets)),
            )
            download.add_argument("--force", action="store_true", help=texts["force_option"])
        self.subcommands(commands)
        return parser

    def arguments(self, parser: argparse.ArgumentParser, command: str) -> None:
        """
        Adding the options of a library to a command

        Description:
            None by default; a library adds options to the parser of the command,
            and their values come to args

        Arguments:
            parser (ArgumentParser): Parser of the command
            command (str): Name of the command: stats or report
        """

    def subcommands(self, commands: argparse._SubParsersAction[Any]) -> None:
        """
        Adding the commands of a library

        Description:
            None by default; a library adds a command with commands.add_parser and
            runs it with its method command_<name>, which takes args and returns
            the exit code

        Arguments:
            commands (argparse._SubParsersAction): Commands of the parser
        """

    def run(self, argv: Sequence[str] | None = None) -> int:
        """
        Running the command

        Description:
            The arguments go to args and the classes of --stats to names, and the
            method command_<name> of the command runs

        Arguments:
            argv (list[str]): Arguments; those of the command line by default

        Returns:
            int: Exit code: 0, 1 if a text could not be read or counted or the
                reader of the output stopped, 2 for wrong arguments, 130 if
                interrupted
        """
        parser = self.parser()
        try:
            self.args = parser.parse_args(argv)
            self.names = self._names(parser, self.args)
            self._check_datasets(parser, self.args)
        except SystemExit as ended:
            # The help and the wrong arguments, which argparse ends with sys.exit
            return int(ended.code or 0)
        try:
            code: int = getattr(self, f"command_{self.args.command}")(self.args)
        except BrokenPipeError:
            # The reader of the output, as head, has stopped: the rest goes nowhere
            _close_stdout()
            return 1
        except KeyboardInterrupt:
            return 130
        return code

    def command_stats(self, args: argparse.Namespace) -> int:
        """
        Running the command stats

        Description:
            The statistics of every text, printed as it is counted in a table, or
            those of all the texts in JSON or CSV, to the output in UTF-8

        Arguments:
            args (argparse.Namespace): Arguments of the command

        Returns:
            int: Exit code: 0, 1 if a text could not be read or counted
        """
        sources = args.files or [_STDIN]
        part = (args.parts or "sentences")[:-1]
        failed = False
        results: dict[str, dict[str, Any]] = {}
        output = self._output(args.output)
        if output is None:
            return 1
        for source in sources:
            found = self._text_stats(source, args)
            failed = failed or found is None or len(found) < len(self.names)
            if found is None:
                continue
            if args.format == "table":
                text = self._tables(source, found, part, many=len(sources) > 1)
                if not self._put(output, text):
                    return 1
            else:
                # The statistics kept, not the objects
                results[source] = {
                    name: _stats_row(value) if isinstance(value, Stats) else value
                    for name, value in found.items()
                }
        if args.format != "table" and not self._put(
            output, _formatted(results, args.format, part)
        ):
            return 1
        return 1 if failed else 0

    def command_report(self, args: argparse.Namespace) -> int:
        """
        Running the command report

        Description:
            The report of a text with the classes of the command that can count
            it, to the output in UTF-8, the encoding the page declares

        Arguments:
            args (argparse.Namespace): Arguments of the command

        Returns:
            int: Exit code: 0, 1 if the text could not be read or a class could not
                count it
        """
        document = self._document(args.file, args.encoding)
        output = self._output(args.output)
        if document is None or output is None:
            return 1
        try:
            report = self.report_class(
                document,
                title=args.title,
                stats_classes={name: self.stats_classes[name] for name in self.names},
                skip_errors=True,
            )
            page = report.to_html()
        except AnyTSError as error:
            self._error(self.texts["file_error"].format(source=args.file, error=error))
            return 1
        for name, failure in report.errors.items():
            self._error(
                self.texts["stats_error"].format(source=args.file, name=name, error=failure)
            )
        if not self._put(output, page):
            return 1
        return 1 if report.errors else 0

    def command_download(self, args: argparse.Namespace) -> int:
        """
        Running the command download

        Description:
            Every dataset of the names, every one of datasets without them, is
            downloaded, again with --force, and named on the standard output; one
            that cannot be downloaded is reported on the standard error and the
            others are downloaded

        Arguments:
            args (argparse.Namespace): Arguments of the command

        Returns:
            int: Exit code: 0, 1 if a dataset could not be downloaded
        """
        output = _Output(None)
        failed = False
        for name in dict.fromkeys(args.names or self.datasets):
            try:
                self.datasets[name]().download(force=args.force)
            except (AnyTSError, OSError) as error:
                self._error(self.texts["file_error"].format(source=name, error=error))
                failed = True
            else:
                self._put(output, self.texts["downloaded"].format(name=name) + "\n")
        return 1 if failed else 0

    def _add_options(self, parser: argparse.ArgumentParser, prefix: str) -> None:
        """Options of the classes, of the output and of the encoding, with the help of the keys
        of the command: stats_option for stats, report_stats_option for report"""
        texts = self.texts
        names = ", ".join(self.stats_classes)
        parser.add_argument(
            "-s",
            "--stats",
            metavar=texts["stats_metavar"],
            help=texts[f"{prefix}stats_option"].format(names=names)
            if self.default_stats is None
            else texts[f"{prefix}stats_option_default"].format(
                names=names, defaults=", ".join(self.default_stats)
            ),
        )
        parser.add_argument(
            "-o", "--output", metavar=texts["output_metavar"], help=texts["output_option"]
        )
        parser.add_argument(
            "-e",
            "--encoding",
            default=_ENCODING,
            type=partial(_encoding, message=texts["unknown_encoding"]),
            metavar=texts["encoding_metavar"],
            help=texts[f"{prefix}encoding_option"],
        )

    def _names(self, parser: argparse.ArgumentParser, args: argparse.Namespace) -> list[str]:
        """Names of the classes of --stats, those of default_stats without it; with --parts,
        those that count such parts, a class named in --stats that does not being an error"""
        option = getattr(args, "stats", None)
        names = list(self.stats_classes if self.default_stats is None else self.default_stats)
        if option is not None:
            names = [name.strip() for name in option.split(",") if name.strip()]
            for name in names:
                if name not in self.stats_classes:
                    parser.error(
                        self.texts["unknown_stats"].format(
                            name=name, names=", ".join(self.stats_classes)
                        )
                    )
        parts = getattr(args, "parts", None)
        if parts is None:
            return names
        if option is not None:
            for name in names:
                if parts not in self.stats_classes[name].part_kinds:
                    parser.error(self.texts["no_parts"].format(name=name, parts=parts))
            return names
        names = [name for name in names if parts in self.stats_classes[name].part_kinds]
        if not names:
            parser.error(self.texts["parts_classes"].format(parts=parts))
        return names

    def _check_datasets(self, parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
        """The names of the command download, each one of datasets"""
        if args.command != "download":
            return
        for name in args.names:
            if name not in self.datasets:
                parser.error(
                    self.texts["unknown_dataset"].format(name=name, names=", ".join(self.datasets))
                )

    def _text_stats(self, source: str, args: argparse.Namespace) -> dict[str, Any] | None:
        """Statistics of the classes of a text, or the rows of its parts, without a class that
        could not count it; None if the text could not be read or parsed"""
        document = self._document(source, args.encoding)
        if document is None:
            return None
        found: dict[str, Any] = {}
        for name in self.names:
            cls = self.stats_classes[name]
            try:
                if args.parts:
                    found[name] = cls._count_parts(
                        document, args.parts, {}, make=partial(self.compute, cls)
                    )
                else:
                    stats = self.compute(cls, document)
                    # A statistic computed when it is read raises here, for its text
                    stats.get_stats()
                    found[name] = stats
            except AnyTSError as error:
                self._error(
                    self.texts["stats_error"].format(source=source, name=name, error=error)
                )
        return found

    def _document(self, source: str, encoding: str) -> Document | None:
        """Document of a file or of the standard input, None with its error reported"""
        try:
            text = _read(source, encoding)
        except UnicodeError as error:
            self._error(self.texts["decode_error"].format(source=source, error=error))
            return None
        except OSError as error:
            self._error(self.texts["file_error"].format(source=source, error=error))
            return None
        try:
            return self.parse(text)
        except AnyTSError as error:
            self._error(self.texts["file_error"].format(source=source, error=error))
            return None

    def _output(self, path: str | None) -> _Output | None:
        """The output of a command, None with its error reported"""
        try:
            return _Output(path)
        except OSError as error:
            self._error(self.texts["file_error"].format(source=path, error=error))
            return None

    def _put(self, output: _Output, text: str) -> bool:
        """Writing to the output, False with its error reported"""
        try:
            output.write(text)
        except BrokenPipeError:
            raise
        except OSError as error:
            self._error(self.texts["file_error"].format(source=output.name, error=error))
            return False
        return True

    def _error(self, message: str) -> None:
        """Message of an error on the standard error"""
        _write(sys.stderr, f"{self.prog}: {message}\n")

    def _tables(self, source: str, found: Mapping[str, Any], part: str, *, many: bool) -> str:
        """Tables of the statistics of a text by class, with a heading where there are several
        texts or classes"""
        from contextlib import redirect_stdout

        tables = io.StringIO()
        for name, value in found.items():
            if many or len(found) > 1:
                tables.write(f"{source}: {name}\n" if many else f"{name}\n")
            if isinstance(value, Stats):
                with redirect_stdout(tables):
                    value.print_stats()
            else:
                tables.write(_parts(value, part).to_string() + "\n")
            tables.write("\n")
        return tables.getvalue()


class _Formatter(argparse.HelpFormatter):
    """Help of the arguments with the usage of the texts of a command"""

    def __init__(self, prog: str, *, usage: str, **kwargs: Any) -> None:
        super().__init__(prog, **kwargs)
        self._usage_prefix = usage

    def add_usage(
        self, usage: str | None, actions: Any, groups: Any, prefix: str | None = None
    ) -> None:
        super().add_usage(usage, actions, groups, self._usage_prefix if prefix is None else prefix)


class _Parser(argparse.ArgumentParser):
    """Parser of a command with the texts of the command: the usage, the headings of its
    positional arguments and options, the help option and the error"""

    def __init__(self, *args: Any, texts: Mapping[str, str], **kwargs: Any) -> None:
        kwargs.update(formatter_class=partial(_Formatter, usage=texts["usage"]), add_help=False)
        super().__init__(*args, **kwargs)
        self.texts = texts
        # The groups of the arguments of argparse, those a library adds among them
        self._positionals.title = texts["positionals"]
        self._optionals.title = texts["options"]
        self.add_argument(
            "-h", "--help", action="help", default=argparse.SUPPRESS, help=texts["help_option"]
        )

    def _print_message(self, message: str, file: Any = None) -> None:
        # The help, the usage and the errors of argparse go out as the output does
        with contextlib.suppress(OSError):
            _write(file or sys.stderr, message)

    def error(self, message: str) -> Any:
        self.print_usage(sys.stderr)
        self.exit(2, self.texts["error"].format(prog=self.prog, message=message) + "\n")


def _encoding(name: str, message: str) -> str:
    """Name of an encoding Python knows, an error of argparse otherwise"""
    try:
        codecs.lookup(name)
    except LookupError:
        raise argparse.ArgumentTypeError(message.format(encoding=name)) from None
    return name


def _read(source: str, encoding: str) -> str:
    """Text of a file or of the standard input, its line breaks read alike"""
    if source == _STDIN:
        wrapper = io.TextIOWrapper(sys.stdin.buffer, encoding=encoding)
        try:
            return wrapper.read()
        finally:
            wrapper.detach()
    return Path(source).read_text(encoding=encoding)


class _Output:
    """The file of the output, made at once so that a wrong path is reported before the texts
    are counted, or the standard output, written in UTF-8 with the line breaks \\n"""

    def __init__(self, path: str | None) -> None:
        self.name = _STDIN if path is None else path
        if self.name != _STDIN:
            with Path(self.name).open("w", encoding="utf-8"):
                pass

    def write(self, text: str) -> None:
        """Writing a text, at once, so that an error of the output comes with it"""
        if self.name != _STDIN:
            with Path(self.name).open("a", encoding="utf-8", newline="\n") as file:
                file.write(text)
            return
        _write(sys.stdout, text)


def _write(stream: Any, text: str) -> None:
    """Writing a text to a standard stream in UTF-8, as bytes, whatever the encoding of the
    console; a stream of text without bytes, as in a test, gets the text, and none, as under
    pythonw, nothing"""
    if stream is None:
        return
    buffer = getattr(stream, "buffer", None)
    if buffer is None:
        stream.write(text)
        return
    stream.flush()
    buffer.write(text.encode("utf-8"))
    buffer.flush()


def _close_stdout() -> None:
    """The standard output to the null device, so that the interpreter does not report the
    closed pipe as it exits"""
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, sys.stdout.fileno())


def _parts(counted: Sequence[tuple[int, int, StatsRow | None]], part: str) -> DataFrame:
    """Table of the parts of one text"""
    from .stats import _parts_dataframe

    return _parts_dataframe([(number, *found) for number, found in enumerate(counted)], part)


def _formatted(results: Mapping[str, Mapping[str, Any]], fmt: str, part: str) -> str:
    """Statistics of all the texts in JSON or CSV; part names the index of the parts"""
    if fmt == "json":
        data = {
            source: {name: _json_value(value, part) for name, value in found.items()}
            for source, found in results.items()
        }
        return json.dumps(data, ensure_ascii=False, allow_nan=False) + "\n"
    # The line ends of CSV, \n alike in a file and on the standard output
    return str(_table(results, part).to_csv(lineterminator="\n"))


def _json_value(value: Any, part: str) -> Any:
    """Flat statistics, or records of the parts, for JSON: nan and infinities as null"""
    if isinstance(value, tuple):
        cls, nested = value
        return _finite(cls._flat(nested))
    table = _parts(value, part).reset_index()
    # The parts without statistics have None for NaN and for the NA of the counts
    table = table.astype(object).where(table.notna(), None)
    return [_finite(record) for record in table.to_dict("records")]


def _finite(stats: Mapping[str, Any]) -> dict[str, Any]:
    """Values for JSON: nan and infinities as None"""
    return {
        str(key): None if isinstance(value, float) and not isfinite(value) else value
        for key, value in stats.items()
    }


def _table(results: Mapping[str, Mapping[str, Any]], part: str) -> DataFrame:
    """One table of the texts, or of their parts, with the columns of every class named by it:
    a value of a dictionary statistic a text or a part lacks is 0 across all of them, and the
    positions of the parts of a text come from any class that counted it"""
    from pandas import DataFrame, MultiIndex, concat

    from .stats import _parts_dataframe, _stats_table

    names = list(dict.fromkeys(name for found in results.values() for name in found))
    columns: list[DataFrame] = []
    bounds: dict[tuple[str, int], tuple[int, int]] = {}
    for name in names:
        found = {source: value[name] for source, value in results.items() if name in value}
        if all(isinstance(value, tuple) for value in found.values()):
            frame = _stats_table(list(found.values()), list(found))
            frame.index.name = "source"
        else:
            keyed = [
                ((source, number), *counted)
                for source, value in found.items()
                for number, counted in enumerate(value)
            ]
            for key, start, end, _ in keyed:
                bounds.setdefault(key, (start, end))
            frame = _parts_dataframe(keyed, ("source", part)).drop(columns=["start", "end"])
        columns.append(frame.add_prefix(f"{name}."))
    if bounds:
        keys = sorted(bounds, key=lambda key: (list(results).index(key[0]), key[1]))
        columns.insert(
            0,
            DataFrame(
                [bounds[key] for key in keys],
                index=MultiIndex.from_tuples(keys, names=["source", part]),
                columns=["start", "end"],
            ),
        )
    return concat(columns, axis=1) if columns else DataFrame()
