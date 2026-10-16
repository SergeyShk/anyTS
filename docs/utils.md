# Utilities

!!! info ""
    **anyts.utils**

Helper functions shared by the extractors and the statistics.

## is_punctuation

<!-- --8<-- [start:is_punctuation] -->
Checks whether a token consists only of punctuation marks and symbols: the characters of the Unicode categories P (punctuation), S (symbols), M (combining marks) and Cf (invisible format characters such as the zero-width space `U+200B`, the byte order mark `U+FEFF` and the zero-width joiner `U+200D`). Multi-character tokens like `?!` and `--`, symbols like `€` and `№` and a lone invisible character that a tokenizer splits off are punctuation too, while a token with a letter or a digit is not (`e` with a combining acute accent is a word); an empty token is punctuation as well. The results are cached by token, so the function is meant for tokens, not whole texts.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `token` | str | `-` | Token |
<!-- --8<-- [end:is_punctuation] -->

!!! example "Example"

    ``` python
    from anyts.utils import is_punctuation

    is_punctuation("?!"), is_punctuation("€"), is_punctuation("no.")
    # (True, True, False)
    ```

## count_letters

<!-- --8<-- [start:count_letters] -->
Counts the letters of a word: the characters of any alphabet (`str.isalpha`), without digits, hyphens and marks. The results are cached by word form, so the function is meant for words, not whole texts.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `word` | str | `-` | Word form |
<!-- --8<-- [end:count_letters] -->

!!! example "Example"

    ``` python
    from anyts.utils import count_letters

    count_letters("well-known"), count_letters("3rd")
    # (9, 2)
    ```

## safe_divide

<!-- --8<-- [start:safe_divide] -->
Divides two numbers and returns `default` for a zero denominator.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `num` | float/int | `-` | Numerator |
| `den` | float/int | `-` | Denominator |
| `default` | float/int | `0` | Value returned for a zero denominator |
<!-- --8<-- [end:safe_divide] -->

## has_words

<!-- --8<-- [start:has_words] -->
Checks whether a text, a `Doc` or a `Span` holds a word: an empty text or one of whitespace and the characters of `is_punctuation` alone holds none.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `source` | str/Doc/Span | `-` | Text, Doc or Span object |
<!-- --8<-- [end:has_words] -->

!!! example "Example"

    ``` python
    from anyts.utils import has_words

    has_words("The cat sleeps"), has_words("?!"), has_words("")
    # (True, False, False)
    ```

## has_sents

<!-- --8<-- [start:has_sents] -->
Checks whether a `Doc` has its sentence boundaries: they count when every token has them, as the parser, `senter` and `sentencizer` set them. The starts of a component that leaves the other tokens unset, such as `start_sents_after_blank_lines` run without the parser, are partial, and the statistics, `kwic`, `sentence_lengths` and the highlighting take the sentences of such a `Doc` from its text, as of a `Doc` without boundaries.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `doc` | Doc | `-` | Doc object |
<!-- --8<-- [end:has_sents] -->

!!! example "Example"

    ``` python
    import spacy
    from anyts.components import start_sents_after_blank_lines
    from anyts.utils import has_sents

    nlp = spacy.blank("xx")
    text = "Notes\n\nThe cat sleeps. The dog eats."
    doc = start_sents_after_blank_lines(nlp(text))
    doc.has_annotation("SENT_START"), has_sents(doc)
    # (True, False)
    nlp.add_pipe("sentencizer")
    has_sents(nlp(text))
    # True
    ```

## is_doc, is_span

<!-- --8<-- [start:is_doc] -->
`is_doc(value)` checks whether a value is a `Doc` object of spaCy without importing spaCy: such an object exists only once spaCy is loaded, so before that every value gives `False`. The core takes a `Doc` this way, and `import anyts` loads no spaCy; a language library checks its sources so too, to keep its own import light.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `value` | object | `-` | Value to check |
<!-- --8<-- [end:is_doc] -->

<!-- --8<-- [start:is_span] -->
`is_span(value)` checks whether a value is a `Span` object of spaCy, without importing spaCy as `is_doc`.
<!-- --8<-- [end:is_span] -->

!!! example "Example"

    ``` python
    import spacy
    from anyts.utils import is_doc, is_span

    doc = spacy.blank("en")("The cat sleeps")
    is_doc(doc), is_doc(doc[:2]), is_span(doc[:2]), is_doc("The cat sleeps")
    # (True, False, True, False)
    ```

## check_sequence

<!-- --8<-- [start:check_sequence] -->
Checks that an argument is a sequence and not a text or an iterator: a string (of characters or bytes), a `Doc`, a `Span`, an iterator or an object that cannot be iterated raises `SourceTypeError`, since a string would be iterated character by character and an iterator would be exhausted by the first pass over it; so does a table - a two-dimensional array or a `DataFrame`. A set or a mapping holds every item once, in no order of the text, and raises the error too, unless `ordered=False` - for a collection whose order and repeats do not matter, such as stop words.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `value` | object | `-` | Value to check |
| `what` | str | `"words"` | What is expected, for the message of the error |
| `ordered` | bool | `True` | Whether the order and the repeats of the items matter |
<!-- --8<-- [end:check_sequence] -->

## check_words

<!-- --8<-- [start:check_words] -->
Checks that an argument is a list of words: it passes `check_sequence` and every item is a string, so that a list of spaCy tokens, which would count every token as a lexeme of its own, raises `SourceTypeError`.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `value` | Iterable | `-` | Value to check |
| `what` | str | `"words"` | What is expected, for the message of the error |
| `ordered` | bool | `True` | Whether the order and the repeats of the words matter |
<!-- --8<-- [end:check_words] -->

## check_integer

<!-- --8<-- [start:check_integer] -->
Checks that a parameter is an integer: a `bool` or a `float`, even a whole one like `5.0`, raises `ParameterError`, since it would fail only later, as an index or a count.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `value` | object | `-` | Value to check |
| `what` | str | `-` | Name of the parameter, for the message of the error |
<!-- --8<-- [end:check_integer] -->

## check_number

<!-- --8<-- [start:check_number] -->
Checks that a parameter is a finite real number: a `bool`, a string, `None`, `nan` or an infinity raises `ParameterError` instead of failing later in a comparison.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `value` | object | `-` | Value to check |
| `what` | str | `-` | Name of the parameter, for the message of the error |
<!-- --8<-- [end:check_number] -->

## check_counts

<!-- --8<-- [start:check_counts] -->
Checks that an argument is a counter - a mapping of words to their frequencies, such as a `Counter`: a value that is not a mapping, a word that is not a string or a frequency that is not a number raises `SourceTypeError`, and a negative, `nan` or infinite frequency `SourceError`.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `value` | object | `-` | Value to check |
<!-- --8<-- [end:check_counts] -->

## merge_labels

<!-- --8<-- [start:merge_labels] -->
Merges the labels given for a plot over its default ones: a label that is not given keeps its default, so a single label can be changed alone. A default with fields in braces, such as `"Moving average ({window})"`, is a format string: a label given for it may use only those fields, and a literal brace in it is doubled (`{{`); the other labels are taken as they are. A format label is tried on sample values of its fields, of the types the plot gives them, so that a format spec the values do not take (`{window:s}` for a number) fails before a figure is created. Labels that are not a mapping of strings, have a key the plot does not know, a field their default does not have or a format spec their values do not take raise `ParameterError`.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `defaults` | dict[str, str] | `-` | Default labels by key |
| `labels` | dict[str, str] | `-` | Labels given; `None` - the default ones |
| `**samples` | object | `-` | Values of the fields of the format labels, for trying the labels given |
<!-- --8<-- [end:merge_labels] -->

The defaults of the visualizers of the core are `anyts.constants.VISUALIZER_LABELS`, by the name of the function.

!!! example "Example"

    ``` python
    from anyts.utils import merge_labels

    merge_labels({"title": "Plot", "xlabel": "x"}, {"title": "My plot"})
    # {'title': 'My plot', 'xlabel': 'x'}
    ```

## check_messages

<!-- --8<-- [start:check_messages] -->
Checks the messages of the errors a class of statistics raises: they must be complete, a string for every key of the defaults, so that an error never turns into a `KeyError`, and a message whose default has fields in braces may use only those fields, with a literal brace doubled (`{{`). The classes of statistics check the `messages` of a subclass when it is defined. Messages that are not a mapping of strings, lack a key or have another, or have a field their default lacks raise `ParameterError`.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `messages` | dict[str, str] | `-` | Messages by key |
| `defaults` | dict[str, str] | `MESSAGES` | Default messages by key |
<!-- --8<-- [end:check_messages] -->

## iter_doc_tokens

<!-- --8<-- [start:iter_doc_tokens] -->
Yields the tokens of the words of a `Doc` or a `Span`: whitespace tokens and the tokens of `is_punctuation`, symbols like `%` and `€` included, are skipped.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `source` | Doc/Span | `-` | Doc or Span object |
<!-- --8<-- [end:iter_doc_tokens] -->

## iter_doc_units

<!-- --8<-- [start:iter_doc_units] -->
Yields the words of a `Doc` or a `Span` as lists of tokens: one token each, as in `iter_doc_tokens`. With `join_hyphens=True` a word that the tokenizer split at its hyphens (`well-known` into `well`, `-`, `known`) is joined back when no whitespace separates its parts and no sentence starts at a hyphen or a part; a language library whose own tokenizer keeps such words whole turns it on, so that a string and a `Doc` give the same words.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `source` | Doc/Span | `-` | Doc or Span object |
| `join_hyphens` | bool | `False` | Join the parts of hyphenated words |
<!-- --8<-- [end:iter_doc_units] -->

## iter_doc_words

<!-- --8<-- [start:iter_doc_words] -->
Yields the words of `iter_doc_units` as tuples: the position of the first character, the position after the last character and the text of the word. A byte order mark glued to the start of a word, as in a file read with `utf-8` instead of `utf-8-sig`, is dropped.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `source` | Doc/Span | `-` | Doc or Span object |
| `join_hyphens` | bool | `False` | Join the parts of hyphenated words |
<!-- --8<-- [end:iter_doc_words] -->

!!! example "Example"

    ``` python
    import spacy

    from anyts.utils import iter_doc_words

    doc = spacy.blank("xx")("A well-known cat")
    [word for _, _, word in iter_doc_words(doc)]
    # ['A', 'well', 'known', 'cat']
    list(iter_doc_words(doc, join_hyphens=True))
    # [(0, 1, 'A'), (2, 12, 'well-known'), (13, 16, 'cat')]
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

## find_phrases

<!-- --8<-- [start:find_phrases] -->
Finds phrases in a sequence of words: the bounds of every phrase found as slices of the words, in order. The words and the phrases are compared by their normalized forms, the lower case by default; at every position the longest phrase is taken, the phrases found do not overlap, and empty phrases are skipped. Words that are not a list of strings raise `SourceTypeError`.

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

## is_number

<!-- --8<-- [start:is_number] -->
`is_number(word, pattern)` checks whether a word is a number by a pattern matched against the whole lower-cased word, `NUMBER_PATTERN` by default, the numbers of `WordsExtractor`; a language passes its own (ordinals, Roman numerals).
<!-- --8<-- [end:is_number] -->

## in_order

<!-- --8<-- [start:in_order] -->
`in_order(words)` puts a collection of words in a fixed order: a list keeps its order, a set or a mapping is sorted.
<!-- --8<-- [end:in_order] -->
