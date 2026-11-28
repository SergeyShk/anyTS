# Words of the tree

The morphology of the words of the [tree of a document](https://sergeyshk.github.io/anyTS/document/#get_tree). The functions take a `TreeWord`: another value raises `SourceTypeError`.

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
    from anyseg import Document

    from anyts.document import get_tree
    from anyts.utils import has_feature

    document = Document.from_tokens("Who has left", [0, 4, 8], [3, 7, 12])
    document.set_columns(feats=["PronType=Int,Rel", "Mood=Ind|VerbForm=Fin", "VerbForm=Part"])
    who, has, left = get_tree(document).words
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
    from anyseg import Document

    from anyts.document import get_tree
    from anyts.utils import is_finite_verb, is_infinitive

    document = Document.from_tokens("She has to go", [0, 4, 8, 11], [3, 7, 10, 13])
    document.set_columns(
        upos=["PRON", "VERB", "PART", "VERB"], feats=[None, "VerbForm=Fin", None, "VerbForm=Inf"]
    )
    words = get_tree(document).words
    [(word.form, is_finite_verb(word), is_infinitive(word)) for word in words]
    ```

=== "Result"

    ```
    [('She', False, False), ('has', True, False), ('to', False, False), ('go', False, True)]
    ```
