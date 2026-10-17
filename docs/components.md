# Components

!!! info ""
    **anyts.components.StatsComponent**, **anyts.components.BasicStatsComponent** and the components of the other classes of statistics

## Description

<!-- --8<-- [start:StatsComponent] -->
The base of the components of [spaCy](https://github.com/explosion/spaCy) that put the statistics of a text into an extension of `Doc`: a component registers the extension when added to a pipeline and puts the statistics of every document into `doc._.<name>`. Writing components in general is described in the [documentation of spaCy](https://spacy.io/usage/processing-pipelines#custom-components).
<!-- --8<-- [end:StatsComponent] -->

## Language hooks

<!-- --8<-- [start:StatsComponent-hooks] -->
A language library subclasses `StatsComponent` for every class of its statistics and registers the subclass as a factory under its prefix, `Language.factory("<prefix>_<statistics>")`, so that the factories of several libraries live in one process; declared as entry points of `spacy_factories`, they load with `spacy.load` without importing the library. The subclass sets the class of its statistics and checks its parameters in its `__init__` before calling the `__init__` of the base, so a wrong parameter fails at `add_pipe`. The components below already carry the parameters and checks of the classes of the core; a library sets its subclass of the statistics on them.

| Hook | Description |
| :--: | :---------: |
| `stats_class` | Class attribute: the class of statistics made of a document, `None` by default; a component with neither a concrete class nor its own `compute` raises `ParameterError` at `add_pipe` |
| `stats_params` | Class attribute: the attributes of the component passed to the class of statistics as keyword arguments, none by default; a name the component lacks raises `ParameterError` at `add_pipe` |
| `compute(doc)` | The statistics of a document, `stats_class(doc, **params)` by default; overridden by a component that computes otherwise, such as one reusing the statistics of another component |
| `prepare(nlp)` | Preparing the pipeline when the component is added, such as the rules of the tokenizer; nothing by default |
| `accepts(doc)` | Whether a document gets the statistics; by default whether it has a word (`has_words`) |
| `messages` | Class attribute: the messages of the errors by key, `MESSAGES` by default |
| `from_extension(doc, name, stats_class, factory=None)` | The statistics another component put into the document, for reuse instead of computing them again; an extension without statistics of the class raises `SourceError`, which names the factory to add. The other component must accept every document the reusing one does, since a document it passes leaves `None` |
<!-- --8<-- [end:StatsComponent-hooks] -->

## Names { #names }

<!-- --8<-- [start:StatsComponent-names] -->
The name of the pipe is the name of the extension: `nlp.add_pipe(factory, name="basic")` puts the statistics into `doc._.basic`. Without `name` both take the name of the factory. The extension follows the pipe when the pipeline renames it (`nlp.rename_pipe`), and a name taken by an extension of another package raises `ParameterError` instead of replacing it. A component taken from another pipeline (`add_pipe(name, source=other)`) is the same object in both, so under a new name it writes to that extension in the other pipeline too; a separate component comes from the factory, `add_pipe(factory, name=...)`. The same component can be added twice under different names, with different parameters. A document with no words - an empty string, whitespace, punctuation alone - passes through a component untouched, its extension left at `None`.
<!-- --8<-- [end:StatsComponent-names] -->

<!-- --8<-- [start:StatsComponent-serialization] -->
!!! warning "Serialization"
    A component keeps an object of statistics in `doc._.<name>`, and spaCy cannot serialize it: `Doc.to_bytes()`, `DocBin(store_user_data=True)` and `nlp.pipe(..., n_process>1)` fail with these components in the pipeline. To save a document, leave the user data out (`doc.to_bytes(exclude=["user_data"])`) or keep `doc._.<name>.get_stats()` separately; for multiprocessing compute the statistics in the main process after `nlp.pipe`, without the components.
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


    class Diversity(DiversityStats):
        def __init__(self, doc, window_len=50):
            words = [word.lower() for _, _, word in iter_doc_words(doc)]
            super().__init__(words, window_len=window_len)


    @Language.factory("demo_diversity")
    class DiversityComponent(StatsComponent):
        stats_class = Diversity
        stats_params = ("window_len",)

        def __init__(self, nlp, name, window_len=50):
            check_params(window_len=window_len, messages=self.messages)
            self.window_len = window_len
            super().__init__(nlp, name)


    nlp = spacy.blank("xx")
    nlp.add_pipe("demo_diversity", name="diversity", config={"window_len": 3})
    nlp("The cat and the dog")._.diversity.ttr
    # 0.8
    nlp("?!")._.diversity
    # None
    ```

## Components of the classes of statistics { #class-components }

<!-- --8<-- [start:class-components] -->
Each class of statistics of the core has a component that takes its parameters in the config of the pipe, checks them at `add_pipe` and passes them to the class; a language library subclasses it, sets its subclass of the statistics as `stats_class` and registers it under its prefix:

``` python
@Language.factory("<prefix>_phon")
class PhonStatsComponent(anyts.components.PhonStatsComponent):
    stats_class = PhonStats  # the subclass of the library
```

The class of the core is the default of `stats_class`. Where it cannot read a `Doc` - an abstract class (`BasicStats`, `LexicalStats`, `PhonStats`), `ReadabilityStats` without the `basic_stats_class` of a library, none at all (`DiversityStatsComponent`, the class of the core taking a list of words) - the component cannot be added until the library gives its class.
<!-- --8<-- [end:class-components] -->

| Component | Class of statistics | Parameters |
| :-------: | :-----------------: | :--------: |
| `BasicStatsComponent` | `BasicStats` | - |
| `ReadabilityStatsComponent` | `ReadabilityStats` | `preset`, `basic` |
| `DiversityStatsComponent` | set by a library | `window_len`, `mtld_threshold`, `mtld_min_len`, `hdd_sample_size`, `log_base` |
| `LexicalStatsComponent` | `LexicalStats` | - |
| `StyleStatsComponent` | `StyleStats` | `stopwords`, `top_n`, `nausea_stopwords` |
| `PhonStatsComponent` | `PhonStats` | `window_len` |
| `SyntaxStatsComponent` | `SyntaxStats` | - |
| `CohesionStatsComponent` | `CohesionStats` | - |

<!-- --8<-- [start:BasicStatsComponent] -->
`BasicStatsComponent` puts the basic statistics of a document into its extension.
<!-- --8<-- [end:BasicStatsComponent] -->

<!-- --8<-- [start:ReadabilityStatsComponent] -->
`ReadabilityStatsComponent` puts the readability metrics into the extension, computed from the document or, with `basic`, from the basic statistics another component put into it. A library sets `basic_factory`, the factory of its component of the basic statistics, which the error names when that extension holds none.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `preset` | str | `None` | Preset of the coefficients, one of the presets of the class; the default of the class if `None` |
| `basic` | str | `None` | Extension of a component of the basic statistics to reuse instead of computing them again |

With `preset` left at `None` the config of a saved pipeline holds no preset, and the pipeline takes the default of the class when it is loaded; a library that wants its default written into the config gives it in the signature of its subclass. A preset that is not a string or not one of the class and an extension not named by a string raise `ParameterError`, a class without `basic_stats_class` and no `basic` `SourceTypeError`.
<!-- --8<-- [end:ReadabilityStatsComponent] -->

<!-- --8<-- [start:DiversityStatsComponent] -->
`DiversityStatsComponent` puts the lexical diversity metrics into the extension, by a class of the library that reads a `Doc`. Its parameters are those of `DiversityStats` - `window_len`, `mtld_threshold`, `mtld_min_len`, `hdd_sample_size`, `log_base` - with the same defaults, and a wrong one raises `ParameterError` (`check_params` of the diversity).
<!-- --8<-- [end:DiversityStatsComponent] -->

<!-- --8<-- [start:LexicalStatsComponent] -->
`LexicalStatsComponent` puts the lexical sophistication statistics into the extension, with the frequency dictionary of its attribute `freq_dict`: `None` by default, for the dictionary of the class, and set by a library in the constructor of its component. A document gets the statistics when it has a word of `iter_doc_words` (with `join_hyphens`) other than a number of the method `is_number`, `anyts.utils.is_number` by default; a library gives the numbers its class leaves out, so a document of numbers alone passes untouched.
<!-- --8<-- [end:LexicalStatsComponent] -->

<!-- --8<-- [start:StyleStatsComponent] -->
`StyleStatsComponent` puts the style metrics into the extension.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `stopwords` | list[str] | `None` | Stopwords of the water content; those of the class if `None` |
| `top_n` | int | `10` | Number of the most frequent words of the academic nausea and of the naturalness by Zipf's law |
| `nausea_stopwords` | list[str] | `None` | Words left out of the most frequent words of the academic nausea; those of the class if `None` |

Stopwords that are not a list of strings raise `SourceTypeError`, a `top_n` that is not an integer of at least one `ParameterError`.
<!-- --8<-- [end:StyleStatsComponent] -->

<!-- --8<-- [start:PhonStatsComponent] -->
`PhonStatsComponent` puts the phonetic statistics into the extension; `window_len` (3 by default) is the window in words of the alliteration and the assonance, and one that is not an integer of at least 2 raises `ParameterError`.
<!-- --8<-- [end:PhonStatsComponent] -->

<!-- --8<-- [start:SyntaxStatsComponent] -->
`SyntaxStatsComponent` puts the syntactic statistics into the extension; they need a parser before it.
<!-- --8<-- [end:SyntaxStatsComponent] -->

<!-- --8<-- [start:CohesionStatsComponent] -->
`CohesionStatsComponent` puts the cohesion statistics into the extension; by default they need the parts of speech and the lemmas before it.
<!-- --8<-- [end:CohesionStatsComponent] -->

## start_sents_after_blank_lines

!!! info ""
    **anyts.components.start_sents_after_blank_lines**

<!-- --8<-- [start:start_sents_after_blank_lines] -->
A component that starts a sentence at the first token after a blank line - a line break, optional whitespace and another line break - so that a heading, a list item or a paragraph without a final mark is a sentence of its own, as in the sentence extractor. It goes before the parser, `senter` or `sentencizer`, which keeps its starts and places the others. The whitespace before such a start stays with the sentence before it, and the marks that open a paragraph (a dash of a dialogue, `¡`, `«`) stay with its first word. Alone, the component leaves the sentences within a paragraph unsplit and sets partial boundaries (`has_sents`), so the statistics take the sentences of such a document from its text. A parsed document, such as one passed through the pipeline again, passes untouched, since spaCy keeps its sentences. A language library registers the component under its prefix, `Language.component("<prefix>_blank_lines", func=start_sents_after_blank_lines)`.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `doc` | Doc | `-` | Doc object |
<!-- --8<-- [end:start_sents_after_blank_lines] -->

!!! example "Example"

    ``` python
    import spacy
    from spacy.language import Language

    from anyts.components import start_sents_after_blank_lines

    Language.component("demo_blank_lines", func=start_sents_after_blank_lines)
    nlp = spacy.blank("xx")
    nlp.add_pipe("demo_blank_lines")
    nlp.add_pipe("sentencizer")
    [sent.text.strip() for sent in nlp("What is new\n\nFaster import. Fewer bugs.").sents]
    # ['What is new', 'Faster import.', 'Fewer bugs.']
    ```
