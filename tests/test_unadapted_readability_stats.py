import re
from math import isnan, log

import pytest
import spacy

from anyts.basic_stats import BasicStats
from anyts.components import UnadaptedReadabilityStatsComponent
from anyts.constants import MESSAGES, UNADAPTED_READABILITY_STATS_DESC
from anyts.exceptions import ParameterError, SourceError, SourceTypeError
from anyts.extractors import SentsExtractor
from anyts.unadapted_readability_stats import (
    UnadaptedReadabilityStats,
    calc_dickes_steiwer,
    calc_eflaw,
    calc_elf,
    calc_forcast,
    calc_fucks,
    calc_gulpease,
    calc_linsear_write,
    calc_powers_sumner_kearl,
    calc_strain_index,
    calc_wheeler_smith,
    calc_wiener_sachtextformel,
)

TEXT = "The cat sat on the mat in 2026. A beautiful day came, and the extraordinary dog barked!"


class Stats(BasicStats):
    def count_syllables(self, word):
        return len(re.findall(r"[aeiouy]+", word, re.IGNORECASE))


class Unadapted(UnadaptedReadabilityStats):
    basic_stats_class = Stats


@pytest.fixture(scope="module")
def stats():
    return Unadapted(TEXT)


def test_formulas_over_the_basic_statistics(stats):
    bs = stats.bs
    words, sents, syllables = bs.n_words, bs.n_sents, bs.n_syllables
    letters = sum(n * count for n, count in bs.c_letters.items())
    by_syllables = lambda least: sum(c for n, c in bs.c_syllables.items() if n >= least)  # noqa: E731
    hard, two = by_syllables(3), by_syllables(2)
    easy = by_syllables(1) - hard
    mini = sum(c for n, c in bs.c_letters.items() if 1 <= n <= 3)
    long = sum(c for n, c in bs.c_letters.items() if n >= 7)
    mono = bs.n_monosyllable_words
    assert stats.forcast == 20 - mono * 150 / words / 10
    score = (easy + 3 * hard) / sents
    assert stats.linsear_write == (score / 2 if score > 20 else (score - 2) / 2)
    assert stats.powers_sumner_kearl == pytest.approx(
        0.0778 * words / sents + 4.55 * syllables / words - 2.2029
    )
    assert stats.eflaw == (words + mini) / sents
    ms, iw, es, sl = 100 * hard / words, 100 * long / words, 100 * mono / words, words / sents
    assert stats.wiener_sachtextformel_1 == pytest.approx(
        0.1935 * ms + 0.1672 * sl + 0.1297 * iw - 0.0327 * es - 0.875
    )
    assert stats.wiener_sachtextformel_2 == pytest.approx(
        0.2007 * ms + 0.1682 * sl + 0.1373 * iw - 2.779
    )
    assert stats.wiener_sachtextformel_3 == pytest.approx(0.2963 * ms + 0.1905 * sl - 1.1144)
    assert stats.wiener_sachtextformel_4 == pytest.approx(0.2744 * ms + 0.2656 * sl - 1.693)
    assert stats.dickes_steiwer == pytest.approx(
        235.95993
        - 73.021 * log(letters / words + 1)
        - 12.56438 * log(words / sents + 1)
        - 50.03293 * bs.n_unique_words / words
    )
    assert stats.gulpease == pytest.approx(89 + (300 * sents - 10 * letters) / words)
    assert stats.fucks == syllables / sents
    assert stats.strain_index == pytest.approx(syllables / sents * 3 / 10)
    assert stats.elf == (syllables - words) / sents
    assert stats.wheeler_smith == pytest.approx(words / sents * two / words * 10)
    # 2026 has no letters and is no mini word
    assert 0 in bs.c_letters
    assert list(stats.get_stats()) == list(UNADAPTED_READABILITY_STATS_DESC)


def test_functions_without_words_or_sentences():
    for value in (
        calc_forcast(0, 0),
        calc_linsear_write(0, 0, 0),
        calc_powers_sumner_kearl(1, 0, 1),
        calc_powers_sumner_kearl(1, 1, 0),
        calc_eflaw(0, 1, 0),
        calc_wiener_sachtextformel(0, 0, 0, 0, 1),
        calc_wiener_sachtextformel(0, 0, 0, 1, 0),
        calc_dickes_steiwer(1, 0, 1, 1),
        calc_dickes_steiwer(1, 1, 0, 1),
        calc_gulpease(1, 0, 1),
        calc_fucks(1, 0),
        calc_strain_index(1, 0),
        calc_elf(1, 1, 0),
        calc_wheeler_smith(1, 0),
    ):
        assert isnan(value)


def test_linsear_write_above_and_below_20():
    # (80 + 3 * 20) / 5 = 28 is halved, (8 + 3 * 2) / 2 = 7 loses 2 first
    assert calc_linsear_write(80, 20, 5) == 14.0
    assert calc_linsear_write(8, 2, 2) == 2.5


@pytest.mark.parametrize("variant", [0, 5, 1.5, "1"])
def test_wiener_variants(variant):
    with pytest.raises(ParameterError):
        calc_wiener_sachtextformel(20, 30, 50, 100, 8, variant)


def test_sources():
    stats = Unadapted(TEXT)
    # The basic statistics of a text may be reused
    assert Unadapted(stats.bs).get_stats() == stats.get_stats()
    with pytest.raises(
        SourceTypeError,
        match=f"^{MESSAGES['no_basic_stats_class'].format(cls='UnadaptedReadabilityStats')}",
    ):
        UnadaptedReadabilityStats(TEXT)
    assert UnadaptedReadabilityStats(stats.bs).fucks == stats.fucks

    class Other(BasicStats):
        def count_syllables(self, word):
            return 1

    with pytest.raises(
        SourceTypeError, match=r"^The basic statistics must be a Stats object, not Other$"
    ):
        Unadapted(Other(TEXT))
    with pytest.raises(SourceTypeError, match=r"^The sentence extractor must be"):
        Unadapted(TEXT, sents_extractor=5)
    with pytest.raises(SourceError, match=r"^The data source has no sentences$"):
        Unadapted(TEXT, sents_extractor=SentsExtractor(min_len=1000))
    with pytest.raises(SourceError, match=r"^The data source has no words$"):
        Unadapted("?!")


def test_component():
    nlp = spacy.blank("en")
    assert UnadaptedReadabilityStatsComponent.stats_class is UnadaptedReadabilityStats

    class Own(UnadaptedReadabilityStatsComponent):
        stats_class = Unadapted

    doc = nlp(TEXT)
    Own(nlp, "anyts_test_unadapted")(doc)
    assert doc._.anyts_test_unadapted.fucks == Unadapted(TEXT).fucks
