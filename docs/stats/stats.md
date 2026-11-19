# Statistics interface

``` {.python .signature}
Stats()
```

<!-- --8<-- [start:Stats] -->
The common interface of the classes of statistics. Every class of statistics is built on it, those of a language library too.

Raises:

- `ParameterError` - when a subclass is defined, messages that `check_messages` rejects, a scale of `level_scales` that is not pairs of a finite lower bound and a band with the bounds descending, and an attribute of 0.4 the core no longer reads: `words_extractor_class`, `sents_extractor_class` and `join_hyphens` (the document comes from `parse`, the words of the counters from `doc_words`) and `doc_units` (`analyze`).
<!-- --8<-- [end:Stats] -->

=== "Code"

    ``` python
    from anyts.stats import Stats


    class TextSize(Stats):
        stats_desc = {"n_words": "Words", "c_lengths": "Words by length"}
        level_scales = {"n_words": ((100, "long"), (0, "short"))}

        def __init__(self, text):
            words = text.split()
            self.n_words = len(words)
            self.c_lengths = {3: sum(len(word) == 3 for word in words)}


    size = TextSize("The cat sat on the mat")
    size.print_stats()
    ```

=== "Result"

    ```
       Statistic    |  Value
    ---------------------------
    Words           |    6
    Words by length |  {3: 5}
    ```

## Methods

<!-- --8<-- [start:Stats-get_stats] -->
`get_stats(*, flat=False)` returns a copy of the statistics of `stat_names`: editing it does not change the object. With `flat=True` the values of a dictionary statistic become keys of their own, joined to its name with an underscore: the distribution `{3: 5}` of `c_lengths` gives the key `c_lengths_3`.
<!-- --8<-- [end:Stats-get_stats] -->

<!-- --8<-- [start:Stats-to_dataframe] -->
`to_dataframe()` returns the flat statistics, `get_stats(flat=True)`, as a one-row `DataFrame` of [pandas](https://pandas.pydata.org/) with a column for every key. A dictionary statistic gives columns only for the keys the text has; the table of several texts, with 0 for a count a text lacks, is that of [`stats_dataframe`](https://sergeyshk.github.io/anyTS/stats/stats/#stats_dataframe).
<!-- --8<-- [end:Stats-to_dataframe] -->

<!-- --8<-- [start:Stats-print_stats] -->
`print_stats()` prints a table of the statistics of `stats_desc` with their descriptions under the headers of `stats_headers`, floats with two decimals; each column is as wide as its longest text.
<!-- --8<-- [end:Stats-print_stats] -->

<!-- --8<-- [start:Stats-describe] -->
`describe(stat)` returns the band of the scale of the statistic `stat` (`level_scale`), and `None` for a statistic without a scale, with an undefined value (nan) or for a key of the flat statistics (`get_stats(flat=True)`), a key of any value of a dictionary statistic included, as the table of another text may have it. A name that is neither of `stat_names` nor a public property of the class raises `UnknownStatError`.
<!-- --8<-- [end:Stats-describe] -->

=== "Code"

    ``` python
    size.get_stats()
    size.get_stats(flat=True)
    size.describe("n_words")
    size.to_dataframe()
    ```

=== "Result"

    ```
    {'n_words': 6, 'c_lengths': {3: 5}}
    {'n_words': 6, 'c_lengths_3': 5}
    'short'
       n_words  c_lengths_3
    0        6            5
    ```

The band is found by [`scale_level`](readability_stats.md#scale_level); `ReadabilityStats` also reads the grade formulas by school stages.

## Parts of a text { #by_parts }

<!-- --8<-- [start:Stats-by_parts] -->
`by_parts(source, parts="sentences", **params)`, a class method, returns the statistics of every sentence (`parts="sentences"`) or paragraph (`"paragraphs"`) of a data source as a `DataFrame`: a row per part, indexed by its number, with its `start` and `end` in the text of the document and its flat statistics, joined by `stats_dataframe`. The source is parsed once, by `parts_document` of the class, and the class with the parameters `params` counts the document of every part ([`document_part`](https://sergeyshk.github.io/anyTS/document/#document_part)); the classes of readability parse as their `basic_stats_class`. A part without words, such as a line of asterisks, or one the class cannot count, such as a number alone on a line for a class without numbers among its words, keeps its row without statistics; a source with no part the class can count raises the error of the class. The numbers of the words and the sentences of the parts add up to those of the whole text, while the unique words, the shares and the means are those of every part.

The parts of a class are its `part_kinds`: `CohesionStats`, whose links run between sentences, counts paragraphs, and `DiversityStats`, which takes words, no parts. Other parts raise `ParameterError`; the source and a part raise the errors of the class.
<!-- --8<-- [end:Stats-by_parts] -->

=== "Code"

    ``` python
    from anyts.basic_stats import BasicStats


    class Vowels(BasicStats):
        def count_syllables(self, word):
            return sum(char in "aeiou" for char in word.lower())


    text = "The cat sleeps. A dog barks loudly.\n\nA bird sings."
    Vowels.by_parts(text)[["start", "end", "n_words", "n_syllables"]]
    Vowels.by_parts(text, "paragraphs")[["start", "end", "n_sents", "n_words"]]
    ```

=== "Result"

    ```
              start  end  n_words  n_syllables
    sentence
    0             0   15        3            4
    1            16   35        4            5
    2            37   50        3            3
               start  end  n_sents  n_words
    paragraph
    0              0   35        2        7
    1             37   50        1        3
    ```

## Table of several texts { #stats_dataframe }

<!-- --8<-- [start:stats_dataframe] -->
``` {.python .signature}
stats_dataframe(stats, index=None, *, messages=None)
```

Returns the flat statistics of several objects of statistics as one `DataFrame`: a row per object, labelled by `index` or numbered, and a column for every key of any of them. A value of a dictionary statistic an object lacks is 0, since its text has no such value, while any other value it lacks is `NaN`. The values of a dictionary with keys of numbers, such as the words by their length, go in the order of the keys.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `stats` | `list[Stats]` | - | Objects of statistics |
| `index` | `list` | `None` | Labels of the rows; their numbers by default |
| `messages` | `dict[str, str]` | `None` | Messages of the errors by key, in place of those of the library |

A value that is not a list, or holds an object that is not of a class of statistics, raises `SourceTypeError`.
<!-- --8<-- [end:stats_dataframe] -->

=== "Code"

    ``` python
    from collections import Counter

    from anyts.stats import Stats, stats_dataframe


    class TextSize(Stats):
        stats_desc = {"n_words": "Words", "c_lengths": "Words by length"}

        def __init__(self, text):
            words = text.split()
            self.n_words = len(words)
            self.c_lengths = dict(sorted(Counter(map(len, words)).items()))


    stats_dataframe([TextSize("The cat sat"), TextSize("A mouse ran away")], index=["first", "second"])
    ```

=== "Result"

    ```
            n_words  c_lengths_1  c_lengths_3  c_lengths_4  c_lengths_5
    first         3            0            3            0            0
    second        4            1            1            1            1
    ```

## For library developers { #hooks }

<details class="library-hooks" markdown>
<summary>Language hooks of a subclass</summary>

<!-- --8<-- [start:Stats-hooks] -->
A class of statistics subclasses `Stats`:

| Hook | Kind | Description |
| :--- | :--- | :---------- |
| `parse(source)` | method | Document of anySeg of a string, a `Doc` or a `Document` ([`to_document`](https://sergeyshk.github.io/anyTS/document/#to_document) by default); a library overrides it to segment and annotate a string in its language. The classes that read a text take their words and sentences from it |
| `stats_desc` | class attribute | Statistics of the class with their descriptions; each is an attribute or a property of the object |
| `stat_names()` | method | Names of the statistics of `get_stats`; the keys of `stats_desc` by default |
| `stats_headers` | class attribute | Headers of the columns for `print_stats`; `("Statistic", "Value")` by default |
| `level_scales` | class attribute | Interpretation scales of `describe` by statistic, as lower bounds and their bands in descending order; none by default |
| `level_scale(stat)` | method | Interpretation scale of a statistic; `level_scales` by default, overridden when the scale depends on the parameters of the object |
| `messages` | class attribute | Messages of the errors by key; `MESSAGES` by default |
| `part_kinds` | class attribute | Parts `by_parts` counts; `("sentences", "paragraphs")` by default |
| `parts_document(source, **params)` | class method | Document whose parts `by_parts` counts, given the parameters of the class: `parse` of an object made without `__init__` by default; a class whose `parse` needs its parameters, or that annotates a string outside `parse`, overrides it |
<!-- --8<-- [end:Stats-hooks] -->

</details>
