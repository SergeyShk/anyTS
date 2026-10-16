# Style metrics

!!! info ""
    **anyts.style_stats.StyleStats**

## Description

<!-- --8<-- [start:StyleStats] -->
The style metrics of a text: the SEO metrics of the services Advego and Text.ru - the classic and the academic nausea, the water content, the spam score, the naturalness by Zipf's law and the density of keywords - and the markers of the officialese style: the verbal nouns, the compound prepositions, the parenthetical expressions and the cliches. The services do not publish their formulas, so the common definitions are taken; they are given in the functions below. The data source can be a text or a `Doc` object of [spaCy](https://github.com/explosion/spaCy).

The words of a string come from the word extractor, in lower case by default; the words of a `Doc` come from its tokens, and an extractor passed explicitly is used on the text of a `Doc`. The SEO metrics are counted on these words; the markers on the word forms in lower case (`forms`), whatever the extractor.

A source that is neither a string nor a `Doc`, an extractor of another type and a list that is not a list of strings raise `SourceTypeError`, a source without words `SourceError`, a `top_n` that is not an integer of at least one `ParameterError`.
<!-- --8<-- [end:StyleStats] -->

## Language hooks

<!-- --8<-- [start:StyleStats-hooks] -->
A language library subclasses `StyleStats`; by default the hooks know no language, so the stopwords, the water, the markers and the verbal nouns are empty:

| Hook | Kind | Description |
| :--: | :--: | :---------: |
| `words_extractor_class` | class attribute | Word extractor of a string and of the forms; `WordsExtractor` by default |
| `join_hyphens` | class attribute | Join the parts of the hyphenated words of a `Doc` |
| `compound_prepositions_list`, `parentheticals_list`, `cliches_list` | class attributes | Compound prepositions, parenthetical expressions and cliches; the parameter `cliches` takes the place of the last |
| `normalize(word)` | method | Normalized form of a word or a phrase, by which the lists are compared; the lower case by default |
| `doc_words(doc)` | method | Words of a `Doc`; the words of `iter_doc_words` in lower case by default |
| `is_stopword(word)` | method | Whether a word is a stopword of the academic nausea, when `nausea_stopwords` is not given |
| `is_water_word(word)` | method | Whether a word is water, when `stopwords` is not given; `is_stopword` by default |
| `is_parenthetical(word)` | method | Whether a word is a parenthetical expression by itself, outside the phrases of `parentheticals_list` |
| `expand_phrases(text, phrases)` | method | Variants of the phrases in the forms of a text (the forms of a verb, contractions), each with its phrase |
| `nouns()` | method | Word forms of the nouns of the text with their lemmas; none by default, so the share of the verbal nouns is `nan` |
| `is_verbal_noun(lemma)` | method | Whether the lemma of a noun is a verbal noun |
| `level_scales` | class attribute | Norms of the services by metric for `describe` |
| `messages` | class attribute | Messages of the errors by key; `MESSAGES` by default |
<!-- --8<-- [end:StyleStats-hooks] -->

## Parameters

<!-- --8<-- [start:StyleStats-parameters] -->
| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `source` | str/Doc | `-` | Data source |
| `words_extractor` | WordsExtractor | `None` | Word extraction tool; used for a `Doc` too, on its text |
| `stopwords` | list[str] | `None` | Words of water; without them `is_water_word` decides |
| `top_n` | int | `10` | Number of the most frequent words of the academic nausea and the naturalness by Zipf's law |
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

The metrics are properties computed on each access. A parenthetical expression is a phrase of `parentheticals_list` or a word of `is_parenthetical` outside those phrases; the phrases of the three lists are found with the variants of `expand_phrases`.
<!-- --8<-- [end:StyleStats-attributes] -->

## Methods

### keyword_density, nausea_words

<!-- --8<-- [start:StyleStats-keyword_density] -->
`keyword_density(*keywords)` gives the density of keywords and phrases in percent (`calc_keyword_density`), `nausea_words()` the most frequent significant words of the academic nausea with their occurrences (`find_nausea_words`).
<!-- --8<-- [end:StyleStats-keyword_density] -->

### markers

<!-- --8<-- [start:StyleStats-markers] -->
Returns the markers of the officialese found in the text by metric - `verbal_nouns`, `compound_prepositions`, `parentheticals`, `cliches` - as the forms write them, in the order of the text.
<!-- --8<-- [end:StyleStats-markers] -->

The other methods - `get_stats`, `to_dataframe`, `print_stats` and `describe` - are those of the [statistics interface](stats.md).

## Metric functions

### Nausea { #calc_classic_nausea }

<!-- --8<-- [start:calc_classic_nausea] -->
`calc_classic_nausea(text)` - the square root of the occurrences of the most frequent word (Advego); it grows with the text, and a text without words gives 0.
<!-- --8<-- [end:calc_classic_nausea] -->

<!-- --8<-- [start:find_nausea_words] -->
`find_nausea_words(text, top_n, stopwords, *, is_stopword, normalize, messages)` - the `top_n` most frequent words without the stopwords with their occurrences, the most frequent first and words of equal frequency in the order of the text. A stopword is a word of the list `stopwords` by its normalized form, or without the list one the predicate `is_stopword` of a language accepts; without both no word is a stopword.
<!-- --8<-- [end:find_nausea_words] -->

<!-- --8<-- [start:calc_academic_nausea] -->
`calc_academic_nausea(text, top_n, stopwords, *, is_stopword, normalize, messages)` - the occurrences of the words of `find_nausea_words` divided by the number of all the words, in percent (Advego). With the stopwords counted, the most frequent words of any text are its conjunctions and prepositions.
<!-- --8<-- [end:calc_academic_nausea] -->

### Water and spam { #calc_water }

<!-- --8<-- [start:calc_water] -->
`calc_water(text, stopwords, *, is_water_word, normalize)` - the share of the words that carry no content in percent (Text.ru): the words of the list `stopwords` by their normalized forms, or without the list those the predicate `is_water_word` of a language accepts.
<!-- --8<-- [end:calc_water] -->

<!-- --8<-- [start:calc_spam] -->
`calc_spam(text)` - the share of the repeated words in percent (Text.ru), every occurrence of a word after the first: `100 * (1 - TTR)`.
<!-- --8<-- [end:calc_spam] -->

### Naturalness by Zipf's law { #calc_zipf_naturalness }

<!-- --8<-- [start:calc_zipf_naturalness] -->
`calc_zipf_naturalness(text, top_n, *, messages)` - the agreement of the frequencies of the most frequent words with the ideal distribution `f_r = f_1 / r`: `100 * (1 -` the mean relative deviation of the frequencies from the ideal ones`)` over the ranks from 2 to `min(top_n, V, f_1)`, since the first rank is ideal by construction and above `f_1` the ideal frequency falls below one. Negative values are cut to 0; without ranks to compare - all the words hapaxes, one lexeme or `top_n` below 2 - the value is `nan`.
<!-- --8<-- [end:calc_zipf_naturalness] -->

### Keywords and phrases { #calc_keyword_density }

<!-- --8<-- [start:calc_keyword_density] -->
`calc_keyword_density(text, keywords)` - the frequency of every keyword per 100 words (Text.ru). A keyword of several words is looked for as a sequence of words, its occurrences may overlap, and the words are compared in any case; the keywords of a set come in sorted order.
<!-- --8<-- [end:calc_keyword_density] -->

<!-- --8<-- [start:calc_phrase_density] -->
`calc_phrase_density(text, phrases, *, expand, normalize)` - the occurrences of the phrases (`find_phrases`) per 100 words; the hook `expand` of a language spells the phrases out in the forms of the text, each variant with its phrase.
<!-- --8<-- [end:calc_phrase_density] -->

### Parameters { #check_params }

<!-- --8<-- [start:StyleStats-check_params] -->
`check_params(top_n, *, messages)` checks the number of the most frequent words, `ParameterError` for one that is not an integer of at least one.
<!-- --8<-- [end:StyleStats-check_params] -->

<!-- --8<-- [start:in_order] -->
`in_order(words)` - the words of a list in their order, of a set or a mapping in sorted order.
<!-- --8<-- [end:in_order] -->

Words, stopwords, keywords and phrases that are not a list of strings raise `SourceTypeError` in every function.

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
