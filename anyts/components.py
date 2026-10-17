from __future__ import annotations

from collections.abc import Mapping
from inspect import isabstract
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar, cast

from .basic_stats import BasicStats
from .cohesion_stats import CohesionStats
from .constants import (
    DIVERSITY_LOG_BASE,
    HDD_SAMPLE_SIZE,
    MATTR_WINDOW_LEN,
    MESSAGES,
    MTLD_MIN_LEN,
    MTLD_TTR_THRESHOLD,
    NAUSEA_TOP_N,
    PHON_WINDOW_LEN,
)
from .diversity_stats import check_params as check_diversity_params
from .exceptions import ParameterError, SourceError
from .extractors import BLANK_LINE
from .lexical_stats import LexicalStats
from .phon_stats import PhonStats
from .phon_stats import check_params as check_phon_params
from .readability_stats import ReadabilityStats
from .style_stats import StyleStats
from .style_stats import check_params as check_style_params
from .syntax_stats import SyntaxStats
from .utils import check_messages, check_words, has_words, is_number, iter_doc_tokens

if TYPE_CHECKING:
    from spacy.language import Language
    from spacy.tokens import Doc
    from thinc.types import Ints2d

Stats = TypeVar("Stats")


class StatsComponent:
    """
    Base of a component of spaCy that puts the statistics of a text into doc._.<name>

    Description:
        A language library subclasses the class for every class of statistics
        and registers the subclass as a factory under the prefix of the library,
        Language.factory("<prefix>_<statistics>"), so that the factories of
        several libraries live in one process; add_pipe(factory, name=...)
        names the extension, which follows the component when the pipeline
        renames it; a component taken from another pipeline is the same object
        there, writing to the extension of its last name. The subclass sets
        stats_class, the class of statistics made of a document, and checks its
        parameters before it calls the __init__ of the base, so that a wrong one
        fails at add_pipe; a subclass with no class of statistics and no compute
        of its own fails at add_pipe too. The components of the classes of the
        core (BasicStatsComponent and the others) carry their parameters, so a
        library sets its subclass of the statistics on them
        A document without words passes untouched, its extension left at None
        (accepts). spaCy does not serialize the objects in the extensions, so
        Doc.to_bytes(), DocBin with store_user_data=True and nlp.pipe with
        n_process > 1 fail on them

    Arguments:
        nlp (Language): Pipeline the component is added to
        name (str): Name of the component in the pipeline and of the extension

    Class attributes:
        stats_class (type): Class of statistics made of a document, None by default
        stats_params (tuple[str, ...]): Attributes of the component passed to the class
            of statistics as its keyword arguments
        messages (dict[str, str]): Messages of the errors by key (MESSAGES)

    Raises:
        ParameterError: If another package registered an extension of Doc with the name,
            or the component has neither a concrete stats_class nor a compute of its own

    Methods:
        prepare: Preparing the pipeline
        accepts: Checking whether a document gets the statistics
        compute: Computing the statistics of a document
        from_extension: Getting the statistics another component put into a document
    """

    stats_class: ClassVar[type[Any] | None] = None
    stats_params: ClassVar[tuple[str, ...]] = ()
    messages: ClassVar[Mapping[str, str]] = MESSAGES

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        check_messages(cls.messages)

    def __init__(self, nlp: Language, name: str):
        if type(self).compute is StatsComponent.compute:
            self._stats_class()
        self.name = name
        self.prepare(nlp)

    @property
    def name(self) -> str:
        """Name of the component in the pipeline and of its extension"""
        return self._name

    @name.setter
    def name(self, name: str) -> None:
        # The pipeline renames its components by this attribute
        _register(name, self.messages)
        self._name = name

    def __setstate__(self, state: dict[str, Any]) -> None:
        # An unpickled component, in another process, registers its extension again
        self.__dict__.update(state)
        _register(self._name, self.messages)

    def prepare(self, nlp: Language) -> None:
        """
        Preparing the pipeline the component is added to

        Description:
            Nothing by default; a language library adds the rules of its
            tokenizer here, for instance

        Arguments:
            nlp (Language): Pipeline
        """
        return

    def accepts(self, doc: Doc) -> bool:
        """
        Checking whether a document gets the statistics

        Arguments:
            doc (Doc): Doc object

        Returns:
            bool: Whether the document has a word (has_words)
        """
        return has_words(doc)

    def compute(self, doc: Doc) -> Any:
        """
        Computing the statistics of a document

        Description:
            An object of stats_class made of the document, with the attributes of
            the component named in stats_params as its keyword arguments; a
            component that computes otherwise, such as one that reuses the
            statistics of another component, overrides the method

        Arguments:
            doc (Doc): Doc object

        Returns:
            object: Statistics of the document
        """
        return self._stats_class()(
            doc, **{name: getattr(self, name) for name in self.stats_params}
        )

    def _stats_class(self) -> type[Any]:
        """The concrete class of statistics of the component"""
        stats_class = self.stats_class
        if stats_class is None or isabstract(stats_class):
            raise ParameterError(self.messages["no_stats_class"].format(cls=type(self).__name__))
        return stats_class

    def from_extension(
        self, doc: Doc, name: str, stats_class: type[Stats], factory: str | None = None
    ) -> Stats:
        """
        Getting the statistics another component put into a document

        Description:
            For a component that reuses the statistics of another one instead of
            computing them again; that component must come first in the pipeline
            and accept every document the reusing one accepts, since a document
            it passes leaves None in its extension

        Arguments:
            doc (Doc): Doc object
            name (str): Name of the extension of the other component
            stats_class (type): Class of the statistics expected there
            factory (str): Factory of the other component, for the message of the error

        Returns:
            object: Statistics of the extension

        Raises:
            SourceError: If the extension does not hold statistics of the class
        """
        stats = doc._.get(name) if doc.has_extension(name) else None
        if not isinstance(stats, stats_class):
            key = "missing_extension" if factory else "missing_extension_any"
            raise SourceError(
                self.messages[key].format(
                    name=name, stats=stats_class.__name__, factory=factory, component=self.name
                )
            )
        return stats

    def __call__(self, doc: Doc) -> Doc:
        """
        Putting the statistics of a document into its extension

        Arguments:
            doc (Doc): Doc object

        Returns:
            Doc: The document; untouched if it is not accepted
        """
        if self.accepts(doc):
            doc._.set(self.name, self.compute(doc))
        return doc


def _register(name: str, messages: Mapping[str, str] = MESSAGES) -> None:
    """Registering the extension of a component, never over one of another package"""
    from spacy.tokens import Doc

    if Doc.has_extension(name) and Doc.get_extension(name) != (None, None, None, None):
        raise ParameterError(messages["foreign_extension"].format(name=name))
    Doc.set_extension(name, default=None, force=True)


class BasicStatsComponent(StatsComponent):
    """
    Component of the basic statistics of a text

    Description:
        Puts an object of stats_class (BasicStats) into doc._.<name>; a language
        library sets its subclass of BasicStats
    """

    stats_class: ClassVar[type[Any] | None] = BasicStats


class ReadabilityStatsComponent(StatsComponent):
    """
    Component of the readability metrics of a text

    Description:
        Puts an object of stats_class (ReadabilityStats) into doc._.<name>, of
        the document or of the basic statistics another component put into it;
        a language library sets its subclass of ReadabilityStats and the factory
        of its component of the basic statistics (basic_factory), named in the
        error when they are missing

    Arguments:
        nlp (Language): Pipeline the component is added to
        name (str): Name of the component in the pipeline and of the extension
        preset (str): Preset of the coefficients of stats_class; its default if None
        basic (str): Extension of a component of the basic statistics to reuse
            instead of computing them again

    Class attributes:
        basic_factory (str|None): Factory of the component of the basic statistics

    Raises:
        ParameterError: If the preset is not a string or is not one of stats_class, or
            the extension is not named by a string
        SourceError: If the named extension holds no basic statistics of the class
    """

    stats_class: ClassVar[type[Any] | None] = ReadabilityStats
    basic_factory: ClassVar[str | None] = None

    def __init__(
        self, nlp: Language, name: str, preset: str | None = None, basic: str | None = None
    ):
        messages = self.messages
        if preset is not None:
            if not isinstance(preset, str):
                raise ParameterError(messages["preset_type"].format(type=type(preset).__name__))
            presets = self._stats_class().presets
            if preset not in presets:
                raise ParameterError(
                    messages["unknown_preset"].format(preset=preset, presets=tuple(presets))
                )
        if basic is not None and not isinstance(basic, str):
            raise ParameterError(messages["extension_name"].format(type=type(basic).__name__))
        self.preset = preset
        self.basic = basic
        super().__init__(nlp, name)

    def compute(self, doc: Doc) -> Any:
        stats_class = self._stats_class()
        source: Any = doc
        if self.basic is not None:
            source = self.from_extension(
                doc, self.basic, stats_class.basic_stats_class or BasicStats, self.basic_factory
            )
        if self.preset is None:
            return stats_class(source)
        return stats_class(source, preset=self.preset)


class DiversityStatsComponent(StatsComponent):
    """
    Component of the lexical diversity metrics of a text

    Description:
        Puts an object of stats_class into doc._.<name>: a subclass of
        DiversityStats of a language library that reads a Doc, since the class
        of the core takes a list of words

    Arguments:
        nlp (Language): Pipeline the component is added to
        name (str): Name of the component in the pipeline and of the extension
        window_len (int): Window size for MATTR and segment size for MSTTR
        mtld_threshold (float): TTR threshold for MTLD, MA-MTLD and MTLD-W
        mtld_min_len (int): Minimum factor length for MTLD, MA-MTLD and MTLD-W
        hdd_sample_size (int): Sample size for HD-D
        log_base (float): Logarithm base for the Summer, Maas and Dugast metrics

    Raises:
        ParameterError: If a parameter is not a number of its range (check_params)
    """

    stats_params: ClassVar[tuple[str, ...]] = (
        "window_len",
        "mtld_threshold",
        "mtld_min_len",
        "hdd_sample_size",
        "log_base",
    )

    def __init__(
        self,
        nlp: Language,
        name: str,
        window_len: int = MATTR_WINDOW_LEN,
        mtld_threshold: float = MTLD_TTR_THRESHOLD,
        mtld_min_len: int = MTLD_MIN_LEN,
        hdd_sample_size: int = HDD_SAMPLE_SIZE,
        log_base: float = DIVERSITY_LOG_BASE,
    ):
        check_diversity_params(
            window_len,
            mtld_threshold,
            mtld_min_len,
            hdd_sample_size,
            log_base,
            messages=self.messages,
        )
        self.window_len = window_len
        self.mtld_threshold = mtld_threshold
        self.mtld_min_len = mtld_min_len
        self.hdd_sample_size = hdd_sample_size
        self.log_base = log_base
        super().__init__(nlp, name)


class LexicalStatsComponent(StatsComponent):
    """
    Component of the lexical sophistication statistics of a text

    Description:
        Puts an object of stats_class, a subclass of LexicalStats of a language
        library, into doc._.<name>, with the frequency dictionary of the
        attribute freq_dict - None by default, for the dictionary of the class;
        a library sets the attribute in the constructor of its component, from a
        directory of its parameters for instance. A document gets the statistics
        when it has a word other than a number (is_number)
    """

    stats_class: ClassVar[type[Any] | None] = LexicalStats
    stats_params: ClassVar[tuple[str, ...]] = ("freq_dict",)
    freq_dict: Any = None

    def accepts(self, doc: Doc) -> bool:
        return any(not is_number(token.text) for token in iter_doc_tokens(doc))


class StyleStatsComponent(StatsComponent):
    """
    Component of the style metrics of a text

    Description:
        Puts an object of stats_class (StyleStats) into doc._.<name>; a language
        library sets its subclass of StyleStats

    Arguments:
        nlp (Language): Pipeline the component is added to
        name (str): Name of the component in the pipeline and of the extension
        stopwords (list[str]): Stopwords for the water content; those of the class
            if not set
        top_n (int): Number of the most frequent words of the academic nausea and
            of the naturalness by Zipf's law
        nausea_stopwords (list[str]): Words left out of the most frequent words of
            the academic nausea; those of the class if not set

    Raises:
        SourceTypeError: If the stopwords are not a list of strings
        ParameterError: If the number of the most frequent words is not an integer
            of at least one
    """

    stats_class: ClassVar[type[Any] | None] = StyleStats
    stats_params: ClassVar[tuple[str, ...]] = ("stopwords", "top_n", "nausea_stopwords")

    def __init__(
        self,
        nlp: Language,
        name: str,
        stopwords: list[str] | None = None,
        top_n: int = NAUSEA_TOP_N,
        nausea_stopwords: list[str] | None = None,
    ):
        check_style_params(top_n, messages=self.messages)
        if stopwords is not None:
            check_words(stopwords, "stopwords", ordered=False)
        if nausea_stopwords is not None:
            check_words(nausea_stopwords, "nausea stopwords", ordered=False)
        self.stopwords = stopwords
        self.top_n = top_n
        self.nausea_stopwords = nausea_stopwords
        super().__init__(nlp, name)


class PhonStatsComponent(StatsComponent):
    """
    Component of the phonetic statistics of a text

    Description:
        Puts an object of stats_class, a subclass of PhonStats of a language
        library, into doc._.<name>

    Arguments:
        nlp (Language): Pipeline the component is added to
        name (str): Name of the component in the pipeline and of the extension
        window_len (int): Window in words of the alliteration and the assonance

    Raises:
        ParameterError: If the window is not an integer of at least 2
    """

    stats_class: ClassVar[type[Any] | None] = PhonStats
    stats_params: ClassVar[tuple[str, ...]] = ("window_len",)

    def __init__(self, nlp: Language, name: str, window_len: int = PHON_WINDOW_LEN):
        check_phon_params(window_len, messages=self.messages)
        self.window_len = window_len
        super().__init__(nlp, name)


class SyntaxStatsComponent(StatsComponent):
    """
    Component of the syntactic statistics of a text

    Description:
        Puts an object of stats_class (SyntaxStats) into doc._.<name>; needs a
        parser before it
    """

    stats_class: ClassVar[type[Any] | None] = SyntaxStats


class CohesionStatsComponent(StatsComponent):
    """
    Component of the cohesion statistics of a text

    Description:
        Puts an object of stats_class (CohesionStats) into doc._.<name>; the
        class of the core needs the parts of speech and the lemmas before it
    """

    stats_class: ClassVar[type[Any] | None] = CohesionStats


def start_sents_after_blank_lines(doc: Doc) -> Doc:
    """
    Starting a sentence at the first token after a blank line

    Description:
        A component of spaCy for the pipeline before the component that sets
        the sentences - the parser, senter or sentencizer - which keeps the
        starts set here and places the others; the whitespace before such a
        start stays with the sentence before it, and the marks that open a
        paragraph (a dash of a dialogue, ¡, «) stay with its first word. On
        its own the component leaves the sentences within a paragraph
        unsplit, and its starts are partial boundaries (has_sents), so the
        statistics take the sentences of such a document from its text. A
        parsed document, such as one passed through the pipeline again,
        passes untouched, since spaCy keeps its sentences. A language library
        registers it under its prefix: Language.component("<prefix>_blank_lines",
        func=start_sents_after_blank_lines)

    Arguments:
        doc (Doc): Doc object

    Returns:
        Doc: The document

    Example:
        >>> import spacy
        >>> from spacy.language import Language
        >>> from anyts.components import start_sents_after_blank_lines
        >>> nlp = spacy.blank("xx")
        >>> _ = nlp.add_pipe("sentencizer")
        >>> [sent.text for sent in nlp("Notes\\n\\nThe cat sleeps.").sents]
        ['Notes\\n\\nThe cat sleeps.']
        >>> _ = Language.component("demo_blank_lines", func=start_sents_after_blank_lines)
        >>> _ = nlp.add_pipe("demo_blank_lines", before="sentencizer")
        >>> [sent.text for sent in nlp("Notes\\n\\nThe cat sleeps.").sents]
        ['Notes\\n\\n', 'The cat sleeps.']
    """
    from spacy.attrs import SENT_START

    if not len(doc) or doc.has_annotation("DEP"):
        return doc
    text = doc.text
    # Written at once: every assignment of is_sent_start makes spaCy scan the whole document
    starts = doc.to_array([SENT_START]).astype("int64")
    end = None
    spaces: list[int] = []
    leading = False
    for token in doc:
        if token.is_space:
            spaces.append(token.i)
            # A space after an opening mark (—\u00a0¡) keeps it with the word, a line break does not
            leading = leading and "\n" not in token.text
            if leading:
                starts[token.i] = -1
            continue
        if end is not None and BLANK_LINE.search(text, end, token.idx):
            starts[spaces] = -1
            starts[token.i] = 1
            leading = not has_words(token.text)
        elif leading:
            starts[token.i] = -1
            leading = not has_words(token.text)
        spaces = []
        end = token.idx + len(token)
    doc.from_array([SENT_START], cast("Ints2d", starts.astype("uint64")))
    return doc
