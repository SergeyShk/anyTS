# Cohesion statistics

!!! info ""
    **anyts.cohesion_stats.CohesionStats**

## Description

<!-- --8<-- [start:CohesionStats] -->
The cohesion statistics of a text in the manner of Coh-Metrix: the overlap of the nouns, of the arguments (nouns and pronouns) and of the content words between adjacent sentences and between all pairs of sentences, the givenness (pronouns, demonstratives, lemmas used before), the temporal cohesion - the repetition of the tense and of the aspect of the verbs of adjacent sentences - and the connectors of a dictionary by class and kind per 1000 words. The sentences are compared by lemmas. The data source is a `Doc` object of [spaCy](https://github.com/explosion/spaCy) with the parts of speech and the lemmas, split into sentences by its boundaries, or by the sentence extractor over its text when one is given or the `Doc` has none.

An extractor of another type and a source that is not a `Doc` raise `SourceTypeError`, a source without the parts of speech, without the lemmas or without words `SourceError`; a dictionary of connectors that is not a dictionary of phrases and pairs of strings raises `SourceTypeError`, an unknown class or kind `ParameterError`.
<!-- --8<-- [end:CohesionStats] -->

## Language hooks

<!-- --8<-- [start:CohesionStats-hooks] -->
A language library subclasses `CohesionStats`. By default the words and their features are read from a `Doc` by Universal Dependencies, and there are no connectors:

| Hook | Kind | Description |
| :--: | :--: | :---------: |
| `analyze(source)` | method | Words of the sentences of a source as `CohesionWord`: the word, its lemma, its part of speech for the rules of the connectors, whether it is a noun, a pronoun, a demonstrative, an argument and a content word, its tense, mood and aspect; by default those of a `Doc`, sentence by sentence (`doc_units`), with the features of `word_info` - a library that reads a string or a `Doc` without these annotations overrides it |
| `doc_units(doc)` | method | Words of the sentences of a `Doc` as lists of tokens: by its boundaries, or by the extractor over its text (`split_doc_units` of `anyts.utils`) |
| `word_info(unit)` | method | Features of a word of a `Doc`; by default a noun is `NOUN` or `PROPN`, a pronoun `PRON` or a possessive, demonstrative or personal determiner, a demonstrative carries `PronType=Dem`, an argument is `NOUN`, `PROPN` or `PRON`, a content word one of `anyts.constants.CONTENT_UD_POS` and no demonstrative, and the tense, the mood and the aspect are the features `Tense`, `Mood` and `Aspect` |
| `load_connectors()` | class method | Dictionary of the connectors of the language, class and kind by connector; empty by default |
| `connector_matcher()` | class method | Matcher of that dictionary, built once for a class and shared by its instances - and by a search of the connectors outside the statistics |
| `connector_matcher_class` | class attribute | Class that finds the connectors with the context rules of the language; `ConnectorMatcher` by default |
| `temporal_features` | class attribute | Features of the verbs whose repetitions make the temporal cohesion, one or more distinct ones of `tense`, `mood` and `aspect` in a tuple, checked when the class is defined; the tense and the aspect by default, as in Coh-Metrix |
| `sents_extractor_class`, `join_hyphens` | class attributes | Sentence extractor of a `Doc` without boundaries, joining of the hyphenated words of a `Doc` |
| `stats_desc`, `stats_headers` | class attributes | Statistics of `get_stats` with their descriptions, headers of the columns for `print_stats` |
| `messages` | class attribute | Messages of the errors by key; `MESSAGES` by default |

The parameters of a library - its model of a string, its word extractor - go to the constructor of its subclass, which keeps them for its `analyze`.
<!-- --8<-- [end:CohesionStats-hooks] -->

## Parameters

<!-- --8<-- [start:CohesionStats-parameters] -->
| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `source` | Doc | `-` | Data source: a `Doc` with the parts of speech and the lemmas, or what `analyze` reads |
| `sents_extractor` | SentsExtractor | `None` | Sentence extraction tool; given here, it splits a `Doc` by its text whatever its boundaries |
| `connectors` | dict[str, tuple[str, str]] | `None` | Class and kind by connector; those of `load_connectors` by default |
<!-- --8<-- [end:CohesionStats-parameters] -->

## Attributes

<!-- --8<-- [start:CohesionStats-attributes] -->
| Attribute | Type | Description |
| :-------: | :--: | :---------: |
| `words`, `lemmas` | tuple[tuple[str]] | Words and lemmas of every sentence with words |
| `n_sents`, `n_words` | int | Numbers of the sentences with words and of the words |
| `n_nouns`, `n_pronouns`, `n_demonstratives`, `n_content_words` | int | Numbers of the words by kind |
| `n_given` | int | Number of the content words whose lemma was used before |
| `n_connectors`, `connector_spans`, `c_connectors` | int, tuple[Connector], dict[str, int] | Number of the connectors, their occurrences and their number by connector |
| `noun_overlap_adjacent`, `noun_overlap_all` | float | Shares of the adjacent and of all pairs of sentences sharing a noun |
| `argument_overlap_adjacent`, `argument_overlap_all` | float | The same for a noun or a pronoun |
| `content_overlap_adjacent`, `content_overlap_all` | float | The same for a content word |
| `content_overlap_prop_adjacent`, `content_overlap_prop_all` | float | Mean share of the shared content words (Dice) in the adjacent and in all pairs |
| `p_pronouns`, `p_demonstratives` | float | Shares of the pronouns and of the demonstratives among the words |
| `pronoun_noun_ratio` | float | Ratio of the pronouns to the nouns |
| `p_given` | float | Share of the content words whose lemma was used before in the text |
| `tense_repetition`, `mood_repetition`, `aspect_repetition` | float | Shares of the adjacent pairs of sentences with the same dominant tense, mood and aspect |
| `temporal_cohesion` | float | Mean of the repetitions of `temporal_features` |
| `connectors` | float | Connectors per 1000 words |
| `connectors_<class>`, `connectors_<kind>` | float | Connectors of every class and kind of the matcher per 1000 words: `connectors_causal`, `connectors_adversative`, `connectors_concessive`, `connectors_temporal`, `connectors_additive`, `connectors_conditional`, `connectors_reformulative`, `connectors_primary` and `connectors_secondary` by default |

An overlap of a text of one sentence, a repetition without two adjacent sentences with the feature, and a share without anything to divide by are `nan`.
<!-- --8<-- [end:CohesionStats-attributes] -->

The methods `get_stats`, `to_dataframe`, `print_stats` and `describe` are those of the [statistics interface](stats.md).

## Metric functions

The overlaps, the givenness, the repetitions and the search of the connectors are described in the [metric functions](cohesion_stats_funcs.md) section.

## Usage example

!!! example "Example"

    ``` python
    import spacy
    from spacy.tokens import Doc

    from anyts.cohesion_stats import CohesionStats


    class English(CohesionStats):
        @classmethod
        def load_connectors(cls):
            return {"however": ("adversative", "secondary")}


    # The cat slept. However, the cat woke.
    doc = Doc(
        spacy.blank("en").vocab,
        words=["The", "cat", "slept", ".", "However", ",", "the", "cat", "woke", "."],
        spaces=[True, True, False, True, False, True, True, True, False, False],
        pos=["DET", "NOUN", "VERB", "PUNCT", "ADV", "PUNCT", "DET", "NOUN", "VERB", "PUNCT"],
        lemmas=["the", "cat", "sleep", ".", "however", ",", "the", "cat", "wake", "."],
        morphs=["", "", "Aspect=Perf|Tense=Past", "", "", "", "", "", "Aspect=Perf|Tense=Past", ""],
        sent_starts=[True, False, False, False, True, False, False, False, False, False],
    )
    stats = English(doc)
    stats.noun_overlap_adjacent, stats.temporal_cohesion
    # (1.0, 1.0)
    stats.connector_spans
    # (Connector(sent=1, start=0, end=1, text='however', cls='adversative', kind='secondary'),)
    ```
