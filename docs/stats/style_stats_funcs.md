# Metric functions

The services publish no formulas, so the common definitions are taken. The language - the stopwords, the water, the normalized form of a word, the spelling of phrases - comes through the keyword parameters; words, stopwords, keywords and phrases that are not a list of strings and hooks that cannot be called raise `SourceTypeError`.

## Classic nausea

!!! info ""
    **anyts.style_stats.calc_classic_nausea()**

<!-- --8<-- [start:calc_classic_nausea] -->
Computation of the classic nausea (Advego): how much one word is pressed. Not corrected for text length, it grows with the text; no words give 0.

Formula:

$$
\sqrt{f_1}
$$

where $f_1$ is the number of occurrences of the most frequent word.

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
<!-- --8<-- [end:calc_classic_nausea] -->

## Words of the academic nausea

!!! info ""
    **anyts.style_stats.find_nausea_words()**

<!-- --8<-- [start:find_nausea_words] -->
The `top_n` most frequent words without the stopwords, with their occurrences: the most frequent first, words of equal frequency in the order of the text. A stopword is a word of `stopwords` by its normalized form or, without the list, a word `is_stopword` accepts; without both there are no stopwords.

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
| `top_n` | int | `10` | Number of the most frequent words (`NAUSEA_TOP_N`) |
| `stopwords` | list[str] | `None` | Stopwords |
| `is_stopword` | Callable | `None` | Whether a word is a stopword, without the list |
| `normalize` | Callable | `str.lower` | Normalized form of a word |
| `messages` | dict[str, str] | `MESSAGES` | Messages of the errors by key |

A `top_n` that is not an integer of at least one raises `ParameterError`.
<!-- --8<-- [end:find_nausea_words] -->

## Academic nausea

!!! info ""
    **anyts.style_stats.calc_academic_nausea()**

<!-- --8<-- [start:calc_academic_nausea] -->
Computation of the academic nausea (Advego): the share of the occurrences of the most frequent significant words (`find_nausea_words`) among all the words, in percent. With the stopwords, the most frequent words of any text would be its conjunctions and prepositions.

Formula:

$$
100 \cdot \frac{\sum_{w \in \textrm{top}_n} f_w}{\textrm{Number of words}}
$$

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
| `top_n` | int | `10` | Number of the most frequent words (`NAUSEA_TOP_N`) |
| `stopwords` | list[str] | `None` | Stopwords |
| `is_stopword` | Callable | `None` | Whether a word is a stopword, without the list |
| `normalize` | Callable | `str.lower` | Normalized form of a word |
| `messages` | dict[str, str] | `MESSAGES` | Messages of the errors by key |

A `top_n` that is not an integer of at least one raises `ParameterError`.
<!-- --8<-- [end:calc_academic_nausea] -->

## Water content

!!! info ""
    **anyts.style_stats.calc_water()**

<!-- --8<-- [start:calc_water] -->
Computation of the water content (Text.ru): the share of the words without content, in percent - the words of `stopwords` by their normalized forms or, without the list, those `is_water_word` accepts.

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
| `stopwords` | list[str] | `None` | Words of water |
| `is_water_word` | Callable | `None` | Whether a word is water, without the list |
| `normalize` | Callable | `str.lower` | Normalized form of a word |
<!-- --8<-- [end:calc_water] -->

## Spam score

!!! info ""
    **anyts.style_stats.calc_spam()**

<!-- --8<-- [start:calc_spam] -->
Computation of the spam score (Text.ru): the share of the repeated words in percent, every occurrence of a word after the first.

Formula:

$$
100 \cdot \left(1 - \frac{\textrm{Number of lexemes}}{\textrm{Number of words}}\right)
$$

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
<!-- --8<-- [end:calc_spam] -->

## Naturalness by Zipf's law

!!! info ""
    **anyts.style_stats.calc_zipf_naturalness()**

<!-- --8<-- [start:calc_zipf_naturalness] -->
Computation of the naturalness by Zipf's law: the agreement of the frequencies of the most frequent words with the ideal distribution $f_r = f_1 / r$, where $r$ is the rank. The first rank is ideal by construction, and above $f_1$ the ideal frequency falls below one, so the ranks run from 2 to $R = \min(\textrm{top\_n}, V, f_1)$. Negative values are cut to 0; without ranks to compare - all the words hapaxes, one lexeme or `top_n` below 2 - the value is `nan`.

Formula:

$$
100 \cdot \left(1 - \frac{1}{R - 1} \sum_{r=2}^{R} \frac{|r \cdot f_r - f_1|}{f_1}\right)
$$

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
| `top_n` | int | `10` | Number of the most frequent words (`NAUSEA_TOP_N`) |
| `messages` | dict[str, str] | `MESSAGES` | Messages of the errors by key |

A `top_n` that is not an integer of at least one raises `ParameterError`.
<!-- --8<-- [end:calc_zipf_naturalness] -->

## Keyword density

!!! info ""
    **anyts.style_stats.calc_keyword_density()**

<!-- --8<-- [start:calc_keyword_density] -->
Computation of the keyword density (Text.ru): the occurrences of every keyword per 100 words. A keyword of several words separated by spaces is a sequence of words whose occurrences may overlap; the words and the keywords are compared by their normalized forms, and the keywords of a set come in sorted order.

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
| `keywords` | list[str] | `-` | Keywords or phrases |
| `normalize` | Callable[[str], str] | `str.lower` | Normalized form of a word and of a keyword |
<!-- --8<-- [end:calc_keyword_density] -->

## Density of phrases

!!! info ""
    **anyts.style_stats.calc_phrase_density()**

<!-- --8<-- [start:calc_phrase_density] -->
Computation of the density of the phrases of a list: their occurrences (`find_phrases`) per 100 words. The hook `expand` spells the phrases out in the forms of the text - the forms of a verb, contractions - every variant with its phrase; so the style metrics count the compound prepositions and the cliches.

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
| `phrases` | list[str] | `-` | Phrases, words separated by spaces |
| `expand` | Callable | `None` | Variants of the phrases in the text, by the words and the phrases |
| `normalize` | Callable | `str.lower` | Normalized form of a word |
<!-- --8<-- [end:calc_phrase_density] -->

## Parenthetical expressions { #parentheticals }

!!! info ""
    **anyts.style_stats.find_parentheticals()**, **anyts.style_stats.calc_parentheticals()**

<!-- --8<-- [start:find_parentheticals] -->
`find_parentheticals(text, phrases=(), *, is_parenthetical=None, expand=None, normalize=str.lower)` finds the parenthetical expressions of a text: the phrases of the list, spelled out by `expand` as in `calc_phrase_density`, and the single words accepted by `is_parenthetical` outside the phrases found. It returns their bounds as slices of the words, in order. `StyleStats` counts its `parentheticals` and finds their markers this way, with its hooks. Hooks that are not callable raise `SourceTypeError`.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `text` | list[str] | `-` | List of words |
| `phrases` | list[str] | `()` | Parenthetical phrases, words separated by spaces |
| `is_parenthetical` | Callable[[str], bool] | `None` | Whether a word is a parenthetical expression by itself; none by default |
| `expand` | Callable | `None` | Variants of the phrases in the forms of the text with the phrase of each; the phrases as they are by default |
| `normalize` | Callable[[str], str] | `str.lower` | Normalized form of a word and of a phrase |
<!-- --8<-- [end:find_parentheticals] -->

<!-- --8<-- [start:calc_parentheticals] -->
`calc_parentheticals(text, phrases=(), *, is_parenthetical=None, expand=None, normalize=str.lower)` gives the expressions of `find_parentheticals` with the same arguments per 100 words.
<!-- --8<-- [end:calc_parentheticals] -->

## Parameters of the metrics { #check_params }

!!! info ""
    **anyts.style_stats.check_params()**

<!-- --8<-- [start:StyleStats-check_params] -->
`check_params(top_n, *, messages)` checks the number of the most frequent words: one that is not an integer of at least one raises `ParameterError`.
<!-- --8<-- [end:StyleStats-check_params] -->


!!! example "Example"

    ``` python
    from anyts.style_stats import calc_academic_nausea, calc_keyword_density, calc_zipf_naturalness

    words = "the cat and the dog and the cat ran".split()
    calc_academic_nausea(words, top_n=2, stopwords={"the", "and"})
    # 33.333333333333336
    calc_zipf_naturalness(["a", "a", "a", "a", "b"])
    # 50.0
    calc_keyword_density(words, ["the cat"])
    # {'the cat': 22.22222222222222}
    ```
