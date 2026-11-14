# Sentence lengths

``` {.python .signature}
sentence_lengths_plot(source, window=10, inset=True, ax=None, labels=None, sents_extractor=None, words_extractor=None)
```

<!-- --8<-- [start:sentence_lengths_plot] -->
The curve of the lengths of the sentences - the rhythm of a text: the length of every sentence in words, in order, the moving average over `window` sentences and an inset with the histogram of the lengths. Short and long sentences in turn are an editorial sign of a lively text, a flat curve of a monotonous one. The function takes the axes `ax` and returns `Axes`.
<!-- --8<-- [end:sentence_lengths_plot] -->

``` python
from anyts.visualizers import sentence_lengths_plot

text = "The cat sleeps. Does the dog? It eats, she said. Then both of them went out."
sentence_lengths_plot(text, window=2)
```

## Parameters

<!-- --8<-- [start:sentence_lengths_plot-parameters] -->
| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `source` | `str` / `Doc` / `Document` / `Iterable[int]` | - | Text, Doc or Document object or lengths of the sentences (a list, a numpy array, a Series) |
| `window` | `int` | `10` | Window of the moving average in sentences |
| `inset` | `bool` | `True` | Show the inset with the histogram |
| `ax` | `Axes` | `None` | Axes for the plot |
| `labels` | `dict[str, str]` | `None` | Labels over the defaults: `title`, `xlabel`, `ylabel`, `length` (the curve), `average` (a format string with `window`), `distribution` (the inset) |
| `sents_extractor` | `SentsExtractor` | `None` | Extractor of the sentences of the text, used in place of those of the document |
| `words_extractor` | `WordsExtractor` | `None` | Extractor of the words of a sentence of the text, used in place of those of the document |

The source and the extractors raise the errors of `sentence_lengths`, and no sentences raise `SourceError`; a `window` that is not an integer of at least one, labels that `merge_labels` refuses and an `ax` that is not a matplotlib `Axes` raise `ParameterError`.
<!-- --8<-- [end:sentence_lengths_plot-parameters] -->

Without an extractor the sentences and the words are those of the [document](https://sergeyshk.github.io/anyTS/document/) of the source (`to_document`); with one, the text is split by the extractors, `SentsExtractor()` and `WordsExtractor()` for the one not given.

## Lengths of the sentences { #sentence_lengths }

``` {.python .signature}
sentence_lengths(source, sents_extractor=None, words_extractor=None)
```

<!-- --8<-- [start:sentence_lengths] -->
The lengths of the sentences in words, in order: the sentences of the document of a text, a `Doc` or a `Document` (`to_document`) and their words with a letter or a digit, or, with an extractor given, the sentences and the words of the extractors on the text. Sentences without words are skipped. Ready lengths (non-negative integers in a sequence or an iterator) are used as they are. The arguments are those of `sentence_lengths_plot`.

A table, a set, a mapping, bytes, a length that is not an integer and an extractor of another type raise `SourceTypeError`, a negative length `SourceError`.
<!-- --8<-- [end:sentence_lengths] -->

=== "Code"

    ``` python
    from anyts.visualizers import sentence_lengths

    sentence_lengths("The cat sleeps. Does the dog? It eats, she said. Then both of them went out.")
    ```

=== "Result"

    ```
    [3, 3, 4, 6]
    ```
