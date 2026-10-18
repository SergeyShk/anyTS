# spaCy objects

!!! info ""
    **anyts.utils**

Checks of spaCy objects without importing spaCy, the words of a `Doc` and their morphology, the parts of a hyphenated word, the sentences of a `Doc` and the tokenizer rules of a language.

## is_doc, is_span

<!-- --8<-- [start:is_doc] -->
`is_doc(value)` checks whether a value is a `Doc` object of spaCy without importing spaCy: such an object exists only once spaCy is loaded, so before that every value gives `False`. A library checks its sources this way to keep its import free of spaCy.

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
Checks whether a `Doc` has its sentence boundaries: they count when every token has them, as after the parser, `senter` or `sentencizer`. The starts of a component that leaves the other tokens unset, such as `start_sents_after_blank_lines` without the parser, are partial; the statistics, `kwic`, `sentence_lengths` and the highlighting take the sentences of such a `Doc` from its text.

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
`joins_previous(token)` checks whether a token continues a word the tokenizer split at its hyphens (`well-known` into `well`, `-`, `known`): the token is a word right after a hyphen that follows a word, with no whitespace around the hyphen and no sentence starting at the hyphen or the token. `iter_doc_units` and the functions of the dependency tree join the parts of a word by this rule with `join_hyphens=True`.
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
Yields the words of a `Doc` or a `Span` as lists of tokens: one token each, as in `iter_doc_tokens`. With `join_hyphens=True` a word that the tokenizer split at its hyphens (`well-known` into `well`, `-`, `known`) is joined back by the rule of `joins_previous`; a language library whose tokenizer keeps such words whole turns it on, so that a string and a `Doc` give the same words.

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
Splits the words of a `Doc` or a `Span` into the sentences of a sentence extractor, for a `Doc` without sentence boundaries or one to split otherwise: the sentences are found in its text in their order, and a word of `iter_doc_units` belongs to the sentence its first token lies in. The words outside the sentences found, those the extractor drops, are left out, so no sentence found gives no words.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `source` | Doc/Span | `-` | Doc or Span object |
| `sents_extractor` | SentsExtractor | `-` | Sentence extraction tool |
| `join_hyphens` | bool | `False` | Join the parts of hyphenated words |
<!-- --8<-- [end:split_doc_units] -->

## add_tokenizer_rules

<!-- --8<-- [start:add_tokenizer_rules] -->
Adds the rules of a language to the tokenizer of a pipeline, so that the tokens of a `Doc` match the words a library splits a string into. The prefixes (such as the dashes of a dialogue glued to a word), suffixes and infixes are regular expressions joined to those of the tokenizer, every branch of a prefix anchored at the start and of a suffix at the end. An abbreviation becomes a single token in lower case, capitalized and in upper case when the tokenizer keeps one of its forms whole. A rule the tokenizer already has as a top-level alternative is not added twice; a tokenizer that is not the `Tokenizer` of spaCy, or whose rules are not regular expressions, is left as it is. A rule is joined to others, so it sets its flags in a group, `(?i:...)`. Rules that are not lists of strings and abbreviations that are not a collection of strings raise `SourceTypeError`, a rule that is not such a regular expression `ParameterError`.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `nlp` | Language | `-` | Pipeline whose tokenizer gets the rules |
| `prefixes` | list[str] | `()` | Patterns of the prefixes, without the anchor |
| `suffixes` | list[str] | `()` | Patterns of the suffixes, without the anchor |
| `infixes` | list[str] | `()` | Patterns of the infixes |
| `abbreviations` | list[str]/set[str] | `()` | Abbreviations in lower case |
<!-- --8<-- [end:add_tokenizer_rules] -->

!!! example "Example"

    ``` python
    import spacy
    from anyts.utils import add_tokenizer_rules

    nlp = spacy.blank("en")
    add_tokenizer_rules(nlp, prefixes=[r"-{2,}(?=\w)"])
    [token.text for token in nlp("--No, he said.")]
    # ['--', 'No', ',', 'he', 'said', '.']
    ```
