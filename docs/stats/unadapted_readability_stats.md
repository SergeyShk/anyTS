# Unadapted readability formulas

``` {.python .signature}
UnadaptedReadabilityStats(source, sents_extractor=None, words_extractor=None)
```

<!-- --8<-- [start:UnadaptedReadabilityStats] -->
Readability formulas made for English, German or Italian, computed from the basic statistics of a text with the coefficients they were published with, without a calibration for its language. Their values compare texts of one language with each other; they are no grade levels of another language. The data source is a text, a `Doc` object of [spaCy](https://github.com/explosion/spaCy) or a ready `BasicStats` object, as for `ReadabilityStats`.

Raises:

- `SourceTypeError` - a source that is neither a string, a `Doc` nor a `BasicStats` object, basic statistics of another class, an extractor of another type, a string or a `Doc` for a class without `basic_stats_class`;
- `SourceError` - a source without words or without sentences.
<!-- --8<-- [end:UnadaptedReadabilityStats] -->

=== "Code"

    ``` python
    import re

    from anyts.basic_stats import BasicStats
    from anyts.unadapted_readability_stats import UnadaptedReadabilityStats


    class Basic(BasicStats):
        def count_syllables(self, word):
            return len(re.findall(r"[aeiouy]+", word, re.IGNORECASE))


    class Unadapted(UnadaptedReadabilityStats):
        basic_stats_class = Basic


    stats = Unadapted("The cat sat on the mat. A beautiful day came, and the extraordinary dog barked!")
    stats.print_stats()
    ```

=== "Result"

    ```
               Metric            |  Value
    ----------------------------------------
    FORCAST grade                |   9.00
    Linsear Write grade          |   3.75
    Powers-Sumner-Kearl grade    |   5.36
    McAlpine EFLAW score         |  13.00
    Wiener Sachtextformel 1      |   2.29
    Wiener Sachtextformel 2      |   2.99
    Wiener Sachtextformel 3      |   4.27
    Wiener Sachtextformel 4      |   3.96
    Dickes-Steiwer index         |  46.26
    Gulpease index               |  87.67
    Fucks index                  |  11.50
    Strain index                 |   3.45
    Easy listening formula (ELF) |   4.00
    Wheeler-Smith index          |  20.00
    ```

## Parameters

<!-- --8<-- [start:UnadaptedReadabilityStats-parameters] -->
| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `source` | `str` / `Doc` / `BasicStats` | - | Data source |
| `sents_extractor` | `SentsExtractor` | `None` | Sentence extraction tool, not used for ready basic statistics |
| `words_extractor` | `WordsExtractor` | `None` | Word extraction tool, not used for ready basic statistics |
<!-- --8<-- [end:UnadaptedReadabilityStats-parameters] -->

## Attributes

<!-- --8<-- [start:UnadaptedReadabilityStats-attributes] -->
| Attribute | Type | Description |
| :-------- | :--- | :---------- |
| `bs` | `BasicStats` | Basic statistics of the text |
<!-- --8<-- [end:UnadaptedReadabilityStats-attributes] -->

## Metrics

<!-- --8<-- [start:UnadaptedReadabilityStats-metrics] -->
Every metric is a property of the object, computed on each access from `bs`, and `get_stats` gives them all. A hard word has `complex_syl_factor` syllables or more (3), a long word `long_word_letter_factor` letters or more (7).

| Metric | Language and readers | Range | Higher means |
| :----- | :------------------- | :---- | :----------- |
| [`forcast`](#forcast) | English technical texts, a grade | 20 and below | Harder |
| [`linsear_write`](#linsear_write) | English, a grade | -1 and above | Harder |
| [`powers_sumner_kearl`](#powers_sumner_kearl) | English primary school texts, a grade | Any | Harder |
| [`eflaw`](#eflaw) | English for foreign learners | 1 and above | Harder |
| [`wiener_sachtextformel_1`](#wiener_sachtextformel) ... [`wiener_sachtextformel_4`](#wiener_sachtextformel) | German non-fiction, a grade from 4 to 15 | Any | Harder |
| [`dickes_steiwer`](#dickes_steiwer) | German, without syllables | Any | Easier |
| [`gulpease`](#gulpease) | Italian, by letters | 0-100 for most texts | Easier |
| [`fucks`](#fucks) | German, syllables per sentence | 0 and above | Harder |
| [`strain_index`](#strain_index) | English | 0 and above | Harder |
| [`elf`](#elf) | English texts read aloud | 0 and above | Harder |
| [`wheeler_smith`](#wheeler_smith) | English primary school texts | 0 and above | Harder |
<!-- --8<-- [end:UnadaptedReadabilityStats-metrics] -->

<div class="metric-card" markdown>

### FORCAST { #forcast }

`forcast`
{ .metric-meta }

<!-- --8<-- [start:calc_forcast] -->
``` {.python .signature}
calc_forcast(n_monosyllable_words, n_words)
```

The grade of Caylor et al. (1973) for technical texts: 20 minus a tenth of the monosyllabic words per 150 words; `nan` without words.

$$
\textrm{FORCAST} = 20 - \frac{150 \times \textrm{Monosyllabic words}}{10 \times \textrm{Words}}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `n_monosyllable_words` | `int` | - | Number of monosyllabic words |
| `n_words` | `int` | - | Number of words |
<!-- --8<-- [end:calc_forcast] -->

</div>

<div class="metric-card" markdown>

### Linsear Write { #linsear_write }

`linsear_write`
{ .metric-meta }

<!-- --8<-- [start:calc_linsear_write] -->
``` {.python .signature}
calc_linsear_write(n_easy_words, n_hard_words, n_sents)
```

The grade of O'Hayre (1966): an easy word, of one or two syllables, weighs 1 and a hard one 3; their sum per sentence $r$ is halved above 20, and otherwise loses 2 before it is halved. It is computed over the whole text rather than a sample of 100 words; `nan` without sentences.

$$
r = \frac{\textrm{Easy words} + 3 \times \textrm{Hard words}}{\textrm{Sentences}}, \quad \textrm{LW} = \begin{cases} r / 2 & r > 20 \\ (r - 2) / 2 & r \le 20 \end{cases}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `n_easy_words` | `int` | - | Number of the words of one or two syllables |
| `n_hard_words` | `int` | - | Number of the words of three syllables or more |
| `n_sents` | `int` | - | Number of sentences |
<!-- --8<-- [end:calc_linsear_write] -->

</div>

<div class="metric-card" markdown>

### Powers-Sumner-Kearl { #powers_sumner_kearl }

`powers_sumner_kearl` · [Powers et al. 1958](https://doi.org/10.1037/h0043254)
{ .metric-meta }

<!-- --8<-- [start:calc_powers_sumner_kearl] -->
``` {.python .signature}
calc_powers_sumner_kearl(n_syllables, n_words, n_sents)
```

The recalculation of the Flesch formula by Powers, Sumner and Kearl (1958) as a grade, for primary school texts; `nan` without words or sentences.

$$
\textrm{PSK} = 0.0778 \times \textrm{ASL} + 4.55 \times \textrm{ASW} - 2.2029
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `n_syllables` | `int` | - | Number of syllables |
| `n_words` | `int` | - | Number of words |
| `n_sents` | `int` | - | Number of sentences |
<!-- --8<-- [end:calc_powers_sumner_kearl] -->

</div>

<div class="metric-card" markdown>

### McAlpine EFLAW { #eflaw }

`eflaw`
{ .metric-meta }

<!-- --8<-- [start:calc_eflaw] -->
``` {.python .signature}
calc_eflaw(n_mini_words, n_words, n_sents)
```

The score of McAlpine (2005) for readers of English as a foreign language: the words and the mini words, of one to three letters (`mini_word_letters`), per sentence; 20 and below is very easy, 30 and above confusing. `nan` without sentences.

$$
\textrm{EFLAW} = \frac{\textrm{Words} + \textrm{Mini words}}{\textrm{Sentences}}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `n_mini_words` | `int` | - | Number of the words of one to three letters |
| `n_words` | `int` | - | Number of words |
| `n_sents` | `int` | - | Number of sentences |
<!-- --8<-- [end:calc_eflaw] -->

</div>

<div class="metric-card" markdown>

### Wiener Sachtextformel { #wiener_sachtextformel }

`wiener_sachtextformel_1` · `wiener_sachtextformel_2` · `wiener_sachtextformel_3` · `wiener_sachtextformel_4`
{ .metric-meta }

<!-- --8<-- [start:calc_wiener_sachtextformel] -->
``` {.python .signature}
calc_wiener_sachtextformel(n_polysyllable_words, n_long_words, n_monosyllable_words, n_words, n_sents, variant=1)
```

The four formulas of Bamberger and Vanecek (1984) for German non-fiction, a grade from 4 to 15, over the percentages of the words of three syllables or more (MS), of more than six letters (IW) and of one syllable (ES) and the mean sentence length (SL); `nan` without words or sentences. A variant that is not an integer from 1 to 4 raises `ParameterError`.

$$
\begin{aligned} \textrm{WSTF}_1 &= 0.1935 \cdot \textrm{MS} + 0.1672 \cdot \textrm{SL} + 0.1297 \cdot \textrm{IW} - 0.0327 \cdot \textrm{ES} - 0.875 \\ \textrm{WSTF}_2 &= 0.2007 \cdot \textrm{MS} + 0.1682 \cdot \textrm{SL} + 0.1373 \cdot \textrm{IW} - 2.779 \\ \textrm{WSTF}_3 &= 0.2963 \cdot \textrm{MS} + 0.1905 \cdot \textrm{SL} - 1.1144 \\ \textrm{WSTF}_4 &= 0.2744 \cdot \textrm{MS} + 0.2656 \cdot \textrm{SL} - 1.693 \end{aligned}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `n_polysyllable_words` | `int` | - | Number of the words of three syllables or more |
| `n_long_words` | `int` | - | Number of the words of more than six letters |
| `n_monosyllable_words` | `int` | - | Number of monosyllabic words |
| `n_words` | `int` | - | Number of words |
| `n_sents` | `int` | - | Number of sentences |
| `variant` | `int` | `1` | Variant of the formula, from 1 to 4 |
<!-- --8<-- [end:calc_wiener_sachtextformel] -->

</div>

<div class="metric-card" markdown>

### Dickes-Steiwer { #dickes_steiwer }

`dickes_steiwer`
{ .metric-meta }

<!-- --8<-- [start:calc_dickes_steiwer] -->
``` {.python .signature}
calc_dickes_steiwer(n_letters, n_words, n_sents, n_types)
```

The short formula of Dickes and Steiwer (1977) for German, as Bamberger and Vanecek (1984) give it, over the letters per word, the words per sentence and the type-token ratio, without syllables; higher is easier. `nan` without words or sentences.

$$
\textrm{DS} = 235.95993 - 73.021 \ln\left(\frac{\textrm{Letters}}{\textrm{Words}} + 1\right) - 12.56438 \ln\left(\frac{\textrm{Words}}{\textrm{Sentences}} + 1\right) - 50.03293 \cdot \textrm{TTR}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `n_letters` | `int` | - | Number of the letters of the words |
| `n_words` | `int` | - | Number of words |
| `n_sents` | `int` | - | Number of sentences |
| `n_types` | `int` | - | Number of the distinct words |
<!-- --8<-- [end:calc_dickes_steiwer] -->

</div>

<div class="metric-card" markdown>

### Gulpease { #gulpease }

`gulpease`
{ .metric-meta }

<!-- --8<-- [start:calc_gulpease] -->
``` {.python .signature}
calc_gulpease(n_letters, n_words, n_sents)
```

The index of Lucisano and Piemontese (1988) for Italian, by letters rather than syllables: from 0, the hardest, to 100, the easiest; below 80 a text is hard for a reader of primary school, below 40 for a reader with a secondary education. `nan` without words.

$$
\textrm{Gulpease} = 89 + \frac{300 \times \textrm{Sentences} - 10 \times \textrm{Letters}}{\textrm{Words}}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `n_letters` | `int` | - | Number of the letters of the words |
| `n_words` | `int` | - | Number of words |
| `n_sents` | `int` | - | Number of sentences |
<!-- --8<-- [end:calc_gulpease] -->

</div>

<div class="metric-card" markdown>

### Fucks { #fucks }

`fucks`
{ .metric-meta }

<!-- --8<-- [start:calc_fucks] -->
``` {.python .signature}
calc_fucks(n_syllables, n_sents)
```

The style characteristic of Fucks (1955): the mean word length in syllables times the mean sentence length in words, the syllables per sentence; `nan` without sentences.

$$
\textrm{Fucks} = \textrm{ASW} \times \textrm{ASL} = \frac{\textrm{Syllables}}{\textrm{Sentences}}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `n_syllables` | `int` | - | Number of syllables |
| `n_sents` | `int` | - | Number of sentences |
<!-- --8<-- [end:calc_fucks] -->

</div>

<div class="metric-card" markdown>

### Strain index { #strain_index }

`strain_index`
{ .metric-meta }

<!-- --8<-- [start:calc_strain_index] -->
``` {.python .signature}
calc_strain_index(n_syllables, n_sents)
```

The index of Nathaniel (2009): the syllables of three sentences over 10, here those of three sentences on average over the whole text; `nan` without sentences.

$$
\textrm{Strain} = \frac{3 \times \textrm{Syllables}}{10 \times \textrm{Sentences}}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `n_syllables` | `int` | - | Number of syllables |
| `n_sents` | `int` | - | Number of sentences |
<!-- --8<-- [end:calc_strain_index] -->

</div>

<div class="metric-card" markdown>

### Easy listening formula { #elf }

`elf` · [Fang 1966](https://doi.org/10.1080/08838156609363529)
{ .metric-meta }

<!-- --8<-- [start:calc_elf] -->
``` {.python .signature}
calc_elf(n_syllables, n_words, n_sents)
```

The formula of Fang (1966) for texts read aloud: the syllables above one per word, per sentence; 12 and below is easy to listen to. `nan` without sentences.

$$
\textrm{ELF} = \frac{\textrm{Syllables} - \textrm{Words}}{\textrm{Sentences}}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `n_syllables` | `int` | - | Number of syllables |
| `n_words` | `int` | - | Number of words |
| `n_sents` | `int` | - | Number of sentences |
<!-- --8<-- [end:calc_elf] -->

</div>

<div class="metric-card" markdown>

### Wheeler-Smith { #wheeler_smith }

`wheeler_smith`
{ .metric-meta }

<!-- --8<-- [start:calc_wheeler_smith] -->
``` {.python .signature}
calc_wheeler_smith(n_polysyllable_words, n_sents)
```

The index of Wheeler and Smith (1954) for primary school texts: the mean sentence length times the share of the words of two syllables or more, times 10, which makes 10 such words per sentence; it reads sentences where the original reads units ended by any final mark. `nan` without sentences.

$$
\textrm{WS} = 10 \times \textrm{ASL} \times \frac{\textrm{Words of two syllables or more}}{\textrm{Words}}
$$

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `n_polysyllable_words` | `int` | - | Number of the words of two syllables or more |
| `n_sents` | `int` | - | Number of sentences |
<!-- --8<-- [end:calc_wheeler_smith] -->

</div>

## Methods

The methods `get_stats`, `to_dataframe`, `print_stats` and `describe` are those of the [statistics interface](stats.md); the formulas have no scales.

## For library developers { #hooks }

<details class="library-hooks" markdown>
<summary>Language hooks of a subclass</summary>

<!-- --8<-- [start:UnadaptedReadabilityStats-hooks] -->
A language library subclasses `UnadaptedReadabilityStats`:

| Hook | Kind | Description |
| :--- | :--- | :---------- |
| `basic_stats_class` | class attribute | Basic statistics of a string or a `Doc`, the class with the syllables of the language; without it the source must be a `BasicStats` object |
| `complex_syl_factor`, `long_word_letter_factor`, `mini_word_letters` | class attributes | Least syllables of a hard word (3), least letters of a long word (7), most letters of a mini word of EFLAW (`EFLAW_MINI_WORD_LETTERS`, 3) |
| `stats_desc`, `stats_headers` | class attributes | Metrics of `get_stats` with their descriptions (`UNADAPTED_READABILITY_STATS_DESC` by default), headers of the columns for `print_stats` |
| `messages` | class attribute | Messages of the errors by key; `MESSAGES` by default |
<!-- --8<-- [end:UnadaptedReadabilityStats-hooks] -->

</details>
