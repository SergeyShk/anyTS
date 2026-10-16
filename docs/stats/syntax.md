# Dependency tree helpers

!!! info ""
    **anyts.syntax**

Functions over the dependency tree of a spaCy `Doc`, a `Span` or a list of tokens. They use only what Universal Dependencies and the ClearNLP labels of the English models share: the head of a token, the relations `cc`, `conj`, `parataxis`, `punct` and `aux`, and the root; the copula `cop` of `predicate_form` exists in Universal Dependencies alone. Everything else is up to a language library.

## is_word

<!-- --8<-- [start:is_word] -->
Checks whether a token is a word: not whitespace and not a token of `is_punctuation`, so symbols like `%`, `€`, `+` and invisible characters are no words either.
<!-- --8<-- [end:is_word] -->

<!-- --8<-- [start:get_words] -->
`get_words(tokens, join_hyphens=False)` returns the words of a sequence of tokens in their order; with `join_hyphens=True` a word the tokenizer split at its hyphens is one word, given by its part that holds its relation, as with the dependents of `get_children` (`governor` in `He is vice-governor`), or by its first part when a hyphen holds it.
<!-- --8<-- [end:get_words] -->

## Hyphenated words { #joins_previous }

<!-- --8<-- [start:joins_previous] -->
A tokenizer may split a word at its hyphens (`well-known` into `well`, `-`, `known`) and a parser then hangs every part on its own head. `joins_previous(token)` checks whether a token continues such a word: it is a word that follows a hyphen with no whitespace around it, the hyphen follows a word, and no sentence starts at the hyphen or at the word - the rule of `iter_doc_units` with `join_hyphens=True`. With `join_hyphens=True`, `get_words`, `get_children`, `count_children`, `subtree_len`, `calc_valency` and `calc_dependency_distances` take such a word for one word with its hyphens. A word that holds the head of the sentence has no head; the head of another one is that of its part hanging outside it, the nearest to the root (a word rather than a hyphen when equal). The dependents of a word are the words whose head hangs on one of its tokens, each given by that part (or by its first part when it hangs by a hyphen), and its subtree is the word and the words that hang on it, directly or through punctuation, so every word has one dependency and is the dependent of one word.
<!-- --8<-- [end:joins_previous] -->

## is_root

<!-- --8<-- [start:is_root] -->
Checks whether a token is the head of its sentence: its head is the token itself.
<!-- --8<-- [end:is_root] -->

## base_dep

<!-- --8<-- [start:base_dep] -->
The relation of a token without its subtype, which Universal Dependencies separates by a colon: `nsubj:pass` gives `nsubj`, `expl:pass` gives `expl`.
<!-- --8<-- [end:base_dep] -->

## get_children, count_children, subtree_len

<!-- --8<-- [start:get_children] -->
`get_children(token, join_hyphens=False)` returns the dependent words of a token, punctuation and whitespace left out; with `join_hyphens=True`, the dependents of the whole hyphenated word the token belongs to.
<!-- --8<-- [end:get_children] -->

<!-- --8<-- [start:count_children] -->
`count_children(token, join_hyphens=False)` counts the dependent words of a token.
<!-- --8<-- [end:count_children] -->

<!-- --8<-- [start:subtree_len] -->
`subtree_len(token, join_hyphens=False)` is the number of words in the subtree of a token: the token itself and all of its direct and indirect dependents.
<!-- --8<-- [end:subtree_len] -->

## calc_dependency_distances

<!-- --8<-- [start:calc_dependency_distances] -->
The dependency distances (Liu 2008): the distance between a word and its head in positions of words, punctuation left out, in the order of the words. The head of a sentence has no dependency and is skipped, as is a word whose head lies outside the given sequence.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `tokens` | Doc/Span/list[Token] | `-` | Sequence of tokens |
| `join_hyphens` | bool | `False` | Take a hyphenated word for one position |
<!-- --8<-- [end:calc_dependency_distances] -->

## calc_tree_depth

<!-- --8<-- [start:calc_tree_depth] -->
The depth of the dependency tree: the longest path from the head of a sentence to a leaf, in relations between words. For a sequence of several sentences the maximum is taken; a sentence of one word has depth 0. With `join_hyphens` a hyphenated word is one word, and the words that hang on any of its parts are one level below it.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `tokens` | Doc/Span/list[Token] | `-` | Sequence of tokens |
| `join_hyphens` | bool | `False` | Take a hyphenated word for one word |
<!-- --8<-- [end:calc_tree_depth] -->

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

<!-- --8<-- [start:predicate_form] -->
`predicate_form(token, auxiliary_form)` gives the verb form of a predicate by the forms (`VerbForm`) of its auxiliaries and copulas - the relations `aux` and `cop` with their subtypes, `anyts.constants.AUXILIARY_DEPS` - as Universal Dependencies annotates them. A finite auxiliary makes the predicate finite wherever it stands (*had arrived*, the German *gekommen sein wird*); otherwise the form of the first auxiliary decides (*to have gone* is an infinitive, *being chosen* a gerund), and without auxiliaries the form of the word itself. A past participle auxiliary counts as finite, since it follows a finite one that the parser may attach to another word (*had been chosen*); a present participle (*having eaten*) does not. A ClearNLP parse has no copula relation, its copula heading the clause with a form of its own, and its passive auxiliary `auxpass` is not read. An auxiliary the model leaves without a form is read by the hook `auxiliary_form` of a language, which gives its form, for instance by its ending, or an empty string to skip it; without the hook such an auxiliary is skipped. A word with no verb form gives an empty string, and a hook that is not callable raises `SourceTypeError`.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `token` | Token | `-` | Token |
| `auxiliary_form` | Callable[[Token], str] | `None` | Verb form of an auxiliary without `VerbForm` |
<!-- --8<-- [end:predicate_form] -->

!!! example "Example"

    ``` python
    import spacy
    from spacy.tokens import Doc
    from anyts.syntax import predicate_form

    vocab = spacy.blank("en").vocab
    doc = Doc(
        vocab,
        words=["She", "had", "been", "chosen"],
        heads=[3, 3, 3, 3],
        deps=["nsubj:pass", "aux", "aux:pass", "ROOT"],
        morphs=["Case=Nom", "VerbForm=Fin", "VerbForm=Part", "VerbForm=Part"],
    )
    predicate_form(doc[3])
    # 'Fin'
    # An auxiliary the model left without a form, read by the hook
    doc = Doc(
        vocab,
        words=["to", "have", "gone"],
        heads=[2, 2, 2],
        deps=["mark", "aux", "ROOT"],
        morphs=["", "", "VerbForm=Part"],
    )
    predicate_form(doc[2]), predicate_form(doc[2], lambda aux: "Inf" if aux.lower_ == "have" else "")
    # ('Part', 'Inf')
    ```

## calc_valency

<!-- --8<-- [start:calc_valency] -->
The valency of a token: the number of its dependent words, the relations `cc`, `conj` and `parataxis` left out; `calc_valency(token, join_hyphens=True)` counts a hyphenated dependent once, so `came` in `Some-one came` has one dependent and not two.
<!-- --8<-- [end:calc_valency] -->

## calc_coordination_chains

<!-- --8<-- [start:calc_coordination_chains] -->
The lengths of the coordination chains, in the order of their first words. A chain is a group of words linked by the relation `conj`, whichever word each conjunct hangs on: Universal Dependencies attaches every conjunct to the first one (`pears → apples`, `plums → apples`), ClearNLP to the previous one (`pears → apples`, `plums → pears`), and both give one chain of three for `apples, pears and plums`. A nested coordination (`cats and dogs, or birds`) and an enumeration that the parser splits between several heads are one chain as well. The length of a chain is the number of its words; a conjunct whose head lies outside the sequence belongs to no chain with it. With `join_hyphens` a hyphenated word is one conjunct, linked by the `conj` of any of its parts (`member and vice-governor` is a chain of two).

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `tokens` | Doc/Span/list[Token] | `-` | Sequence of tokens |
| `join_hyphens` | bool | `False` | Take a hyphenated word for one word |
<!-- --8<-- [end:calc_coordination_chains] -->
