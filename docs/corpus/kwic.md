# KWIC concordance

!!! info ""
    **anyts.corpus.kwic()**, **anyts.corpus.format_kwic()**, **anyts.corpus.print_kwic()**, **anyts.corpus.Concordance**

## Description

<!-- --8<-- [start:kwic] -->
A KWIC concordance (keyword in context) - every occurrence of a word or a phrase with its context on the left and on the right. The occurrences are looked for among the words of the text by the word form, ignoring case or respecting it (`ignore_case=False`), or by the lemma (`by_lemma=True`), where a phrase is given by lemmas or as it is written, since every word of it is lemmatized. The text and the keyword are split into words the same way, and punctuation and symbols are words of neither. The context is `window` words on each side as they are written in the text, with the punctuation between them; whitespace collapses into one space, and occurrences do not overlap.
<!-- --8<-- [end:kwic] -->

## Language hooks

<!-- --8<-- [start:kwic-hooks] -->
The language enters through four parameters, which a language library fills in its own `kwic`:

| Parameter | Default | Description |
| :-------: | :-----: | :---------: |
| `tokenize` | a run of word characters | The words of a string and of the keyword as triples of the start, the end and the text |
| `lemmatize` | the word and the lemma of the model | The lemmas of a word, given its text and its tokens in a `Doc` (none for a string and the keyword); a word matches when one of its lemmas is one of those of the keyword |
| `fold` | `str.lower` | The folding of a word form (with `ignore_case`) or a lemma before the comparison, such as the letters a language takes for the same |
| `join_hyphens` | `False` | Join the parts of the hyphenated words of a `Doc` the tokenizer split (`iter_doc_units`) |

The words of a `Doc` are its tokens, a byte order mark at the start of a word left out. By default the lemmas of a word are the word itself and, for a word of one token of a `Doc` with lemmas, the lemma of the model, so a word is found by its own form and a `Doc` of a pipeline with a lemmatizer is searched by its lemmas.
<!-- --8<-- [end:kwic-hooks] -->

## Parameters

<!-- --8<-- [start:kwic-parameters] -->
| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `source` | str/Doc | `-` | Text or Doc object |
| `keyword` | str | `-` | Word or phrase |
| `window` | int | `5` | Number of words of context on each side |
| `by_lemma` | bool | `False` | Compare lemmas instead of word forms |
| `ignore_case` | bool | `True` | Ignore case when comparing word forms |

A keyword without words, a negative window and a hook that is not callable raise `ParameterError`; a source that is neither a string nor a `Doc` and a keyword that is not a string raise `SourceTypeError`.
<!-- --8<-- [end:kwic-parameters] -->

<!-- --8<-- [start:format_kwic] -->
`format_kwic(concordances, width=40)` aligns the lines on the keyword: the left context is cut on the left and aligned to the right, the right one is cut on the right; `width` is the width of a context in characters, at least one.
<!-- --8<-- [end:format_kwic] -->

<!-- --8<-- [start:print_kwic] -->
`print_kwic(concordances, width=40)` prints the result of `format_kwic`.
<!-- --8<-- [end:print_kwic] -->

## Result

<!-- --8<-- [start:Concordance] -->
A list of `Concordance` named tuples in the order of the text.

| Field | Type | Description |
| :---: | :--: | :---------- |
| `start` | int | Position of the first character of the occurrence in the text |
| `end` | int | Position after the last character of the occurrence |
| `left` | str | Context on the left |
| `keyword` | str | Occurrence as written in the text |
| `right` | str | Context on the right |
<!-- --8<-- [end:Concordance] -->

## Example

!!! example "Example"

    ``` python
    from anyts.corpus import kwic, print_kwic

    text = (
        "The cat was at the window and watched the birds. The birds flew away and the cat "
        "fell asleep at the window. Tomorrow the cat will be at the window and watch the birds."
    )
    lines = kwic(text, "window", window=3)
    lines[0]
    # Concordance(start=19, end=25, left='was at the', keyword='window', right='and watched the')

    print_kwic(lines, width=20)
    #           was at the  window  and watched the
    #        asleep at the  window  . Tomorrow the cat
    #            be at the  window  and watch the

    lemmas = {"watched": "watch", "birds": "bird"}
    [
        line.keyword
        for line in kwic(
            text,
            "watch the bird",
            by_lemma=True,
            lemmatize=lambda word, tokens: [lemmas.get(word, word)],
        )
    ]
    # ['watched the birds', 'watch the birds']
    ```
