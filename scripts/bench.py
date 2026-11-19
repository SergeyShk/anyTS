"""
Speed and memory of the classes of statistics against master

The classes read frozen documents: CoNLL-U files of texts annotated by the pipelines of the
language libraries, in the folder of the environment variable BENCH_DATA or of --data, by
default core_snapshot/bench-documents next to the clone of the repository. Every class
runs once over all of them to warm up, then REPEATS times; the fastest run is its time. Its
memory is the largest peak of the memory Python allocates for one document, which does not
change from round to round, so run takes it in the first round only (take --no-memory). The
garbage collector runs before every measurement and not during it, since the trees hold cycles.

Usage:
    make bench [BASE=REF]
    uv run python scripts/bench.py run [--data DIR] [--base REF]
    uv run python scripts/bench.py take OUT [--data DIR] [--no-memory]
    uv run python scripts/bench.py compare OLD NEW

run takes the classes of a worktree of a base, the commit this branch starts from on master
(git merge-base) by default or a tag or commit of --base, and of this tree, in the same
environment and in ROUNDS rounds in turn, the fastest of them counting, and prints the table
of both; a class one of them lacks, and the memory of a take without it, has a dash. The base
runs with the dependencies of this tree: a change of a dependency, such as anySeg, is measured
by take in the environment of each side and compare.
"""

import argparse
import gc
import importlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import tracemalloc
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, NamedTuple

ROOT = Path(__file__).resolve().parents[1]
REPEATS = 3
# Rounds of the base and this tree in turn, so that a change of the load of the machine falls
# on both
ROUNDS = 3
VOWELS = "aeiouyáéíóúüаеёиоуыэюя"
VOWEL_GROUP = re.compile(f"[{VOWELS}]+")
SYLLABLE = re.compile(f"[^{VOWELS}]*[{VOWELS}]+(?:[^{VOWELS}]+$)?")


class Entry(NamedTuple):
    ipm: float
    range: float
    dispersion: float


class Frequencies:
    """Frequency dictionary of a frequency by the length of a lemma"""

    min_ipm = 0.5

    def lookup(self, lemma: str) -> Entry:
        return Entry(float(len(lemma)), 1.0, 0.5)

    def ipm(self, lemma: str) -> float:
        return float(len(lemma))


def _basic() -> Callable[[Any], Any]:
    from anyts.basic_stats import BasicStats

    class Basic(BasicStats):
        def count_syllables(self, word: str) -> int:
            return len(VOWEL_GROUP.findall(word.lower()))

    return Basic


def _readability() -> Callable[[Any], Any]:
    from anyts.readability_stats import ReadabilityStats

    return type("Readability", (ReadabilityStats,), {"basic_stats_class": _basic()})


def _phon() -> Callable[[Any], Any]:
    from anyts.phon_stats import PhonStats

    class Phon(PhonStats):
        def syllabify(self, word: str) -> Sequence[str]:
            return SYLLABLE.findall(word) or [word]

    return Phon


def _diversity() -> Callable[[Any], Any]:
    from anyts.diversity_stats import DiversityStats
    from anyts.document import document_words

    return lambda document: DiversityStats([word.lower() for word in document_words(document)])


def _lexical() -> Callable[[Any], Any]:
    from anyts.lexical_stats import LexicalStats

    return type("Lexical", (LexicalStats,), {"freq_dict_class": Frequencies})


def _core(module: str, name: str) -> Callable[[], Callable[[Any], Any]]:
    return lambda: getattr(importlib.import_module(f"anyts.{module}"), name)


# Every class with the hooks of a language it needs, made when the tree has it
CLASSES: dict[str, Callable[[], Callable[[Any], Any]]] = {
    "get_tree": _core("document", "get_tree"),
    "BasicStats": _basic,
    "ReadabilityStats": _readability,
    "StyleStats": _core("style_stats", "StyleStats"),
    "PhonStats": _phon,
    "DiversityStats": _diversity,
    "LexicalStats": _lexical,
    "MorphStats": _core("morph_stats", "MorphStats"),
    "SyntaxStats": _core("syntax_stats", "SyntaxStats"),
    "CohesionStats": _core("cohesion_stats", "CohesionStats"),
}


def data_files(data: Path) -> list[Path]:
    paths = sorted(data.rglob("*.conllu"))
    if not paths:
        raise SystemExit(f"No CoNLL-U files in {data}: set BENCH_DATA or --data")
    return paths


def documents(data: Path) -> list[Any]:
    from anyseg import read_conllu

    return [read_conllu(path.read_text(encoding="utf-8"))[0] for path in data_files(data)]


def measure(
    make: Callable[[Any], Any], sources: Sequence[Any], memory: bool = True
) -> dict[str, float]:
    def run(source: Any) -> None:
        stats = make(source)
        if hasattr(stats, "get_stats"):
            stats.get_stats()

    for source in sources:
        run(source)
    times = []
    peaks = []
    try:
        for _ in range(REPEATS):
            gc.collect()
            gc.disable()
            start = time.perf_counter()
            for source in sources:
                run(source)
            times.append(time.perf_counter() - start)
            gc.enable()
        for source in sources if memory else ():
            gc.collect()
            gc.disable()
            tracemalloc.start()
            run(source)
            peaks.append(tracemalloc.get_traced_memory()[1])
            tracemalloc.stop()
            gc.enable()
    finally:
        gc.enable()
    return {"time": min(times), "memory": max(peaks)} if peaks else {"time": min(times)}


def take(out: Path, data: Path, memory: bool = True) -> None:
    import anyts

    sources = documents(data)
    results = {}
    for name, factory in CLASSES.items():
        try:
            make = factory()
        except (ImportError, AttributeError):
            continue
        results[name] = measure(make, sources, memory)
    meta = {"anyts": str(Path(anyts.__file__).parent), "documents": len(sources)}
    out.write_text(json.dumps({"meta": meta, "classes": results}, indent=1), encoding="utf-8")


def compare(old: Path, new: Path, names: tuple[str, str] = ("old", "new")) -> None:
    before, after = (
        json.loads(path.read_text(encoding="utf-8"))["classes"] for path in (old, new)
    )
    print(
        f"{'':18}{names[0] + ', s':>12}{names[1] + ', s':>12}{'change':>9}"
        f"{names[0] + ', MB':>13}{names[1] + ', MB':>13}{'change':>9}"
    )
    for name in {**before, **after}:
        first, second = before.get(name), after.get(name)
        print(
            f"{name:18}{_value(first, 'time', 1):>12}{_value(second, 'time', 1):>12}"
            f"{_change(first, second, 'time'):>9}"
            f"{_value(first, 'memory', 1e6):>13}{_value(second, 'memory', 1e6):>13}"
            f"{_change(first, second, 'memory'):>9}"
        )


def _value(stats: dict[str, float] | None, key: str, unit: float) -> str:
    if stats is None or key not in stats:
        return "-"
    return f"{stats[key] / unit:.{3 if key == 'time' else 1}f}"


def _change(first: dict[str, float] | None, second: dict[str, float] | None, key: str) -> str:
    if first is None or second is None or not first.get(key) or key not in second:
        return ""
    return f"{(second[key] - first[key]) / first[key] * 100:+.1f} %"


def run(data: Path, base: str | None = None) -> None:
    data_files(data)
    script = str(Path(__file__).resolve())
    base = base or _git("merge-base", "HEAD", "master")
    with tempfile.TemporaryDirectory() as folder:
        tree = Path(folder) / "base"
        _git("worktree", "add", "--quiet", "--detach", str(tree), base)
        try:
            # The anyts of the worktree comes first on the path, in the same environment
            environment = {**os.environ, "PYTHONPATH": str(tree), "PYTHONDONTWRITEBYTECODE": "1"}
            command = [sys.executable, script, "take"]
            for round_ in range(ROUNDS):
                for side, env in (("base", environment), ("this", None)):
                    out = f"{folder}/{side}-{round_}.json"
                    memory = [] if round_ == 0 else ["--no-memory"]
                    _take([*command, out, "--data", str(data), *memory], env)
            for side in ("base", "this"):
                _fastest(Path(folder), side)
            compare(Path(folder, "base.json"), Path(folder, "this.json"), ("base", "this"))
        finally:
            _git("worktree", "remove", str(tree))


def _fastest(folder: Path, side: str) -> None:
    """The measurements of a side over the rounds in one file: the fastest time of every class
    and its memory of the rounds that take it"""
    rounds = [
        json.loads(path.read_text(encoding="utf-8"))["classes"]
        for path in sorted(folder.glob(f"{side}-*.json"))
    ]
    classes = {
        name: {
            "time": min(found[name]["time"] for found in rounds),
            "memory": max(found[name]["memory"] for found in rounds if "memory" in found[name]),
        }
        for name in rounds[0]
    }
    (folder / f"{side}.json").write_text(json.dumps({"classes": classes}), encoding="utf-8")


def _git(*args: str) -> str:
    """Output of a git command; its failure ends the run with its message and code"""
    done = subprocess.run(
        ["git", "-C", str(ROOT), *args], check=False, stdout=subprocess.PIPE, text=True
    )
    if done.returncode:
        raise SystemExit(done.returncode)
    return done.stdout.strip()


def _take(command: list[str], environment: dict[str, str] | None) -> None:
    """A measurement in a process of its own; its failure ends the run with its code"""
    code = subprocess.run(command, env=environment, check=False).returncode
    if code:
        raise SystemExit(code)


def _default_data() -> Path:
    """BENCH_DATA, or core_snapshot/bench-documents next to the main clone of the repository"""
    if "BENCH_DATA" in os.environ:
        return Path(os.environ["BENCH_DATA"])
    common = Path(_git("rev-parse", "--path-format=absolute", "--git-common-dir"))
    return common.parent.parent / "core_snapshot" / "bench-documents"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0].strip())
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("run", "take"):
        command = commands.add_parser(name)
        if name == "take":
            command.add_argument("out", type=Path)
            command.add_argument("--no-memory", dest="memory", action="store_false")
        command.add_argument("--data", type=Path)
        if name == "run":
            command.add_argument("--base")
    command = commands.add_parser("compare")
    command.add_argument("old", type=Path)
    command.add_argument("new", type=Path)
    args = parser.parse_args()
    if args.command == "run":
        run(args.data or _default_data(), args.base)
    elif args.command == "take":
        take(args.out, args.data or _default_data(), args.memory)
    else:
        compare(args.old, args.new)


if __name__ == "__main__":
    main()
