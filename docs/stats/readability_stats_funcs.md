# Metric functions

The coefficients of the formulas are parameters; the defaults below are those of the original English formulas. A formula of counts gives `nan` when the number of words or of sentences it divides by is zero.

## Flesch reading ease

!!! info ""
    **anyts.readability_stats.calc_flesch_reading_easy()**

<!-- --8<-- [start:calc_flesch_reading_easy] -->
Computation of the Flesch reading ease (Flesch, 1948).

The higher the value, the easier the text; the scale runs nominally from 0 to 100, though the simplest texts go above 100 and the hardest below 0.

Formula:

$$
c - a \cdot \frac{\textrm{Number of words}}{\textrm{Number of sentences}} - b \cdot \frac{\textrm{Number of syllables}}{\textrm{Number of words}}
$$
<!-- --8<-- [end:calc_flesch_reading_easy] -->

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `n_syllables` | int | `-` | Number of syllables |
| `n_words` | int | `-` | Number of words |
| `n_sents` | int | `-` | Number of sentences |
| `a` | float | `1.015` | Coefficient a, at the mean sentence length |
| `b` | float | `84.6` | Coefficient b, at the mean word length |
| `c` | float | `206.835` | Coefficient c, the constant |

## Flesch-Kincaid grade

!!! info ""
    **anyts.readability_stats.calc_flesch_kincaid_grade()**

<!-- --8<-- [start:calc_flesch_kincaid_grade] -->
Computation of the Flesch-Kincaid grade (Kincaid et al., 1975).

The years of schooling needed to read the text; the higher the value, the harder the text.

Formula:

$$
a \cdot \frac{\textrm{Number of words}}{\textrm{Number of sentences}} + b \cdot \frac{\textrm{Number of syllables}}{\textrm{Number of words}} - c
$$
<!-- --8<-- [end:calc_flesch_kincaid_grade] -->

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `n_syllables` | int | `-` | Number of syllables |
| `n_words` | int | `-` | Number of words |
| `n_sents` | int | `-` | Number of sentences |
| `a` | float | `0.39` | Coefficient a, at the mean sentence length |
| `b` | float | `11.8` | Coefficient b, at the mean word length |
| `c` | float | `15.59` | Coefficient c, the constant |

## Coleman-Liau index

!!! info ""
    **anyts.readability_stats.calc_coleman_liau_index()**

<!-- --8<-- [start:calc_coleman_liau_index] -->
Computation of the Coleman-Liau index (Coleman and Liau, 1975).

The years of schooling needed to read the text from the letters and the sentences per 100 words; the higher the value, the harder the text.

Formula:

$$
a \cdot \frac{100 \cdot \textrm{Number of letters}}{\textrm{Number of words}} - b \cdot \frac{100 \cdot \textrm{Number of sentences}}{\textrm{Number of words}} - c
$$
<!-- --8<-- [end:calc_coleman_liau_index] -->

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `n_letters` | int | `-` | Number of letters of the words |
| `n_words` | int | `-` | Number of words |
| `n_sents` | int | `-` | Number of sentences |
| `a` | float | `0.0588` | Coefficient a, at the letters per 100 words |
| `b` | float | `0.296` | Coefficient b, at the sentences per 100 words |
| `c` | float | `15.8` | Coefficient c, the constant |

## Automated readability index (ARI)

!!! info ""
    **anyts.readability_stats.calc_automated_readability_index()**

<!-- --8<-- [start:calc_automated_readability_index] -->
Computation of the automated readability index (Smith and Senter, 1967).

The years of schooling needed to read the text from the letters per word and the words per sentence; the higher the value, the harder the text.

Formula:

$$
a \cdot \frac{\textrm{Number of letters}}{\textrm{Number of words}} + b \cdot \frac{\textrm{Number of words}}{\textrm{Number of sentences}} - c
$$
<!-- --8<-- [end:calc_automated_readability_index] -->

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `n_letters` | int | `-` | Number of letters of the words |
| `n_words` | int | `-` | Number of words |
| `n_sents` | int | `-` | Number of sentences |
| `a` | float | `4.71` | Coefficient a, at the letters per word |
| `b` | float | `0.5` | Coefficient b, at the mean sentence length |
| `c` | float | `21.43` | Coefficient c, the constant |

## SMOG index

!!! info ""
    **anyts.readability_stats.calc_smog_index()**

<!-- --8<-- [start:calc_smog_index] -->
Computation of the SMOG index (McLaughlin, 1969).

The years of schooling needed to read the text from the polysyllabic words per sentence; the higher the value, the harder the text. In the original formula the polysyllabic words have three or more syllables and `b` brings their number to a sample of 30 sentences.

Formula:

$$
a \cdot \sqrt{b \cdot \frac{\textrm{Number of polysyllabic words}}{\textrm{Number of sentences}}} + c
$$
<!-- --8<-- [end:calc_smog_index] -->

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `n_complex` | int | `-` | Number of polysyllabic words |
| `n_sents` | int | `-` | Number of sentences |
| `a` | float | `1.043` | Coefficient a, at the square root |
| `b` | float | `30` | Coefficient b, the number of sentences of the sample |
| `c` | float | `3.1291` | Coefficient c, the constant |

## Gunning fog index

!!! info ""
    **anyts.readability_stats.calc_gunning_fog_index()**

<!-- --8<-- [start:calc_gunning_fog_index] -->
Computation of the Gunning fog index (Gunning, 1952).

The years of schooling needed to read the text from the mean sentence length and the percentage of complex words, in the original formula the words of three or more syllables; the higher the value, the harder the text.

Formula:

$$
a \cdot \left(\frac{\textrm{Number of words}}{\textrm{Number of sentences}} + \frac{100 \cdot \textrm{Number of complex words}}{\textrm{Number of words}}\right)
$$
<!-- --8<-- [end:calc_gunning_fog_index] -->

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `n_complex` | int | `-` | Number of complex words |
| `n_words` | int | `-` | Number of words |
| `n_sents` | int | `-` | Number of sentences |
| `a` | float | `0.4` | Coefficient a |

## LIX readability index

!!! info ""
    **anyts.readability_stats.calc_lix()**

<!-- --8<-- [start:calc_lix] -->
Computation of the LIX readability index (Björnsson, 1968).

The mean sentence length plus the percentage of long words, the words of more than six letters; there are no coefficients to fit. The higher the value, the harder the text:

| Value | Text |
| :---: | :--- |
| `0-30` | very easy texts, children's books |
| `30-40` | easy texts, fiction, newspaper articles |
| `40-50` | texts of medium difficulty, magazine articles |
| `50-60` | hard texts, popular science, official texts |
| `60-100` | very hard texts, laws and bureaucratic language |

Formula:

$$
\frac{\textrm{Number of words}}{\textrm{Number of sentences}} + \frac{100 \cdot \textrm{Number of long words}}{\textrm{Number of words}}
$$

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `n_long_words` | int | `-` | Number of long words |
| `n_words` | int | `-` | Number of words |
| `n_sents` | int | `-` | Number of sentences |
<!-- --8<-- [end:calc_lix] -->

## RIX readability index

!!! info ""
    **anyts.readability_stats.calc_rix()**

<!-- --8<-- [start:calc_rix] -->
Computation of the RIX readability index (Anderson, 1983).

The long words, of more than six letters, per sentence; there are no coefficients to fit. The higher the value, the harder the text:

| Value | Grade |
| :---: | :---: |
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

Formula:

$$
\frac{\textrm{Number of long words}}{\textrm{Number of sentences}}
$$

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `n_long_words` | int | `-` | Number of long words |
| `n_sents` | int | `-` | Number of sentences |
<!-- --8<-- [end:calc_rix] -->

## Legibilidad µ

!!! info ""
    **anyts.readability_stats.calc_mu_index()**

<!-- --8<-- [start:calc_mu_index] -->
Computation of Legibilidad µ (Muñoz Baquedano and Muñoz Urra, 2006).

The mean number of letters per word divided by its sample variance, times 100; there are no coefficients to fit, and the higher the value, the easier the text. Words without letters (numbers) are left out; with fewer than two words or without variability the index is undefined (`nan`).

Formula:

$$
100 \cdot \frac{\bar{x}}{s^2}, \quad s^2 = \frac{\sum (x_i - \bar{x})^2}{n - 1}
$$

where $x_i$ is the number of letters of a word and $n$ the number of words.

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `c_letters` | dict[int, int] | `-` | Distribution of words by number of letters |
<!-- --8<-- [end:calc_mu_index] -->

## Reading ease as a grade

!!! info ""
    **anyts.readability_stats.flesch_reading_easy_to_grade()**

<!-- --8<-- [start:flesch_reading_easy_to_grade] -->
Conversion of the Flesch reading ease into years of schooling for the consensus grade: the grade of the first band whose lower bound the value reaches, or `below` under the last bound; values above 100 belong to the first band.
<!-- --8<-- [end:flesch_reading_easy_to_grade] -->

The default bands are those of `text_standard` of [textstat](https://github.com/textstat/textstat), which follow the table of Flesch (1948) down to 60 and split his lower bands, with 8.5 for its grades 8 and 9: 90-100 - 5, 80-90 - 6, 70-80 - 7, 60-70 - 8.5, 50-60 - 10, 40-50 - 11, 30-40 - 12, below 30 - 13 (`anyts.constants.READING_EASE_GRADES`).

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `flesch_reading_easy` | float | `-` | Value of the reading ease |
| `grades` | list[tuple[float, float]] | `READING_EASE_GRADES` | Lower bounds and their grades in descending order of the bounds |
| `below` | float | `13` | Grade below the last bound |

## Consensus grade

!!! info ""
    **anyts.readability_stats.calc_consensus_grade()**

<!-- --8<-- [start:calc_consensus_grade] -->
Computation of the consensus grade: the median of the values of the grade formulas rounded half up, together with the reading ease converted into years of schooling by `to_grade` and added without rounding - so a band of 8.5 votes for 8.5. No values at all and a grade that is not a finite number raise `ParameterError`, a `to_grade` that is not callable `SourceTypeError`.

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `grades` | list[float] | `-` | Values of the grade formulas |
| `flesch_reading_easy` | float | `None` | Value of the reading ease |
| `to_grade` | Callable | `flesch_reading_easy_to_grade` | Conversion of the reading ease into years of schooling |
<!-- --8<-- [end:calc_consensus_grade] -->

## School stage and age

!!! info ""
    **anyts.readability_stats.grade_to_age()**

<!-- --8<-- [start:grade_to_age] -->
The school stage and reader age by the value of a grade formula: the value is rounded half up and falls into the first stage whose last year it does not exceed, values below 1 into the first stage; above the last stage lies `above`. A grade that is not a finite number raises `ParameterError`.
<!-- --8<-- [end:grade_to_age] -->

The default stages are those of the United States (`anyts.constants.GRADE_AGE_LEVELS` and `POSTGRADUATE_LEVEL`):

| Grade | Stage | Age |
| :---: | :---: | :-: |
| 1-5 | elementary school, grades 1-5 | 6-11 years |
| 6-8 | middle school, grades 6-8 | 11-14 years |
| 9-12 | high school, grades 9-12 | 14-18 years |
| 13-16 | college | 18-22 years |
| above 16 | graduate school | over 22 years |

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `grade` | float | `-` | Value of a grade formula |
| `levels` | list[tuple[int, int, str, str]] | `GRADE_AGE_LEVELS` | Stages as the first and the last year, the stage and the age, in ascending order |
| `above` | tuple[str, str] | `POSTGRADUATE_LEVEL` | Stage and age above the last stage |

## Band of a scale

!!! info ""
    **anyts.readability_stats.scale_level()**

<!-- --8<-- [start:scale_level] -->
The band of a scale for a value: the scale is given as the lower bounds of its bands in descending order, the value falls into the first band whose bound it reaches, and the lowest band is open below. A value that is not a finite number and an empty scale raise `ParameterError`.

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `value` | float | `-` | Value of a metric |
| `scale` | list[tuple[float, Any]] | `-` | Lower bounds and their bands in descending order |
<!-- --8<-- [end:scale_level] -->

## Reading time

!!! info ""
    **anyts.readability_stats.calc_reading_time()**

<!-- --8<-- [start:calc_reading_time] -->
Computation of the reading time of a text in minutes: the number of words divided by the reading speed; a speed that is not a positive number raises `ParameterError`.
<!-- --8<-- [end:calc_reading_time] -->

The default speed is the silent reading speed of adults in English, 238 words per minute (Brysbaert, 2019).

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `n_words` | int | `-` | Number of words |
| `wpm` | float | `238` | Reading speed, words per minute |
