# Metric functions

!!! info ""
    **anyts.syntax_stats**

Functions over the dependency tree of a spaCy `Doc`, a `Span` or a list of tokens; its words are the tokens of `anyts.utils.is_word`. They use only what Universal Dependencies and the ClearNLP labels of the English models share: the head of a token, the relations `cc`, `conj`, `parataxis`, `punct` and `aux`, the subjects `nsubj` and `csubj`, the modifiers of a noun `amod`, `det`, `nmod`, `nummod` and `acl`, and the root; the copula `cop` of `predicate_form` exists in Universal Dependencies alone. Everything else is up to a language library.

## get_words

<!-- --8<-- [start:get_words] -->
`get_words(tokens, join_hyphens=False)` returns the words of a sequence of tokens in their order; with `join_hyphens=True` a word the tokenizer split at its hyphens is one word, given by its part that holds its relation, as with the dependents of `get_children` (`governor` in `He is vice-governor`), or by its first part when a hyphen holds it.
<!-- --8<-- [end:get_words] -->

## Hyphenated words { #hyphenated-words }

<!-- --8<-- [start:hyphenated_words] -->
A tokenizer may split a word at its hyphens (`well-known` into `well`, `-`, `known`), and a parser then hangs every part on its own head. With `join_hyphens=True` the functions of the tree take a word whose parts `anyts.utils.joins_previous` joins for one word with its hyphens. A word holding the head of the sentence has no head; the head of another one is that of its part hanging outside it, the nearest to the root (a word rather than a hyphen when equal). The dependents of a word are the words whose head hangs on one of its tokens, each given by that part (or by its first part when it hangs by a hyphen); its subtree is the word and the words that hang on it, directly or through punctuation. So every word has one dependency and is the dependent of one word.
<!-- --8<-- [end:hyphenated_words] -->

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
The dependency distances (Liu 2008): the distance between a word and its head in positions of words, punctuation left out, in the order of the words. The head of a sentence and a word whose head lies outside the sequence are skipped.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `tokens` | Doc/Span/list[Token] | `-` | Sequence of tokens |
| `join_hyphens` | bool | `False` | Take a hyphenated word for one position |
<!-- --8<-- [end:calc_dependency_distances] -->

## calc_tree_depth

<!-- --8<-- [start:calc_tree_depth] -->
The depth of the dependency tree: the longest path from the head of a sentence to a leaf, in relations between words; the maximum for several sentences, 0 for a sentence of one word. With `join_hyphens` a hyphenated word is one word, and the words that hang on any of its parts are one level below it.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `tokens` | Doc/Span/list[Token] | `-` | Sequence of tokens |
| `join_hyphens` | bool | `False` | Take a hyphenated word for one word |
<!-- --8<-- [end:calc_tree_depth] -->

## predicate_form { #verb-forms }

<!-- --8<-- [start:predicate_form] -->
`predicate_form(token, auxiliary_form)` gives the verb form of a predicate by the forms (`VerbForm`) of its auxiliaries and copulas (`aux` and `cop` with their subtypes, `anyts.constants.AUXILIARY_DEPS`), as Universal Dependencies annotates them. A finite auxiliary makes the predicate finite wherever it stands (*had arrived*, the German *gekommen sein wird*); otherwise the first auxiliary decides (*to have gone* is an infinitive, *being chosen* a gerund), and without auxiliaries the word itself. A past participle auxiliary counts as finite, since it follows a finite one the parser may attach to another word (*had been chosen*); a present participle (*having eaten*) does not. A ClearNLP parse has no copula relation: its copula heads the clause with its own form, and its passive auxiliary `auxpass` is not read. An auxiliary the model leaves without a form is read by the language hook `auxiliary_form`, which gives its form or an empty string to skip it; without the hook it is skipped. A word with no verb form gives an empty string; a hook that is not callable raises `SourceTypeError`.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `token` | Token | `-` | Token |
| `auxiliary_form` | Callable[[Token], str] | `None` | Verb form of an auxiliary without `VerbForm` |
<!-- --8<-- [end:predicate_form] -->

!!! example "Example"

    ``` python
    import spacy
    from spacy.tokens import Doc
    from anyts.syntax_stats import predicate_form

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
The valency of a token: the number of its dependent words, the relations `cc`, `conj`, `parataxis` and `punct` left out (`anyts.constants.VALENCY_IGNORED_DEPS`); `calc_valency(token, join_hyphens=True)` counts a hyphenated dependent once, so `came` in `Some-one came` has one dependent and not two.
<!-- --8<-- [end:calc_valency] -->

## calc_coordination_chains

<!-- --8<-- [start:calc_coordination_chains] -->
The lengths of the coordination chains, in the order of their first words. A chain is a group of words linked by `conj`, whichever word each conjunct hangs on: Universal Dependencies attaches every conjunct to the first one (`pears → apples`, `plums → apples`), ClearNLP to the previous one (`pears → apples`, `plums → pears`); both give one chain of three for `apples, pears and plums`. A nested coordination (`cats and dogs, or birds`) and an enumeration split between several heads are one chain too. The length of a chain is the number of its words; a conjunct whose head lies outside the sequence is not linked to it. With `join_hyphens` a hyphenated word is one conjunct, linked by the `conj` of any of its parts (`member and vice-governor` is a chain of two).

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `tokens` | Doc/Span/list[Token] | `-` | Sequence of tokens |
| `join_hyphens` | bool | `False` | Take a hyphenated word for one word |
<!-- --8<-- [end:calc_coordination_chains] -->

## is_predicate

<!-- --8<-- [start:is_predicate] -->
`is_predicate(token, join_hyphens=False)` checks whether a word can be the predicate of its clause: a verb (`VERB`, `AUX`) or a word with a subject of its own (`nsubj`, `csubj` and their subtypes, `anyts.constants.SUBJECT_DEPS`), so the nominal predicate of `he is tall` passes and a parenthetical word does not.
<!-- --8<-- [end:is_predicate] -->

## Clauses and passive { #clauses }

!!! info ""
    **anyts.syntax_stats.is_clause_head()**, **anyts.syntax_stats.is_infinitive_clause()**, **anyts.syntax_stats.is_subordinate_clause_head()**, **anyts.syntax_stats.is_passive()**, **anyts.syntax_stats.has_agent()**, **anyts.syntax_stats.is_agentless()**

<!-- --8<-- [start:is_clause_head] -->
`is_clause_head(token, join_hyphens=False, is_infinitive_periphrasis=None)` checks whether a word heads a clause: the head of the sentence or a word with `ccomp`, `advcl`, `acl`, `csubj` or `parataxis` (`anyts.constants.CLAUSE_DEPS`, subtypes included) whose predicate (`predicate_form`, so `has been built` is finite) is not a participle, a converb or a gerund (`NONFINITE_CLAUSE_FORMS`, counted apart), nor an infinitive under `acl`; under `xcomp`, a finite predicate or an infinitive clause (`is_infinitive_clause`). A `parataxis` and a conjunct of a clause head count only as predicates (`is_predicate`); an infinitive conjunct is no clause by the check `is_infinitive_periphrasis`, since a model may attach the infinitive of a periphrasis to its verb as `conj`; a loop of conjuncts is no clause. A check of a periphrasis that is not callable raises `SourceTypeError`.
<!-- --8<-- [end:is_clause_head] -->

<!-- --8<-- [start:is_infinitive_clause] -->
`is_infinitive_clause(token, is_infinitive_periphrasis=None, is_clause_head=is_clause_head)` checks whether an infinitive complement heads a clause of its own: an infinitive (`predicate_form`, so `to be chosen` is one) under `xcomp` (*wants to leave*), unless the language check `is_infinitive_periphrasis` says it makes one predicate with its head (*can leave*, *begins to leave*), or the word it completes, the first one up its chain of infinitive complements, heads no clause by the check `is_clause_head`: an infinitive in a participial phrase or under an infinitive under `acl` (*trying to leave*, *the wish to try to leave*) belongs to that phrase. Without the check of a periphrasis every such infinitive complement is a clause; a check that is not callable raises `SourceTypeError`.
<!-- --8<-- [end:is_infinitive_clause] -->

<!-- --8<-- [start:is_subordinate_clause_head] -->
`is_subordinate_clause_head(token, is_clause_head=is_clause_head)` checks whether a word heads a subordinate clause: a clause head by the check `is_clause_head` with `ccomp`, `advcl`, `acl` or `csubj` (`SUBORDINATE_CLAUSE_DEPS`) or `xcomp`, or a conjunct of one, by the relation of the first word up its chain of conjuncts. A check that is not callable raises `SourceTypeError`.
<!-- --8<-- [end:is_subordinate_clause_head] -->

<!-- --8<-- [start:is_passive] -->
`is_passive(token, join_hyphens=False)` checks whether a word is a passive verb form: a verb with `Voice=Pass` or a dependent `nsubj:pass`, `csubj:pass`, `aux:pass`, or `nsubjpass`, `csubjpass`, `auxpass` of ClearNLP (`PASSIVE_DEPS`).
<!-- --8<-- [end:is_passive] -->

<!-- --8<-- [start:has_agent] -->
`has_agent(token, join_hyphens=False)` checks whether a word has an agent: a dependent `obl:agent`, or `agent` of ClearNLP (`AGENT_DEPS`).
<!-- --8<-- [end:has_agent] -->

<!-- --8<-- [start:is_agentless] -->
`is_agentless(token, join_hyphens=False)` checks whether a word is a passive form (`is_passive`) without an agent (`has_agent`).
<!-- --8<-- [end:is_agentless] -->

## Noun phrases { #noun-phrases }

<!-- --8<-- [start:count_noun_modifiers] -->
`count_noun_modifiers(token, join_hyphens=False)` counts the modifiers of a noun phrase: the dependents with the relations `amod`, `det`, `nmod`, `nummod`, `acl` and their subtypes (`anyts.constants.NOUN_MODIFIER_DEPS`); `conj` and `appos` are no modifiers.
<!-- --8<-- [end:count_noun_modifiers] -->

<!-- --8<-- [start:calc_modifier_chains] -->
The lengths of the chains of nested modifiers, in the order of the words. A chain is two or more modifiers each hanging on the previous one, such as the complements of `the increase of the efficiency of the use of resources` (length 3); the check `is_modifier` of a language says what a modifier is (a complement with a preposition, a noun in the genitive). A chain starts at a modifier whose head is none, and its length is the number of modifiers in its longest branch. The links are those of `get_children`: punctuation is no link, and with `join_hyphens` a hyphenated word is one link. A check that is not callable raises `SourceTypeError`.

| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `tokens` | Doc/Span/list[Token] | `-` | Sequence of tokens |
| `is_modifier` | Callable[[Token], bool] | `-` | Whether a word is a modifier of the chain |
| `join_hyphens` | bool | `False` | Take a hyphenated word for one word |
<!-- --8<-- [end:calc_modifier_chains] -->

!!! example "Example"

    ``` python
    import spacy
    from spacy.tokens import Doc
    from anyts.syntax_stats import calc_modifier_chains

    doc = Doc(
        spacy.blank("en").vocab,
        words=["the", "use", "of", "the", "water", "of", "the", "river"],
        heads=[1, 1, 4, 4, 1, 7, 7, 4],
        deps=["det", "ROOT", "case", "det", "nmod", "case", "det", "nmod"],
    )
    calc_modifier_chains(doc, lambda token: token.dep_ == "nmod")
    # [2]
    ```
