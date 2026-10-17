# spaCy objects

!!! info ""
    **anyts.utils**

Checks of the objects of spaCy without importing it, the words of a `Doc` and their morphology, the parts of a word the tokenizer split at its hyphens and the sentences of a `Doc`.

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

## is_word

<!-- --8<-- [start:is_word] -->
Checks whether a token is a word: not whitespace and not a token of `is_punctuation`, so symbols like `%`, `€`, `+` and invisible characters are no words either. The words of `iter_doc_tokens` and the nodes of the dependency tree of the syntactic statistics are such tokens.
<!-- --8<-- [end:is_word] -->

## has_feature

<!-- --8<-- [start:has_feature] -->
Checks whether a token carries a morphological feature with a given value: `has_feature(token, "VerbForm", "Fin")`.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `token` | Token | `-` | Token |
| `field` | str | `-` | Name of the feature |
| `value` | str | `-` | Value of the feature |
<!-- --8<-- [end:has_feature] -->

## Verb forms { #verb-forms }

<!-- --8<-- [start:is_finite_verb] -->
`is_finite_verb(token)` checks whether a token is a finite verb: the part of speech `VERB` with `VerbForm=Fin`, so a finite auxiliary (`AUX`) is not one.
<!-- --8<-- [end:is_finite_verb] -->

<!-- --8<-- [start:is_infinitive] -->
`is_infinitive(token)` checks whether a token is an infinitive, `VerbForm=Inf` whatever its part of speech.
<!-- --8<-- [end:is_infinitive] -->

## joins_previous

<!-- --8<-- [start:joins_previous] -->
A tokenizer may split a word at its hyphens (`well-known` into `well`, `-`, `known`). `joins_previous(token)` checks whether a token continues such a word: it is a word that follows a hyphen with no whitespace around it, the hyphen follows a word, and no sentence starts at the hyphen or at the word. `iter_doc_units` and the functions of the dependency tree join the parts of a word by this rule with `join_hyphens=True`.
<!-- --8<-- [end:joins_previous] -->

## iter_doc_tokens

<!-- --8<-- [start:iter_doc_tokens] -->
Yields the tokens of the words of a `Doc` or a `Span` (`is_word`): whitespace tokens and the tokens of `is_punctuation`, symbols like `%` and `€` included, are skipped.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `source` | Doc/Span | `-` | Doc or Span object |
<!-- --8<-- [end:iter_doc_tokens] -->

## iter_doc_units

<!-- --8<-- [start:iter_doc_units] -->
Yields the words of a `Doc` or a `Span` as lists of tokens: one token each, as in `iter_doc_tokens`. With `join_hyphens=True` a word that the tokenizer split at its hyphens (`well-known` into `well`, `-`, `known`) is joined back when no whitespace separates its parts and no sentence starts at a hyphen or a part (`joins_previous`); a language library whose own tokenizer keeps such words whole turns it on, so that a string and a `Doc` give the same words.

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

## split_doc_units

<!-- --8<-- [start:split_doc_units] -->
Splits the words of a `Doc` into the sentences of a sentence extractor, for a `Doc` without sentence boundaries or one to split otherwise: the sentences are found in its text in their order, and a word of `iter_doc_units` belongs to the sentence its first token lies in. The words outside the sentences found - those the extractor drops - are left out, so with no sentence found there are no words.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `source` | Doc | `-` | Doc object |
| `sents_extractor` | SentsExtractor | `-` | Sentence extraction tool |
| `join_hyphens` | bool | `False` | Join the parts of hyphenated words |
<!-- --8<-- [end:split_doc_units] -->
