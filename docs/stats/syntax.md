# Dependency tree helpers

!!! info ""
    **anyts.syntax**

Functions over the dependency tree of a spaCy `Doc`, a `Span` or a list of tokens. They use only what Universal Dependencies and the ClearNLP labels of the English models share: the head of a token, the relations `cc`, `conj`, `parataxis` and `punct`, and the root; everything else is up to a language library.

## is_word

<!-- --8<-- [start:is_word] -->
Checks whether a token is a word: not whitespace and not a token of [`is_punctuation`](../utils.md#is_punctuation), so symbols like `%`, `€`, `+` and invisible characters are no words either.
<!-- --8<-- [end:is_word] -->

<!-- --8<-- [start:get_words] -->
`get_words(tokens)` returns the words of a sequence of tokens in their order.
<!-- --8<-- [end:get_words] -->

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
`get_children(token)` returns the dependent words of a token, punctuation and whitespace left out.
<!-- --8<-- [end:get_children] -->

<!-- --8<-- [start:count_children] -->
`count_children(token)` counts the dependent words of a token.
<!-- --8<-- [end:count_children] -->

<!-- --8<-- [start:subtree_len] -->
`subtree_len(token)` is the number of words in the subtree of a token: the token itself and all of its direct and indirect dependents.
<!-- --8<-- [end:subtree_len] -->

## calc_dependency_distances

<!-- --8<-- [start:calc_dependency_distances] -->
The dependency distances (Liu 2008): the distance between a word and its head in positions of words, punctuation left out, in the order of the words. The head of a sentence has no dependency and is skipped, as is a word whose head lies outside the given sequence.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `tokens` | Doc/Span/list[Token] | `-` | Sequence of tokens |
<!-- --8<-- [end:calc_dependency_distances] -->

## calc_tree_depth

<!-- --8<-- [start:calc_tree_depth] -->
The depth of the dependency tree: the longest path from the head of a sentence to a leaf, in relations between words. For a sequence of several sentences the maximum is taken; a sentence of one word has depth 0.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `tokens` | Doc/Span/list[Token] | `-` | Sequence of tokens |
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

## calc_valency

<!-- --8<-- [start:calc_valency] -->
The valency of a token: the number of its dependent words, the relations `cc`, `conj` and `parataxis` left out.
<!-- --8<-- [end:calc_valency] -->

## calc_coordination_chains

<!-- --8<-- [start:calc_coordination_chains] -->
The lengths of the coordination chains, in the order of their first words. A chain is a group of words linked by the relation `conj`, whichever word each conjunct hangs on: Universal Dependencies attaches every conjunct to the first one (`pears → apples`, `plums → apples`), ClearNLP to the previous one (`pears → apples`, `plums → pears`), and both give one chain of three for `apples, pears and plums`. A nested coordination (`cats and dogs, or birds`) and an enumeration that the parser splits between several heads are one chain as well. The length of a chain is the number of its words; a conjunct whose head lies outside the sequence belongs to no chain with it.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `tokens` | Doc/Span/list[Token] | `-` | Sequence of tokens |
<!-- --8<-- [end:calc_coordination_chains] -->
