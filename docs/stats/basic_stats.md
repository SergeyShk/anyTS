# Basic statistics

``` {.python .signature}
BasicStats(source, sents_extractor=None, words_extractor=None, normalize=False, complex_syl_factor=3, long_word_letter_factor=7)
```

<!-- --8<-- [start:BasicStats] -->
The basic statistics of a text: the counts of its sentences, words, characters, syllables and punctuation marks and the distributions of its words. The data source is a text or a `Doc` object of [spaCy](https://github.com/explosion/spaCy). Letters are counted by `str.isalpha`, so digits, hyphens and marks inside a word are not letters.

The words and the sentences of a string come from the extractors. A `Doc` gives its tokens as words, without punctuation marks and symbols such as `€` or `%`, and its boundaries as sentences, or those of the sentence extractor when it has none or only partial ones (`has_sents`); an extractor given is used on its text instead. A blank line ends a sentence of a string and of a `Doc` without boundaries; a `Doc` with boundaries does so when its pipeline has `start_sents_after_blank_lines` (registered by a language library under its own name) before the parser, `senter` or `sentencizer`. A sentence without words, such as punctuation alone, is not counted.

Raises:

- `SourceTypeError` - a source that is neither a string nor a `Doc`, an extractor of another type;
- `SourceError` - a source without words;
- `ParameterError` - a threshold that is not an integer of at least one, a `normalize` that is not a `bool`.
<!-- --8<-- [end:BasicStats] -->

A subclass with the syllables of a language - here the groups of vowels, a rough rule for English.

=== "Code"

    ``` python
    import re

    from anyts.basic_stats import BasicStats


    class Stats(BasicStats):
        def count_syllables(self, word):
            return len(re.findall(r"[aeiouy]+", word, re.IGNORECASE))


    bs = Stats("The cat sat on the mat. A beautiful day!")
    bs.print_stats()
    ```

=== "Result"

    ```
                       Statistic                    |  Value
    -----------------------------------------------------------
    Sentences                                       |    2
    Words                                           |    9
    Unique words                                    |    8
    Long words                                      |    1
    Complex words                                   |    1
    Simple words                                    |    8
    Monosyllabic words                              |    8
    Polysyllabic words                              |    1
    Characters                                      |    40
    Letters                                         |    30
    Spaces                                          |    8
    Syllables                                       |    11
    Punctuation marks                               |    2
    Entropy of the word lengths in letters (bits)   |   1.45
    Entropy of the word lengths in syllables (bits) |   0.50
    ```

## Parameters

<!-- --8<-- [start:BasicStats-parameters] -->
| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `source` | `str` / `Doc` | - | Data source (a string or a Doc object) |
| `sents_extractor` | `SentsExtractor` | `None` | Sentence extraction tool; used for a Doc too, on its text |
| `words_extractor` | `WordsExtractor` | `None` | Word extraction tool; used for a Doc too, on its text |
| `normalize` | `bool` | `False` | Compute normalized statistics |
| `complex_syl_factor` | `int` | `COMPLEX_SYL_FACTOR` | Minimum number of syllables in a complex word |
| `long_word_letter_factor` | `int` | `LONG_WORD_LETTER_FACTOR` | Minimum number of letters in a long word |

The object keeps `normalize`, `complex_syl_factor` and `long_word_letter_factor` under their names.
<!-- --8<-- [end:BasicStats-parameters] -->

The thresholds of the core are `COMPLEX_SYL_FACTOR = 3` and `LONG_WORD_LETTER_FACTOR = 7` of `anyts.constants`.

## Statistics

<!-- --8<-- [start:BasicStats-attributes] -->
| Statistic | Type | Description | Normalized |
| :-------- | :--- | :---------- | :--------- |
| `c_letters` | `dict[int, int]` | Distribution of words by number of letters | - |
| `c_syllables` | `dict[int, int]` | Distribution of words by number of syllables | - |
| `n_sents` | `int` | Number of sentences containing words | - |
| `n_words` | `int` | Number of words | - |
| `n_unique_words` | `int` | Number of unique words, case ignored | `p_unique_words` |
| `n_long_words` | `int` | Number of long words, of at least `long_word_letter_factor` letters | `p_long_words` |
| `n_complex_words` | `int` | Number of complex words, of at least `complex_syl_factor` syllables | `p_complex_words` |
| `n_simple_words` | `int` | Number of simple words: with a syllable, below the complex ones | `p_simple_words` |
| `n_monosyllable_words` | `int` | Number of monosyllabic words | `p_monosyllable_words` |
| `n_polysyllable_words` | `int` | Number of polysyllabic words, of two syllables or more | `p_polysyllable_words` |
| `n_chars` | `int` | Number of characters without the line breaks | - |
| `n_letters` | `int` | Number of letters | `p_letters` |
| `n_spaces` | `int` | Number of spaces of Unicode (category Zs), such as the no-break space, and tabs | `p_spaces` |
| `n_syllables` | `int` | Number of syllables | - |
| `n_punctuations` | `int` | Number of punctuation marks | `p_punctuations` |
| `letters_entropy` | `float` | Shannon entropy in bits of the word lengths in letters, of `c_letters`: 0 when the words have one length | - |
| `syllables_entropy` | `float` | Shannon entropy in bits of the word lengths in syllables, of `c_syllables` | - |
| `c_punctuations` | `dict[str, int]` | Distribution of punctuation marks by type ([`count_punctuations`](#count_punctuations)) | - |

With `normalize=True` the object has the normalized statistics too, of the type `float`: the counts of the words divided by the number of words, those of the characters by the number of characters.
<!-- --8<-- [end:BasicStats-attributes] -->

## Methods

<!-- --8<-- [start:BasicStats-count_words_by] -->
`count_words_by_syllables(min_syllables)` and `count_words_by_letters(min_letters)` return the number of words with at least the given number of syllables or letters; a minimum that is not an integer raises `ParameterError`.
<!-- --8<-- [end:BasicStats-count_words_by] -->

<!-- --8<-- [start:BasicStats-get_stats] -->
`get_stats(flat)` returns a dictionary with the distributions `c_letters` and `c_syllables`, the statistics of `stats_desc`, the distribution `c_punctuations` and, with `normalize=True`, the normalized counts, as a copy: editing it does not change the object. With `flat=True` the distributions give a key for every value the text has, such as `c_letters_3` and `c_punctuations_comma`.
<!-- --8<-- [end:BasicStats-get_stats] -->

<!-- --8<-- [start:BasicStats-print_stats] -->
`print_stats()` prints a table with the statistics of `stats_desc`, their descriptions and the headers from `stats_headers`.
<!-- --8<-- [end:BasicStats-print_stats] -->

=== "Code"

    ``` python
    bs.count_words_by_syllables(2), bs.count_words_by_letters(4)
    bs.get_stats()["c_letters"]
    ```

=== "Result"

    ```
    (1, 1)
    {1: 1, 2: 1, 3: 6, 9: 1}
    ```

The frame of the statistics (`to_dataframe`) and their reading (`describe`) are those of the [statistics interface](stats.md).

## Punctuation marks { #count_punctuations }

<!-- --8<-- [start:count_punctuations] -->
``` {.python .signature}
count_punctuations(text, marks=PUNCTUATION_MARKS, dash_pattern=DASH_PATTERN)
```

Counts punctuation marks by type, the distribution of `c_punctuations`: commas, periods, question and exclamation marks, ellipses, colons, semicolons, dashes, hyphens, guillemets, quotation marks, parentheses and other marks. Dashes typed with hyphens (`dash_pattern`) are counted first, then ellipses - `…`, three or more periods, or two after `?` and `!`, one mark whose periods are not counted as periods (`Who?..` is a question and an ellipsis) - then each mark by its type in `marks`; any other character of the Unicode categories P and S is another mark (`§`, `€`, `°`).

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `text` | `str` | - | Text string |
| `marks` | `dict[str, str]` | `PUNCTUATION_MARKS` | Type of every mark, among `PUNCTUATION_TYPES` |
| `dash_pattern` | `Pattern` | `DASH_PATTERN` | Dashes typed with hyphens |

A mark of `marks` that is not a single character or has an unknown type raises `ParameterError`; a text that is not a string, `marks` that are not a mapping and a `dash_pattern` that is not a compiled regular expression raise `SourceTypeError`.
<!-- --8<-- [end:count_punctuations] -->

In the core the types are `anyts.constants.PUNCTUATION_TYPES`, and `marks` and `dash_pattern` are `PUNCTUATION_MARKS` and `DASH_PATTERN` of `anyts.basic_stats`. The marks count `¿` and `¡` as question and exclamation marks (`¿So?` has two), `—`, `–` and the horizontal bar `―` as dashes, `«»` as guillemets and `"“”‘’` as quotation marks; a hyphen inside a word, before a digit or at a line break inside a word is a hyphen (`well-known`, `-5`). A dash typed with hyphens is a run of two or more hyphens, or a hyphen after whitespace, a closing mark or at the start of a line, before a space of a line (a Unicode separator such as the no-break space, or a tab: `SPACES`) or the end of the text, or between a letter and an opening or a closing mark (`--Hello --said John`, `- They left - he said`).

=== "Code"

    ``` python
    from anyts.basic_stats import count_punctuations

    counts = count_punctuations('"Well..." - he said - "a well-known cat?!"')
    {kind: count for kind, count in counts.items() if count}
    ```

=== "Result"

    ```
    {'question': 1, 'exclamation': 1, 'ellipsis': 1, 'dash': 2, 'hyphen': 1, 'straight_quotes': 4}
    ```

## Dashes typed with hyphens { #dash_pattern }

<!-- --8<-- [start:dash_pattern] -->
``` {.python .signature}
dash_pattern(conjunctions=(), hanging_before_comma=False)
```

Builds the `dash_pattern` of `count_punctuations`. A hanging hyphen glued to a letter or a digit and carried on to a later word (`pre- and post-war`, `5- and 10-year`) stays a hyphen before spaces of a line and one of the `conjunctions`, case ignored, and with `hanging_before_comma` before a comma (`two-, three- and four-year`). A language whose dialogue closes a line with a hyphen before a comma (`-Come -he said-, and left`) leaves `hanging_before_comma` off. Without the parameters the pattern is `DASH_PATTERN`.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `conjunctions` | `Collection[str]` | `()` | Conjunctions after a hanging hyphen |
| `hanging_before_comma` | `bool` | `False` | Take a hyphen between a letter and a comma for a hanging one |

Conjunctions that are not a collection of strings raise `SourceTypeError`, and an empty conjunction `ParameterError`.
<!-- --8<-- [end:dash_pattern] -->

=== "Code"

    ``` python
    from anyts.basic_stats import count_punctuations, dash_pattern

    text = "pre- and post-war, two-, three- and four-year - he said"
    counts = count_punctuations(text, dash_pattern=dash_pattern(["and"], hanging_before_comma=True))
    counts["dash"], counts["hyphen"]
    ```

=== "Result"

    ```
    (1, 5)
    ```

## For library developers { #hooks }

<details class="library-hooks" markdown>
<summary>Language hooks of a subclass</summary>

<!-- --8<-- [start:BasicStats-hooks] -->
A language library subclasses `BasicStats`:

| Hook | Kind | Description |
| :--- | :--- | :---------- |
| `count_syllables(word)` | method | The syllables of a word; abstract |
| `sents_extractor_class`, `words_extractor_class` | class attributes | The extractors used when none is given; `SentsExtractor` and `WordsExtractor` by default |
| `join_hyphens` | class attribute | Join the parts of the hyphenated words of a `Doc` (`iter_doc_words`); `False` by default |
| `count_punctuations(text)` | method | The punctuation marks by type; `count_punctuations` of the module by default |
| `stats_desc` | class attribute | The counts of `get_stats` with their descriptions for `print_stats`; `anyts.constants.BASIC_STATS_DESC` by default |

The other hooks, `stats_headers`, `level_scales` and `messages`, come from `Stats`. The thresholds of the complex and the long words are parameters; a library sets its own defaults in its `__init__` and passes them on.
<!-- --8<-- [end:BasicStats-hooks] -->

</details>
