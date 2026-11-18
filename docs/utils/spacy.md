# spaCy objects

Checks of spaCy objects without importing spaCy and the morphology of the words of the [tree of a document](https://sergeyshk.github.io/anyTS/document/#get_tree). The functions of a word take a `TreeWord`: another value, such as a spaCy `Token`, raises `SourceTypeError`.

## Doc, Span, Token and Language objects { #is_doc-is_span }

<!-- --8<-- [start:is_doc] -->
``` {.python .signature}
is_doc(value)
```

Checks whether a value is a `Doc` object of spaCy without importing spaCy: such an object exists only once spaCy is loaded, so before that every value gives `False`. A library checks its sources this way to keep its import free of spaCy.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `value` | `object` | - | Value to check |
<!-- --8<-- [end:is_doc] -->

<!-- --8<-- [start:is_span] -->
``` {.python .signature}
is_span(value)
```

Checks whether a value is a `Span` object of spaCy, without importing spaCy as `is_doc`.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `value` | `object` | - | Value to check |
<!-- --8<-- [end:is_span] -->

<!-- --8<-- [start:is_token] -->
``` {.python .signature}
is_token(value)
```

Checks whether a value is a `Token` object of spaCy, without importing spaCy as `is_doc`.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `value` | `object` | - | Value to check |
<!-- --8<-- [end:is_token] -->

<!-- --8<-- [start:is_language] -->
``` {.python .signature}
is_language(value)
```

Checks whether a value is a `Language` pipeline of spaCy, without importing spaCy as `is_doc`: a library checks a pipeline passed to it this way.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `value` | `object` | - | Value to check |
<!-- --8<-- [end:is_language] -->

=== "Code"

    ``` python
    import spacy

    from anyts.utils import is_doc, is_language, is_span, is_token

    nlp = spacy.blank("en")
    doc = nlp("The cat sleeps")
    is_doc(doc), is_doc(doc[:2]), is_span(doc[:2]), is_doc("The cat sleeps")
    is_language(nlp), is_language("en_core_web_sm"), is_token(doc[0])
    ```

=== "Result"

    ```
    (True, False, True, False)
    (True, False, True)
    ```

## Morphological features { #has_feature }

<!-- --8<-- [start:has_feature] -->
``` {.python .signature}
has_feature(word, field, value)
```

Checks whether a word of the tree of a document carries a morphological feature with a given value: `has_feature(word, "VerbForm", "Fin")`; a feature with several values (`PronType=Int,Rel`) carries each of them.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `word` | `TreeWord` | - | Word of the tree |
| `field` | `str` | - | Name of the feature |
| `value` | `str` | - | Value of the feature |
<!-- --8<-- [end:has_feature] -->

=== "Code"

    ``` python
    from spacy.tokens import Doc
    from spacy.vocab import Vocab

    from anyts.document import get_tree, to_document
    from anyts.utils import has_feature

    doc = Doc(
        Vocab(),
        words=["Who", "has", "left"],
        morphs=["PronType=Int,Rel", "Mood=Ind|VerbForm=Fin", "VerbForm=Part"],
    )
    who, has, left = get_tree(to_document(doc)).words
    has_feature(has, "VerbForm", "Fin"), has_feature(left, "VerbForm", "Fin")
    has_feature(who, "PronType", "Rel")
    ```

=== "Result"

    ```
    (True, False)
    True
    ```

## Verb forms { #verb-forms }

<!-- --8<-- [start:is_finite_verb] -->
``` {.python .signature}
is_finite_verb(word)
```

Checks whether a word of the tree of a document is a finite verb: the part of speech `VERB` with `VerbForm=Fin`, so a finite auxiliary (`AUX`) is not one.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `word` | `TreeWord` | - | Word of the tree |
<!-- --8<-- [end:is_finite_verb] -->

<!-- --8<-- [start:is_infinitive] -->
``` {.python .signature}
is_infinitive(word)
```

Checks whether a word of the tree of a document is an infinitive, `VerbForm=Inf` whatever its part of speech.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `word` | `TreeWord` | - | Word of the tree |
<!-- --8<-- [end:is_infinitive] -->

=== "Code"

    ``` python
    from spacy.tokens import Doc
    from spacy.vocab import Vocab

    from anyts.document import get_tree, to_document
    from anyts.utils import is_finite_verb, is_infinitive

    doc = Doc(
        Vocab(),
        words=["She", "has", "to", "go"],
        pos=["PRON", "VERB", "PART", "VERB"],
        morphs=["", "VerbForm=Fin", "", "VerbForm=Inf"],
    )
    words = get_tree(to_document(doc)).words
    [(word.form, is_finite_verb(word), is_infinitive(word)) for word in words]
    ```

=== "Result"

    ```
    [('She', False, False), ('has', True, False), ('to', False, False), ('go', False, True)]
    ```
