from __future__ import annotations

from abc import ABCMeta, abstractmethod
from collections import Counter
from collections.abc import Collection, Mapping, Sequence
from math import comb, fsum, nan
from typing import TYPE_CHECKING, Any, ClassVar

import numpy as np

from .constants import MESSAGES, PHON_STATS_DESC, PHON_WINDOW_LEN
from .exceptions import ParameterError, SourceError, SourceTypeError
from .extractors import WordsExtractor
from .stats import Stats
from .utils import (
    check_integer,
    check_sequence,
    check_words,
    is_doc,
    iter_doc_words,
    safe_divide,
    shannon_entropy,
)

if TYPE_CHECKING:
    from spacy.tokens import Doc


def check_params(window_len: int, *, messages: Mapping[str, str] = MESSAGES) -> None:
    """
    Checking the parameters of the phonetic statistics

    Arguments:
        window_len (int): Window in words of the alliteration and the assonance
        messages (dict[str, str]): Messages of the errors by key (MESSAGES)

    Raises:
        ParameterError: If the window is not an integer or is below 2
    """
    check_integer(window_len, "size of a window")
    if window_len < 2:
        raise ParameterError(messages["phon_window_len"])


class PhonStats(Stats, metaclass=ABCMeta):
    """
    Base of the phonetic statistics of a text

    Description:
        The sounds of a text: the shares of the classes of sounds, the
        consonant clusters, the hiatuses, the CV patterns, the hardness, the
        alliteration and the assonance (calc_repetition_index) and the
        syllables; a syllable without a sound of the classes (a number) is no
        syllable. A language library subclasses the class, sets its classes of
        sounds and implements syllabify. The sounds are the letters of a word by
        default, or those of its transcription (transcribe).
        get_stats, to_dataframe, print_stats and describe come from Stats

    Arguments:
        source (str|Doc): Data source (a string or a Doc object)
        words_extractor (WordsExtractor): Word extraction tool; used for a Doc too, on
            its text
        window_len (int): Window in words of the alliteration and the assonance

    Attributes:
        words (tuple[str]): Words in lower case
        window_len (int): Window of the alliteration and the assonance
        syllables (tuple[tuple[str, ...]]): Syllables of every word (syllabify)
        sounds (tuple[Sequence[str]]): Sounds of every word (transcribe)
        n_vowels, n_sonorants, n_voiced, n_voiceless, n_consonants (int): Number of the
            vowels, the sonorant, voiced and voiceless consonants and all the consonants
        c_clusters (dict[int, int]): Number of the consonant clusters by length
        c_syllable_patterns (dict[str, int]): Number of the syllables by CV pattern
        p_vowels, p_sonorants, p_voiced, p_voiceless (float): Shares of the sounds
        consonant_vowel_ratio (float): Ratio of the consonants to the vowels
        p_heavy_clusters (float): Share of the clusters of three consonants or more
        p_hiatus (float): Hiatuses per word
        cv_entropy (float): Shannon entropy of the CV patterns of the words, in bits
        hardness (float): Voiceless consonants to the vowels and the sonorants
        alliteration (float): Alliteration index
        assonance (float): Assonance index
        p_open_syllables (float): Share of the open syllables
        mean_syllable_len (float): Mean length of a syllable in sounds

    Methods:
        doc_words: Words of a Doc
        transcribe: Sounds of a word
        syllabify: Syllables of a word
        syllable_sounds: Sounds of every syllable of a word
        word_hiatus: Number of the hiatuses of a word

    Class attributes:
        words_extractor_class (type[WordsExtractor]): Word extractor of a string
        join_hyphens (bool): Join the parts of the hyphenated words of a Doc
        vowels, sonorants, voiced, voiceless (frozenset[str]): Classes of the sounds: the
            vowels, the sonorants and the voiced and voiceless obstruents, disjoint
        skipped (frozenset[str]): Sounds that keep a consonant cluster whole, in no class
        glides (frozenset[str]): Vowels that make no hiatus after a vowel
        stats_desc (dict[str, str]): Statistics of get_stats and their descriptions for
            print_stats

    Raises:
        SourceTypeError: If the source is neither a string nor a Doc object or the
            extractor is of another type
        SourceError: If the source has no words
        ParameterError: If the window is not an integer or is below 2; when a class is
            defined, if its classes of sounds or skipped overlap
    """

    words_extractor_class: ClassVar[type[WordsExtractor]] = WordsExtractor
    join_hyphens: ClassVar[bool] = False
    vowels: ClassVar[frozenset[str]] = frozenset()
    sonorants: ClassVar[frozenset[str]] = frozenset()
    voiced: ClassVar[frozenset[str]] = frozenset()
    voiceless: ClassVar[frozenset[str]] = frozenset()
    skipped: ClassVar[frozenset[str]] = frozenset()
    glides: ClassVar[frozenset[str]] = frozenset()
    stats_desc: ClassVar[Mapping[str, str]] = PHON_STATS_DESC

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        classes = ("vowels", "sonorants", "voiced", "voiceless", "skipped")
        for index, first in enumerate(classes):
            for second in classes[index + 1 :]:
                if shared := getattr(cls, first) & getattr(cls, second):
                    raise ParameterError(
                        cls.messages["phon_classes"].format(
                            first=first, second=second, cls=cls.__name__, sounds=sorted(shared)
                        )
                    )

    def __init__(
        self,
        source: str | Doc,
        words_extractor: WordsExtractor | None = None,
        window_len: int = PHON_WINDOW_LEN,
    ):
        messages = self.messages
        if words_extractor is not None and not isinstance(words_extractor, WordsExtractor):
            raise SourceTypeError(messages["words_extractor_type"])
        check_params(window_len, messages=messages)
        if is_doc(source) and words_extractor is not None:
            source = source.text
        if is_doc(source):
            words = self.doc_words(source)
        elif isinstance(source, str):
            extractor = words_extractor or self.words_extractor_class(lowercase=True)
            words = tuple(word.lower() for word in extractor.extract(source))
        else:
            raise SourceTypeError(messages["source_type"])
        if not words:
            raise SourceError(messages["no_words"])
        self.words = words
        self.window_len = window_len
        counts = Counter(words)
        word_syllables = {word: tuple(self.syllabify(word)) for word in counts}
        word_sounds = {word: self.transcribe(word) for word in counts}
        self.syllables = tuple(word_syllables[word] for word in words)
        self.sounds = tuple(word_sounds[word] for word in words)
        consonants = self.sonorants | self.voiced | self.voiceless
        sounds: Counter[str] = Counter()
        all_syllables: Counter[tuple[str, ...]] = Counter()
        clusters: Counter[int] = Counter()
        patterns: Counter[str] = Counter()
        for word, count in counts.items():
            for sound, number in Counter(word_sounds[word]).items():
                sounds[sound] += number * count
            for syllable in self.syllable_sounds(word):
                all_syllables[tuple(syllable)] += count
            for size in consonant_clusters(word_sounds[word], consonants, self.skipped):
                clusters[size] += count
            if pattern := cv_pattern(word_sounds[word], self.vowels, consonants):
                patterns[pattern] += count
        syllable_patterns = {
            syllable: cv_pattern(syllable, self.vowels, consonants) for syllable in all_syllables
        }
        syllables = {
            syllable: count
            for syllable, count in all_syllables.items()
            if syllable_patterns[syllable]
        }
        self.n_vowels = sum(sounds[sound] for sound in self.vowels)
        self.n_sonorants = sum(sounds[sound] for sound in self.sonorants)
        self.n_voiced = sum(sounds[sound] for sound in self.voiced)
        self.n_voiceless = sum(sounds[sound] for sound in self.voiceless)
        self.n_consonants = self.n_sonorants + self.n_voiced + self.n_voiceless
        n_sounds = self.n_vowels + self.n_consonants
        self.c_clusters = dict(sorted(clusters.items()))
        pattern_counts: Counter[str] = Counter()
        for syllable, count in syllables.items():
            pattern_counts[syllable_patterns[syllable]] += count
        self.c_syllable_patterns = dict(sorted(pattern_counts.items()))
        self.p_vowels = safe_divide(self.n_vowels, n_sounds, nan)
        self.p_sonorants = safe_divide(self.n_sonorants, n_sounds, nan)
        self.p_voiced = safe_divide(self.n_voiced, n_sounds, nan)
        self.p_voiceless = safe_divide(self.n_voiceless, n_sounds, nan)
        self.consonant_vowel_ratio = safe_divide(self.n_consonants, self.n_vowels, nan)
        n_clusters = sum(self.c_clusters.values())
        self.p_heavy_clusters = safe_divide(
            sum(count for size, count in self.c_clusters.items() if size >= 3), n_clusters, nan
        )
        n_hiatus = sum(self.word_hiatus(word) * count for word, count in counts.items())
        self.p_hiatus = n_hiatus / len(words) if n_sounds else nan
        self.cv_entropy = shannon_entropy(patterns)
        self.hardness = safe_divide(self.n_voiceless, self.n_vowels + self.n_sonorants, nan)
        self.alliteration = calc_repetition_index(self.sounds, window_len, consonants)
        self.assonance = calc_repetition_index(self.sounds, window_len, self.vowels)
        n_syllables = sum(syllables.values())
        open_syllables = sum(
            count
            for syllable, count in syllables.items()
            if syllable_patterns[syllable].endswith("V")
        )
        self.p_open_syllables = safe_divide(open_syllables, n_syllables, nan)
        self.mean_syllable_len = safe_divide(
            sum(len(syllable) * count for syllable, count in syllables.items()),
            n_syllables,
            nan,
        )

    def doc_words(self, doc: Doc) -> tuple[str, ...]:
        """
        Getting the words of a Doc

        Description:
            The words of iter_doc_words in lower case, with the hyphenated words
            joined by join_hyphens

        Arguments:
            doc (Doc): Doc object

        Returns:
            tuple[str]: Words
        """
        return tuple(text.lower() for _, _, text in iter_doc_words(doc, self.join_hyphens))

    def transcribe(self, word: str) -> Sequence[str]:
        """
        Getting the sounds of a word

        Description:
            The letters of the word by default; a library whose letters stand
            for sounds by rules gives the transcription

        Arguments:
            word (str): Word in lower case

        Returns:
            Sequence[str]: Sounds
        """
        return word

    @abstractmethod
    def syllabify(self, word: str) -> Sequence[str]:
        """
        Getting the syllables of a word

        Description:
            Implemented by a language library

        Arguments:
            word (str): Word in lower case

        Returns:
            Sequence[str]: Syllables as the word writes them
        """
        raise NotImplementedError

    def syllable_sounds(self, word: str) -> Sequence[Sequence[str]]:
        """
        Getting the sounds of every syllable of a word

        Description:
            The transcription of every syllable of syllabify by default; a
            library whose sounds depend on the place of a syllable gives them
            otherwise

        Arguments:
            word (str): Word in lower case

        Returns:
            Sequence[Sequence[str]]: Sounds of every syllable
        """
        return [self.transcribe(syllable) for syllable in self.syllabify(word)]

    def word_hiatus(self, word: str) -> int:
        """
        Counting the hiatuses of a word

        Description:
            The runs of vowels of its sounds (count_hiatus with glides) by
            default; a library may count them by the syllables

        Arguments:
            word (str): Word in lower case

        Returns:
            int: Number of hiatuses
        """
        return count_hiatus(self.transcribe(word), self.vowels, self.glides)


def cv_pattern(sounds: Sequence[str], vowels: Collection[str], consonants: Collection[str]) -> str:
    """
    Getting the CV pattern of a word or a syllable

    Description:
        Every vowel is V and every consonant C; the other sounds (signs,
        digits, letters of another script) are left out

    Arguments:
        sounds (list[str]): Sounds or letters of the word
        vowels (collection[str]): Vowels
        consonants (collection[str]): Consonants

    Returns:
        str: CV pattern

    Example:
        >>> from anyts.phon_stats import cv_pattern
        >>> cv_pattern("strong", set("aeiou"), set("bcdfghjklmnpqrstvwxyz"))
        'CCCVCC'
    """
    return "".join(
        "V" if sound in vowels else "C"
        for sound in sounds
        if sound in vowels or sound in consonants
    )


def consonant_clusters(
    sounds: Sequence[str], consonants: Collection[str], skipped: Collection[str] = ()
) -> tuple[int, ...]:
    """
    Getting the lengths of the consonant clusters of a word

    Description:
        A cluster is a run of consonants, a single one included; a sound of
        skipped (a sign that marks the previous consonant) neither counts nor
        breaks the run, any other sound breaks it

    Arguments:
        sounds (list[str]): Sounds or letters of the word
        consonants (collection[str]): Consonants
        skipped (collection[str]): Sounds that keep a cluster whole

    Returns:
        tuple[int, ...]: Lengths of the clusters in the order of the word

    Example:
        >>> from anyts.phon_stats import consonant_clusters
        >>> consonant_clusters("strength", set("bcdfghjklmnpqrstvwxyz"))
        (3, 4)
    """
    sizes = []
    size = 0
    for sound in sounds:
        if sound in consonants:
            size += 1
        elif sound in skipped:
            continue
        else:
            if size:
                sizes.append(size)
            size = 0
    if size:
        sizes.append(size)
    return tuple(sizes)


def count_hiatus(
    sounds: Sequence[str], vowels: Collection[str], glides: Collection[str] = ()
) -> int:
    """
    Counting the hiatuses of a word by its vowels in a row

    Description:
        A run of two vowels or more is one hiatus; a vowel of glides after a
        vowel makes none (a letter that writes a glide and a vowel)

    Arguments:
        sounds (list[str]): Sounds or letters of the word
        vowels (collection[str]): Vowels
        glides (collection[str]): Vowels that make no hiatus after a vowel

    Returns:
        int: Number of hiatuses

    Example:
        >>> from anyts.phon_stats import count_hiatus
        >>> count_hiatus("poem", set("aeiou")), count_hiatus("cooperation", set("aeiou"))
        (1, 2)
    """
    hiatus = 0
    previous_vowel = False
    run = False
    for sound in sounds:
        is_vowel = sound in vowels
        if is_vowel and previous_vowel and sound not in glides:
            if not run:
                hiatus += 1
            run = True
        else:
            run = False
        previous_vowel = is_vowel
    return hiatus


def calc_repetition_index(
    words: Sequence[Collection[str]], window_len: int, features: Collection[str] | None = None
) -> float:
    """
    Computing the repetition index

    Description:
        The windows of window_len neighbouring words where a feature occurs in
        two words or more, summed over the features, over the number expected
        in random order: about 1 for random repetitions, well above 1 when they
        gather. A word counts each of its features (the characters of a string
        or the items of a collection) once

    Arguments:
        words (list[str]|list[list[str]]): Features of every word, such as its
            letters or the sounds of its transcription
        window_len (int): Window in words
        features (Collection[str]|None): Features to count, all of them by default

    Returns:
        float: Value of the index, nan for a text shorter than the window or
            without a feature shared by two words

    Raises:
        SourceTypeError: If the words are not a list (check_sequence), a word is
            neither a string nor a collection of strings, or the features are not
            a collection of strings
        ParameterError: If the window is not an integer or is below 2

    Example:
        >>> from anyts.phon_stats import calc_repetition_index
        >>> words = ["sea", "sun", "gas", "fog", "box", "hat"]
        >>> calc_repetition_index(words, 2, {"s"})
        2.0
    """
    check_sequence(words)
    keys = list(map(_word_key, words))
    unique = list(dict.fromkeys(keys))
    for word in unique:
        if not isinstance(word, str):
            check_words(word, "features of a word", ordered=False)
    if features is not None:
        check_words(features, "features", ordered=False)
        features = frozenset(features)
    check_params(window_len)
    n_words = len(words)
    if n_words < window_len:
        return nan
    columns: dict[str, int] = {}
    cells: tuple[list[int], list[int]] = ([], [])
    for row, word in enumerate(unique):
        for feature in word:
            if features is None or feature in features:
                cells[0].append(row)
                cells[1].append(columns.setdefault(feature, len(columns)))
    presence = np.zeros((len(unique), len(columns)), dtype=np.int8)
    presence[cells] = 1
    indices = dict(zip(unique, range(len(unique)), strict=True))
    rows = np.fromiter(map(indices.__getitem__, keys), dtype=np.int64, count=n_words)
    observed, counts = _count_windows(presence, rows, window_len)
    total = comb(n_words, window_len)
    expected = (n_words - window_len + 1) * fsum(
        _repetition_probability(count, n_words, window_len, total) for count in counts
    )
    return safe_divide(observed, expected, nan)


def _word_key(word: Collection[str]) -> Collection[str]:
    """A word itself, or the tuple of its features when it cannot be a key of a dict"""
    try:
        hash(word)
    except TypeError:
        check_words(word, "features of a word", ordered=False)
        return tuple(word)
    return word


def _count_windows(
    presence: np.ndarray, rows: np.ndarray, window_len: int, block_size: int = 64
) -> tuple[int, list[int]]:
    """
    Number of the windows with a feature in two words or more, summed over the
    features, and the number of the words with every feature

    Description:
        Counted in blocks of columns, so that a large alphabet takes little memory
    """
    observed = 0
    counts: list[int] = []
    for start in range(0, presence.shape[1], block_size):
        block = presence[rows, start : start + block_size]
        cumulative = np.zeros((len(rows) + 1, block.shape[1]), dtype=np.int32)
        np.cumsum(block, axis=0, out=cumulative[1:])
        observed += int((cumulative[window_len:] - cumulative[:-window_len] >= 2).sum())
        counts.extend(cumulative[-1].tolist())
    return observed, counts


def _repetition_probability(count: int, n_words: int, window_len: int, total: int) -> float:
    """
    Probability that a window of the words in random order holds two or more
    of the count words with a feature (the hypergeometric distribution); total
    is C(n_words, window_len)
    """
    rest = n_words - count
    return (total - comb(rest, window_len) - count * comb(rest, window_len - 1)) / total
