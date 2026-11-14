"""
Speed and memory of the classes of statistics against master

The classes read frozen documents: CoNLL-U files of texts annotated by the pipelines of the
language libraries, in BENCH_DATA (../core_snapshot/bench-documents by default). Every class
runs once over all of them to warm up, then REPEATS times; the fastest run is its time. Its
memory is the largest peak of the memory Python allocates for one document. The garbage
collector runs before every measurement and not during it, since the trees hold cycles.

Usage:
    make bench
    uv run python scripts/bench.py run [--data DIR]
    uv run python scripts/bench.py take OUT [--data DIR]
    uv run python scripts/bench.py compare OLD NEW

run takes the classes of a worktree of master and of this tree in the same environment and
prints the table of both.
"""

import argparse
import gc
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
DATA = Path(os.environ.get("BENCH_DATA", ROOT.parent / "core_snapshot" / "bench-documents"))
REPEATS = 5
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


def stats_classes() -> dict[str, Callable[[Any], Any]]:
    """The classes of the core with the hooks of a language they need, by name"""
    from anyts.basic_stats import BasicStats
    from anyts.cohesion_stats import CohesionStats
    from anyts.diversity_stats import DiversityStats
    from anyts.document import document_words, get_tree
    from anyts.lexical_stats import LexicalStats
    from anyts.morph_stats import MorphStats
    from anyts.phon_stats import PhonStats
    from anyts.readability_stats import ReadabilityStats
    from anyts.style_stats import StyleStats
    from anyts.syntax_stats import SyntaxStats

    class Basic(BasicStats):
        def count_syllables(self, word: str) -> int:
            return len(VOWEL_GROUP.findall(word.lower()))

    class Readability(ReadabilityStats):
        basic_stats_class = Basic

    class Phon(PhonStats):
        def syllabify(self, word: str) -> Sequence[str]:
            return SYLLABLE.findall(word) or [word]

    class Lexical(LexicalStats):
        freq_dict_class = Frequencies

    return {
        "get_tree": get_tree,
        "BasicStats": Basic,
        "ReadabilityStats": Readability,
        "StyleStats": StyleStats,
        "PhonStats": Phon,
        "DiversityStats": lambda document: DiversityStats(
            [word.lower() for word in document_words(document)]
        ),
        "LexicalStats": Lexical,
        "MorphStats": MorphStats,
        "SyntaxStats": SyntaxStats,
        "CohesionStats": CohesionStats,
    }


def documents(data: Path) -> list[Any]:
    from anyseg import read_conllu

    paths = sorted(data.rglob("*.conllu"))
    if not paths:
        raise SystemExit(f"No CoNLL-U files in {data}: set BENCH_DATA or --data")
    return [read_conllu(path.read_text(encoding="utf-8"))[0] for path in paths]


def measure(make: Callable[[Any], Any], sources: Sequence[Any]) -> dict[str, float]:
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
        for source in sources:
            gc.collect()
            gc.disable()
            tracemalloc.start()
            run(source)
            peaks.append(tracemalloc.get_traced_memory()[1])
            tracemalloc.stop()
            gc.enable()
    finally:
        gc.enable()
    return {"time": min(times), "memory": max(peaks)}


def take(out: Path, data: Path) -> None:
    import anyts

    sources = documents(data)
    results = {name: measure(make, sources) for name, make in stats_classes().items()}
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
    for name, first in before.items():
        second = after.get(name)
        if second is None:
            continue
        print(
            f"{name:18}{first['time']:12.3f}{second['time']:12.3f}"
            f"{_change(first['time'], second['time']):>9}"
            f"{first['memory'] / 1e6:13.1f}{second['memory'] / 1e6:13.1f}"
            f"{_change(first['memory'], second['memory']):>9}"
        )


def _change(first: float, second: float) -> str:
    return f"{(second - first) / first * 100:+.1f} %" if first else ""


def run(data: Path) -> None:
    script = str(Path(__file__).resolve())
    with tempfile.TemporaryDirectory() as folder:
        master = Path(folder) / "master"
        git = ["git", "-C", str(ROOT), "worktree"]
        subprocess.run([*git, "add", "--quiet", "--detach", str(master), "master"], check=True)
        try:
            # The anyts of the worktree comes first on the path, in the same environment
            environment = {**os.environ, "PYTHONPATH": str(master), "PYTHONDONTWRITEBYTECODE": "1"}
            command = [sys.executable, script, "take"]
            subprocess.run(
                [*command, f"{folder}/master.json", "--data", str(data)],
                env=environment,
                check=True,
            )
            subprocess.run([*command, f"{folder}/this.json", "--data", str(data)], check=True)
            compare(Path(folder, "master.json"), Path(folder, "this.json"), ("master", "this"))
        finally:
            subprocess.run([*git, "remove", str(master)], check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0].strip())
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("run", "take"):
        command = commands.add_parser(name)
        if name == "take":
            command.add_argument("out", type=Path)
        command.add_argument("--data", type=Path, default=DATA)
    command = commands.add_parser("compare")
    command.add_argument("old", type=Path)
    command.add_argument("new", type=Path)
    args = parser.parse_args()
    if args.command == "run":
        run(args.data)
    elif args.command == "take":
        take(args.out, args.data)
    else:
        compare(args.old, args.new)


if __name__ == "__main__":
    main()
