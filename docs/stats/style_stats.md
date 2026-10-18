# Style metrics

!!! info ""
    **anyts.style_stats.StyleStats**

## Description

<!-- --8<-- [start:StyleStats] -->
The style metrics of a text: the SEO metrics of Advego and Text.ru - the classic and the academic nausea, the water content, the spam score, the naturalness by Zipf's law and the keyword density - and the markers of the officialese style: the verbal nouns, the compound prepositions, the parenthetical expressions and the cliches. The services publish no formulas, so the common definitions are taken, as the metric functions give them. The data source is a text or a `Doc` object of [spaCy](https://github.com/explosion/spaCy).

The SEO metrics are counted on the words of the word extractor, in lower case by default, or on the tokens of a `Doc`; an extractor passed explicitly is used on the text of a `Doc`. The markers are counted on the word forms in lower case (`forms`), whatever the extractor.

A source that is neither a string nor a `Doc`, an extractor of another type and a list that is not a list of strings raise `SourceTypeError`, a source without words `SourceError`, a `top_n` that is not an integer of at least one `ParameterError`.
<!-- --8<-- [end:StyleStats] -->

## Language hooks

<!-- --8<-- [start:StyleStats-hooks] -->
A language library subclasses `StyleStats`; by default the hooks know no language, so there are no stopwords, water, markers or verbal nouns:

| Hook | Kind | Description |
| :--: | :--: | :---------: |
| `words_extractor_class` | class attribute | Word extractor of a string and of the forms; `WordsExtractor` by default |
| `join_hyphens` | class attribute | Join the parts of the hyphenated words of a `Doc` |
| `compound_prepositions_list`, `parentheticals_list`, `cliches_list` | class attributes | Compound prepositions, parenthetical expressions and cliches, checked as lists of strings when the class is defined; the parameter `cliches` replaces the last |
| `normalize(word)` | method | Normalized form of a word or a phrase, by which the lists and the keywords are compared; the lower case by default |
| `doc_words(doc)` | method | Words of a `Doc`; the words of `iter_doc_words` in lower case by default |
| `is_stopword(word)` | method | Whether a word is a stopword of the academic nausea, when `nausea_stopwords` is not given |
| `is_water_word(word)` | method | Whether a word is water, when `stopwords` is not given; `is_stopword` by default |
| `is_parenthetical(word)` | method | Whether a word is a parenthetical expression by itself, outside the phrases of `parentheticals_list` |
| `expand_phrases(text, phrases)` | method | Variants of the phrases in the forms of a text (the forms of a verb, contractions), each with its phrase |
| `nouns()` | method | Word forms of the nouns with their lemmas; none by default, so the share of the verbal nouns is `nan` |
| `is_verbal_noun(lemma)` | method | Whether the lemma of a noun is a verbal noun |
| `level_scales` | class attribute | Norms of the services by metric for `describe` |
| `stats_desc`, `stats_headers` | class attributes | Metrics of `get_stats` with their descriptions (`anyts.constants.STYLE_STATS_DESC` by default), headers of the columns for `print_stats` |
| `messages` | class attribute | Messages of the errors by key; `MESSAGES` by default |
<!-- --8<-- [end:StyleStats-hooks] -->

## Parameters

<!-- --8<-- [start:StyleStats-parameters] -->
| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `source` | str/Doc | `-` | Data source |
| `words_extractor` | WordsExtractor | `None` | Word extraction tool; used for a `Doc` too, on its text |
| `stopwords` | list[str] | `None` | Words of water; without them `is_water_word` decides |
| `top_n` | int | `10` | Number of the most frequent words of the academic nausea and the naturalness by Zipf's law (`NAUSEA_TOP_N`) |
| `cliches` | list[str] | `None` | Cliches; `cliches_list` of the class by default |
| `nausea_stopwords` | list[str] | `None` | Stopwords of the academic nausea; without them `is_stopword` decides |

A set of words is taken in sorted order.
<!-- --8<-- [end:StyleStats-parameters] -->

## Attributes

<!-- --8<-- [start:StyleStats-attributes] -->
| Attribute | Type | Description |
| :-------: | :--: | :---------: |
| `words` | tuple[str] | Words of the SEO metrics |
| `forms` | tuple[str] | Word forms in lower case, of the markers |
| `classic_nausea` | float | Classic nausea |
| `academic_nausea` | float | Academic nausea in percent |
| `water` | float | Water content in percent |
| `spam` | float | Spam score in percent |
| `zipf_naturalness` | float | Naturalness by Zipf's law in percent |
| `verbal_nouns` | float | Share of the verbal nouns among the nouns in percent |
| `compound_prepositions` | float | Compound prepositions per 100 words |
| `parentheticals` | float | Parenthetical expressions per 100 words |
| `cliches` | float | Cliches per 100 words |

The metrics are properties computed on each access. A parenthetical expression is a phrase of `parentheticals_list` or a word of `is_parenthetical` outside those phrases; the phrases of the three lists are found with their variants (`expand_phrases`).
<!-- --8<-- [end:StyleStats-attributes] -->

## Methods

### keyword_density, nausea_words

<!-- --8<-- [start:StyleStats-keyword_density] -->
`keyword_density(*keywords)` gives the density of keywords and phrases in percent (`calc_keyword_density` with `normalize` of the class), `nausea_words()` the most frequent significant words of the academic nausea with their occurrences (`find_nausea_words`).
<!-- --8<-- [end:StyleStats-keyword_density] -->

### markers

<!-- --8<-- [start:StyleStats-markers] -->
Returns the markers of the officialese found by metric - `verbal_nouns`, `compound_prepositions`, `parentheticals`, `cliches` - as the forms write them, in the order of the text.
<!-- --8<-- [end:StyleStats-markers] -->

The other methods - `get_stats`, `to_dataframe`, `print_stats` and `describe` - are those of the [statistics interface](stats.md).

## Metric functions

The metrics and their functions are described in the [metric functions](style_stats_funcs.md) section.

## Usage example

!!! example "Example"

    ``` python
    from anyts.style_stats import StyleStats


    class Style(StyleStats):
        cliches_list = ("make a decision",)

        def is_stopword(self, word):
            return word in {"the", "and", "a", "to"}


    style = Style("The board will make a decision and the board will vote")
    style.academic_nausea, style.water, style.cliches
    # (63.63636363636363, 36.36363636363637, 9.090909090909092)
    style.markers()["cliches"]
    # ('make a decision',)
    ```
