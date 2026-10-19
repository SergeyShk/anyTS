# Style metrics

``` {.python .signature}
StyleStats(source, words_extractor=None, stopwords=None, top_n=10, cliches=None, nausea_stopwords=None)
```

<!-- --8<-- [start:StyleStats] -->
The style metrics of a text: the SEO metrics of Advego and Text.ru and the markers of the officialese style. The services publish no formulas, so the common definitions are taken. The data source is a text or a `Doc` object of [spaCy](https://github.com/explosion/spaCy).

The SEO metrics are counted on the words of the word extractor, in lower case by default, or on the tokens of a `Doc`; an extractor passed explicitly is used on the text of a `Doc`. The markers are counted on the word forms in lower case (`forms`), whatever the extractor.

Raises:

- `SourceTypeError` - a source that is neither a string nor a `Doc`, an extractor of another type, a list that is not a list of strings;
- `SourceError` - a source without words;
- `ParameterError` - a `top_n` that is not an integer of at least one.
<!-- --8<-- [end:StyleStats] -->

=== "Code"

    ``` python
    from anyts.style_stats import StyleStats


    class Style(StyleStats):
        cliches_list = ("make a decision",)
        parentheticals_list = ("of course",)

        def is_stopword(self, word):
            return word in {"the", "and", "a", "to", "will", "of"}


    style = Style("Of course the board will make a decision and the board will vote")
    style.print_stats()
    ```

=== "Result"

    ```
                      Metric                  |  Value
    -----------------------------------------------------
    Classic nausea                            |   1.41
    Academic nausea (%)                       |  46.15
    Water content (%)                         |  53.85
    Spam score (%)                            |  23.08
    Naturalness by Zipf's law (%)             |   0.00
    Verbal nouns (% of nouns)                 |   nan
    Compound prepositions (per 100 words)     |   0.00
    Parenthetical expressions (per 100 words) |   7.69
    Officialese cliches (per 100 words)       |   7.69
    ```

## Parameters

<!-- --8<-- [start:StyleStats-parameters] -->
| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `source` | `str` / `Doc` | - | Data source |
| `words_extractor` | `WordsExtractor` | `None` | Word extraction tool; used for a `Doc` too, on its text |
| `stopwords` | `list[str]` | `None` | Words of water; without them `is_water_word` decides |
| `top_n` | `int` | `10` | Number of the most frequent words of the academic nausea and the naturalness by Zipf's law (`NAUSEA_TOP_N`) |
| `cliches` | `list[str]` | `None` | Cliches; `cliches_list` of the class by default |
| `nausea_stopwords` | `list[str]` | `None` | Stopwords of the academic nausea; without them `is_stopword` decides |

A set of words is taken in sorted order.
<!-- --8<-- [end:StyleStats-parameters] -->

## Attributes

<!-- --8<-- [start:StyleStats-attributes] -->
| Attribute | Type | Description |
| :-------- | :--- | :---------- |
| `words` | `tuple[str]` | Words of the SEO metrics |
| `forms` | `tuple[str]` | Word forms in lower case, of the markers |

The metrics are properties computed on each access.
<!-- --8<-- [end:StyleStats-attributes] -->

## Metrics

<!-- --8<-- [start:StyleStats-metrics] -->
`get_stats` gives all the metrics. A metric is computed by the function of its card on `words` or `forms` with the hooks of the class.

| Metric | Measures | Range | Higher means |
| :----- | :------- | :---- | :----------- |
| [`classic_nausea`](#classic_nausea) | Repetition of the most frequent word | 0 and above, grows with the text | One word pressed harder |
| [`academic_nausea`](#academic_nausea) | Share of the most frequent significant words | 0-100 % | A narrower vocabulary |
| [`water`](#water) | Share of the words without content | 0-100 % | Less content per word |
| [`spam`](#spam) | Share of the repeated words | 0-100 % | More repetition |
| [`zipf_naturalness`](#zipf_naturalness) | Agreement of the top frequencies with Zipf's law | 0-100 %, `nan` without ranks to compare | Closer to a natural text |
| [`verbal_nouns`](#verbal_nouns) | Share of the verbal nouns among the nouns | 0-100 %, `nan` without nouns | A more nominal style |
| [`compound_prepositions`](#phrase_density) | Compound prepositions per 100 words | 0-100 | More officialese |
| [`parentheticals`](#parentheticals) | Parenthetical expressions per 100 words | 0-100 | More insertions |
| [`cliches`](#phrase_density) | Cliches per 100 words | 0-100 | More cliches |
<!-- --8<-- [end:StyleStats-metrics] -->

<div class="metric-card" markdown>

### Classic nausea { #classic_nausea }

`classic_nausea` · [Advego](https://advego.com/text/seo/)
{ .metric-meta }

<!-- --8<-- [start:calc_classic_nausea] -->
``` {.python .signature}
calc_classic_nausea(text)
```

How much one word is pressed: the square root of the occurrences $f_1$ of the most frequent word. The value is not corrected for the length of the text, so it grows with the text; no words give 0.

$$
\sqrt{f_1}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
<!-- --8<-- [end:calc_classic_nausea] -->

</div>

<div class="metric-card" markdown>

### Academic nausea { #academic_nausea }

`academic_nausea` · `nausea_words()` · [Advego](https://advego.com/text/seo/)
{ .metric-meta }

<!-- --8<-- [start:calc_academic_nausea] -->
``` {.python .signature}
calc_academic_nausea(text, top_n=10, stopwords=None, *, is_stopword=None, normalize=str.lower, messages=MESSAGES)
```

The share of the occurrences of the `top_n` most frequent significant words among all the words, in percent. Without the stopwords the most frequent words of any text would be its conjunctions and prepositions.

$$
100 \cdot \frac{\sum_{w \in \textrm{top}_n} f_w}{\textrm{Number of words}}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
| `top_n` | `int` | `10` | Number of the most frequent words (`NAUSEA_TOP_N`) |
| `stopwords` | `list[str]` | `None` | Stopwords |
| `is_stopword` | `Callable` | `None` | Whether a word is a stopword, without the list |
| `normalize` | `Callable` | `str.lower` | Normalized form of a word |
| `messages` | `dict[str, str]` | `MESSAGES` | Messages of the errors by key |

A `top_n` that is not an integer of at least one raises `ParameterError`.
<!-- --8<-- [end:calc_academic_nausea] -->

<!-- --8<-- [start:find_nausea_words] -->
``` {.python .signature}
find_nausea_words(text, top_n=10, stopwords=None, *, is_stopword=None, normalize=str.lower, messages=MESSAGES)
```

The words the academic nausea counts, with their occurrences: the most frequent first, words of equal frequency in the order of the text. A stopword is a word of `stopwords` by its normalized form or, without the list, a word `is_stopword` accepts; without both there are no stopwords. The arguments are those of `calc_academic_nausea`.
<!-- --8<-- [end:find_nausea_words] -->

</div>

<div class="metric-card" markdown>

### Water content { #water }

`water` · [Text.ru](https://text.ru/seo)
{ .metric-meta }

<!-- --8<-- [start:calc_water] -->
``` {.python .signature}
calc_water(text, stopwords=None, *, is_water_word=None, normalize=str.lower)
```

The share of the words without content, in percent: the words of `stopwords` by their normalized forms or, without the list, those `is_water_word` accepts.

$$
100 \cdot \frac{\textrm{Number of water words}}{\textrm{Number of words}}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
| `stopwords` | `list[str]` | `None` | Words of water |
| `is_water_word` | `Callable` | `None` | Whether a word is water, without the list |
| `normalize` | `Callable` | `str.lower` | Normalized form of a word |
<!-- --8<-- [end:calc_water] -->

</div>

<div class="metric-card" markdown>

### Spam score { #spam }

`spam` · [Text.ru](https://text.ru/seo)
{ .metric-meta }

<!-- --8<-- [start:calc_spam] -->
``` {.python .signature}
calc_spam(text)
```

The share of the repeated words in percent: every occurrence of a word after the first.

$$
100 \cdot \left(1 - \frac{\textrm{Number of lexemes}}{\textrm{Number of words}}\right)
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
<!-- --8<-- [end:calc_spam] -->

</div>

<div class="metric-card" markdown>

### Naturalness by Zipf's law { #zipf_naturalness }

`zipf_naturalness`
{ .metric-meta }

<!-- --8<-- [start:calc_zipf_naturalness] -->
``` {.python .signature}
calc_zipf_naturalness(text, top_n=10, *, messages=MESSAGES)
```

The agreement of the frequencies of the most frequent words with the ideal distribution $f_r = f_1 / r$, where $r$ is the rank. The first rank is ideal by construction, and above $f_1$ the ideal frequency falls below one, so the ranks run from 2 to $R = \min(\textrm{top\_n}, V, f_1)$. Negative values are cut to 0. Without ranks to compare - all the words hapaxes, one lexeme or `top_n` below 2 - the value is `nan`.

$$
100 \cdot \left(1 - \frac{1}{R - 1} \sum_{r=2}^{R} \frac{|r \cdot f_r - f_1|}{f_1}\right)
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
| `top_n` | `int` | `10` | Number of the most frequent words (`NAUSEA_TOP_N`) |
| `messages` | `dict[str, str]` | `MESSAGES` | Messages of the errors by key |

A `top_n` that is not an integer of at least one raises `ParameterError`.
<!-- --8<-- [end:calc_zipf_naturalness] -->

</div>

<div class="metric-card" markdown>

### Verbal nouns { #verbal_nouns }

`verbal_nouns`
{ .metric-meta }

<!-- --8<-- [start:StyleStats-verbal_nouns] -->
The share of the nouns whose lemma is a verbal noun (`is_verbal_noun`) among the nouns of the hook `nouns`, in percent. Without the hooks of a language there are no nouns, and the value is `nan`.
<!-- --8<-- [end:StyleStats-verbal_nouns] -->

</div>

<div class="metric-card" markdown>

### Compound prepositions and cliches { #phrase_density }

`compound_prepositions` · `cliches`
{ .metric-meta }

<!-- --8<-- [start:calc_phrase_density] -->
``` {.python .signature}
calc_phrase_density(text, phrases, *, expand=None, normalize=str.lower)
```

The occurrences of the phrases of a list (`find_phrases`) per 100 words. The hook `expand` spells the phrases out in the forms of the text - the forms of a verb, contractions - every variant with its phrase. `StyleStats` counts its compound prepositions and cliches this way, on `forms` with `expand_phrases`.

$$
100 \cdot \frac{\textrm{Number of phrases found}}{\textrm{Number of words}}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
| `phrases` | `list[str]` | - | Phrases, words separated by spaces |
| `expand` | `Callable` | `None` | Variants of the phrases in the text, by the words and the phrases |
| `normalize` | `Callable` | `str.lower` | Normalized form of a word |
<!-- --8<-- [end:calc_phrase_density] -->

</div>

<div class="metric-card" markdown>

### Parenthetical expressions { #parentheticals }

`parentheticals`
{ .metric-meta }

<!-- --8<-- [start:find_parentheticals] -->
``` {.python .signature}
find_parentheticals(text, phrases=(), *, is_parenthetical=None, expand=None, normalize=str.lower)
```

The parenthetical expressions of a text: the phrases of the list, spelled out by `expand` as in `calc_phrase_density`, and the single words accepted by `is_parenthetical` outside the phrases found. The result is their bounds as slices of the words, in order. `StyleStats` counts its `parentheticals` and finds their markers this way, with its hooks.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
| `phrases` | `list[str]` | `()` | Parenthetical phrases, words separated by spaces |
| `is_parenthetical` | `Callable[[str], bool]` | `None` | Whether a word is a parenthetical expression by itself; none by default |
| `expand` | `Callable` | `None` | Variants of the phrases in the forms of the text with the phrase of each; the phrases as they are by default |
| `normalize` | `Callable[[str], str]` | `str.lower` | Normalized form of a word and of a phrase |
<!-- --8<-- [end:find_parentheticals] -->

<!-- --8<-- [start:calc_parentheticals] -->
``` {.python .signature}
calc_parentheticals(text, phrases=(), *, is_parenthetical=None, expand=None, normalize=str.lower)
```

The expressions of `find_parentheticals` with the same arguments per 100 words.
<!-- --8<-- [end:calc_parentheticals] -->

</div>

<div class="metric-card" markdown>

### Keyword density { #keyword_density }

`keyword_density(*keywords)` · [Text.ru](https://text.ru/seo)
{ .metric-meta }

<!-- --8<-- [start:calc_keyword_density] -->
``` {.python .signature}
calc_keyword_density(text, keywords, normalize=str.lower)
```

The occurrences of every keyword per 100 words. A keyword of several words separated by spaces is a sequence of words whose occurrences may overlap. The words and the keywords are compared by their normalized forms, and the keywords of a set come in sorted order.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `list[str]` | - | List of words |
| `keywords` | `list[str]` | - | Keywords or phrases |
| `normalize` | `Callable[[str], str]` | `str.lower` | Normalized form of a word and of a keyword |
<!-- --8<-- [end:calc_keyword_density] -->

</div>

The functions check their words: words, stopwords, keywords and phrases that are not a list of strings, and hooks that cannot be called, raise `SourceTypeError`.

## Methods

<!-- --8<-- [start:StyleStats-keyword_density] -->
`keyword_density(*keywords)` gives the density of keywords and phrases in percent (`calc_keyword_density` with `normalize` of the class), `nausea_words()` the most frequent significant words of the academic nausea with their occurrences (`find_nausea_words`).
<!-- --8<-- [end:StyleStats-keyword_density] -->

<!-- --8<-- [start:StyleStats-markers] -->
`markers()` returns the markers of the officialese found by metric - `verbal_nouns`, `compound_prepositions`, `parentheticals`, `cliches` - as the forms write them, in the order of the text.
<!-- --8<-- [end:StyleStats-markers] -->

=== "Code"

    ``` python
    style.markers()
    style.keyword_density("board")
    ```

=== "Result"

    ```
    {'verbal_nouns': (), 'compound_prepositions': (), 'parentheticals': ('of course',), 'cliches': ('make a decision',)}
    {'board': 15.384615384615385}
    ```

The other methods - `get_stats`, `to_dataframe`, `print_stats` and `describe` - are those of the [statistics interface](stats.md).

## For library developers { #hooks }

<details class="library-hooks" markdown>
<summary>Language hooks of a subclass</summary>

<!-- --8<-- [start:StyleStats-hooks] -->
A language library subclasses `StyleStats`; by default the hooks know no language, so there are no stopwords, water, markers or verbal nouns:

| Hook | Kind | Description |
| :--- | :--- | :---------- |
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

<!-- --8<-- [start:StyleStats-check_params] -->
``` {.python .signature}
check_params(top_n, *, messages=MESSAGES)
```

Checks the number of the most frequent words: one that is not an integer of at least one raises `ParameterError`.
<!-- --8<-- [end:StyleStats-check_params] -->

</details>
