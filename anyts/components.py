from abc import ABCMeta, abstractmethod
from typing import Any, TypeVar

from spacy.language import Language
from spacy.tokens import Doc

from .exceptions import SourceError
from .utils import has_words

Stats = TypeVar("Stats")


class StatsComponent(metaclass=ABCMeta):
    """
    Base of a component of spaCy that puts the statistics of a text into doc._.<name>

    Description:
        A language library subclasses the class for every class of statistics
        and registers the subclass as a factory under the prefix of the library,
        Language.factory("<prefix>_<statistics>"), so that the factories of
        several libraries live in one process; add_pipe(factory, name=...)
        names the extension. The subclass checks its parameters before it calls
        the __init__ of the base, so that a wrong one fails at add_pipe, and
        implements compute; a subclass without it fails at add_pipe too
        A document without words passes untouched, its extension left at None
        (accepts). spaCy does not serialize the objects in the extensions, so
        Doc.to_bytes(), DocBin with store_user_data=True and nlp.pipe with
        n_process > 1 fail on them

    Arguments:
        nlp (Language): Pipeline the component is added to
        name (str): Name of the component in the pipeline and of the extension

    Methods:
        prepare: Preparing the pipeline
        accepts: Checking whether a document gets the statistics
        compute: Computing the statistics of a document
        from_extension: Getting the statistics another component put into a document
    """

    def __init__(self, nlp: Language, name: str):
        self.name = name
        self.prepare(nlp)
        Doc.set_extension(self.name, default=None, force=True)

    def __setstate__(self, state: dict[str, Any]) -> None:
        # An unpickled component, in another process, registers its extension again
        self.__dict__.update(state)
        Doc.set_extension(self.name, default=None, force=True)

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
            component = f"the component {factory}" if factory else "the component"
            raise SourceError(
                f"The extension {name} holds no {stats_class.__name__}: add {component} "
                f"with the name {name} before {self.name}"
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
