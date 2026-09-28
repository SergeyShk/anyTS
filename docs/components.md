# Components

!!! info ""
    **anyts.components.StatsComponent**

## Description

<!-- --8<-- [start:StatsComponent] -->
The base of the components of [spaCy](https://github.com/explosion/spaCy) that put the statistics of a text into an extension of `Doc`: a component registers the extension when it is added to a pipeline and, for every document, computes the statistics and puts them into `doc._.<name>`. Writing components in general is described in the [documentation of spaCy](https://spacy.io/usage/processing-pipelines#custom-components).
<!-- --8<-- [end:StatsComponent] -->

## Language hooks

<!-- --8<-- [start:StatsComponent-hooks] -->
A language library subclasses `StatsComponent` for every class of its statistics and registers the subclass as a factory under the prefix of the library - `Language.factory("<prefix>_<statistics>")` - so that the factories of several libraries live in one process. Declared as entry points of `spacy_factories`, the factories load with `spacy.load` without importing the library. The subclass checks its parameters in its `__init__` before it calls the `__init__` of the base, so a wrong parameter fails at `add_pipe`.

| Hook | Description |
| :--: | :---------: |
| `compute(doc)` | The statistics of a document; an abstract method, so a subclass without it fails at `add_pipe` |
| `prepare(nlp)` | Preparing the pipeline when the component is added, such as the rules of the tokenizer; nothing by default |
| `accepts(doc)` | Whether a document gets the statistics; by default whether it has a word (`has_words`) |
| `from_extension(doc, name, stats_class, factory=None)` | The statistics another component put into the document, for reusing them instead of computing them again; an extension without statistics of the class raises `SourceError`, which names the factory to add. The other component must accept every document the reusing one does, since a document it passes leaves `None` |
<!-- --8<-- [end:StatsComponent-hooks] -->

## Names { #names }

<!-- --8<-- [start:StatsComponent-names] -->
The name of the pipe is the name of the extension: `nlp.add_pipe(factory, name="basic")` puts the statistics into `doc._.basic`. Without `name` the pipe and the extension keep the name of the factory. The extension follows the pipe when the pipeline renames it (`nlp.rename_pipe`), and a name taken by an extension of another package raises `ParameterError` instead of replacing it. A component taken from another pipeline (`add_pipe(name, source=other)`) is the same object in both, so under a new name it writes to that extension in the other pipeline too; a component of its own comes from the factory, `add_pipe(factory, name=...)`. The same component can be added twice under different names, with different parameters. A document with no words - an empty string, whitespace, punctuation alone - passes through a component untouched, its extension left at `None`.
<!-- --8<-- [end:StatsComponent-names] -->

<!-- --8<-- [start:StatsComponent-serialization] -->
!!! warning "Serialization"
    A component keeps an object of statistics in `doc._.<name>`, and spaCy cannot serialize it: `Doc.to_bytes()`, `DocBin(store_user_data=True)` and `nlp.pipe(..., n_process>1)` fail with these components in the pipeline. To save a document, leave the user data out (`doc.to_bytes(exclude=["user_data"])`) or keep `doc._.<name>.get_stats()` on your own; for multiprocessing compute the statistics in the main process after `nlp.pipe`, without the components.
<!-- --8<-- [end:StatsComponent-serialization] -->

## Parameters

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `nlp` | Language | `-` | Pipeline the component is added to |
| `name` | str | `-` | Name of the component in the pipeline and of the extension |

## Usage example

A component of the lexical diversity of the words of a `Doc`.

!!! example "Example"

    ``` python
    import spacy
    from spacy.language import Language

    from anyts import DiversityStats
    from anyts.components import StatsComponent
    from anyts.diversity_stats import check_params
    from anyts.utils import iter_doc_words


    @Language.factory("demo_diversity")
    class DiversityComponent(StatsComponent):
        def __init__(self, nlp, name="demo_diversity", window_len=50):
            check_params(window_len=window_len)
            self.window_len = window_len
            super().__init__(nlp, name)

        def compute(self, doc):
            words = [word.lower() for _, _, word in iter_doc_words(doc)]
            return DiversityStats(words, window_len=self.window_len)


    nlp = spacy.blank("xx")
    nlp.add_pipe("demo_diversity", name="diversity", config={"window_len": 3})
    nlp("The cat and the dog")._.diversity.ttr
    # 0.8
    nlp("?!")._.diversity
    # None
    ```
