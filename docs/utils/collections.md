# Collections and phrases

!!! info ""
    **anyts.utils**

A fixed order of a collection, the search of phrases in a list of words and the counts of the words of spans.

## in_order

<!-- --8<-- [start:in_order] -->
`in_order(words)` puts a collection of words in a fixed order: a list keeps its order, a set or a mapping is sorted.
<!-- --8<-- [end:in_order] -->

## find_phrases

<!-- --8<-- [start:find_phrases] -->
Finds phrases in a sequence of words and gives their bounds as slices of the words, in order. The words and the phrases are compared by their normalized forms, the lower case by default; at every position the longest phrase is taken, the phrases found do not overlap, and empty phrases are skipped. Words that are not a list of strings raise `SourceTypeError`.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `words` | list[str] | `-` | Words of the text |
| `phrases` | list[str] | `-` | Phrases, words separated by spaces |
| `normalize` | Callable | `str.lower` | Normalized form of a word and of a phrase |
<!-- --8<-- [end:find_phrases] -->

!!! example "Example"

    ``` python
    from anyts.utils import find_phrases

    find_phrases(["In", "fact", "it", "rains"], ["in fact", "in"])
    # [(0, 2)]
    ```

## count_words_by_spans

<!-- --8<-- [start:count_words_by_spans] -->
Counts the words in every span of a text - a sentence, say - by the positions of the first characters of the words and the bounds of the spans, both in order. A word belongs to the span of its first character, and a span without words is skipped. Positions or spans that are not a sequence raise `SourceTypeError`.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `starts` | list[int] | `-` | Positions of the first characters of the words |
| `spans` | list[tuple[int, int]] | `-` | Spans: the start and the position after the end |
<!-- --8<-- [end:count_words_by_spans] -->

!!! example "Example"

    ``` python
    from anyts.utils import count_words_by_spans

    count_words_by_spans([0, 4, 10, 14, 20], [(0, 9), (9, 10), (10, 19), (20, 24)])
    # [2, 2, 1]
    ```
