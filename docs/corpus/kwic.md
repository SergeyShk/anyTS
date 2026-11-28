# KWIC concordance

``` {.python .signature}
kwic(source, keyword, window=5, by_lemma=False, ignore_case=True, tokenize=None, lemmatize=None, fold=str.lower, sentenize=None, *, messages=None)
```

<!-- --8<-- [start:kwic] -->
A KWIC concordance (keyword in context) - every occurrence of a word or a phrase with its context on both sides. Occurrences are found among the words of the text by the word form, ignoring case or respecting it (`ignore_case=False`), or by the lemma (`by_lemma=True`); the keyword is lemmatized as a string, so with a lemmatizer a phrase may be written in any form and without one it is given by lemmas. The words are those of the [document](https://sergeyshk.github.io/anyTS/document/) of the text - the tokens of a string by the tokenizer, of a `Document` its own - and the keyword is split as a string: a tokenizer that splits a string as the document is split finds the same in both. A word has a letter or a digit, so punctuation and symbols are not words; forms are compared in the composed form of Unicode (NFC), without soft hyphens, and forms and lemmas without the final period of a word with a letter: a tokenizer by Universal Dependencies leaves the period of an abbreviation to it inside a sentence and splits it off at the end, so the keyword `Sr.` finds the word of `El Sr. García vino` and `EE. UU.` the words of `Viajó a EE. UU. en mayo`.

A phrase does not cross the end of a sentence or a paragraph of the document unless the keyword has a final mark or a sentence start in the same place (`U.S. Army`). The sentences are those of a `Document`, or of the sentence splitter for a string and the keyword (by default those of `SentsExtractor`). The context is `window` words on each side as written, punctuation included; whitespace collapses into one space, and occurrences do not overlap.
<!-- --8<-- [end:kwic] -->

=== "Code"

    ``` python
    from anyts.corpus import kwic, print_kwic

    text = (
        "The cat was at the window and watched the birds. The birds flew away and the cat "
        "fell asleep at the window. Tomorrow the cat will be at the window and watch the birds."
    )
    lines = kwic(text, "window", window=3)
    lines[0]
    print_kwic(lines, width=20)

    lemmas = {"watched": "watch", "birds": "bird"}
    [
        line.keyword
        for line in kwic(
            text,
            "watch the bird",
            by_lemma=True,
            lemmatize=lambda word, words: [lemmas.get(word, word)],
        )
    ]
    ```

=== "Result"

    ```
    Concordance(start=19, end=25, left='was at the', keyword='window', right='and watched the')
              was at the  window  and watched the
           asleep at the  window  . Tomorrow the cat
               be at the  window  and watch the
    ['watched the birds', 'watch the birds']
    ```

## Parameters

<!-- --8<-- [start:kwic-parameters] -->
| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `source` | `str` / `Document` | - | Text or Document object |
| `keyword` | `str` | - | Word or phrase |
| `window` | `int` | `5` | Number of words of context on each side |
| `by_lemma` | `bool` | `False` | Compare lemmas instead of word forms |
| `ignore_case` | `bool` | `True` | Ignore case when comparing word forms |

A keyword without words, a window that is not an integer or is negative and a `by_lemma` or `ignore_case` that is not a `bool` raise `ParameterError`; a source that is neither a string nor a `Document`, a keyword that is not a string and a hook that is not callable raise `SourceTypeError`.
<!-- --8<-- [end:kwic-parameters] -->

## Result

<!-- --8<-- [start:Concordance] -->
``` {.python .signature}
Concordance(start, end, left, keyword, right)
```

A list of `Concordance` named tuples in the order of the text.

| Field | Type | Description |
| :---- | :--- | :---------- |
| `start` | `int` | Position of the first character of the occurrence in the text |
| `end` | `int` | Position after the last character of the occurrence |
| `left` | `str` | Context on the left |
| `keyword` | `str` | Occurrence as written in the text |
| `right` | `str` | Context on the right |
<!-- --8<-- [end:Concordance] -->

## Aligned lines { #format_kwic }

<!-- --8<-- [start:format_kwic] -->
``` {.python .signature}
format_kwic(concordances, width=40, *, messages=None)
```

Aligns the lines on the keyword in a text, one line per occurrence: the left context is cut on the left and aligned to the right, the right one cut on the right. The lines may come from any iterable and are taken in the composed form of Unicode (NFC), so the widths count characters as shown.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `concordances` | `list[Concordance]` | - | Lines of a concordance |
| `width` | `int` | `40` | Width of a context in characters |
| `messages` | `dict[str, str]` | `None` | Messages of the errors by key, in place of those of the library |

Lines that are a string, cannot be iterated or are not concordances raise `SourceTypeError`, and a `width` that is not an integer of at least one `ParameterError`.
<!-- --8<-- [end:format_kwic] -->

<!-- --8<-- [start:print_kwic] -->
``` {.python .signature}
print_kwic(concordances, width=40, *, messages=None)
```

Prints the result of `format_kwic`.
<!-- --8<-- [end:print_kwic] -->

## For library developers { #hooks }

<details class="library-hooks" markdown>
<summary>Language hooks of the parameters</summary>

<!-- --8<-- [start:kwic-hooks] -->
The language enters through four parameters:

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `tokenize` | `Callable` | `None` | The tokens of a string and of the keyword as triples of the start, the end and the text or objects with them, such as the spans of anySeg, the default tokens of `to_document` filling the gaps; words of `\w` and punctuation marks by default |
| `lemmatize` | `Callable` | `None` | The lemmas of a word, given its text and its words of Universal Dependencies (`Word` objects of anySeg; none for the keyword), or one lemma as a string; a word matches when one of its lemmas is one of those of the keyword |
| `fold` | `Callable` | `str.lower` | The folding of a word form (with `ignore_case`) or a lemma before the comparison, such as the letters a language takes for the same |
| `sentenize` | `Callable` | `None` | The sentences, as triples of the start, the end and the text or objects with them in any order, of a string and of the keyword; those of `SentsExtractor` by default |
| `messages` | `dict[str, str]` | `None` | Messages of the errors by key, in place of those of the library |

A `tokenize` that does not give the tokens in order as triples or spans of integer bounds within the string and a string raises `SourceTypeError`, and so does a `sentenize` whose sentences do not lie within it. By default the lemmas of a word are the word itself and, for a token of one word of Universal Dependencies with a lemma, that lemma: a word is found by its own form, and a word of a document with lemmas by its lemma too.
<!-- --8<-- [end:kwic-hooks] -->

</details>
