# Syntactic statistics

!!! info ""
    **anyts.syntax_stats.SyntaxStats**

## Description

<!-- --8<-- [start:SyntaxStats] -->
The syntactic statistics of a text by its dependency tree (Ivanov, Solnyshkina and Solovyev 2018): dependency distances, tree depth, leaves and subtrees, valency of the finite verbs, coordination chains, clauses, modifiers of a noun, participial clauses, passive, infinitives, negations, split predicates and the ratio of the nouns to the verbs. The data source is a `Doc` object of [spaCy](https://github.com/explosion/spaCy) with a dependency parse. Punctuation, symbols and whitespace are no nodes of the tree, and the distances are counted in positions of words. The measures of a sentence (the longest dependency, the depth, the nodes per leaf) are averaged over the sentences; the constructions are given per sentence.

A source that is not a `Doc` raises `SourceTypeError`; a source without a dependency parse (relations and sentence boundaries), without lemmas when the class requires them, or without words raises `SourceError`.
<!-- --8<-- [end:SyntaxStats] -->

## Language hooks

<!-- --8<-- [start:SyntaxStats-hooks] -->
A language library subclasses `SyntaxStats`. The defaults read Universal Dependencies with its morphological features and the relations it shares with ClearNLP; the passive and its agent read the relations of both:

| Hook | Kind | Description |
| :--: | :--: | :---------: |
| `parse(source)` | method | `Doc` of a source; by default the source itself, which must be a `Doc`; a library may parse a string |
| `is_clause_head(token)` | method | Whether a word heads a clause; by default `is_clause_head` of the module with `join_hyphens` of the class and the hook `is_infinitive_periphrasis` |
| `is_infinitive_periphrasis(token)` | method | Whether an infinitive under `xcomp`, or an infinitive conjunct, makes one predicate with its head, a modal or phasal verb (*can leave*, *begins to leave*); none by default, so every infinitive complement is a clause |
| `is_subordinate_clause_head(token)` | method | Whether a clause head heads a subordinate clause, asked only of the words of `is_clause_head`; by default `is_subordinate_clause_head` of the module over the hook `is_clause_head` |
| `is_participle_clause(token)` | method | Whether a word heads a participial clause; by default a participle that is not the head of the sentence, has no auxiliary or copula and has a dependent (`calc_valency`) |
| `is_passive(token)` | method | Whether a word is a passive verb form; by default `is_passive` of the module with `join_hyphens` of the class |
| `is_agentless(token)` | method | Whether a passive form has no agent; by default the hook `is_passive` without an agent (`has_agent` of the module) |
| `is_negation(token)` | method | Whether a word is a word of negation; by default `Polarity=Neg` or a word of `negation_words`, a conjunction excluded |
| `find_split_predicates(words)` | method | Pairs of a light verb and the noun that carries its meaning (`to make a decision`); none by default |
| `negation_words` | class attribute | Words of negation besides `Polarity=Neg`, in lower case; none by default |
| `join_hyphens` | class attribute | Take a word the tokenizer split at its hyphens for one word, in the tree and in the default hooks |
| `requires_lemmas` | class attribute | Whether the source must carry lemmas, for hooks that read them |
| `stats_desc`, `stats_headers` | class attributes | Statistics of `get_stats` with their descriptions (`SYNTAX_STATS_DESC` by default), headers of the columns for `print_stats` |
| `messages` | class attribute | Messages of the errors by key; `MESSAGES` by default |

The subclass adds the statistics of the constructions of its language (chains of complements by `calc_modifier_chains`, its own clauses) in its constructor from `sents`, with its own `stats_desc`. A `negation_words` that is not a collection of strings raises `SourceTypeError` when the class is defined, and so does a `parse` that does not return a `Doc` when the statistics are computed.
<!-- --8<-- [end:SyntaxStats-hooks] -->

## Parameters

<!-- --8<-- [start:SyntaxStats-parameters] -->
| Parameter | Type | Default | Description |
| :-------: | :--: | :-----: | :---------: |
| `source` | Doc | `-` | Data source: a `Doc` with a dependency parse, or what `parse` takes |
<!-- --8<-- [end:SyntaxStats-parameters] -->

## Attributes

<!-- --8<-- [start:SyntaxStats-attributes] -->
| Attribute | Type | Description |
| :-------: | :--: | :---------: |
| `sents` | tuple[tuple[Token]] | Words of every sentence with words |
| `n_sents`, `n_words` | int | Numbers of the sentences with words and of the words |
| `n_leaves`, `n_subtrees` | int | Numbers of the words without and with dependent words |
| `n_coordination_chains` | int | Number of the coordination chains |
| `n_clauses`, `n_subordinate_clauses`, `n_complex_sents` | int | Numbers of the clauses, of the subordinate clauses and of the sentences with one |
| `n_nouns`, `n_verbs` | int | Numbers of the nouns (`NOUN`, `PROPN`) and of the verb forms (`VERB`) |
| `n_participle_clauses` | int | Number of the participial clauses |
| `n_passive`, `n_agentless_passive` | int | Numbers of the passive forms and of those with no agent |
| `n_infinitives`, `n_negations` | int | Numbers of the infinitives and of the words of negation |
| `n_split_predicates`, `split_predicates` | int, tuple[str] | Number of the split predicates and the predicates, the verb and the noun |
| `c_children` | dict[int, int] | Number of the words by number of dependent words |
| `c_deps` | dict[str, int] | Number of the words by relation |
| `mean_dependency_distance`, `std_dependency_distance` | float | Mean and standard deviation of the dependency distance |
| `max_dependency_distance` | float | Mean of the longest dependencies of the sentences that have dependencies |
| `p_adjacent_dependencies` | float | Share of the dependencies of length 1 |
| `tree_depth` | float | Mean depth of the tree of a sentence |
| `leaves_per_sent`, `subtrees_per_sent` | float | Leaves and subtrees per sentence |
| `nodes_per_leaf` | float | Mean over the sentences of the words per leaf |
| `verb_valency` | float | Mean number of the dependents of a finite verb |
| `coordination_chains_per_sent`, `mean_coordination_chain_len` | float | Coordination chains per sentence and their mean length |
| `clauses_per_sent`, `mean_clause_len` | float | Clauses per sentence and their mean length in words |
| `subordinate_clauses_per_sent`, `p_complex_sents` | float | Subordinate clauses per sentence and the share of the sentences with one |
| `modifiers_per_noun` | float | Mean number of the modifiers of a noun (`count_noun_modifiers`) |
| `participle_clauses_per_sent`, `mean_participle_clause_len` | float | Participial clauses per sentence and their mean length in words |
| `p_passive`, `p_agentless_passive` | float | Share of the passive forms among the verb forms and of those with no agent among them |
| `infinitives_per_sent`, `negations_per_sent`, `split_predicates_per_sent` | float | Infinitives, words of negation and split predicates per sentence |
| `noun_verb_ratio` | float | Ratio of the nouns to the verb forms |

A share, a ratio or a mean without anything to divide by is `nan`.
<!-- --8<-- [end:SyntaxStats-attributes] -->

The methods `get_stats`, `to_dataframe`, `print_stats` and `describe` are those of the [statistics interface](stats.md).

## Metric functions

The functions of the tree are described in the [metric functions](syntax_stats_funcs.md) section.

## Usage example

!!! example "Example"

    ``` python
    import spacy
    from spacy.tokens import Doc

    from anyts.syntax_stats import SyntaxStats

    # It was not built by them
    doc = Doc(
        spacy.blank("en").vocab,
        words=["It", "was", "not", "built", "by", "them"],
        heads=[3, 3, 3, 3, 5, 3],
        deps=["nsubj:pass", "aux:pass", "advmod", "ROOT", "case", "obl:agent"],
        pos=["PRON", "AUX", "PART", "VERB", "ADP", "PRON"],
        morphs=["", "VerbForm=Fin", "Polarity=Neg", "VerbForm=Part|Voice=Pass", "", ""],
    )
    stats = SyntaxStats(doc)
    stats.mean_dependency_distance, stats.p_passive, stats.p_agentless_passive
    # (1.8, 1.0, 0.0)
    stats.negations_per_sent
    # 1.0
    ```
