from math import isnan, log2, log10
from typing import ClassVar, NamedTuple

import pytest
import spacy

from anyts.constants import LEXICAL_STATS_DESC, MESSAGES
from anyts.exceptions import ParameterError, SourceError, SourceTypeError
from anyts.extractors import WordsExtractor
from anyts.lexical_stats import LexicalStats, LexicalWord, calc_surprisal, is_number
from anyts.utils import is_doc, iter_doc_words


class Entry(NamedTuple):
    ipm: float
    range: int
    dispersion: float


class Dictionary:
    """A frequency dictionary of a few lemmas"""

    min_ipm = 0.5
    entries: ClassVar = {
        "the": Entry(50000.0, 40, 0.99),
        "cat": Entry(100.0, 38, 0.9),
        "sit": Entry(1000.0, 40, 0.95),
        "mat": Entry(10.0, 20, 0.7),
    }

    def lookup(self, lemma):
        return self.entries.get(lemma)

    def ipm(self, lemma):
        entry = self.lookup(lemma)
        return entry.ipm if entry else 0.0


FUNCTION_WORDS = frozenset({"the", "on", "a"})
TOP = {"the": 1, "on": 5, "a": 3, "sit": 900, "cat": 1500, "mat": 8000}
LEMMAS = {"sat": "sit", "cats": "cat"}


class English(LexicalStats):
    """Lemmas of a small table, function words of a list"""

    freq_dict_class = Dictionary

    def analyze(self, source):
        if is_doc(source):
            words = [text for _, _, text in iter_doc_words(source)]
        elif isinstance(source, str):
            words = WordsExtractor().extract(source)
        else:
            raise SourceTypeError("The data source is set incorrectly")
        return [
            LexicalWord(
                word, LEMMAS.get(word.lower(), word.lower()), word.lower() not in FUNCTION_WORDS
            )
            for word in words
            if not is_number(word)
        ]

    def rank(self, lemma):
        return TOP.get(lemma)


TEXT = "The cat sat on the mat in 2020, the cats sat"


@pytest.fixture(scope="module")
def stats():
    return English(TEXT)


def test_words_and_lemmas(stats):
    assert stats.words == ("The", "cat", "sat", "on", "the", "mat", "in", "the", "cats", "sat")
    assert stats.lemmas == ("the", "cat", "sit", "on", "the", "mat", "in", "the", "cat", "sit")
    assert stats.keys == stats.lemmas
    assert stats.n_words == 10 and stats.n_content_words == 6
    assert stats.lexical_density == 0.6
    assert stats.ranks == (1, 1500, 900, 5, 1, 8000, None, 1, 1500, 900)


def test_statistics_by_the_dictionary(stats):
    found = [50000.0] * 3 + [100.0] * 2 + [1000.0] * 2 + [10.0]
    content = [100.0, 1000.0, 10.0, 100.0, 1000.0]
    assert stats.n_found == 8 and stats.coverage == 0.8
    assert stats.mean_ipm == pytest.approx(sum(found) / 8)
    assert stats.mean_ipm_content == pytest.approx(sum(content) / 5)
    assert stats.mean_log_ipm == pytest.approx(sum(map(log10, found)) / 8)
    assert stats.mean_log_ipm_content == pytest.approx(sum(map(log10, content)) / 5)
    assert stats.mean_range == pytest.approx((40 * 3 + 38 * 2 + 40 * 2 + 20) / 8)
    assert stats.mean_dispersion == pytest.approx((0.99 * 3 + 0.9 * 2 + 0.95 * 2 + 0.7) / 8)
    ipms = [50000, 100, 1000, 0.5, 50000, 10, 0.5, 50000, 100, 1000]
    surprisal = sum(-log2(ipm / 1_000_000) for ipm in ipms) / 10
    assert stats.surprisal == pytest.approx(surprisal)
    assert stats.perplexity == pytest.approx(2**surprisal)


def test_bands(stats):
    assert (stats.p_top1000, stats.p_top2000, stats.p_top5000) == (0.6, 0.8, 0.8)
    assert stats.p_top10000 == 0.9
    assert stats.p_beyond_top10000 == pytest.approx(0.1)
    assert stats.band_coverage((1, 5), unique=True) == {1: 1 / 6, 5: 2 / 6}
    assert stats.band_coverage([1000], unique=True) == {1000: 0.5}
    assert list(stats.get_stats()) == list(LEXICAL_STATS_DESC)


@pytest.mark.parametrize(
    ("bands", "message"),
    [
        ("1000", "must be a list, not str"),
        (5, "must be a list, not int"),
        ([0], "from 1 to 10000, not 0"),
        ([10001], "not 10001"),
        ([1.5], "not 1.5"),
        ([True], "not True"),
    ],
)
def test_band_errors(stats, bands, message):
    with pytest.raises(ParameterError, match=message):
        stats.band_coverage(bands)


def test_hooks_of_the_keys_and_the_list():
    class Keyed(English):
        def dictionary_keys(self):
            return tuple(word.lower() for word in self.words)

        def top_size(self):
            return 20000

    keyed = Keyed(TEXT)
    assert keyed.keys[2] == "sat" and keyed.entries[2] is None
    assert keyed.n_found == 5
    assert keyed.band_coverage([20000]) == {20000: 0.9}
    with pytest.raises(ParameterError, match="from 1 to 20000"):
        keyed.band_coverage([20001])


def test_source_of_a_doc():
    doc = spacy.blank("en")("The cats sat")
    assert English(doc).lemmas == ("the", "cat", "sit")


def test_numbers():
    assert is_number("2020") and is_number("-5") and is_number("10%")
    assert not is_number("cat")
    roman = __import__("re").compile(r"[ivxlcdm]+")
    assert is_number("XIV", roman) and not is_number("2020", roman)


@pytest.mark.parametrize(
    ("kwargs", "error", "message"),
    [
        ({"source": 5}, SourceTypeError, "data source"),
        ({"source": "2020 ... 1999"}, SourceError, "no words"),
        ({"source": TEXT, "freq_dict": {}}, SourceTypeError, "must be a Dictionary"),
    ],
)
def test_errors(kwargs, error, message):
    with pytest.raises(error, match=message):
        English(**kwargs)


def test_without_a_class_of_the_dictionary():
    class Bare(English):
        freq_dict_class = None

    with pytest.raises(SourceTypeError, match=r"^Bare has no frequency dictionary"):
        Bare(TEXT)
    assert Bare(TEXT, freq_dict=Dictionary()).coverage == 0.8


def test_analyze_is_required():
    with pytest.raises(TypeError, match="abstract"):
        LexicalStats(TEXT)


def test_surprisal_function():
    assert calc_surprisal(["the", "unknown"], Dictionary()) == pytest.approx(
        (-log2(50000 / 1_000_000) - log2(0.5 / 1_000_000)) / 2
    )
    assert isnan(calc_surprisal([], Dictionary()))
    with pytest.raises(SourceTypeError, match="must have ipm and min_ipm, not dict"):
        calc_surprisal(["the"], {"the": 1})
    with pytest.raises(SourceTypeError):
        calc_surprisal("the", Dictionary())


def test_own_messages():
    class Own(English):
        messages: ClassVar = {**MESSAGES, "band_bound": "Own {size} {band}"}

    with pytest.raises(ParameterError, match=r"^Own 10000 0$"):
        Own(TEXT).band_coverage([0])


def test_without_a_list():
    class Unranked(English):
        rank = LexicalStats.rank

    unranked = Unranked(TEXT)
    assert unranked.ranks == (None,) * 10
    assert unranked.p_top1000 == 0.0 and unranked.p_beyond_top10000 == 1.0
