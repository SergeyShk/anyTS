from abc import ABCMeta, abstractmethod
from collections.abc import Mapping
from typing import Any, ClassVar, TypeVar

from spacy.language import Language
from spacy.tokens import Doc, Token

from .constants import MESSAGES
from .exceptions import ParameterError, SourceError
from .extractors import BLANK_LINE
from .utils import check_messages, has_words

Stats = TypeVar("Stats")


class StatsComponent(metaclass=ABCMeta):
    """
    Base of a component of spaCy that puts the statistics of a text into doc._.<name>

    Description:
        A language library subclasses the class for every class of statistics
        and registers the subclass as a factory under the prefix of the library,
        Language.factory("<prefix>_<statistics>"), so that the factories of
        several libraries live in one process; add_pipe(factory, name=...)
        names the extension, which follows the component when the pipeline
        renames it; a component taken from another pipeline is the same object
        there, writing to the extension of its last name. The subclass checks
        its parameters before it calls the __init__ of the base, so that a wrong
        one fails at add_pipe, and implements compute; a subclass without it
        fails at add_pipe too
        A document without words passes untouched, its extension left at None
        (accepts). spaCy does not serialize the objects in the extensions, so
        Doc.to_bytes(), DocBin with store_user_data=True and nlp.pipe with
        n_process > 1 fail on them

    Arguments:
        nlp (Language): Pipeline the component is added to
        name (str): Name of the component in the pipeline and of the extension

    Class attributes:
        messages (dict[str, str]): Messages of the errors by key (MESSAGES)

    Raises:
        ParameterError: If another package registered an extension of Doc with the name

    Methods:
        prepare: Preparing the pipeline
        accepts: Checking whether a document gets the statistics
        compute: Computing the statistics of a document
        from_extension: Getting the statistics another component put into a document
    """

    messages: ClassVar[Mapping[str, str]] = MESSAGES

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        check_messages(cls.messages)

    def __init__(self, nlp: Language, name: str):
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

    @abstractmethod
    def compute(self, doc: Doc) -> Any:
        """
        Computing the statistics of a document

        Description:
            A language library implements the method

        Arguments:
            doc (Doc): Doc object

        Returns:
            object: Statistics of the document
        """
        raise NotImplementedError

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
        stats = doc._.get(name) if Doc.has_extension(name) else None
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


def start_sents_after_blank_lines(doc: Doc) -> Doc:
    """
    Starting a sentence at the first token after a blank line

    Description:
        A component of spaCy for the pipeline before the component that sets
        the sentences - the parser, senter or sentencizer - which keeps the
        starts set here and places the others; the whitespace before such a
        start stays with the sentence before it. On its own the component
        leaves the sentences within a paragraph unsplit. A language library
        registers it under its prefix: Language.component("<prefix>_blank_lines",
        func=start_sents_after_blank_lines)

    Arguments:
        doc (Doc): Doc object

    Returns:
        Doc: The document

    Raises:
        SourceError: If the document is parsed, since spaCy keeps the sentences
            of a parsed document

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
    if len(doc) and doc.has_annotation("DEP"):
        raise SourceError(
            "The sentences of a parsed document cannot be changed: add the component "
            "before the parser"
        )
    text = doc.text
    end = None
    spaces: list[Token] = []
    for token in doc:
        if token.is_space:
            spaces.append(token)
            continue
        if end is not None and BLANK_LINE.search(text, end, token.idx):
            for space in spaces:
                space.is_sent_start = False
            token.is_sent_start = True
        spaces = []
        end = token.idx + len(token)
    return doc


def _register(name: str, messages: Mapping[str, str] = MESSAGES) -> None:
    """Registering the extension of a component, never over one of another package"""
    if Doc.has_extension(name) and Doc.get_extension(name) != (None, None, None, None):
        raise ParameterError(messages["foreign_extension"].format(name=name))
    Doc.set_extension(name, default=None, force=True)
