# HTML report

The report of a text in one HTML file with nothing outside it: no script, no style sheet, no font and no image to fetch, so that it opens without a network and can be sent as it is. A language library sets its classes, its highlighting and the texts in its language, and its command line writes the report (`<command> report`).

## Report { #Report }

<!-- --8<-- [start:Report] -->
``` {.python .signature}
Report(source, title=None, stats_classes=None)
```

The HTML report of the statistics of a text. The text is parsed once (`parse`), and its sections follow `sections`, each a method `section_<name>` that gives a fragment of HTML:

| Section | Content |
| :------ | :------ |
| `statistics` | A table per class of `stats_classes`: the description of every statistic of `stat_names`, its value - a float with two decimals, a distribution as its pairs - and its reading (`describe`) |
| `sentences` | The text of every sentence with the statistics of `sentence_columns` ([`by_parts`](https://sergeyshk.github.io/anyTS/stats/stats/#by_parts)); none without them |
| `highlight` | The text highlighted by `highlight_class` with its default layers; none without it |
| `plots` | The plots of `plots` in SVG with their captions: the lengths of the sentences (`sentence_lengths_plot`) by default; none for a text without sentences |

The style is in the page and the plots draw their text as paths, so they need no font. Every text of the source and of the statistics goes through `escape`, so that it never becomes markup.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `source` | `str` / `Doc` / `Document` | - | Data source |
| `title` | `str` | `None` | Title of the report; the text `title` by default |
| `stats_classes` | `dict[str, type[Stats]]` | `None` | Classes of statistics by name; those of the class by default |

The object keeps `document`, `title` and the statistics of every class by name, `stats`. `to_html()` returns the page, and `save(path, encoding="utf-8")` writes it to a file. A source a class cannot count raises the error of the class.
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
| `sentence_columns` | class attribute | Statistics of every sentence, as pairs of the name of a class and of a statistic; none by default |
| `highlight_class` | class attribute | Highlighting of the text (`HighlightedText`), with its default layers; none by default |
| `visualizer_labels` | class attribute | Labels of the plots by visualizer, over `VISUALIZER_LABELS`; none by default |
| `texts` | class attribute | Headings and labels by key, `REPORT_TEXTS` by default, the language of the page `lang` among them: complete, as the messages of a class of statistics |
| `sections` | class attribute | Sections in their order; `("statistics", "sentences", "highlight", "plots")` by default |
| `section_<name>()` | method | Fragment of HTML of a section; a library overrides one or adds its own and names it in `sections` |
| `parse(source)` | method | Document of a source, once for all the sections; `to_document` by default |
| `compute(cls, document)` | method | Statistics of a class of the document, as `compute` of `Command` |
| `plots()` | method | Captions and figures of matplotlib of the section `plots` |
<!-- --8<-- [end:Report-hooks] -->

</details>
