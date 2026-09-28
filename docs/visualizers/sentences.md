# Sentence lengths

!!! info ""
    **anyts.visualizers.sentence_lengths_plot()**, **anyts.visualizers.sentence_lengths()**

## Description

<!-- --8<-- [start:sentence_lengths_plot] -->
The curve of the lengths of the sentences - the rhythm of a text: the length of every sentence in words in order, the moving average over a window of `window` sentences and an inset with the histogram of the lengths. Short and long sentences in turn are an editorial sign of a lively text, a flat curve - of a monotonous one. The function takes the axes `ax` and returns `Axes`.
<!-- --8<-- [end:sentence_lengths_plot] -->

<!-- --8<-- [start:sentence_lengths] -->
`sentence_lengths(source)` extracts the lengths: a string is split into sentences by the sentence extractor and every sentence into words by the word extractor; the sentences of a `Doc` come from its boundaries and its words from `iter_doc_words` with `join_hyphens`, while a `Doc` without boundaries is counted as its text, by the extractors; sentences without words are skipped. Ready lengths - a sequence or an iterator of integers that are not negative - are used as they are; a table, a set, a mapping, bytes or a length that is not an integer raise `SourceTypeError`, a negative length `SourceError`.
<!-- --8<-- [end:sentence_lengths] -->

## Parameters

<!-- --8<-- [start:sentence_lengths_plot-parameters] -->
| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `source` | str/Doc/Iterable[int] | `-` | Text, Doc object or lengths of the sentences (a list, a numpy array, a Series) |
| `window` | int | `10` | Window of the moving average in sentences |
| `inset` | bool | `True` | Show the inset with the histogram |
| `ax` | Axes | `None` | Axes for the plot |
| `labels` | dict[str, str] | `None` | Labels over the defaults: `title`, `xlabel`, `ylabel`, `length` (the curve), `average` (a format string with `window`), `distribution` (the inset) |
| `sents_extractor` | SentsExtractor | `None` | Extractor of the sentences of a string; the sentence extractor of the library by default |
| `words_extractor` | WordsExtractor | `None` | Extractor of the words of a sentence of a string; the word extractor of the library by default |
<!-- --8<-- [end:sentence_lengths_plot-parameters] -->

The core functions also take `join_hyphens`, `False` by default: join the parts of hyphenated words of a `Doc` with sentence boundaries (`iter_doc_words`); a library whose tokenizer keeps hyphenated words whole sets it. The extractors of the core are `SentsExtractor()` and `WordsExtractor()`.

## Usage example

!!! example "Example"

    ``` python
    from anyts.visualizers import sentence_lengths, sentence_lengths_plot

    text = "The cat sleeps. Does the dog? It eats, she said. Then both of them went out."
    sentence_lengths(text)
    # [3, 3, 4, 6]
    sentence_lengths_plot(text, window=2)
    ```
