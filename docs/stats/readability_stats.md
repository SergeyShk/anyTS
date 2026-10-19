# Readability metrics

``` {.python .signature}
ReadabilityStats(source, sents_extractor=None, words_extractor=None, preset='original')
```

<!-- --8<-- [start:ReadabilityStats] -->
The [readability](https://en.wikipedia.org/wiki/Readability) metrics of a text from its basic statistics: the mean sentence length in words, the mean word length in syllables or letters, the share of polysyllabic and of long words and the variability of word length. The data source is a text, a `Doc` object of [spaCy](https://github.com/explosion/spaCy) or ready basic statistics, which are reused as they are; the extractors are passed on to the basic statistics of a text or a `Doc`. The formulas count only the letters of the counted words, so a word extractor that drops words does not lengthen the mean word.

The metrics are properties computed on each access, so a change of the `coefficients` of an object applies at once.

Raises:

- `SourceTypeError` - a source that is neither a string, a `Doc` nor basic statistics, basic statistics of a class other than those of the library, an extractor of another type, a string or a `Doc` to a class without `basic_stats_class`;
- `SourceError` - a source without words or sentences;
- `ParameterError` - an unknown preset or one that is not a string.
<!-- --8<-- [end:ReadabilityStats] -->

A subclass with the basic statistics of a language - here the syllables are the groups of vowels, a rough rule for English.

=== "Code"

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
    rs.print_stats()
    ```

=== "Result"

    ```
               Metric           |  Value
    ---------------------------------------
    Flesch reading ease         |  98.87
    Flesch-Kincaid grade        |   0.59
    Coleman-Liau index          |  -2.78
    Automated readability index |  -3.48
    SMOG index                  |   7.17
    Gunning fog index           |   6.24
    LIX readability index       |  15.61
    RIX readability index       |   0.50
    Legibilidad µ               |  66.67
    Consensus grade             |   3.00
    Reading time (min)          |   0.04
    ```

## Parameters

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `source` | `str` / `Doc` / `BasicStats` | - | Data source (a string, a Doc object or ready basic statistics) |
| `sents_extractor` | `SentsExtractor` | `None` | Sentence extraction tool |
| `words_extractor` | `WordsExtractor` | `None` | Word extraction tool |
| `preset` | `str` | `'original'` | Coefficient preset |

In the core `basic_stats_class` is `None`, so the class takes only a ready `BasicStats` object of a library. The object keeps the basic statistics of the text in `bs`, the name of the preset in `preset`, read-only, and the coefficients of the preset by formula in `coefficients`, a copy that can be changed for one object. An object of another preset can reuse the basic statistics: `ReadabilityStats(rs.bs, preset=...)`.

## Presets { #presets }

The coefficients of the formulas are parameters of their functions, and a preset gives them by formula. The core defaults are the original English formulas: the preset `original` of `anyts.constants.READABILITY_PRESETS`, the grade formulas Flesch-Kincaid, Coleman-Liau, ARI, SMOG and Gunning fog, polysyllabic words of three syllables and long words of seven letters, the school stages of the United States, the scales of the reading ease, LIX and RIX, the years of schooling of the reading ease of `text_standard` of textstat (`READING_EASE_GRADES`, 13 below 30), and the reading speed of 238 words per minute with the norm `adult` - 183 words per minute aloud and 238 silently (Brysbaert, 2019).

## Metrics

<!-- --8<-- [start:ReadabilityStats-metrics] -->
A formula is computed by the function of its card on the counts of `bs`, with its coefficients in `coefficients`; a formula of counts gives `nan` when the number of words or of sentences it divides by is zero.

| Metric | Measures | Range | Higher means |
| :----- | :------- | :---- | :----------- |
| [`flesch_reading_easy`](#flesch_reading_easy) | Ease of reading by the sentence length and the syllables per word | Nominally 0-100, above 100 for the simplest texts and below 0 for the hardest | An easier text |
| [`flesch_kincaid_grade`](#flesch_kincaid_grade) | Grade by the sentence length and the syllables per word | Years of schooling, below 0 for the simplest texts | A harder text |
| [`coleman_liau_index`](#coleman_liau_index) | Grade by the letters and the sentences per 100 words | Years of schooling, below 0 for the simplest texts | A harder text |
| [`automated_readability_index`](#automated_readability_index) | Grade by the letters per word and the sentence length | Years of schooling, below 0 for the simplest texts | A harder text |
| [`smog_index`](#smog_index) | Grade by the polysyllabic words per sentence | Years of schooling | A harder text |
| [`gunning_fog_index`](#gunning_fog_index) | Grade by the sentence length and the share of complex words | Years of schooling | A harder text |
| [`lix`](#lix) | Sentence length and the share of long words | 0 and above | A harder text |
| [`rix`](#rix) | Long words per sentence | 0 and above | A harder text |
| [`mu_index`](#mu_index) | Mean word length in letters against its variance | Above 0, `nan` with fewer than two words or without variability | An easier text |
| [`consensus_grade`](#consensus_grade) | Median of the grade formulas and the reading ease as a grade | Years of schooling, below 0 for the simplest texts | A harder text |
| [`reading_time`](#reading_time) | Reading time at the reading speed (`reading_speed`) | Minutes, above 0 | A longer text |
<!-- --8<-- [end:ReadabilityStats-metrics] -->

<div class="metric-card" markdown>

### Flesch reading ease { #flesch_reading_easy }

`flesch_reading_easy` · Flesch, 1948
{ .metric-meta }

``` {.python .signature}
calc_flesch_reading_easy(n_syllables, n_words, n_sents, a=1.015, b=84.6, c=206.835)
```

<!-- --8<-- [start:calc_flesch_reading_easy] -->
The ease of reading a text by the mean sentence length in words and the mean word length in syllables.

$$
c - a \cdot \frac{\textrm{Number of words}}{\textrm{Number of sentences}} - b \cdot \frac{\textrm{Number of syllables}}{\textrm{Number of words}}
$$
<!-- --8<-- [end:calc_flesch_reading_easy] -->

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `n_syllables` | `int` | - | Number of syllables |
| `n_words` | `int` | - | Number of words |
| `n_sents` | `int` | - | Number of sentences |
| `a` | `float` | `1.015` | Coefficient a, at the mean sentence length |
| `b` | `float` | `84.6` | Coefficient b, at the mean word length |
| `c` | `float` | `206.835` | Coefficient c, the constant |

</div>

<div class="metric-card" markdown>

### Flesch-Kincaid grade { #flesch_kincaid_grade }

`flesch_kincaid_grade` · Kincaid et al., 1975
{ .metric-meta }

``` {.python .signature}
calc_flesch_kincaid_grade(n_syllables, n_words, n_sents, a=0.39, b=11.8, c=15.59)
```

<!-- --8<-- [start:calc_flesch_kincaid_grade] -->
The years of schooling needed to read the text, by the mean sentence length in words and the mean word length in syllables.

$$
a \cdot \frac{\textrm{Number of words}}{\textrm{Number of sentences}} + b \cdot \frac{\textrm{Number of syllables}}{\textrm{Number of words}} - c
$$
<!-- --8<-- [end:calc_flesch_kincaid_grade] -->

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `n_syllables` | `int` | - | Number of syllables |
| `n_words` | `int` | - | Number of words |
| `n_sents` | `int` | - | Number of sentences |
| `a` | `float` | `0.39` | Coefficient a, at the mean sentence length |
| `b` | `float` | `11.8` | Coefficient b, at the mean word length |
| `c` | `float` | `15.59` | Coefficient c, the constant |

</div>

<div class="metric-card" markdown>

### Coleman-Liau index { #coleman_liau_index }

`coleman_liau_index` · Coleman and Liau, 1975
{ .metric-meta }

``` {.python .signature}
calc_coleman_liau_index(n_letters, n_words, n_sents, a=0.0588, b=0.296, c=15.8)
```

<!-- --8<-- [start:calc_coleman_liau_index] -->
The years of schooling needed to read the text, by the letters and the sentences per 100 words.

$$
a \cdot \frac{100 \cdot \textrm{Number of letters}}{\textrm{Number of words}} - b \cdot \frac{100 \cdot \textrm{Number of sentences}}{\textrm{Number of words}} - c
$$
<!-- --8<-- [end:calc_coleman_liau_index] -->

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `n_letters` | `int` | - | Number of letters of the words |
| `n_words` | `int` | - | Number of words |
| `n_sents` | `int` | - | Number of sentences |
| `a` | `float` | `0.0588` | Coefficient a, at the letters per 100 words |
| `b` | `float` | `0.296` | Coefficient b, at the sentences per 100 words |
| `c` | `float` | `15.8` | Coefficient c, the constant |

</div>

<div class="metric-card" markdown>

### Automated readability index (ARI) { #automated_readability_index }

`automated_readability_index` · Smith and Senter, 1967
{ .metric-meta }

``` {.python .signature}
calc_automated_readability_index(n_letters, n_words, n_sents, a=4.71, b=0.5, c=21.43)
```

<!-- --8<-- [start:calc_automated_readability_index] -->
The years of schooling needed to read the text, by the letters per word and the words per sentence.

$$
a \cdot \frac{\textrm{Number of letters}}{\textrm{Number of words}} + b \cdot \frac{\textrm{Number of words}}{\textrm{Number of sentences}} - c
$$
<!-- --8<-- [end:calc_automated_readability_index] -->

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `n_letters` | `int` | - | Number of letters of the words |
| `n_words` | `int` | - | Number of words |
| `n_sents` | `int` | - | Number of sentences |
| `a` | `float` | `4.71` | Coefficient a, at the letters per word |
| `b` | `float` | `0.5` | Coefficient b, at the mean sentence length |
| `c` | `float` | `21.43` | Coefficient c, the constant |

</div>

<div class="metric-card" markdown>

### SMOG index { #smog_index }

`smog_index` · McLaughlin, 1969
{ .metric-meta }

``` {.python .signature}
calc_smog_index(n_complex, n_sents, a=1.043, b=30, c=3.1291)
```

<!-- --8<-- [start:calc_smog_index] -->
The years of schooling needed to read the text, by the polysyllabic words per sentence. In the original formula the polysyllabic words have three or more syllables and `b` brings their number to a sample of 30 sentences.

$$
a \cdot \sqrt{b \cdot \frac{\textrm{Number of polysyllabic words}}{\textrm{Number of sentences}}} + c
$$

A number of words or sentences that is not a non-negative integer raises `ParameterError`.
<!-- --8<-- [end:calc_smog_index] -->

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `n_complex` | `int` | - | Number of polysyllabic words |
| `n_sents` | `int` | - | Number of sentences |
| `a` | `float` | `1.043` | Coefficient a, at the square root |
| `b` | `float` | `30` | Coefficient b, the number of sentences of the sample |
| `c` | `float` | `3.1291` | Coefficient c, the constant |

</div>

<div class="metric-card" markdown>

### Gunning fog index { #gunning_fog_index }

`gunning_fog_index` · Gunning, 1952
{ .metric-meta }

``` {.python .signature}
calc_gunning_fog_index(n_complex, n_words, n_sents, a=0.4)
```

<!-- --8<-- [start:calc_gunning_fog_index] -->
The years of schooling needed to read the text, by the mean sentence length and the percentage of complex words, in the original formula the words of three or more syllables.

$$
a \cdot \left(\frac{\textrm{Number of words}}{\textrm{Number of sentences}} + \frac{100 \cdot \textrm{Number of complex words}}{\textrm{Number of words}}\right)
$$
<!-- --8<-- [end:calc_gunning_fog_index] -->

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `n_complex` | `int` | - | Number of complex words |
| `n_words` | `int` | - | Number of words |
| `n_sents` | `int` | - | Number of sentences |
| `a` | `float` | `0.4` | Coefficient a |

</div>

<div class="metric-card" markdown>

### LIX readability index { #lix }

`lix` · Björnsson, 1968
{ .metric-meta }

<!-- --8<-- [start:calc_lix] -->
``` {.python .signature}
calc_lix(n_long_words, n_words, n_sents)
```

The mean sentence length plus the percentage of long words, the words of more than six letters; there are no coefficients to fit. The values read as text types:

| Value | Text |
| :---- | :--- |
| `0-30` | very easy texts, children's books |
| `30-40` | easy texts, fiction, newspaper articles |
| `40-50` | texts of medium difficulty, magazine articles |
| `50-60` | hard texts, popular science, official texts |
| `60-100` | very hard texts, laws and bureaucratic language |

$$
\frac{\textrm{Number of words}}{\textrm{Number of sentences}} + \frac{100 \cdot \textrm{Number of long words}}{\textrm{Number of words}}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `n_long_words` | `int` | - | Number of long words |
| `n_words` | `int` | - | Number of words |
| `n_sents` | `int` | - | Number of sentences |
<!-- --8<-- [end:calc_lix] -->

</div>

<div class="metric-card" markdown>

### RIX readability index { #rix }

`rix` · Anderson, 1983
{ .metric-meta }

<!-- --8<-- [start:calc_rix] -->
``` {.python .signature}
calc_rix(n_long_words, n_sents)
```

The long words, of more than six letters, per sentence; there are no coefficients to fit. The values read as grades:

| Value | Grade |
| :---- | :---- |
| `< 0.2` | 1 |
| `0.2-0.5` | 2 |
| `0.5-0.8` | 3 |
| `0.8-1.3` | 4 |
| `1.3-1.8` | 5 |
| `1.8-2.4` | 6 |
| `2.4-3.0` | 7 |
| `3.0-3.7` | 8 |
| `3.7-4.5` | 9 |
| `4.5-5.3` | 10 |
| `5.3-6.2` | 11 |
| `6.2-7.2` | 12 |
| `> 7.2` | college |

$$
\frac{\textrm{Number of long words}}{\textrm{Number of sentences}}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `n_long_words` | `int` | - | Number of long words |
| `n_sents` | `int` | - | Number of sentences |
<!-- --8<-- [end:calc_rix] -->

</div>

<div class="metric-card" markdown>

### Legibilidad µ { #mu_index }

`mu_index` · Muñoz Baquedano and Muñoz Urra, 2006
{ .metric-meta }

<!-- --8<-- [start:calc_mu_index] -->
``` {.python .signature}
calc_mu_index(c_letters)
```

The mean number of letters per word divided by its sample variance, times 100; there are no coefficients to fit. Words without letters (numbers) are left out; with fewer than two words or without variability the index is undefined (`nan`).

$$
100 \cdot \frac{\bar{x}}{s^2}, \quad s^2 = \frac{\sum (x_i - \bar{x})^2}{n - 1}
$$

where $x_i$ is the number of letters of a word and $n$ the number of words.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `c_letters` | `dict[int, int]` | - | Distribution of words by number of letters |

A `c_letters` that is not a mapping raises `SourceTypeError`.
<!-- --8<-- [end:calc_mu_index] -->

</div>

<div class="metric-card" markdown>

### Consensus grade { #consensus_grade }

`consensus_grade`
{ .metric-meta }

<!-- --8<-- [start:ReadabilityStats-consensus] -->
The `consensus_grade` attribute is the median of the values of the grade formulas (`grade_stats`) rounded half up, together with the reading ease in years of schooling (`reading_ease_to_grade`), not rounded. A library aligns the bounds of `reading_ease_grades`, and of each scale of `preset_reading_ease_grades`, with its scale of the reading ease, so that the consensus grade and `describe` read the value alike.
<!-- --8<-- [end:ReadabilityStats-consensus] -->

<!-- --8<-- [start:calc_consensus_grade] -->
``` {.python .signature}
calc_consensus_grade(grades, flesch_reading_easy=None, to_grade=flesch_reading_easy_to_grade)
```

The median of the values of the grade formulas rounded half up, together with the reading ease in years of schooling by `to_grade`, not rounded - so a band of 8.5 votes for 8.5.

$$
\textrm{median}\left(\lfloor g_1 + 0.5 \rfloor, \ldots, \lfloor g_k + 0.5 \rfloor, \textrm{to\_grade}(\textrm{reading ease})\right)
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `grades` | `list[float]` | - | Values of the grade formulas |
| `flesch_reading_easy` | `float` | `None` | Value of the reading ease |
| `to_grade` | `Callable` | `flesch_reading_easy_to_grade` | Conversion of the reading ease into years of schooling |

No values at all, a grade or a reading ease that is not a finite number raise `ParameterError`; grades that are not a list and a `to_grade` that is not callable raise `SourceTypeError`.
<!-- --8<-- [end:calc_consensus_grade] -->

``` {.python .signature}
flesch_reading_easy_to_grade(flesch_reading_easy, grades=((90, 5), (80, 6), (70, 7), (60, 8.5), (50, 10), (40, 11), (30, 12)), below=13)
```

<!-- --8<-- [start:flesch_reading_easy_to_grade] -->
Conversion of the Flesch reading ease into years of schooling for the consensus grade: the grade of the first band whose lower bound the value reaches, or `below` under the last bound; values above 100 belong to the first band. A reading ease or a `below` that is not a finite number raises `ParameterError`, and so do `grades` that are empty or not pairs of finite numbers with descending bounds.
<!-- --8<-- [end:flesch_reading_easy_to_grade] -->

The default bands are those of `text_standard` of [textstat](https://github.com/textstat/textstat), which follow the table of Flesch (1948) down to 60 and split his lower bands, with 8.5 for its grades 8 and 9: 90-100 - 5, 80-90 - 6, 70-80 - 7, 60-70 - 8.5, 50-60 - 10, 40-50 - 11, 30-40 - 12, below 30 - 13 (`anyts.constants.READING_EASE_GRADES`).

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `flesch_reading_easy` | `float` | - | Value of the reading ease |
| `grades` | `list[tuple[float, float]]` | `READING_EASE_GRADES` | Lower bounds and their grades in descending order of the bounds |
| `below` | `float` | `13` | Grade below the last bound |

</div>

<div class="metric-card" markdown>

### Reading time { #reading_time }

`reading_time` · `reading_time_by_speed(wpm)` · `reading_time_by_norm(norm)` · Brysbaert, 2019
{ .metric-meta }

``` {.python .signature}
calc_reading_time(n_words, wpm=238, *, messages=MESSAGES)
```

<!-- --8<-- [start:calc_reading_time] -->
The reading time of a text in minutes: the number of words divided by the reading speed.

$$
\frac{\textrm{Number of words}}{\textrm{wpm}}
$$

A number of words that is not a non-negative integer and a speed that is not a positive number raise `ParameterError`.
<!-- --8<-- [end:calc_reading_time] -->

The default speed is the silent reading speed of adults in English, 238 words per minute.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `n_words` | `int` | - | Number of words |
| `wpm` | `float` | `238` | Reading speed, words per minute (`READING_SPEED_WPM`) |
| `messages` | `dict[str, str]` | `MESSAGES` | Messages of the errors by key, a keyword |

</div>

## Methods

<!-- --8<-- [start:ReadabilityStats-describe_grade] -->
`describe_grade(stat)` returns the school stage and reader age for the consensus grade or the grade formula `stat`, `consensus_grade` by default; another metric raises `ParameterError`.
<!-- --8<-- [end:ReadabilityStats-describe_grade] -->

<!-- --8<-- [start:ReadabilityStats-describe_level] -->
`describe_level(stat)` returns the band of the interpretation scale (`level_scale`) of the metric `stat`, `flesch_reading_easy` by default; a metric without a scale of bands and an undefined value (nan) raise `ParameterError`.
<!-- --8<-- [end:ReadabilityStats-describe_level] -->

<!-- --8<-- [start:ReadabilityStats-describe] -->
`describe(stat)` returns the reading of any metric by its scale: for the consensus grade and a grade formula the school stage and reader age (`describe_grade`), for a metric with a scale of bands (`level_scale`) its band, for another metric of `grade_scales` the stage and age of the years of schooling its scale gives, and `None` for a metric without a scale or with an undefined value (nan). A name that is neither in `stats_desc` nor a public property of the class raises `UnknownStatError`.
<!-- --8<-- [end:ReadabilityStats-describe] -->

<!-- --8<-- [start:ReadabilityStats-reading_time_by_speed] -->
`reading_time_by_speed(wpm)` returns the reading time of the text in minutes at the speed `wpm`, words per minute; a speed that is not a positive number raises `ParameterError`.
<!-- --8<-- [end:ReadabilityStats-reading_time_by_speed] -->

<!-- --8<-- [start:ReadabilityStats-reading_time_by_norm] -->
`reading_time_by_norm(norm)` returns the reading times of the text in minutes at the speeds of the norm `norm` of `reading_speed_norms`, in their order; an unknown norm raises `ParameterError`.
<!-- --8<-- [end:ReadabilityStats-reading_time_by_norm] -->

<!-- --8<-- [start:ReadabilityStats-get_stats] -->
`get_stats()` returns a dictionary of the readability metrics of `stats_desc`.
<!-- --8<-- [end:ReadabilityStats-get_stats] -->

<!-- --8<-- [start:ReadabilityStats-print_stats] -->
`print_stats()` prints a table of the readability metrics with their descriptions from `stats_desc` under the headers of `stats_headers`.
<!-- --8<-- [end:ReadabilityStats-print_stats] -->

=== "Code"

    ``` python
    rs.describe_grade()
    rs.describe("flesch_reading_easy"), rs.describe("lix"), rs.describe("mu_index")
    rs.reading_time_by_norm("adult")
    ```

=== "Result"

    ```
    'elementary school, grades 1-5 (6-11 years)'
    ('5th grade', "very easy texts, children's books", None)
    (0.04918032786885246, 0.037815126050420166)
    ```

The frame of the metrics (`to_dataframe`) is that of the [statistics interface](stats.md).

## Scales { #scales }

The default scales of `describe_level` are the school levels of Flesch for the reading ease (`anyts.constants.READING_EASE_LEVELS`, How to Write Plain English, 1979), the text types of Björnsson for [LIX](#lix) (`LIX_LEVELS`) and the grades of Anderson for [RIX](#rix) (`RIX_LEVELS`), whose last band, from 7.2 up, is "college and above". The reading ease reads as follows:

| Reading ease | Level |
| :----------- | :---- |
| `90-100` | 5th grade |
| `80-90` | 6th grade |
| `70-80` | 7th grade |
| `60-70` | 8th and 9th grade |
| `50-60` | 10th to 12th grade |
| `30-50` | college |
| `10-30` | college graduate |
| `< 10` | professional |

By default RIX is read by its scale of bands; `grade_scales` keeps its grades as years of schooling (`anyts.constants.RIX_GRADES`, college as 13) for a library whose scales of bands leave RIX out.

### School stage and age { #grade_to_age }

``` {.python .signature}
grade_to_age(grade, levels=((1, 5, 'elementary school, grades 1-5', '6-11 years'), (6, 8, 'middle school, grades 6-8', '11-14 years'), (9, 12, 'high school, grades 9-12', '14-18 years'), (13, 16, 'college', '18-22 years')), above=('graduate school', 'over 22 years'))
```

<!-- --8<-- [start:grade_to_age] -->
The school stage and reader age by the value of a grade formula: the value is rounded half up and falls into the first stage whose last year it does not exceed, values below 1 into the first stage; above the last stage lies `above`. A grade that is not a finite number, stages that are not quadruples of two whole years and two strings in ascending order of the years and an `above` that is not a pair of strings raise `ParameterError`.
<!-- --8<-- [end:grade_to_age] -->

The default stages are those of the United States (`anyts.constants.GRADE_AGE_LEVELS` and `POSTGRADUATE_LEVEL`):

| Grade | Stage | Age |
| :---- | :---- | :-- |
| 1-5 | elementary school, grades 1-5 | 6-11 years |
| 6-8 | middle school, grades 6-8 | 11-14 years |
| 9-12 | high school, grades 9-12 | 14-18 years |
| 13-16 | college | 18-22 years |
| above 16 | graduate school | over 22 years |

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `grade` | `float` | - | Value of a grade formula |
| `levels` | `list[tuple[int, int, str, str]]` | `GRADE_AGE_LEVELS` | Stages as the first and the last year, the stage and the age, in ascending order |
| `above` | `tuple[str, str]` | `POSTGRADUATE_LEVEL` | Stage and age above the last stage |

### Band of a scale { #scale_level }

<!-- --8<-- [start:scale_level] -->
``` {.python .signature}
scale_level(value, scale)
```

The band of a scale for a value: the scale is given as the lower bounds of its bands in descending order, the value falls into the first band whose bound it reaches, and the lowest band is open below.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `value` | `float` | - | Value of a metric |
| `scale` | `list[tuple[float, Any]]` | - | Lower bounds and their bands in descending order |

A value that is not a finite number and a scale that is empty, not a list of pairs of a finite lower bound and a band or with bounds that do not descend raise `ParameterError`.
<!-- --8<-- [end:scale_level] -->

=== "Code"

    ``` python
    from anyts.constants import READING_EASE_LEVELS
    from anyts.readability_stats import scale_level

    scale_level(45, READING_EASE_LEVELS), scale_level(-40, READING_EASE_LEVELS)
    ```

=== "Result"

    ```
    ('college', 'professional')
    ```

## For library developers { #hooks }

<details class="library-hooks" markdown>
<summary>Language hooks of a subclass</summary>

<!-- --8<-- [start:ReadabilityStats-hooks] -->
A language library subclasses `ReadabilityStats`:

| Hook | Kind | Description |
| :--- | :--- | :---------- |
| `basic_stats_class` | class attribute | Its subclass of `BasicStats` for a string or a `Doc`; without it the source must be a `BasicStats` object |
| `presets` | class attribute | Coefficients of the formulas by preset; a formula missing from a preset takes the defaults of its function |
| `grade_stats` | class attribute | Grade formulas of the consensus grade; `anyts.constants.READABILITY_GRADE_STATS` by default |
| `stats_desc`, `stats_headers` | class attributes | Metrics of `get_stats` with their descriptions (`READABILITY_STATS_DESC` by default), headers of the columns for `print_stats` |
| `smog_complex_syl_factor` | class attribute | Minimum number of syllables in a polysyllabic word of SMOG and Gunning fog; `SMOG_COMPLEX_SYL_FACTOR` by default |
| `lix_long_word_letter_factor` | class attribute | Minimum number of letters in a long word of LIX and RIX; `LIX_LONG_WORD_LETTER_FACTOR` by default |
| `grade_age_levels`, `postgraduate_level` | class attributes | School stages and ages of `describe_grade` |
| `level_scales` | class attribute | Interpretation scales by metric, as lower bounds and their bands |
| `preset_level_scales` | class attribute | Interpretation scales by preset and metric, in place of `level_scales` for the preset |
| `level_scale(stat)` | method | Interpretation scale of a metric for `describe_level` and `describe`; that of `preset_level_scales`, else of `level_scales` by default |
| `grade_scales` | class attribute | Scales of a metric in years of schooling for `describe`, as lower bounds and grades; a scale of bands comes first, so a metric read by years of schooling stays out of `level_scales` and `preset_level_scales` |
| `reading_speed`, `reading_speed_norms` | class attributes | Reading speed of `reading_time` and the speeds of the norms, words per minute; `READING_SPEED_WPM` and `READING_SPEED_NORMS` by default |
| `reading_ease_grades` | class attribute | Scale of the reading ease in years of schooling for the consensus grade, as lower bounds and grades, the lowest band open below |
| `preset_reading_ease_grades` | class attribute | Scales of `reading_ease_grades` by preset, in its place for the preset |
| `reading_ease_to_grade(flesch_reading_easy)` | method | Years of schooling for the reading ease in the consensus grade; the band of the scale of the preset in `preset_reading_ease_grades`, else of `reading_ease_grades` by default |
| `messages` | class attribute | Messages of the errors by key; `MESSAGES` by default |

A formula of the library is a property of the subclass named in `stats_desc`, and in `grade_stats` when it gives years of schooling; its coefficients may live in the presets under its name. The preset is a parameter: a library sets its own default in its `__init__` and passes it on. When the class is defined, `ParameterError` is raised by a preset unknown to `presets` among the keys of `preset_level_scales` or `preset_reading_ease_grades`, by a scale of them, of `grade_scales` or of `reading_ease_grades` that is not one of `scale_level` with finite grades, by `grade_age_levels` that are not quadruples of the first and the last year, the stage and the age in ascending order of the years, and by a `postgraduate_level` that is not a pair of strings.
<!-- --8<-- [end:ReadabilityStats-hooks] -->

</details>
