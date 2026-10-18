from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Collection, Mapping, Sequence
from math import nan, sqrt
from typing import TYPE_CHECKING, Any, ClassVar

from .constants import MESSAGES, NAUSEA_TOP_N, STYLE_STATS_DESC
from .exceptions import ParameterError, SourceError, SourceTypeError
from .extractors import WordsExtractor
from .stats import Stats
from .utils import (
    check_callable,
    check_integer,
    check_words,
    find_phrases,
    in_order,
    is_doc,
    iter_doc_words,
    safe_divide,
)

if TYPE_CHECKING:
    from spacy.tokens import Doc

Expander = Callable[[Sequence[str], Collection[str]], Mapping[str, str]]


def check_params(top_n: int, *, messages: Mapping[str, str] = MESSAGES) -> None:
    """
    Checking the parameters of the style metrics

    Arguments:
        top_n (int): Number of the most frequent words
        messages (dict[str, str]): Messages of the errors by key (MESSAGES)

    Raises:
        ParameterError: If the number of the most frequent words is not an integer or is
            below one
    """
    check_integer(top_n, "number of the most frequent words")
    if top_n < 1:
        raise ParameterError(messages["top_n"])


class StyleStats(Stats):
    """
    Base of the style metrics of a text

    Description:
        The SEO metrics of Advego and Text.ru and the markers of the officialese
        style. The services publish no formulas, so the common definitions are
        taken (see the functions). A language library subclasses the class and
        sets its hooks: the lists of phrases, the stopwords, the spelling of
        phrases, the nouns and the norms of the services (level_scales)
        A string gives the words of the word extractor, in lower case by
        default; a Doc gives its tokens (doc_words), or the words of an
        extractor given on its text. The markers are counted on the word forms
        in lower case (forms), whatever the extractor.
        get_stats, to_dataframe, print_stats and describe come from Stats

    Arguments:
        source (str|Doc): Data source (a string or a Doc object)
        words_extractor (WordsExtractor): Word extraction tool
        stopwords (list[str]): Words of water; without them is_water_word decides
        top_n (int): Number of the most frequent words of the academic nausea and the
            naturalness by Zipf's law
        cliches (list[str]): Cliches; cliches_list of the class by default
        nausea_stopwords (list[str]): Stopwords of the academic nausea; without them
            is_stopword decides

    Attributes:
        words (tuple[str]): Words of the SEO metrics
        forms (tuple[str]): Word forms in lower case, of the markers
        stopwords (tuple[str]|None): Words of water
        nausea_stopwords (tuple[str]|None): Stopwords of the academic nausea
        top_n (int): Number of the most frequent words
        cliches_list (tuple[str]): Cliches
        classic_nausea (float): Classic nausea
        academic_nausea (float): Academic nausea in percent
        water (float): Water content in percent
        spam (float): Spam score in percent
        zipf_naturalness (float): Naturalness by Zipf's law in percent
        verbal_nouns (float): Share of the verbal nouns among the nouns in percent
        compound_prepositions (float): Compound prepositions per 100 words
        parentheticals (float): Parenthetical expressions per 100 words
        cliches (float): Cliches per 100 words

    Methods:
        normalize: Normalized form of a word
        doc_words: Words of a Doc
        is_stopword: Whether a word is a stopword of the academic nausea
        is_water_word: Whether a word is water
        is_parenthetical: Whether a word is a parenthetical expression by itself
        expand_phrases: Variants of phrases in the forms of a text
        nouns: Nouns of the text with their lemmas
        is_verbal_noun: Whether the lemma of a noun is a verbal noun
        keyword_density: Density of keywords and phrases
        nausea_words: Most frequent significant words of the academic nausea
        markers: Markers of the officialese found in the text

    Class attributes:
        words_extractor_class (type[WordsExtractor]): Word extractor of a string and of
            the forms
        join_hyphens (bool): Join the parts of the hyphenated words of a Doc
        compound_prepositions_list (tuple[str]): Compound prepositions
        parentheticals_list (tuple[str]): Parenthetical expressions
        cliches_list (tuple[str]): Cliches
        stats_desc (dict[str, str]): Metrics of get_stats and their descriptions for
            print_stats

    Raises:
        SourceTypeError: If the source is neither a string nor a Doc object, the
            extractor is of another type or a list is not a list of strings; when a
            class is defined, if a list of its phrases is not a list of strings
        SourceError: If the source has no words
        ParameterError: If top_n is not an integer or is below one
    """

    words_extractor_class: ClassVar[type[WordsExtractor]] = WordsExtractor
    join_hyphens: ClassVar[bool] = False
    compound_prepositions_list: ClassVar[tuple[str, ...]] = ()
    parentheticals_list: ClassVar[tuple[str, ...]] = ()
    cliches_list: tuple[str, ...] = ()
    stats_desc: ClassVar[Mapping[str, str]] = STYLE_STATS_DESC
    stats_headers: ClassVar[tuple[str, str]] = ("Metric", "Value")

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        for name in ("compound_prepositions_list", "parentheticals_list", "cliches_list"):
            check_words(getattr(cls, name), name, ordered=False)

    def __init__(
        self,
        source: str | Doc,
        words_extractor: WordsExtractor | None = None,
        stopwords: Collection[str] | None = None,
        top_n: int = NAUSEA_TOP_N,
        cliches: Collection[str] | None = None,
        nausea_stopwords: Collection[str] | None = None,
    ):
        messages = self.messages
        if words_extractor is not None and not isinstance(words_extractor, WordsExtractor):
            raise SourceTypeError(messages["words_extractor_type"])
        check_params(top_n, messages=messages)
        for words, what in (
            (stopwords, "stopwords"),
            (nausea_stopwords, "nausea stopwords"),
            (cliches, "cliches"),
        ):
            if words is not None:
                check_words(words, what, ordered=False)
        if is_doc(source) and words_extractor is not None:
            source = source.text
        if is_doc(source):
            self.words = self.doc_words(source)
            self.forms = self.words
        elif isinstance(source, str):
            self.forms = self.words_extractor_class(lowercase=True).extract(source)
            self.words = words_extractor.extract(source) if words_extractor else self.forms
        else:
            raise SourceTypeError(messages["source_type"])
        if not self.words:
            raise SourceError(messages["no_words"])
        self.stopwords = in_order(stopwords) if stopwords is not None else None
        self.nausea_stopwords = (
            in_order(nausea_stopwords) if nausea_stopwords is not None else None
        )
        self.top_n = top_n
        if cliches is not None:
            self.cliches_list = in_order(cliches)

    def normalize(self, word: str) -> str:
        """
        Getting the normalized form of a word or a phrase

        Description:
            The lower case by default; a library overrides it for letters
            written in two ways. The stopwords and the phrases are compared by it

        Arguments:
            word (str): Word or phrase

        Returns:
            str: Normalized form
        """
        return word.lower()

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

    def is_stopword(self, word: str) -> bool:
        """
        Checking whether a word is a stopword of the academic nausea

        Description:
            No word by default; a library gives the function words of its
            language. The list nausea_stopwords, when given, replaces it

        Arguments:
            word (str): Word

        Returns:
            bool: Result of the check
        """
        return False

    def is_water_word(self, word: str) -> bool:
        """
        Checking whether a word is water

        Description:
            is_stopword by default; the list stopwords, when given, replaces it

        Arguments:
            word (str): Word

        Returns:
            bool: Result of the check
        """
        return self.is_stopword(word)

    def is_parenthetical(self, word: str) -> bool:
        """
        Checking whether a word is a parenthetical expression by itself

        Description:
            No word by default; an accepted word counts as a parenthetical
            expression outside the phrases of parentheticals_list

        Arguments:
            word (str): Word

        Returns:
            bool: Result of the check
        """
        return False

    def expand_phrases(self, text: Sequence[str], phrases: Collection[str]) -> dict[str, str]:
        """
        Spelling out phrases in the forms of a text

        Description:
            Every phrase as it is by default; a library adds the forms of a verb
            or the contractions, each with its phrase

        Arguments:
            text (list[str]): List of words
            phrases (list[str]|set[str]): Phrases, words separated by spaces

        Returns:
            dict[str, str]: Variants of the phrases with the phrase of each
        """
        return {phrase: phrase for phrase in in_order(phrases)}

    def nouns(self) -> list[tuple[str, str]]:
        """
        Getting the nouns of the text with their lemmas

        Description:
            None by default, so the share of the verbal nouns is nan; a library
            gives them by its parser or its morphology

        Returns:
            list[tuple[str, str]]: Word forms of the nouns in lower case with their lemmas
        """
        return []

    def is_verbal_noun(self, lemma: str) -> bool:
        """
        Checking whether the lemma of a noun is a verbal noun

        Arguments:
            lemma (str): Lemma of a noun

        Returns:
            bool: Result of the check, False by default
        """
        return False

    @property
    def classic_nausea(self) -> float:
        return calc_classic_nausea(self.words)

    @property
    def academic_nausea(self) -> float:
        return calc_academic_nausea(
            self.words,
            self.top_n,
            self.nausea_stopwords,
            is_stopword=self.is_stopword,
            normalize=self.normalize,
            messages=self.messages,
        )

    @property
    def water(self) -> float:
        return calc_water(
            self.words, self.stopwords, is_water_word=self.is_water_word, normalize=self.normalize
        )

    @property
    def spam(self) -> float:
        return calc_spam(self.words)

    @property
    def zipf_naturalness(self) -> float:
        return calc_zipf_naturalness(self.words, self.top_n, messages=self.messages)

    @property
    def verbal_nouns(self) -> float:
        nouns = self.nouns()
        verbal = sum(1 for _, lemma in nouns if self.is_verbal_noun(lemma))
        return safe_divide(verbal, len(nouns), nan) * 100

    @property
    def compound_prepositions(self) -> float:
        return self._density(self.compound_prepositions_list)

    @property
    def parentheticals(self) -> float:
        return calc_parentheticals(
            self.forms,
            self.parentheticals_list,
            is_parenthetical=self.is_parenthetical,
            expand=self.expand_phrases,
            normalize=self.normalize,
        )

    @property
    def cliches(self) -> float:
        return self._density(self.cliches_list)

    def _density(self, phrases: Collection[str]) -> float:
        """Occurrences of the phrases in the forms per 100 words"""
        return calc_phrase_density(
            self.forms, phrases, expand=self.expand_phrases, normalize=self.normalize
        )

    def _phrase_spans(self, phrases: Collection[str]) -> list[tuple[int, int]]:
        """Bounds of the phrases in the forms, with their variants"""
        return find_phrases(self.forms, self.expand_phrases(self.forms, phrases), self.normalize)

    def keyword_density(self, *keywords: str) -> dict[str, float]:
        """
        Computing the density of keywords and phrases

        Arguments:
            keywords (tuple[str]): Keywords or phrases of several words separated by spaces

        Returns:
            dict[str, float]: Density of every keyword in percent
        """
        return calc_keyword_density(self.words, keywords, self.normalize)

    def nausea_words(self) -> dict[str, int]:
        """
        Getting the most frequent significant words of the academic nausea

        Returns:
            dict[str, int]: Occurrences of the top_n most frequent words without the
                stopwords, the most frequent first
        """
        return find_nausea_words(
            self.words,
            self.top_n,
            self.nausea_stopwords,
            is_stopword=self.is_stopword,
            normalize=self.normalize,
            messages=self.messages,
        )

    def markers(self) -> dict[str, tuple[str, ...]]:
        """
        Getting the markers of the officialese found in the text

        Description:
            The words and phrases counted by verbal_nouns, compound_prepositions,
            parentheticals and cliches, in the order of the text as the forms
            write them; a phrase is found with the variants of expand_phrases

        Returns:
            dict[str, tuple[str, ...]]: Name of the metric - the words and phrases found
        """
        forms = self.forms
        found = {
            "compound_prepositions": self._phrase_spans(self.compound_prepositions_list),
            "parentheticals": find_parentheticals(
                forms,
                self.parentheticals_list,
                is_parenthetical=self.is_parenthetical,
                expand=self.expand_phrases,
                normalize=self.normalize,
            ),
            "cliches": self._phrase_spans(self.cliches_list),
        }
        verbal = tuple(form for form, lemma in self.nouns() if self.is_verbal_noun(lemma))
        return {
            "verbal_nouns": verbal,
            **{
                name: tuple(" ".join(forms[start:end]) for start, end in spans)
                for name, spans in found.items()
            },
        }


def calc_classic_nausea(text: Sequence[str]) -> float:
    """
    Computing the classic nausea

    Description:
        The square root of the occurrences of the most frequent word (Advego):
        how much one word is pressed. Not corrected for length, it grows with
        the text

    References:
        https://advego.com/text/seo/

    Arguments:
        text (list[str]): List of words

    Returns:
        float: Value of the nausea, 0 for no words

    Raises:
        SourceTypeError: If the words are not a list of strings
    """
    check_words(text)
    if not len(text):
        return 0.0
    return sqrt(max(Counter(text).values()))


def find_nausea_words(
    text: Sequence[str],
    top_n: int = NAUSEA_TOP_N,
    stopwords: Collection[str] | None = None,
    *,
    is_stopword: Callable[[str], bool] | None = None,
    normalize: Callable[[str], str] = str.lower,
    messages: Mapping[str, str] = MESSAGES,
) -> dict[str, int]:
    """
    Finding the most frequent significant words of the academic nausea

    Description:
        The top_n most frequent words without the stopwords, the most frequent
        first, ties in the order of the text. A stopword is a word of stopwords
        by its normalized form or, without the list, one is_stopword accepts;
        without both there are none

    Arguments:
        text (list[str]): List of words
        top_n (int): Number of the most frequent words
        stopwords (list[str]|set[str]): Stopwords
        is_stopword (callable): Whether a word is a stopword
        normalize (callable): Normalized form of a word, the lower case by default
        messages (dict[str, str]): Messages of the errors by key (MESSAGES)

    Returns:
        dict[str, int]: Occurrences of every word

    Raises:
        SourceTypeError: If the words or the stopwords are not a list of strings, or
            is_stopword or normalize is not callable
        ParameterError: If top_n is not an integer or is below one

    Example:
        >>> from anyts.style_stats import find_nausea_words
        >>> find_nausea_words(["cat", "and", "cat", "and", "dog"], top_n=1, stopwords=["and"])
        {'cat': 2}
    """
    check_words(text)
    check_params(top_n, messages=messages)
    stops = _stop_flags(text, stopwords, is_stopword, normalize, "check of a stopword")
    significant = [word for word, stop in zip(text, stops, strict=True) if not stop]
    return dict(Counter(significant).most_common(top_n))


def _stop_flags(
    text: Sequence[str],
    stopwords: Collection[str] | None,
    is_stopword: Callable[[str], bool] | None,
    normalize: Callable[[str], str],
    what: str,
) -> list[bool]:
    """Whether every word is a stopword: of the list, by its normalized form, or of the predicate"""
    check_callable(normalize, "normalization")
    if is_stopword is not None:
        check_callable(is_stopword, what)
    if stopwords is not None:
        check_words(stopwords, "stopwords", ordered=False)
        stopwords_set = {normalize(word) for word in stopwords}
        return [normalize(word) in stopwords_set for word in text]
    if is_stopword is not None:
        return [is_stopword(word) for word in text]
    return [False] * len(text)


def calc_academic_nausea(
    text: Sequence[str],
    top_n: int = NAUSEA_TOP_N,
    stopwords: Collection[str] | None = None,
    *,
    is_stopword: Callable[[str], bool] | None = None,
    normalize: Callable[[str], str] = str.lower,
    messages: Mapping[str, str] = MESSAGES,
) -> float:
    """
    Computing the academic nausea

    Description:
        The occurrences of the top_n words of find_nausea_words over the number
        of all the words, in percent (Advego)

    References:
        https://advego.com/text/seo/

    Arguments:
        text (list[str]): List of words
        top_n (int): Number of the most frequent words
        stopwords (list[str]|set[str]): Stopwords
        is_stopword (callable): Whether a word is a stopword, without the list
        normalize (callable): Normalized form of a word, the lower case by default
        messages (dict[str, str]): Messages of the errors by key (MESSAGES)

    Returns:
        float: Value of the nausea in percent

    Raises:
        SourceTypeError: If the words or the stopwords are not a list of strings, or
            is_stopword or normalize is not callable
        ParameterError: If top_n is not an integer or is below one
    """
    found = find_nausea_words(
        text, top_n, stopwords, is_stopword=is_stopword, normalize=normalize, messages=messages
    )
    return safe_divide(100 * sum(found.values()), len(text))


def calc_water(
    text: Sequence[str],
    stopwords: Collection[str] | None = None,
    *,
    is_water_word: Callable[[str], bool] | None = None,
    normalize: Callable[[str], str] = str.lower,
) -> float:
    """
    Computing the water content

    Description:
        The share of the words without content in percent (Text.ru): the words
        of stopwords by their normalized forms or, without the list, those
        is_water_word accepts

    References:
        https://text.ru/seo

    Arguments:
        text (list[str]): List of words
        stopwords (list[str]|set[str]): Words of water
        is_water_word (callable): Whether a word is water, without the list
        normalize (callable): Normalized form of a word, the lower case by default

    Returns:
        float: Value of the water content in percent

    Raises:
        SourceTypeError: If the words or the stopwords are not a list of strings, or
            is_water_word or normalize is not callable
    """
    check_words(text)
    return safe_divide(
        100 * sum(_stop_flags(text, stopwords, is_water_word, normalize, "check of a water word")),
        len(text),
    )


def calc_spam(text: Sequence[str]) -> float:
    """
    Computing the spam score

    Description:
        The share of the repeated words in percent (Text.ru), every occurrence
        of a word after the first: 100 · (1 - TTR)

    References:
        https://text.ru/seo

    Arguments:
        text (list[str]): List of words

    Returns:
        float: Value of the spam score in percent

    Raises:
        SourceTypeError: If the words are not a list of strings
    """
    check_words(text)
    n_words = len(text)
    return safe_divide(100 * (n_words - len(set(text))), n_words)


def calc_zipf_naturalness(
    text: Sequence[str], top_n: int = NAUSEA_TOP_N, *, messages: Mapping[str, str] = MESSAGES
) -> float:
    """
    Computing the naturalness of a text by Zipf's law

    Description:
        The agreement of the frequencies of the most frequent words with the
        ideal f_r = f_1 / r, f_1 being the top frequency and r the rank:
        100 · (1 - the mean relative deviation from the ideal) over the ranks 2
        to min(top_n, V, f_1). Negative values are cut to 0; nan without ranks
        to compare: all the words hapaxes, one lexeme or top_n below 2

    References:
        https://en.wikipedia.org/wiki/Zipf's_law

    Arguments:
        text (list[str]): List of words
        top_n (int): Number of the most frequent words
        messages (dict[str, str]): Messages of the errors by key (MESSAGES)

    Returns:
        float: Value of the naturalness in percent, nan without ranks to compare

    Raises:
        SourceTypeError: If the words are not a list of strings
        ParameterError: If top_n is not an integer or is below one
    """
    check_words(text)
    check_params(top_n, messages=messages)
    frequencies = sorted(Counter(text).values(), reverse=True)
    if not frequencies:
        return nan
    top_freq = frequencies[0]
    n_ranks = min(top_n, len(frequencies), top_freq)
    if n_ranks < 2:
        return nan
    # In integers: the relative deviations of exact halves would come out below 50
    deviation = sum(
        abs(freq * rank - top_freq) for rank, freq in enumerate(frequencies[1:n_ranks], start=2)
    )
    span = top_freq * (n_ranks - 1)
    return max(0.0, 100 * (span - deviation) / span)


def calc_keyword_density(
    text: Sequence[str], keywords: Collection[str], normalize: Callable[[str], str] = str.lower
) -> dict[str, float]:
    """
    Computing the density of keywords

    Description:
        The occurrences of every keyword per 100 words (Text.ru). A keyword of
        several words separated by spaces is a sequence of words, and its
        occurrences may overlap. The words and the keywords are compared by
        their normalized forms; the keywords of a set come in sorted order

    References:
        https://text.ru/seo

    Arguments:
        text (list[str]): List of words
        keywords (list[str]|set[str]): Keywords or phrases
        normalize (callable): Normalized form of a word and of a keyword, the lower
            case by default

    Returns:
        dict[str, float]: Density of every keyword in percent

    Raises:
        SourceTypeError: If the words or the keywords are not a list of strings, or
            normalize is not callable

    Example:
        >>> from anyts.style_stats import calc_keyword_density
        >>> calc_keyword_density("the cat and the dog".split(), ["the", "the cat"])
        {'the': 40.0, 'the cat': 20.0}
    """
    check_words(text)
    check_words(keywords, "keywords", ordered=False)
    check_callable(normalize, "normalization")
    n_words = len(text)
    normalized = [normalize(word) for word in text]
    density = {}
    for keyword in in_order(keywords):
        parts = normalize(keyword).split()
        size = len(parts)
        if not size:
            density[keyword] = 0.0
            continue
        count = sum(1 for i in range(n_words - size + 1) if normalized[i : i + size] == parts)
        density[keyword] = safe_divide(100 * count, n_words)
    return density


def calc_phrase_density(
    text: Sequence[str],
    phrases: Collection[str],
    *,
    expand: Expander | None = None,
    normalize: Callable[[str], str] = str.lower,
) -> float:
    """
    Computing the density of the phrases of a list

    Description:
        The occurrences of the phrases (find_phrases) per 100 words; expand
        spells the phrases out in the forms of the text (the forms of a verb,
        contractions), every variant with its phrase

    Arguments:
        text (list[str]): List of words
        phrases (list[str]|set[str]): Phrases, words separated by spaces
        expand (callable): Variants of the phrases in the text, by the words and
            the phrases
        normalize (callable): Normalized form of a word, the lower case by default

    Returns:
        float: Occurrences per 100 words

    Raises:
        SourceTypeError: If the words or the phrases are not a list of strings, or
            expand or normalize is not callable
    """
    check_words(text)
    check_words(phrases, "phrases", ordered=False)
    if expand is not None:
        check_callable(expand, "expansion of the phrases")
    variants = expand(text, phrases) if expand is not None else phrases
    return safe_divide(len(find_phrases(text, variants, normalize)), len(text)) * 100


def find_parentheticals(
    text: Sequence[str],
    phrases: Collection[str] = (),
    *,
    is_parenthetical: Callable[[str], bool] | None = None,
    expand: Expander | None = None,
    normalize: Callable[[str], str] = str.lower,
) -> list[tuple[int, int]]:
    """
    Finding the parenthetical expressions of a text

    Description:
        The phrases of the list (spelled out by expand, as in
        calc_phrase_density) and the single words accepted by is_parenthetical
        outside the phrases found

    Arguments:
        text (list[str]): List of words
        phrases (list[str]|set[str]): Parenthetical phrases, words separated by spaces
        is_parenthetical (callable): Whether a word is a parenthetical expression by
            itself; none by default
        expand (callable): Variants of the phrases in the forms of the text with the
            phrase of each; the phrases as they are by default
        normalize (callable): Normalized form of a word and of a phrase, the lower
            case by default

    Returns:
        list[tuple[int, int]]: Bounds of the expressions as slices of the words, in order

    Raises:
        SourceTypeError: If the words or the phrases are not a list of strings, or
            is_parenthetical, expand or normalize is not callable

    Example:
        >>> from anyts.style_stats import find_parentheticals
        >>> find_parentheticals(
        ...     "in fact it is surely true".split(), ["in fact"], is_parenthetical={"surely"}.__contains__
        ... )
        [(0, 2), (4, 5)]
    """
    check_words(text)
    check_words(phrases, "phrases", ordered=False)
    for hook, what in (
        (is_parenthetical, "check of a parenthetical word"),
        (expand, "expansion of the phrases"),
    ):
        if hook is not None:
            check_callable(hook, what)
    variants = expand(text, phrases) if expand is not None else phrases
    spans = find_phrases(text, variants, normalize)
    if is_parenthetical is None:
        return spans
    covered = {position for start, end in spans for position in range(start, end)}
    singles = [
        (position, position + 1)
        for position, word in enumerate(text)
        if position not in covered and is_parenthetical(word)
    ]
    return sorted(spans + singles)


def calc_parentheticals(
    text: Sequence[str],
    phrases: Collection[str] = (),
    *,
    is_parenthetical: Callable[[str], bool] | None = None,
    expand: Expander | None = None,
    normalize: Callable[[str], str] = str.lower,
) -> float:
    """
    Computing the density of the parenthetical expressions

    Description:
        The expressions of find_parentheticals per 100 words

    Arguments:
        text (list[str]): List of words
        phrases (list[str]|set[str]): Parenthetical phrases, words separated by spaces
        is_parenthetical (callable): Whether a word is a parenthetical expression by
            itself; none by default
        expand (callable): Variants of the phrases in the forms of the text with the
            phrase of each; the phrases as they are by default
        normalize (callable): Normalized form of a word and of a phrase, the lower
            case by default

    Returns:
        float: Parenthetical expressions per 100 words

    Raises:
        SourceTypeError: If the words or the phrases are not a list of strings, or
            is_parenthetical, expand or normalize is not callable
    """
    spans = find_parentheticals(
        text, phrases, is_parenthetical=is_parenthetical, expand=expand, normalize=normalize
    )
    return safe_divide(len(spans), len(text)) * 100
