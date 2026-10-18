# Statistics interface

!!! info ""
    **anyts.stats.Stats**

## Description

<!-- --8<-- [start:Stats] -->
The common interface of the classes of statistics: the dictionary of the statistics, nested or flat, a one-row frame of [pandas](https://pandas.pydata.org/), a printed table with descriptions and the reading of a statistic by its scale. Every class of statistics is built on it, those of a language library too.
<!-- --8<-- [end:Stats] -->

## Hooks

<!-- --8<-- [start:Stats-hooks] -->
A class of statistics subclasses `Stats`:

| Hook | Kind | Description |
| :--: | :--: | :---------: |
| `stats_desc` | class attribute | Statistics of the class with their descriptions; each is an attribute or a property of the object |
| `stat_names()` | method | Names of the statistics of `get_stats`; the keys of `stats_desc` by default |
| `stats_headers` | class attribute | Headers of the columns for `print_stats`; `("Statistic", "Value")` by default |
| `level_scales` | class attribute | Interpretation scales of `describe` by statistic, as lower bounds and their bands in descending order; none by default |
| `level_scale(stat)` | method | Interpretation scale of a statistic; `level_scales` by default, overridden when the scale depends on the parameters of the object |
| `messages` | class attribute | Messages of the errors by key; `MESSAGES` by default, checked when the class is defined |

A scale of `level_scales` that is not pairs of a finite lower bound and a band with the bounds descending raises `ParameterError` when the class is defined.
<!-- --8<-- [end:Stats-hooks] -->

## Methods

### get_stats

<!-- --8<-- [start:Stats-get_stats] -->
Returns a copy of the statistics of `stat_names`: editing it does not change the object. With `flat=True` the values of a dictionary statistic become keys of their own, joined to its name with an underscore: the distribution `{3: 5}` of `c_lengths` gives the key `c_lengths_3`.

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `flat` | bool | `False` | Turn the values of the dictionary statistics into keys of their own |
<!-- --8<-- [end:Stats-get_stats] -->

### to_dataframe

<!-- --8<-- [start:Stats-to_dataframe] -->
Returns the flat statistics, `get_stats(flat=True)`, as a `pandas.DataFrame` of one row with a column for every key. A dictionary statistic gives columns only for the keys the text has, so in frames of several texts joined with `pandas.concat` a count a text lacks is `NaN`. Only these columns may be filled with 0: elsewhere `NaN` is an undefined value.
<!-- --8<-- [end:Stats-to_dataframe] -->

### print_stats

<!-- --8<-- [start:Stats-print_stats] -->
Prints a table of the statistics of `stats_desc` with their descriptions under the headers of `stats_headers`, floats with two decimals; each column is as wide as its longest text.
<!-- --8<-- [end:Stats-print_stats] -->

### describe

<!-- --8<-- [start:Stats-describe] -->
Returns the band of the scale of a statistic (`level_scale`), and `None` for a statistic without a scale or with an undefined value (nan). A name that is neither of `stat_names` nor a public property of the class raises `UnknownStatError`.

Parameters:

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `stat` | str | `-` | Name of the statistic |
<!-- --8<-- [end:Stats-describe] -->

The band is found by [`scale_level`](readability_stats_funcs.md#band-of-a-scale); `ReadabilityStats` also reads the grade formulas by school stages.

## Usage example

!!! example "Example"

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
    size.get_stats(flat=True)
    # {'n_words': 6, 'c_lengths_3': 5}
    size.describe("n_words")
    # 'short'
    size.print_stats()
    #    Statistic    |  Value
    # ---------------------------
    # Words           |    6
    # Words by length |  {3: 5}
    ```
