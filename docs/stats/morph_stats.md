# Morphological statistics

``` {.python .signature}
MorphStats(source)
```

<!-- --8<-- [start:MorphStats] -->
The morphological statistics of a text: the part of speech and the features of [Universal Dependencies](https://universaldependencies.org/u/feat/) of every word, counted by value or given word by word. By default the data source is a `Doc` object of [spaCy](https://github.com/explosion/spaCy) with the parts of speech, read by `token.pos_` and `token.morph`; a language library reads a string or a `Doc` without them in its own way.

Raises:

- `SourceTypeError` - a source that is not a `Doc`, an `analyze` that does not give `MorphWord` objects;
- `SourceError` - a source without parts of speech or without words.
<!-- --8<-- [end:MorphStats] -->

=== "Code"

    ``` python
    import spacy
    from spacy.tokens import Doc

    from anyts.morph_stats import MorphStats

    doc = Doc(
        spacy.blank("en").vocab,
        words=["The", "cats", "slept", "and", "they", "dream", "."],
        pos=["DET", "NOUN", "VERB", "CCONJ", "PRON", "VERB", "PUNCT"],
        morphs=[
            "Definite=Def|PronType=Art",
            "Number=Plur",
            "Mood=Ind|Tense=Past|VerbForm=Fin",
            "",
            "Case=Nom|Number=Plur|Person=3|PronType=Prs",
            "Mood=Ind|Tense=Pres|VerbForm=Fin",
            "PunctType=Peri",
        ],
    )
    stats = MorphStats(doc)
    stats.get_stats("pos", "number", "tense")
    stats.tags[:3]
    ```

=== "Result"

    ```
    {'pos': {'DET': 1, 'NOUN': 1, 'VERB': 2, 'CCONJ': 1, 'PRON': 1}, 'number': {None: 4, 'Plur': 2}, 'tense': {None: 4, 'Past': 1, 'Pres': 1}}
    ('Definite=Def|PronType=Art', 'Number=Plur', 'Mood=Ind|Tense=Past|VerbForm=Fin')
    ```

## Parameters

<!-- --8<-- [start:MorphStats-parameters] -->
| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `source` | `str` / `Doc` | - | Data source: a `Doc` with the parts of speech, or what `analyze` takes |
<!-- --8<-- [end:MorphStats-parameters] -->

## Attributes

<!-- --8<-- [start:MorphStats-attributes] -->
| Attribute | Type | Description |
| :-------- | :--- | :---------- |
| `words` | `tuple[str]` | Words of the text |
| `tags` | `tuple[str]` | Features of every word in the CoNLL-U format (`Case=Nom|Number=Plur`), `_` for a word without them |
| `pos` | `tuple[str / None]` | Part of speech of every word |
| `animacy`, `aspect`, ..., `voice` | `tuple[str / None]` | Value of a statistic for every word, `None` for a word without the feature |
<!-- --8<-- [end:MorphStats-attributes] -->

## Statistics

<!-- --8<-- [start:MorphStats-metrics] -->
Every statistic is a tuple of the values of the words, and `get_stats` counts them. Besides the part of speech `pos`, the statistics of the core are the features of Universal Dependencies (`MORPH_FEATURES`); a value of several is kept as Universal Dependencies writes it (`Int,Rel`).

| Statistic | Feature | Statistic | Feature |
| :-------- | :------ | :-------- | :------ |
| `animacy` | `Animacy` | `person` | `Person` |
| `aspect` | `Aspect` | `polarity` | `Polarity` |
| `case` | `Case` | `polite` | `Polite` |
| `definite` | `Definite` | `poss` | `Poss` |
| `degree` | `Degree` | `pron_type` | `PronType` |
| `gender` | `Gender` | `reflex` | `Reflex` |
| `mood` | `Mood` | `tense` | `Tense` |
| `num_type` | `NumType` | `verb_form` | `VerbForm` |
| `number` | `Number` | `voice` | `Voice` |
<!-- --8<-- [end:MorphStats-metrics] -->

## Methods

<!-- --8<-- [start:MorphStats-get_stats] -->
`get_stats(*stats, filter_none=False, flat=False)` gives the number of the words by value of every statistic selected, all of them by default, in the order of the first occurrences; `None` counts the words without the feature, and `filter_none` leaves them out. With `flat` the keys are `statistic_value`, such as `pos_NOUN`, without the words that lack the feature, as in `to_dataframe`. An unknown statistic raises `UnknownStatError`, a `filter_none` or a `flat` that is not a `bool` - `ParameterError`.
<!-- --8<-- [end:MorphStats-get_stats] -->

<!-- --8<-- [start:MorphStats-explain_text] -->
`explain_text(*stats, filter_none=False)` gives every word with the values of the statistics selected; `filter_none` leaves out those a word lacks. An unknown statistic raises `UnknownStatError`.
<!-- --8<-- [end:MorphStats-explain_text] -->

<!-- --8<-- [start:MorphStats-print_stats] -->
`print_stats(*stats, filter_none=False)` prints a table for every statistic selected: the descriptions of its values from the most frequent, with the number of the words. A value of several joins the descriptions of its parts with a slash. An unknown statistic raises `UnknownStatError`.
<!-- --8<-- [end:MorphStats-print_stats] -->

=== "Code"

    ``` python
    stats.get_stats("number", "tense", filter_none=True)
    stats.get_stats("tense", flat=True)
    stats.explain_text("pos", "tense", filter_none=True)[:3]
    stats.print_stats("tense", "pron_type")
    ```

=== "Result"

    ```
    {'number': {'Plur': 2}, 'tense': {'Past': 1, 'Pres': 1}}
    {'tense_Past': 1, 'tense_Pres': 1}
    (('The', {'pos': 'DET'}), ('cats', {'pos': 'NOUN'}), ('slept', {'pos': 'VERB', 'tense': 'Past'}))
    -----------------Tense------------------
    Unknown                       |    4
    Past                          |    1
    Present                       |    1

    --------------Pronoun type--------------
    Unknown                       |    4
    Article                       |    1
    Personal                      |    1
    ```

<!-- --8<-- [start:MorphStats-markers] -->
`get_markers()` gives the markers of a language computed from the features - shares of grammatical forms, each of its own base - by the names of `markers_desc`, and `print_markers()` prints them with their descriptions. A library computes them; there are none by default.
<!-- --8<-- [end:MorphStats-markers] -->

The other methods - `to_dataframe` and `describe` - are those of the [statistics interface](stats.md); the morphological statistics have no scales.

## For library developers { #hooks }

<details class="library-hooks" markdown>
<summary>Language hooks of a subclass</summary>

<!-- --8<-- [start:MorphStats-hooks] -->
A language library subclasses `MorphStats`. By default the words and their features are read from a `Doc` by Universal Dependencies:

| Hook | Kind | Description |
| :--- | :--- | :---------- |
| `analyze(source)` | method | Words of a source as `MorphWord`: the word, its part of speech and its features of Universal Dependencies by name; by default those of a `Doc` with the parts of speech (`iter_doc_tokens`), with `token.pos_` and `token.morph`; a library that reads a string or a `Doc` without them overrides it |
| `feature_names` | class attribute | Feature of Universal Dependencies by statistic, `MORPH_FEATURES` by default; a statistic is an identifier other than `pos`, `tags`, `words` and the names of the class, since it becomes an attribute of the object |
| `stats_desc` | class attribute | `pos` and the statistics of `feature_names` with their names, in the order of `get_stats`; `MORPH_STATS_DESC` by default |
| `values_desc` | class attribute | Descriptions of the values by statistic for `print_stats`, `MORPH_VALUES_DESC` by default; a value without one is printed as it is |
| `unknown_value` | class attribute | Description of the words without the feature in `print_stats`, `"Unknown"` by default |
| `get_markers()` | method | Markers of the language computed from the statistics; none by default |
| `markers_desc`, `markers_headers` | class attributes | Markers of `get_markers` with their descriptions, headers of the columns for `print_markers` |
| `messages` | class attribute | Messages of the errors by key; `MESSAGES` by default |

The parameters of a library - its model of a string, its word extractor - go to the constructor of its subclass, which keeps them for its `analyze`. When a class is defined, a `feature_names` that is not a mapping of such statistics to the names of features, a `stats_desc` that does not name `pos` and the statistics of `feature_names`, and a `values_desc` that is not a mapping of statistics to mappings of strings raise `ParameterError`; an `analyze` that does not give `MorphWord` objects of a string, a string or `None` and a mapping of strings, and a `get_markers` that gives no value of a marker of `markers_desc` to `print_markers`, raise `SourceTypeError`.
<!-- --8<-- [end:MorphStats-hooks] -->

</details>

<!-- --8<-- [start:MorphWord] -->
`MorphWord` is a word of `analyze`: its text `word`, its part of speech `pos` (`None` when unknown) and its features `features` - the values of the features of Universal Dependencies by their names (`{"Case": "Nom"}`), a value of several joined by commas.
<!-- --8<-- [end:MorphWord] -->
