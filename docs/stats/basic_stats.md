# Basic statistics

!!! info ""
    **anyts.basic_stats.BasicStats**, **anyts.basic_stats.count_punctuations()**

## Description

<!-- --8<-- [start:BasicStats] -->
The basic statistics of a text: the counts of its sentences, words, characters, letters, spaces, syllables and punctuation marks, the distributions of the words by letters and by syllables, and the long, complex, simple, monosyllabic and polysyllabic words. The data source can be either a text or a `Doc` object of [spaCy](https://github.com/explosion/spaCy). Letters are counted by `str.isalpha`, so digits, hyphens and marks inside a word are not letters.

The words of a string come from the word extractor and its sentences from the sentence extractor. The words of a `Doc` come from its tokens (punctuation marks and symbols such as `€` or `%` dropped) and its sentences from its boundaries, or from the sentence extractor when it has none; an extractor passed explicitly is used on the text of the `Doc`. A sentence of punctuation alone holds no word and is not counted.
<!-- --8<-- [end:BasicStats] -->

## Language hooks

<!-- --8<-- [start:BasicStats-hooks] -->
A language library subclasses `BasicStats`:

| Hook | Kind | Description |
| :--: | :--: | :---------: |
| `count_syllables(word)` | method | The syllables of a word; an abstract method, since syllables depend on the language |
| `sents_extractor_class`, `words_extractor_class` | class attributes | The extractors used when none is given; `SentsExtractor` and `WordsExtractor` of the core by default |
| `join_hyphens` | class attribute | Join the parts of the hyphenated words of a `Doc` (`iter_doc_words`); `False` by default |
| `count_punctuations(text)` | method | The punctuation marks by type; `count_punctuations` of the module by default |
| `stats_desc`, `stats_headers` | class attributes | The descriptions of the statistics and the headers of the columns for `print_stats` |

The thresholds of the complex and the long words are parameters; a library sets its own defaults in its `__init__` and passes them on.
<!-- --8<-- [end:BasicStats-hooks] -->

## Parameters

<!-- --8<-- [start:BasicStats-parameters] -->
| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `source` | str/Doc | `-` | Data source (a string or a Doc object) |
| `sents_extractor` | SentsExtractor | `None` | Sentence extraction tool; used for a Doc too, on its text |
| `words_extractor` | WordsExtractor | `None` | Word extraction tool; used for a Doc too, on its text |
| `normalize` | bool | `False` | Compute normalized statistics |
| `complex_syl_factor` | int | `COMPLEX_SYL_FACTOR` | Minimum number of syllables in a complex word |
| `long_word_letter_factor` | int | `LONG_WORD_LETTER_FACTOR` | Minimum number of letters in a long word |

A source that is neither a string nor a `Doc` and an extractor of another type raise `SourceTypeError`, a source without words `SourceError`, a threshold that is not an integer of at least one `ParameterError`.
<!-- --8<-- [end:BasicStats-parameters] -->

The thresholds of the core are `COMPLEX_SYL_FACTOR = 3` and `LONG_WORD_LETTER_FACTOR = 7` of `anyts.constants`.

## Attributes

<!-- --8<-- [start:BasicStats-attributes] -->
| Attribute | Type | Description |
| :-------: | :--: | :---------: |
| `c_letters` | dict[int, int] | Distribution of words by number of letters |
| `c_syllables` | dict[int, int] | Distribution of words by number of syllables |
| `n_sents` | int | Number of sentences containing words |
| `n_words` | int | Number of words |
| `n_unique_words` | int | Number of unique words, case ignored |
| `n_long_words` | int | Number of long words |
| `n_complex_words` | int | Number of complex words |
| `n_simple_words` | int | Number of simple words: with a syllable, below the complex ones |
| `n_monosyllable_words` | int | Number of monosyllabic words |
| `n_polysyllable_words` | int | Number of polysyllabic words |
| `n_chars` | int | Number of characters without the line breaks |
| `n_letters` | int | Number of letters |
| `n_spaces` | int | Number of spaces and tabs |
| `n_syllables` | int | Number of syllables |
| `n_punctuations` | int | Number of punctuation marks |
| `c_punctuations` | dict[str, int] | Distribution of punctuation marks by type |
| `p_unique_words` | float | Normalized number of unique words |
| `p_long_words` | float | Normalized number of long words |
| `p_complex_words` | float | Normalized number of complex words |
| `p_simple_words` | float | Normalized number of simple words |
| `p_monosyllable_words` | float | Normalized number of monosyllabic words |
| `p_polysyllable_words` | float | Normalized number of polysyllabic words |
| `p_letters` | float | Normalized number of letters |
| `p_spaces` | float | Normalized number of spaces |
| `p_punctuations` | float | Normalized number of punctuation marks |

The counts of the words are normalized by the number of words, those of the characters by the number of characters; the normalized statistics are computed with `normalize=True`.
<!-- --8<-- [end:BasicStats-attributes] -->

## Methods

### count_words_by_syllables, count_words_by_letters

<!-- --8<-- [start:BasicStats-count_words_by] -->
`count_words_by_syllables(min_syllables)` and `count_words_by_letters(min_letters)` return the number of words with at least the given number of syllables or letters; a minimum that is not an integer raises `ParameterError`.
<!-- --8<-- [end:BasicStats-count_words_by] -->

### get_stats

<!-- --8<-- [start:BasicStats-get_stats] -->
Returns a dictionary with the computed statistics - a copy: editing it does not change the object.
<!-- --8<-- [end:BasicStats-get_stats] -->

### print_stats

<!-- --8<-- [start:BasicStats-print_stats] -->
Prints a table with the counts of the statistics, their descriptions from `stats_desc` and the headers from `stats_headers`.
<!-- --8<-- [end:BasicStats-print_stats] -->

## Punctuation marks { #count_punctuations }

<!-- --8<-- [start:count_punctuations] -->
`count_punctuations(text, marks=PUNCTUATION_MARKS, dash_pattern=DASH_PATTERN)` counts punctuation marks by the types of `anyts.constants.PUNCTUATION_TYPES` - the same distribution lives in the `c_punctuations` attribute: commas, periods, question and exclamation marks (the inverted `¿` and `¡` included, so `¿So?` carries two question marks), ellipses (the `…` character, three or more periods, or two periods after `?` and `!` - one mark whose periods do not count as periods: `Who?..` is a question and an ellipsis), colons, semicolons, dashes (`—`, `–` and the horizontal bar `―`, as well as a run of two or more hyphens, a hyphen after whitespace, at the start of a line or after a closing mark, before a space, a tab or the end of the text, or between a letter and an opening or a closing mark, as a dash is typed in plain text: `--Hello --said John`, `- They left - he said`), hyphens inside words, before digits and at the end of a line inside a word (`well-known`, `-5`), guillemets `«»`, straight and curly quotation marks `"“”‘’`, parentheses and the other marks: every remaining character of the Unicode categories P and S (`‹›`, `§`, `€`, `°`). `marks` gives the type of every mark - a single character of a type of `PUNCTUATION_TYPES`, otherwise `ParameterError` - and `dash_pattern` the dashes typed with hyphens as a compiled regular expression, for a language whose conventions differ; a text that is not a string, marks that are not a mapping and dashes that are not a compiled expression raise `SourceTypeError`.
<!-- --8<-- [end:count_punctuations] -->

## Usage example

A subclass with the syllables of a language - here the groups of vowels, a rough rule for English.

!!! example "Example"

    ``` python
    import re

    from anyts.basic_stats import BasicStats


    class Stats(BasicStats):
        def count_syllables(self, word):
            return len(re.findall(r"[aeiouy]+", word, re.IGNORECASE))


    bs = Stats("The cat sat on the mat. A beautiful day!")
    bs.n_sents, bs.n_words, bs.n_syllables, bs.n_complex_words
    # (2, 9, 11, 1)
    bs.c_punctuations["exclamation"]
    # 1
    ```
