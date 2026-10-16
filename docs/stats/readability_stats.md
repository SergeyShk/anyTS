# Readability metrics

!!! info ""
    **anyts.readability_stats.ReadabilityStats**

## Description

<!-- --8<-- [start:ReadabilityStats] -->
The [readability](https://en.wikipedia.org/wiki/Readability) metrics of a text from its basic statistics: the mean sentence length in words, the mean word length in syllables or letters, the share of polysyllabic and of long words and the variability of word length. The data source can be a text, a `Doc` object of [spaCy](https://github.com/explosion/spaCy) or ready basic statistics - then the text is not counted again; the extractors are passed on to the basic statistics of a text or a `Doc`, while ready ones are taken as they are. The letters of the formulas are those of the counted words, so a word extractor that drops words does not lengthen the mean word.

The metrics are properties computed on each access, so a change of the `coefficients` of an object applies at once.

A source that is neither a string, a `Doc` nor basic statistics, basic statistics of a class other than those of the library and an extractor of another type raise `SourceTypeError`, a source without words or sentences `SourceError`, an unknown preset or one that is not a string `ParameterError`.
<!-- --8<-- [end:ReadabilityStats] -->

## Language hooks

<!-- --8<-- [start:ReadabilityStats-hooks] -->
A language library subclasses `ReadabilityStats`:

| Hook | Kind | Description |
| :--: | :--: | :---------: |
| `basic_stats_class` | class attribute | Its subclass of `BasicStats`, which counts a string or a `Doc`; without it the source must be a `BasicStats` object |
| `presets` | class attribute | Coefficients of the formulas by preset; a formula missing from a preset takes the defaults of its function |
| `grade_stats` | class attribute | Grade formulas of the consensus grade |
| `stats_desc`, `stats_headers` | class attributes | Metrics of `get_stats` with their descriptions, headers of the columns for `print_stats` |
| `smog_complex_syl_factor` | class attribute | Minimum number of syllables in a polysyllabic word of SMOG and Gunning fog |
| `lix_long_word_letter_factor` | class attribute | Minimum number of letters in a long word of LIX and RIX |
| `grade_age_levels`, `postgraduate_level` | class attributes | School stages and ages of `describe_grade` |
| `level_scales` | class attribute | Interpretation scales by metric, as lower bounds and their bands |
| `preset_level_scales` | class attribute | Interpretation scales by preset and metric, which take the place of those of `level_scales` for the objects of the preset |
| `level_scale(stat)` | method | Interpretation scale of a metric for `describe_level` and `describe`; that of `preset_level_scales`, else of `level_scales` by default |
| `grade_scales` | class attribute | Scales that convert a metric into years of schooling for `describe`, as lower bounds and grades; a metric with a scale of bands is read by its bands, so a library that reads it by years of schooling leaves it out of `level_scales` and `preset_level_scales` |
| `reading_speed`, `reading_speed_norms` | class attributes | Reading speed of `reading_time` and the speeds of the norms, words per minute |
| `reading_ease_grades` | class attribute | Scale that converts the reading ease into years of schooling for the consensus grade, as lower bounds and grades, the lowest band open below |
| `preset_reading_ease_grades` | class attribute | Scales of `reading_ease_grades` by preset, which take its place for the objects of the preset |
| `reading_ease_to_grade(flesch_reading_easy)` | method | Years of schooling for the reading ease in the consensus grade; the band of the scale of the preset in `preset_reading_ease_grades`, else of `reading_ease_grades` by default |
| `messages` | class attribute | Messages of the errors by key; `MESSAGES` by default |

A formula of the library is a property of the subclass named in `stats_desc`, and in `grade_stats` when it gives years of schooling; its coefficients may live in the presets under its name. The preset is a parameter: a library sets its own default in its `__init__` and passes it on. A preset unknown to `presets` among the keys of `preset_level_scales` or `preset_reading_ease_grades` raises `ParameterError` when the class is defined.
<!-- --8<-- [end:ReadabilityStats-hooks] -->

The core defaults are the original English formulas: the preset `original` of `anyts.constants.READABILITY_PRESETS`, the grade formulas Flesch-Kincaid, Coleman-Liau, ARI, SMOG and Gunning fog, polysyllabic words of three syllables and long words of seven letters, the school stages of the United States, the scales of the reading ease, LIX and RIX, the years of schooling of the reading ease of `text_standard` of textstat (`READING_EASE_GRADES`, 13 below 30), and the reading speed of 238 words per minute with the norm `adult` - 183 words per minute aloud and 238 silently (Brysbaert, 2019).

## Parameters

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `source` | str/Doc/BasicStats | `-` | Data source (a string, a Doc object or ready basic statistics) |
| `sents_extractor` | SentsExtractor | `None` | Sentence extraction tool |
| `words_extractor` | WordsExtractor | `None` | Word extraction tool |
| `preset` | str | `original` | Coefficient preset |

The core class has no basic statistics of its own (`basic_stats_class` is `None`), so it takes only a ready `BasicStats` object of a library.

## Attributes

| Attribute | Type | Description |
| :-------: | :--: | :---------: |
| `flesch_reading_easy` | float | Flesch reading ease |
| `flesch_kincaid_grade` | float | Flesch-Kincaid grade |
| `coleman_liau_index` | float | Coleman-Liau index |
| `automated_readability_index` | float | Automated readability index |
| `smog_index` | float | SMOG index |
| `gunning_fog_index` | float | Gunning fog index |
| `lix` | float | LIX readability index |
| `rix` | float | RIX readability index |
| `mu_index` | float | Legibilidad µ |
| `consensus_grade` | float | Consensus grade over the grade formulas and the reading ease |
| `reading_time` | float | Reading time in minutes at the reading speed |
| `bs` | BasicStats | Basic statistics of the text |
| `preset` | str | Name of the coefficient preset, read-only: an object of another preset can reuse the basic statistics, `ReadabilityStats(rs.bs, preset=...)` |
| `coefficients` | dict[str, tuple[float, ...]] | Coefficients of the preset by formula, a copy that can be changed for one object |

The formulas are described in the [metric functions](readability_stats_funcs.md) section.

## Consensus grade { #consensus_grade }

<!-- --8<-- [start:ReadabilityStats-consensus] -->
The formulas that give years of schooling (`grade_stats`) are summarized in the `consensus_grade` attribute: the median of their values rounded half up, together with the reading ease converted into years of schooling (`reading_ease_to_grade`) without rounding. A library aligns the bounds of `reading_ease_grades`, or of the scale of each preset in `preset_reading_ease_grades`, with its scale of the reading ease, so that the consensus grade and `describe` read the value alike.
<!-- --8<-- [end:ReadabilityStats-consensus] -->

## Methods

### describe_grade

<!-- --8<-- [start:ReadabilityStats-describe_grade] -->
Returns the school stage and reader age for the consensus grade or a grade formula; another metric raises `ParameterError`.

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `stat` | str | `consensus_grade` | Name of the grade formula |
<!-- --8<-- [end:ReadabilityStats-describe_grade] -->

### describe_level

<!-- --8<-- [start:ReadabilityStats-describe_level] -->
Returns the band of the interpretation scale of a metric (`level_scale`); a metric without a scale of bands and an undefined value (nan) raise `ParameterError`.

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `stat` | str | `flesch_reading_easy` | Name of the metric |
<!-- --8<-- [end:ReadabilityStats-describe_level] -->

The default scales are the school levels of Flesch for the reading ease (`anyts.constants.READING_EASE_LEVELS`, How to Write Plain English, 1979), the text types of Björnsson for [LIX](readability_stats_funcs.md#lix-readability-index) (`LIX_LEVELS`) and the grades of Anderson for [RIX](readability_stats_funcs.md#rix-readability-index) (`RIX_LEVELS`), whose last band, from 7.2 up, is "college and above":

| Reading ease | Level |
| :----------: | :---: |
| `90-100` | 5th grade |
| `80-90` | 6th grade |
| `70-80` | 7th grade |
| `60-70` | 8th and 9th grade |
| `50-60` | 10th to 12th grade |
| `30-50` | college |
| `10-30` | college graduate |
| `< 10` | professional |

### describe

<!-- --8<-- [start:ReadabilityStats-describe] -->
Returns the reading of any metric by its scale: for the consensus grade and a grade formula the school stage and reader age (`describe_grade`), for a metric with a scale of bands (`level_scale`) its band, for another metric of `grade_scales` the stage and age of the years of schooling its scale gives, and `None` for a metric without a scale or with an undefined value (nan). A name that is neither in `stats_desc` nor a public property of the class raises `UnknownStatError`.

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `stat` | str | `-` | Name of the metric |
<!-- --8<-- [end:ReadabilityStats-describe] -->

By default RIX reads by its scale of bands; `grade_scales` keeps its grades as years of schooling (`anyts.constants.RIX_GRADES`, college as 13) for a library whose scales of bands leave RIX out.

### reading_time_by_speed

<!-- --8<-- [start:ReadabilityStats-reading_time_by_speed] -->
Returns the reading time of the text in minutes at the given speed; a speed that is not a positive number raises `ParameterError`.

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `wpm` | float | `-` | Reading speed, words per minute |
<!-- --8<-- [end:ReadabilityStats-reading_time_by_speed] -->

### reading_time_by_norm

<!-- --8<-- [start:ReadabilityStats-reading_time_by_norm] -->
Returns the reading times of the text in minutes at the speeds of a norm of `reading_speed_norms`, in their order; an unknown norm raises `ParameterError`.

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `norm` | str | `-` | Name of the reading speed norm |
<!-- --8<-- [end:ReadabilityStats-reading_time_by_norm] -->

### get_stats

<!-- --8<-- [start:ReadabilityStats-get_stats] -->
Returns a dictionary with the computed readability metrics of `stats_desc`.
<!-- --8<-- [end:ReadabilityStats-get_stats] -->

### print_stats

<!-- --8<-- [start:ReadabilityStats-print_stats] -->
Prints a table with the computed readability metrics, their descriptions from `stats_desc` and the headers from `stats_headers`.
<!-- --8<-- [end:ReadabilityStats-print_stats] -->

The frame of the metrics (`to_dataframe`) is that of the [statistics interface](stats.md).

## Usage example

A subclass with the basic statistics of a language - here the syllables are the groups of vowels, a rough rule for English.

!!! example "Example"

    ``` python
    import re

    from anyts.basic_stats import BasicStats
    from anyts.readability_stats import ReadabilityStats


    class Stats(BasicStats):
        def count_syllables(self, word):
            return len(re.findall(r"[aeiouy]+", word, re.IGNORECASE))


    class Readability(ReadabilityStats):
        basic_stats_class = Stats


    rs = Readability("The cat sat on the mat. A beautiful day!")
    round(rs.flesch_reading_easy, 2), round(rs.flesch_kincaid_grade, 2)
    # (98.87, 0.59)
    rs.consensus_grade, rs.describe_grade()
    # (3.0, 'elementary school, grades 1-5 (6-11 years)')
    rs.describe("flesch_reading_easy"), rs.describe("lix"), rs.describe("mu_index")
    # ('5th grade', "very easy texts, children's books", None)
    rs.reading_time_by_norm("adult")
    # (0.04918032786885246, 0.037815126050420166)
    ```
