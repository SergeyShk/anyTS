# HTML report

The report of a text in one HTML file with nothing outside it: no script, no style sheet, no font and no image to fetch, so that it opens without a network and can be sent as it is. A language library sets its classes, its highlighting and the texts in its language, and its command line writes the report (`<command> report`).

## Report { #Report }

<!-- --8<-- [start:Report] -->
``` {.python .signature}
Report(source, title=None, stats_classes=None, *, skip_errors=False)
```

The HTML report of the statistics of a text. The text is parsed once (`parse`), every class counts it and its sentences by `compute`, and its sections follow `sections`, each a method `section_<name>` that gives a fragment of HTML:

| Section | Content |
| :------ | :------ |
| `statistics` | A table per class of `stats_classes` under its title (`titles`): the description of every statistic of `stats_desc`, as `print_stats`, its value - a float with two decimals, a smaller one than 0.1 with two significant digits, a distribution as its pairs from the most frequent, with the values described by `value_desc`, an undefined value as the text `undefined` - and its reading (`describe`); the classes left out by `skip_errors` are named above |
| `sentences` | The text of every sentence with words, numbered as on the plot of their lengths, with the statistics of `sentence_columns` ([`by_parts`](https://sergeyshk.github.io/anyTS/stats/stats/#by_parts)); none without them. A text of more than `max_sentences` such sentences has those with the highest values of the first statistic, in their order |
| `highlight` | The text highlighted by `highlight_class` with its default layers, its styles in the head of the page; none without it |
| `plots` | The plots of `plots` in SVG with their captions: the lengths of the sentences (`sentence_lengths_plot`) by default, without a mark on every sentence for a text of more than 300 of them; none for a text without sentences |

The page is the same for the same text, and no text of the source or of the statistics becomes markup.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `source` | `str` / `Document` | - | Data source |
| `title` | `str` | `None` | Title of the report; the text `title` by default |
| `stats_classes` | `dict[str, type[Stats]]` | `None` | Classes of statistics by name; those of the class by default |
| `skip_errors` | `bool` | `False` | Leave out a class that cannot count the source, with its error in `errors`, instead of raising it |

The object keeps its classes by name, `classes`, `document`, `title`, the statistics of every class by name, `stats`, and the errors of the classes left out, `errors`. `to_html()` returns the page, and `save(path)` writes it to a file in UTF-8, the encoding the page declares. A source a class cannot count raises the error of the class, unless `skip_errors`; a `skip_errors` that is not a `bool` and `stats_classes` that are not a dictionary of classes of statistics raise `ParameterError`.
<!-- --8<-- [end:Report] -->

=== "Code"

    ``` python
    from anyts.basic_stats import BasicStats
    from anyts.report import Report


    class Vowels(BasicStats):
        def count_syllables(self, word):
            return sum(char in "aeiou" for char in word.lower())


    class VowelsReport(Report):
        stats_classes = {"basic": Vowels}
        sentence_columns = (("basic", "n_words"), ("basic", "n_syllables"))


    report = VowelsReport("The cat sleeps. A dog barks loudly!", title="Two sentences")
    page = report.to_html()
    page.startswith("<!DOCTYPE html>"), page.count("<svg"), report.stats["basic"].n_words
    ```

=== "Result"

    ```
    (True, 1, 7)
    ```

## Text for HTML { #escape }

<!-- --8<-- [start:escape] -->
``` {.python .signature}
escape(value)
```

Returns the text of a value, its `str`, for HTML: the characters `&`, `<`, `>`, `"` and `'` become character references, so that a text of the source or of the statistics never becomes markup, in an element or in an attribute.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `value` | `object` | - | Value |
<!-- --8<-- [end:escape] -->

=== "Code"

    ``` python
    from anyts.report import escape

    escape('<script>alert("x")</script>')
    ```

=== "Result"

    ```
    '&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;'
    ```

## For library developers { #hooks }

<details class="library-hooks" markdown>
<summary>Hooks of a report</summary>

<!-- --8<-- [start:Report-hooks] -->
A report of a library subclasses `Report`:

| Hook | Kind | Description |
| :--- | :--- | :---------- |
| `stats_classes` | class attribute | Classes of statistics by name; none by default |
| `titles` | class attribute | Headings of the classes by name; the names by default |
| `sentence_columns` | class attribute | Statistics of every sentence, as pairs of the name of a class and of a statistic, a key of its flat statistics among them; none by default |
| `max_sentences` | class attribute | Sentences of the table at most, those with the highest values of its first statistic for a longer text; 100 by default |
| `highlight_class` | class attribute | Highlighting of the text (`HighlightedText`), with its default layers; none by default |
| `visualizer_labels` | class attribute | Labels of the plots by visualizer, over `VISUALIZER_LABELS`; none by default |
| `texts` | class attribute | Headings and labels by key, `REPORT_TEXTS` by default, the language of the page `lang` among them: complete, as the messages of a class of statistics |
| `messages` | class attribute | Messages of the errors of the report by key, `MESSAGES` by default: complete |
| `sections` | class attribute | Sections in their order; `("statistics", "sentences", "highlight", "plots")` by default |
| `section_<name>()` | method | Fragment of HTML of a section; a library overrides one or adds its own and names it in `sections` |
| `parse(source)` | method | Document of a source, once for all the sections; `to_document` by default. It may read `classes`, set before it, to annotate only what the classes of the report need |
| `compute(stats_class, document)` | class method | Statistics of a class of the document or of its sentence; `DiversityStats` of the words of the document (`document_words`). `compute` of `Command` is that of its report, so that the command counts alike |
| `plots()` | method | Captions and figures of matplotlib of the section `plots`, made on a `Figure`, not with `pyplot`, so that a command chooses no interactive backend |
<!-- --8<-- [end:Report-hooks] -->

</details>
