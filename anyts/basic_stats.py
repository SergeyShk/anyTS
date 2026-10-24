from __future__ import annotations

import re
import unicodedata
from abc import ABCMeta, abstractmethod
from collections import Counter
from collections.abc import Collection, Iterable, Mapping
from re import Pattern
from typing import TYPE_CHECKING, ClassVar

from .constants import (
    BASIC_STATS_DESC,
    COMPLEX_SYL_FACTOR,
    LONG_WORD_LETTER_FACTOR,
    MESSAGES,
    PUNCTUATION_TYPES,
    SPACES,
)
from .exceptions import ParameterError, SourceError, SourceTypeError
from .extractors import SentsExtractor, WordsExtractor
from .stats import Stats
from .utils import (
    check_bool,
    check_integer,
    check_words,
    count_letters,
    has_sents,
    has_words,
    is_doc,
    iter_doc_words,
    shannon_entropy,
    source_type_error,
)

if TYPE_CHECKING:
    from spacy.tokens import Doc, Span

_NORMALIZED_STATS = (
    "p_unique_words",
    "p_long_words",
    "p_complex_words",
    "p_simple_words",
    "p_monosyllable_words",
    "p_polysyllable_words",
    "p_letters",
    "p_spaces",
    "p_punctuations",
)
_ELLIPSIS_PATTERN = re.compile(r"…|\.{3,}|(?<=[?!])\.{2}")
_SPACE = f"[{re.escape(''.join(SPACES))}]"
# The dashes of dash_pattern; the underscore of italics counts as an opening or a closing mark
_DASHES = (
    r"-{2,}|(?:(?<=\s)|(?<=[.,;:!?…»”\"')\]_])|^)-(?!\d)"
    rf"|-(?=(?:{_SPACE})|\Z)"
    r"|(?<=[^\W\d_])-(?=[¿¡«“\"'(\[_])|(?<=[^\W\d_])-(?=[.,;:!?…»”\"')\]_])"
)


def dash_pattern(
    conjunctions: Collection[str] = (), hanging_before_comma: bool = False
) -> Pattern[str]:
    """
    Building the pattern of the dashes typed with hyphens

    Description:
        A dash typed with hyphens is a run of two or more hyphens, or a hyphen
        after whitespace, a closing mark or at the start of a line, before a
        space of a line (SPACES) or the end of the text, or between a letter
        and an opening or a closing mark. A hanging hyphen glued to a letter
        or a digit ("pre- and post-war", "5- and 10-year") stays a hyphen
        before spaces of a line and one of the conjunctions, case ignored, and
        with hanging_before_comma before a comma ("two-, three- and
        four-year"); a language whose dialogue closes a line with a hyphen
        before a comma ("-Come -he said-, and left") leaves it off

    Arguments:
        conjunctions (Collection[str]): Conjunctions after a hanging hyphen
        hanging_before_comma (bool): Take a hyphen between a letter and a comma
            for a hanging one

    Returns:
        Pattern: Compiled regular expression for count_punctuations

    Raises:
        SourceTypeError: If the conjunctions are not a collection of strings
        ParameterError: If a conjunction is empty

    Example:
        >>> from anyts.basic_stats import count_punctuations, dash_pattern
        >>> text = "pre- and post-war, two-, three- and four-year - he said"
        >>> counts = count_punctuations(text, dash_pattern=dash_pattern(["and"], True))
        >>> counts["dash"], counts["hyphen"]
        (1, 5)
    """
    check_words(conjunctions, "conjunctions", ordered=False)
    if any(not conjunction for conjunction in conjunctions):
        raise ParameterError("A conjunction must not be empty")
    unique = sorted(set(conjunctions))
    hanging = []
    if unique:
        alternatives = "|".join(map(re.escape, unique))
        hanging.append(rf"{_SPACE}+(?i:{alternatives})(?!\w)")
    if hanging_before_comma:
        hanging.append(",")
    if not hanging:
        return re.compile(_DASHES, re.MULTILINE)
    guard = rf"(?!(?<=[^\W_])-(?:{'|'.join(hanging)}))"
    return re.compile(rf"{guard}(?:{_DASHES})", re.MULTILINE)


DASH_PATTERN = dash_pattern()

PUNCTUATION_MARKS = {
    ",": "comma",
    ".": "period",
    "?": "question",
    "¿": "question",
    "!": "exclamation",
    "¡": "exclamation",
    ":": "colon",
    ";": "semicolon",
    "—": "dash",
    "–": "dash",
    "―": "dash",
    "-": "hyphen",
    "«": "angle_quotes",
    "»": "angle_quotes",
    '"': "straight_quotes",
    "“": "straight_quotes",
    "”": "straight_quotes",
    "‘": "straight_quotes",
    "’": "straight_quotes",
    "(": "parentheses",
    ")": "parentheses",
}
_DELETE_SPACES = str.maketrans("", "", "".join(SPACES))


class BasicStats(Stats, metaclass=ABCMeta):
    """
    Base of the basic statistics of a text

    Description:
        Counts of the sentences, words, characters, syllables and punctuation
        marks of a text. A language library implements count_syllables and
        may override count_punctuations and the class attributes
        The words and the sentences of a string come from the extractors. A Doc
        gives its tokens as words and its boundaries as sentences, or those of
        the sentence extractor when it has none or only partial ones
        (has_sents); an extractor given is used on its text instead. A sentence
        counts when it holds a word
        The other methods come from Stats

    Arguments:
        source (str|Doc): Data source (a string or a Doc object)
        sents_extractor (SentsExtractor): Sentence extraction tool
        words_extractor (WordsExtractor): Word extraction tool
        normalize (bool): Compute the normalized statistics
        complex_syl_factor (int): Minimum number of syllables in a complex word
        long_word_letter_factor (int): Minimum number of letters in a long word

    Attributes:
        normalize (bool): Whether the normalized statistics are computed
        complex_syl_factor (int): Minimum number of syllables in a complex word
        long_word_letter_factor (int): Minimum number of letters in a long word
        c_letters (dict[int, int]): Distribution of words by number of letters
        c_syllables (dict[int, int]): Distribution of words by number of syllables
        letters_entropy, syllables_entropy (float): Shannon entropy in bits of the
            distributions c_letters and c_syllables
        n_sents (int): Number of sentences containing words
        n_words (int): Number of words
        n_unique_words (int): Number of unique words, case ignored
        n_long_words (int): Number of long words
        n_complex_words (int): Number of complex words
        n_simple_words (int): Number of simple words
        n_monosyllable_words (int): Number of monosyllabic words
        n_polysyllable_words (int): Number of polysyllabic words
        n_chars (int): Number of characters without the line breaks
        n_letters (int): Number of letters
        n_spaces (int): Number of spaces of Unicode (Zs), such as the no-break space, and tabs
        n_syllables (int): Number of syllables
        n_punctuations (int): Number of punctuation marks
        c_punctuations (dict[str, int]): Distribution of punctuation marks by type
        p_unique_words (float): Normalized number of unique words
        p_long_words (float): Normalized number of long words
        p_complex_words (float): Normalized number of complex words
        p_simple_words (float): Normalized number of simple words
        p_monosyllable_words (float): Normalized number of monosyllabic words
        p_polysyllable_words (float): Normalized number of polysyllabic words
        p_letters (float): Normalized number of letters
        p_spaces (float): Normalized number of spaces
        p_punctuations (float): Normalized number of punctuation marks

    Methods:
        count_syllables: Counting the syllables of a word
        count_punctuations: Counting the punctuation marks of a text by type
        count_words_by_syllables: Number of words with at least the given number of syllables
        count_words_by_letters: Number of words with at least the given number of letters
        stat_names: Names of the statistics of get_stats

    Class attributes:
        sents_extractor_class (type[SentsExtractor]): Sentence extractor used when none is given
        words_extractor_class (type[WordsExtractor]): Word extractor used when none is given
        join_hyphens (bool): Join the parts of the hyphenated words of a Doc
        stats_desc (dict[str, str]): Counts of get_stats and their descriptions for print_stats

    Raises:
        SourceTypeError: If the source is neither a string nor a Doc object, or an extractor
            is of another type
        SourceError: If the source has no words
        ParameterError: If a factor is not an integer or is below one, or normalize is
            not a bool
    """

    sents_extractor_class: ClassVar[type[SentsExtractor]] = SentsExtractor
    words_extractor_class: ClassVar[type[WordsExtractor]] = WordsExtractor
    join_hyphens: ClassVar[bool] = False
    stats_desc: ClassVar[Mapping[str, str]] = BASIC_STATS_DESC

    def __init__(
        self,
        source: str | Doc,
        sents_extractor: SentsExtractor | None = None,
        words_extractor: WordsExtractor | None = None,
        normalize: bool = False,
        complex_syl_factor: int = COMPLEX_SYL_FACTOR,
        long_word_letter_factor: int = LONG_WORD_LETTER_FACTOR,
    ):
        messages = self.messages
        _check_extractors(sents_extractor, words_extractor, messages)
        check_bool(normalize, "normalization")
        _check_factor(
            complex_syl_factor,
            "minimum number of syllables in a complex word",
            messages["complex_syl_factor"],
        )
        _check_factor(
            long_word_letter_factor,
            "minimum number of letters in a long word",
            messages["long_word_letter_factor"],
        )
        sents: Iterable[Span] | Iterable[str]
        if is_doc(source):
            text = source.text
            if sents_extractor is not None:
                sents = sents_extractor.extract(text)
            elif has_sents(source):
                sents = source.sents
            else:
                sents = self.sents_extractor_class().extract(text)
            if words_extractor is not None:
                words = words_extractor.extract(text)
            else:
                words = tuple(word for _, _, word in iter_doc_words(source, self.join_hyphens))
        elif isinstance(source, str):
            text = source
            sents = (sents_extractor or self.sents_extractor_class()).extract(text)
            words = (words_extractor or self.words_extractor_class()).extract(text)
        else:
            raise source_type_error(messages, source)
        if not words:
            raise SourceError(messages["no_words"])

        self.normalize = normalize
        self.complex_syl_factor = complex_syl_factor
        self.long_word_letter_factor = long_word_letter_factor
        letters_per_word = tuple(count_letters(word) for word in words)
        syllables_per_word = tuple(self.count_syllables(word) for word in words)
        self.c_letters = dict(sorted(Counter(letters_per_word).items()))
        self.c_syllables = dict(sorted(Counter(syllables_per_word).items()))
        self.letters_entropy = shannon_entropy(self.c_letters)
        self.syllables_entropy = shannon_entropy(self.c_syllables)
        self.n_sents = sum(1 for sent in sents if has_words(sent))
        self.n_words = len(words)
        self.n_unique_words = len({word.lower() for word in words})
        self.n_long_words = self.count_words_by_letters(long_word_letter_factor)
        self.n_complex_words = self.count_words_by_syllables(complex_syl_factor)
        self.n_simple_words = sum(
            count for spw, count in self.c_syllables.items() if complex_syl_factor > spw > 0
        )
        self.n_monosyllable_words = self.c_syllables.get(1, 0)
        self.n_polysyllable_words = (
            self.n_words - self.c_syllables.get(1, 0) - self.c_syllables.get(0, 0)
        )
        self.n_chars = len(text) - text.count("\n") - text.count("\r")
        self.n_letters = sum(map(str.isalpha, text))
        self.n_spaces = len(text) - len(text.translate(_DELETE_SPACES))
        self.n_syllables = sum(syllables_per_word)
        punctuations = self.count_punctuations(text)
        self.n_punctuations = sum(punctuations.values())
        self.c_punctuations = punctuations

        if normalize:
            self.p_unique_words = self.n_unique_words / self.n_words
            self.p_long_words = self.n_long_words / self.n_words
            self.p_complex_words = self.n_complex_words / self.n_words
            self.p_simple_words = self.n_simple_words / self.n_words
            self.p_monosyllable_words = self.n_monosyllable_words / self.n_words
            self.p_polysyllable_words = self.n_polysyllable_words / self.n_words
            self.p_letters = self.n_letters / self.n_chars
            self.p_spaces = self.n_spaces / self.n_chars
            self.p_punctuations = self.n_punctuations / self.n_chars

    @abstractmethod
    def count_syllables(self, word: str) -> int:
        """
        Counting the syllables of a word

        Description:
            Implemented by a language library

        Arguments:
            word (str): Word

        Returns:
            int: Number of syllables
        """
        raise NotImplementedError

    def count_punctuations(self, text: str) -> dict[str, int]:
        """
        Counting the punctuation marks of a text by type

        Description:
            By default count_punctuations of the module

        Arguments:
            text (str): Text string

        Returns:
            dict[str, int]: Number of marks of each type in the order of PUNCTUATION_TYPES
        """
        return count_punctuations(text)

    def count_words_by_syllables(self, min_syllables: int) -> int:
        """
        Getting the number of words with at least the given number of syllables

        Arguments:
            min_syllables (int): Minimum number of syllables in a word

        Returns:
            int: Number of words

        Raises:
            ParameterError: If the minimum is not an integer
        """
        check_integer(min_syllables, "minimum number of syllables")
        return sum(count for spw, count in self.c_syllables.items() if spw >= min_syllables)

    def count_words_by_letters(self, min_letters: int) -> int:
        """
        Getting the number of words with at least the given number of letters

        Arguments:
            min_letters (int): Minimum number of letters in a word

        Returns:
            int: Number of words

        Raises:
            ParameterError: If the minimum is not an integer
        """
        check_integer(min_letters, "minimum number of letters")
        return sum(count for cpw, count in self.c_letters.items() if cpw >= min_letters)

    def stat_names(self) -> tuple[str, ...]:
        """
        Getting the names of the statistics of get_stats

        Returns:
            tuple[str, ...]: c_letters, c_syllables, the statistics of stats_desc,
                c_punctuations and, with normalize, the normalized counts
        """
        names = ("c_letters", "c_syllables", *self.stats_desc, "c_punctuations")
        return (*names, *_NORMALIZED_STATS) if self.normalize else names


def _check_factor(value: int, what: str, message: str) -> None:
    """
    Checking a threshold of the complex or the long words

    Arguments:
        value (int): Threshold
        what (str): Name of the threshold, for the message of a value that is not an integer
        message (str): Message of a threshold below one

    Raises:
        ParameterError: If the threshold is not an integer or is below one
    """
    check_integer(value, what)
    if value < 1:
        raise ParameterError(message)


def _check_extractors(
    sents_extractor: SentsExtractor | None,
    words_extractor: WordsExtractor | None,
    messages: Mapping[str, str] = MESSAGES,
) -> None:
    """Checking the types of the extractors given, SourceTypeError for another type"""
    if sents_extractor is not None and not isinstance(sents_extractor, SentsExtractor):
        raise SourceTypeError(messages["sents_extractor_type"])
    if words_extractor is not None and not isinstance(words_extractor, WordsExtractor):
        raise SourceTypeError(messages["words_extractor_type"])


def count_punctuations(
    text: str,
    marks: Mapping[str, str] = PUNCTUATION_MARKS,
    dash_pattern: Pattern[str] = DASH_PATTERN,
) -> dict[str, int]:
    """
    Counting punctuation marks by type

    Description:
        The dashes typed with hyphens (dash_pattern) are counted first, then
        the ellipses (…, three or more periods, or two after ? and !: "Who?.."
        is a question and an ellipsis), then every other mark by marks; any
        other character of the Unicode categories P and S is another mark. With
        the defaults ¿ and ¡ are question and exclamation marks, and a hyphen
        inside a word, before a digit or at a line break inside a word is a
        hyphen

    Arguments:
        text (str): Text string
        marks (dict[str, str]): Type of every mark, among PUNCTUATION_TYPES
        dash_pattern (Pattern): Dashes typed with hyphens

    Returns:
        dict[str, int]: Number of marks of each type in the order of PUNCTUATION_TYPES

    Raises:
        SourceTypeError: If the text is not a string, the marks are not a mapping or
            the dashes are not a compiled regular expression
        ParameterError: If a mark is not a single character or its type is unknown

    Example:
        >>> from anyts.basic_stats import count_punctuations
        >>> counts = count_punctuations('"Well..." - he said - "a well-known cat?!"')
        >>> {kind: count for kind, count in counts.items() if count}
        {'question': 1, 'exclamation': 1, 'ellipsis': 1, 'dash': 2, 'hyphen': 1, 'straight_quotes': 4}
    """
    if not isinstance(text, str):
        raise SourceTypeError(f"A text string is expected, not {type(text).__name__}")
    if not isinstance(marks, Mapping):
        raise SourceTypeError(f"The marks must be a mapping, not {type(marks).__name__}")
    if not isinstance(dash_pattern, Pattern):
        raise SourceTypeError(
            f"The dashes must be a compiled regular expression, not {type(dash_pattern).__name__}"
        )
    for char, kind in marks.items():
        if not isinstance(char, str) or len(char) != 1:
            raise ParameterError(f"A punctuation mark must be a single character, not {char!r}")
        if not isinstance(kind, str) or kind not in PUNCTUATION_TYPES:
            raise ParameterError(
                f"Unknown type of the mark {char!r}: {kind!r}. "
                f"Available types: {tuple(PUNCTUATION_TYPES)}"
            )
    counts = dict.fromkeys(PUNCTUATION_TYPES, 0)
    # Dashes first, so that one after an ellipsis still sees it (so...-he said)
    rest, counts["dash"] = dash_pattern.subn("", text)
    rest, counts["ellipsis"] = _ELLIPSIS_PATTERN.subn("", rest)
    chars = Counter(rest)
    for char, kind in marks.items():
        counts[kind] += chars[char]
    counts["other"] += sum(
        count
        for char, count in chars.items()
        if char not in marks and unicodedata.category(char)[0] in "PS"
    )
    return counts
