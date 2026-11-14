# Syntactic statistics

``` {.python .signature}
SyntaxStats(source)
```

<!-- --8<-- [start:SyntaxStats] -->
The syntactic statistics of a text by its dependency tree ([Ivanov, Solnyshkina and Solovyev 2018](https://dialogue-conf.org/media/4302/ivanovvv.pdf)): the measures of the tree and of the syntactic constructions. The data source is a text, a `Doc` object of [spaCy](https://github.com/explosion/spaCy) or a `Document` of [anySeg](https://github.com/SergeyShk/anySeg) with a dependency parse and parts of speech; a language library parses a string in its `parse`. The tree is that of its [document](https://sergeyshk.github.io/anyTS/document/#get_tree) (`get_tree`), and its nodes are the words of Universal Dependencies of the document with a letter or a digit: punctuation marks and symbols are none, and the tokens of the document decide what a word is. The distances are counted in positions of words. The units of L2SCA, the prepositional chains and the similarity of sentences are computed on first use, so a subclass whose `stats_desc` does not name them does not pay for them.

Raises:

- `SourceTypeError` - a source that is neither a string, a `Doc` nor a `Document`, a `parse` that returns no `Document`;
- `SourceError` - a source without a dependency parse, without parts of speech, without lemmas when the class requires them, or without words.
<!-- --8<-- [end:SyntaxStats] -->

=== "Code"

    ``` python
    import spacy
    from spacy.tokens import Doc

    from anyts.syntax_stats import SyntaxStats

    # She said that the house was not built by him.
    doc = Doc(
        spacy.blank("en").vocab,
        words="She said that the house was not built by him .".split(),
        heads=[1, 1, 7, 4, 7, 7, 7, 1, 9, 7, 1],
        deps="nsubj ROOT mark det nsubj:pass aux:pass advmod ccomp case obl:agent punct".split(),
        pos="PRON VERB SCONJ DET NOUN AUX PART VERB ADP PRON PUNCT".split(),
        morphs="_ VerbForm=Fin _ _ _ VerbForm=Fin Polarity=Neg VerbForm=Part|Voice=Pass _ _ _".split(),
    )
    stats = SyntaxStats(doc)
    stats.print_stats()
    ```

=== "Result"

    ```
                             Statistic                         |  Value
    ----------------------------------------------------------------------
    Mean dependency distance                                   |   2.44
    Standard deviation of the dependency distance              |   1.77
    Mean of the longest dependencies of the sentences          |   6.00
    Share of adjacent dependencies                             |   0.44
    Depth of the dependency tree                               |   3.00
    Leaves per sentence                                        |   6.00
    Subtrees per sentence                                      |   4.00
    Mean of the nodes per leaf of the sentences                |   1.67
    Mean number of words before the root of a sentence         |   1.00
    Valency of the finite verbs                                |   2.00
    Coordination chains per sentence                           |   0.00
    Mean length of a coordination chain                        |   nan
    Clauses per sentence                                       |   2.00
    Mean length of a clause (words)                            |   5.00
    Subordinate clauses per sentence                           |   1.00
    Share of sentences with a subordinate clause               |   1.00
    Infinitive clauses per sentence                            |   0.00
    T-units per sentence                                       |   1.00
    Mean length of a T-unit (words)                            |  10.00
    Clauses per T-unit                                         |   2.00
    Share of T-units with a subordinate clause                 |   1.00
    Verb phrases per T-unit                                    |   2.00
    Coordinate phrases per clause                              |   0.00
    Complex nominals per clause                                |   0.50
    Modifiers per noun phrase                                  |   1.00
    Prepositional chains per sentence                          |   0.00
    Maximum length of a prepositional chain                    |    0
    Participial clauses per sentence                           |   0.00
    Mean length of a participial clause (words)                |   nan
    Share of passive forms among the verbs                     |   0.50
    Share of agentless forms among the passive ones            |   0.00
    Infinitives per sentence                                   |   0.00
    Words of negation per sentence                             |   1.00
    Split predicates per sentence                              |   0.00
    Share of nominal subjects before their head                |   1.00
    Share of nominal objects before their head                 |   nan
    Edit distance of the parts of speech of adjacent sentences |   nan
    Syntactic similarity of adjacent sentences                 |   nan
    Ratio of nouns to verbs                                    |   0.50
    ```

## Parameters

<!-- --8<-- [start:SyntaxStats-parameters] -->
| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `source` | `str` / `Doc` / `Document` | - | Data source with a dependency parse and parts of speech, or a text that `parse` annotates |
<!-- --8<-- [end:SyntaxStats-parameters] -->

## Attributes

<!-- --8<-- [start:SyntaxStats-attributes] -->
| Attribute | Type | Description |
| :-------- | :--- | :---------- |
| `sents` | `tuple[tuple[TreeWord]]` | Words of the tree of every sentence with words |
| `n_sents`, `n_words` | `int` | Numbers of the sentences with words and of the words |
| `n_leaves`, `n_subtrees` | `int` | Numbers of the words without and with dependent words |
| `n_coordination_chains` | `int` | Number of the coordination chains |
| `n_clauses`, `n_subordinate_clauses`, `n_complex_sents` | `int` | Numbers of the clauses, of the subordinate clauses and of the sentences with one |
| `n_infinitive_clauses` | `int` | Number of the infinitive clauses |
| `n_t_units`, `n_complex_t_units` | `int` | Numbers of the T-units and of those with a subordinate clause |
| `n_l2sca_clauses` | `int` | Number of the clauses of L2SCA, without the predicates sharing a subject and the infinitive clauses |
| `n_verb_phrases`, `n_coordinate_phrases`, `n_complex_nominals` | `int` | Numbers of the verb phrases, of the coordinate phrases and of the complex nominals |
| `n_nouns`, `n_verbs` | `int` | Numbers of the nouns (`NOUN`, `PROPN`) and of the verb forms (`VERB`) |
| `n_prep_chains` | `int` | Number of the prepositional chains |
| `n_participle_clauses` | `int` | Number of the participial clauses |
| `n_passive`, `n_agentless_passive` | `int` | Numbers of the passive forms and of those with no agent |
| `n_infinitives`, `n_negations` | `int` | Numbers of the infinitives and of the words of negation |
| `n_split_predicates`, `split_predicates` | `int`, `tuple[str]` | Number of the split predicates and the predicates, the verb and the noun |
| `n_nominal_subjects`, `n_preverbal_subjects` | `int` | Numbers of the nominal subjects and of those before their head |
| `n_nominal_objects`, `n_preverbal_objects` | `int` | Numbers of the nominal direct objects and of those before their head |
| `c_children` | `dict[int, int]` | Number of the words by number of dependent words |
| `c_deps` | `dict[str, int]` | Number of the words by relation |
<!-- --8<-- [end:SyntaxStats-attributes] -->

## Metrics

<!-- --8<-- [start:SyntaxStats-metrics] -->
Every metric is an attribute of the object, computed when it is created - the units of L2SCA, the prepositional chains and the similarity of sentences on first use - and `get_stats` gives them all. The measures of a sentence (the longest dependency, the depth, the nodes per leaf) are averaged over the sentences; the constructions are given per sentence.

| Metric | Measures | Range | Higher means |
| :----- | :------- | :---- | :----------- |
| [`mean_dependency_distance`](#dependency_distances) | Mean distance between a word and its head | 1 and above, `nan` without dependencies | Harder to process |
| [`std_dependency_distance`](#dependency_distances) | Standard deviation of the dependency distance | 0 and above, `nan` without dependencies | Less even distances |
| [`max_dependency_distance`](#dependency_distances) | Mean of the longest dependencies of the sentences that have dependencies | 1 and above, `nan` without dependencies | Longer longest dependencies |
| [`p_adjacent_dependencies`](#dependency_distances) | Share of the dependencies of length 1 | 0-1, `nan` without dependencies | More links between neighbours |
| [`tree_depth`](#tree_depth) | Mean depth of the tree of a sentence | 0 and above | Deeper embedding |
| [`leaves_per_sent`](#leaves) | Leaves per sentence | 0 and above | Longer or flatter sentences |
| [`subtrees_per_sent`](#leaves) | Subtrees per sentence | 0 and above | More phrases in a sentence |
| [`nodes_per_leaf`](#leaves) | Mean over the sentences of the words per leaf | 1 and above, `nan` for a sentence without leaves | Longer branches |
| [`words_before_root`](#words_before_root) | Mean number of the words before the root of a sentence | 0 and above, `nan` without a root among the words | A later main predicate |
| [`verb_valency`](#valency) | Mean number of the dependents of a finite verb | 0 and above, `nan` without finite verbs | More dependents of a verb |
| [`coordination_chains_per_sent`](#coordination_chains) | Coordination chains per sentence | 0 and above | More coordination |
| [`mean_coordination_chain_len`](#coordination_chains) | Mean length of a coordination chain in words | 2 and above, `nan` without chains | Longer enumerations |
| [`clauses_per_sent`](#clauses) | Clauses per sentence | 0 and above | More clauses in a sentence |
| [`mean_clause_len`](#clauses) | Mean length of a clause in words | 1 and above, `nan` without clauses | Longer clauses |
| [`subordinate_clauses_per_sent`](#subordinate_clauses) | Subordinate clauses per sentence | 0 and above | More subordination |
| [`p_complex_sents`](#subordinate_clauses) | Share of the sentences with a subordinate clause | 0-1 | More complex sentences |
| [`infinitive_clauses_per_sent`](#infinitive_clauses) | Infinitive clauses per sentence (*wants to leave*, *came to help*), which are not subordinate | 0 and above | More infinitive clauses |
| [`t_units_per_sent`](#l2sca) | T-units per sentence (T/S) | 0 and above | More main clauses in a sentence |
| [`mean_t_unit_len`](#l2sca) | Mean length of a T-unit in words (MLT) | 1 and above, `nan` without T-units | Longer T-units |
| [`clauses_per_t_unit`](#l2sca) | Clauses per T-unit (C/T) | 1 and above, `nan` without T-units | More subordination |
| [`p_complex_t_units`](#l2sca) | Share of the T-units with a subordinate clause (CT/T) | 0-1, `nan` without T-units | More complex T-units |
| [`verb_phrases_per_t_unit`](#l2sca) | Verb phrases per T-unit (VP/T) | 0 and above, `nan` without T-units | More verb phrases |
| [`coordinate_phrases_per_clause`](#l2sca) | Coordinate phrases per clause (CP/C) | 0 and above, `nan` without clauses | More phrasal coordination |
| [`complex_nominals_per_clause`](#l2sca) | Complex nominals per clause (CN/C) | 0 and above, `nan` without clauses | Denser noun phrases |
| [`modifiers_per_noun`](#noun_modifiers) | Mean number of the modifiers of a noun | 0 and above, `nan` without nouns | Heavier noun phrases |
| [`prep_chains_per_sent`](#prep_chains) | Chains of nested complements with a preposition per sentence | 0 and above | More nested complements |
| [`max_prep_chain_len`](#prep_chains) | Length of the longest prepositional chain | 0, or 2 and above | Longer chains |
| [`participle_clauses_per_sent`](#participle_clauses) | Participial clauses per sentence | 0 and above | More participial clauses |
| [`mean_participle_clause_len`](#participle_clauses) | Mean length of a participial clause in words | 1 and above, `nan` without participial clauses | Longer participial clauses |
| [`p_passive`](#passive) | Share of the passive forms among the verb forms | 0-1, `nan` without verb forms | More passive |
| [`p_agentless_passive`](#passive) | Share of the forms with no agent among the passive ones | 0-1, `nan` without passive forms | More passive without an agent |
| [`infinitives_per_sent`](#constructions) | Infinitives per sentence | 0 and above | More infinitives |
| [`negations_per_sent`](#constructions) | Words of negation per sentence | 0 and above | More negation |
| [`split_predicates_per_sent`](#constructions) | Split predicates per sentence | 0 and above | More split predicates |
| [`p_preverbal_subjects`](#word_order) | Share of the nominal subjects before their head | 0-1, `nan` without nominal subjects | Fewer inverted subjects |
| [`p_preverbal_objects`](#word_order) | Share of the nominal direct objects before their head | 0-1, `nan` without nominal objects | More fronted objects |
| [`pos_edit_distance`](#similarity) | Mean edit distance of the parts of speech of adjacent sentences over the longer one | 0-1, `nan` for one sentence | Less alike sentences |
| [`syntax_similarity`](#similarity) | Mean similarity of the dependency triples of adjacent sentences | 0-1, `nan` for one sentence | More alike sentences |
| [`noun_verb_ratio`](#noun_verb_ratio) | Ratio of the nouns to the verb forms | 0 and above, `nan` without verb forms | A more nominal style |
<!-- --8<-- [end:SyntaxStats-metrics] -->

<div class="metric-card" markdown>

### Dependency distance { #dependency_distances }

`mean_dependency_distance` · `std_dependency_distance` · `max_dependency_distance` · `p_adjacent_dependencies`
{ .metric-meta }

<!-- --8<-- [start:calc_dependency_distances] -->
``` {.python .signature}
calc_dependency_distances(words)
```

The dependency distances (Liu 2008): the distance between a word and its head in positions of words (`get_words`), punctuation left out, in the order of the words. The head of a sentence and a word whose head lies outside the sequence or is a punctuation mark are skipped.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `words` | `list[TreeWord]` | - | Words of the tree, such as those of a sentence |
<!-- --8<-- [end:calc_dependency_distances] -->

</div>

<div class="metric-card" markdown>

### Tree depth { #tree_depth }

`tree_depth`
{ .metric-meta }

<!-- --8<-- [start:calc_tree_depth] -->
``` {.python .signature}
calc_tree_depth(words)
```

The depth of the dependency tree: the longest path from the head of a sentence to a leaf, in relations between words, through punctuation; the maximum for several sentences, 0 for a sentence of one word.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `words` | `list[TreeWord]` | - | Words of the tree, such as those of a sentence |
<!-- --8<-- [end:calc_tree_depth] -->

</div>

<div class="metric-card" markdown>

### Leaves and subtrees { #leaves }

`leaves_per_sent` · `subtrees_per_sent` · `nodes_per_leaf`
{ .metric-meta }

<!-- --8<-- [start:SyntaxStats-leaves] -->
A leaf is a word without dependent words (`count_children`), a subtree a word with them. The nodes per leaf are the words of a sentence over its leaves, averaged over the $S$ sentences.

$$
\frac{1}{S} \sum_{s=1}^{S} \frac{\textrm{Number of words of } s}{\textrm{Number of leaves of } s}
$$
<!-- --8<-- [end:SyntaxStats-leaves] -->

</div>

<div class="metric-card" markdown>

### Words before the root { #words_before_root }

`words_before_root` · [Coh-Metrix](https://doi.org/10.1017/CBO9780511894664)
{ .metric-meta }

<!-- --8<-- [start:SyntaxStats-words_before_root] -->
The left embeddedness of Coh-Metrix (SYNLE): the number of the words of a sentence before its root, the main predicate, averaged over the sentences whose root is a word. The root of a sentence with a copula is its nominal part (*she **is** a **doctor***), as Universal Dependencies has it. In a language with a free word order the measure reads the order as much as the complexity.
<!-- --8<-- [end:SyntaxStats-words_before_root] -->

</div>

<div class="metric-card" markdown>

### Valency of the finite verbs { #valency }

`verb_valency`
{ .metric-meta }

<!-- --8<-- [start:calc_valency] -->
``` {.python .signature}
calc_valency(word)
```

The valency of a word: the number of its dependent words (`get_children`), the relations `cc`, `conj`, `parataxis` and `punct` left out (`anyts.constants.VALENCY_IGNORED_DEPS`).

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `word` | `TreeWord` | - | Word of the tree |
<!-- --8<-- [end:calc_valency] -->

</div>

<div class="metric-card" markdown>

### Coordination chains { #coordination_chains }

`coordination_chains_per_sent` · `mean_coordination_chain_len`
{ .metric-meta }

<!-- --8<-- [start:calc_coordination_chains] -->
``` {.python .signature}
calc_coordination_chains(words)
```

The lengths of the coordination chains, in the order of their first words. A chain is a group of words linked by `conj`, whichever word each conjunct hangs on: Universal Dependencies attaches every conjunct to the first one (`pears → apples`, `plums → apples`), ClearNLP to the previous one (`pears → apples`, `plums → pears`); both give one chain of three for `apples, pears and plums`. A nested coordination (`cats and dogs, or birds`) and an enumeration split between several heads are one chain too. The length of a chain is the number of its words; a conjunct whose head lies outside the sequence is not linked to it.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `words` | `list[TreeWord]` | - | Words of the tree, such as those of a sentence |
<!-- --8<-- [end:calc_coordination_chains] -->

</div>

<div class="metric-card" markdown>

### Clauses { #clauses }

`clauses_per_sent` · `mean_clause_len`
{ .metric-meta }

<!-- --8<-- [start:is_clause_head] -->
``` {.python .signature}
is_clause_head(word, is_infinitive_periphrasis=None, auxiliary_form=None)
```

Checks whether a word heads a clause: the head of the sentence or a word with `ccomp`, `advcl`, `acl`, `csubj` or `parataxis` (`anyts.constants.CLAUSE_DEPS`, subtypes included) whose predicate (`predicate_form`, so `has been built` is finite) is not a participle, a converb or a gerund (`NONFINITE_CLAUSE_FORMS`, counted apart), nor an infinitive under `acl`; under `xcomp`, a finite predicate or an infinitive clause (`is_infinitive_clause`). A `parataxis` and a conjunct of a clause head count only as predicates (`is_predicate`); an infinitive conjunct and an infinitive subject (`csubj`) are no clause by the check `is_infinitive_periphrasis`, since a model may attach the infinitive of a periphrasis to its verb as `conj` and to a modal word as `csubj`; a loop of conjuncts is no clause.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `word` | `TreeWord` | - | Word of the tree |
| `is_infinitive_periphrasis` | `Callable[[TreeWord], bool]` | `None` | Whether an infinitive makes one predicate with its head; none by default |
| `auxiliary_form` | `Callable[[TreeWord], str]` | `None` | Verb form of an auxiliary without `VerbForm` (`predicate_form`); none by default |

A value that is not a `TreeWord` and a check of a periphrasis or a form of an auxiliary that is not callable raise `SourceTypeError`.
<!-- --8<-- [end:is_clause_head] -->

<!-- --8<-- [start:is_infinitive_clause] -->
``` {.python .signature}
is_infinitive_clause(word, is_infinitive_periphrasis=None, is_clause_head=None, auxiliary_form=None)
```

Checks whether an infinitive complement heads a clause of its own: an infinitive (`predicate_form`, so `to be chosen` is one) under `xcomp` (*wants to leave*), unless the language check `is_infinitive_periphrasis` says it makes one predicate with its head (*can leave*, *begins to leave*), or the word it completes, the first one up its chain of non-finite complements under `xcomp` (*kept trying to leave*, *seemed able to leave*) and of the infinitives of a periphrasis that a model attaches as `conj` or `csubj`, heads no clause by the check `is_clause_head`: an infinitive in a participial phrase or under an infinitive under `acl` (*trying to leave*, *the wish to try to leave*) belongs to that phrase. A ClearNLP parse hangs an infinitive after a predicative adjective on an `acomp` or `oprd` (*is ready to leave*), which heads no clause, so that infinitive is none.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `word` | `TreeWord` | - | Word of the tree |
| `is_infinitive_periphrasis` | `Callable[[TreeWord], bool]` | `None` | Whether an infinitive makes one predicate with its head; none by default |
| `is_clause_head` | `Callable[[TreeWord], bool]` | `None` | Whether a word heads a clause; `is_clause_head` of the module with the hooks of this check if not given |
| `auxiliary_form` | `Callable[[TreeWord], str]` | `None` | Verb form of an auxiliary without `VerbForm` (`predicate_form`); none by default |

A value that is not a `TreeWord` and a check or a form of an auxiliary that is not callable raise `SourceTypeError`.
<!-- --8<-- [end:is_infinitive_clause] -->

</div>

<div class="metric-card" markdown>

### Subordinate clauses { #subordinate_clauses }

`subordinate_clauses_per_sent` · `p_complex_sents`
{ .metric-meta }

<!-- --8<-- [start:is_subordinate_clause_head] -->
``` {.python .signature}
is_subordinate_clause_head(word, is_clause_head=None, auxiliary_form=None, subordinating_marks=(), is_subordinating_mark=None)
```

Checks whether a word heads a subordinate clause: a clause head by the check `is_clause_head` with `ccomp`, `advcl`, `acl` or `csubj` (`SUBORDINATE_CLAUSE_DEPS`), or `xcomp` (a complement a model attaches as `xcomp`), or a conjunct of one, by the relation of the first word up its chain of conjuncts; neither the predicate of that word nor its own is an infinitive, which heads an infinitive clause, counted apart, and a finite conjunct with a subject of its own of an infinitive takes the kind of the clause of the first word above the infinitives that is none. A conjunct or a parataxis with a subordinating mark (`is_subordinating_mark`) heads a subordinate clause, since a model may attach a clause of *because* as `conj`, and so do its conjuncts with a subject of their own; those sharing its subject do not, as a model attaches the predicates of the main clause to it as well.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `word` | `TreeWord` | - | Word of the tree |
| `is_clause_head` | `Callable[[TreeWord], bool]` | `None` | Whether a word heads a clause; `is_clause_head` of the module with the hooks of this check if not given |
| `auxiliary_form` | `Callable[[TreeWord], str]` | `None` | Verb form of an auxiliary without `VerbForm` (`predicate_form`); none by default |
| `subordinating_marks` | `Collection[str]` | `()` | Subordinating conjunctions in lower case, the words of a fixed expression after a space; none by default |
| `is_subordinating_mark` | `Callable[[TreeWord], bool]` | `None` | Whether a mark is a subordinating conjunction; `is_subordinating_mark` of the module with `subordinating_marks` if not given |

A value that is not a `TreeWord`, a check or a form of an auxiliary that is not callable and marks that are not a collection of strings raise `SourceTypeError`.
<!-- --8<-- [end:is_subordinate_clause_head] -->

<!-- --8<-- [start:is_subordinating_mark] -->
``` {.python .signature}
is_subordinating_mark(word, subordinating_marks=())
```

Checks whether a mark is a subordinating conjunction: a word with the relation `mark` whose form in lower case, with the words of its fixed expression after a space (*so that*), is one of `subordinating_marks`. The default of the hook `SyntaxStats.is_subordinating_mark`, which a library overrides to read the context of a word that is a conjunction and a pronoun.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `word` | `TreeWord` | - | Word of the tree |
| `subordinating_marks` | `Collection[str]` | `()` | Subordinating conjunctions in lower case, the words of a fixed expression after a space; none by default |

A value that is not a `TreeWord` and marks that are not a collection of strings raise `SourceTypeError`.
<!-- --8<-- [end:is_subordinating_mark] -->

</div>

<div class="metric-card" markdown>

### Infinitive clauses { #infinitive_clauses }

`infinitive_clauses_per_sent`
{ .metric-meta }

<!-- --8<-- [start:is_infinitive_clause_head] -->
``` {.python .signature}
is_infinitive_clause_head(word, is_clause_head=None, auxiliary_form=None, subordinating_marks=(), is_subordinating_mark=None)
```

Checks whether a word heads an infinitive clause: a clause head by the check `is_clause_head` whose own predicate is an infinitive, under `xcomp` or a relation of `SUBORDINATE_CLAUSE_DEPS` (*wants to leave*, *asked him to leave*, *came to help*, *it is hard to say*) or a conjunct of one, the first word up its chain of conjuncts deciding as in `is_subordinate_clause_head`; an infinitive under `conj` or `parataxis` with a subordinating mark, or an infinitive conjunct of it, heads one too (*came , in order to help*). Such a clause is counted apart from the subordinate ones, as grammars of many languages take it for a part of a simple sentence.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `word` | `TreeWord` | - | Word of the tree |
| `is_clause_head` | `Callable[[TreeWord], bool]` | `None` | Whether a word heads a clause; `is_clause_head` of the module with the hooks of this check if not given |
| `auxiliary_form` | `Callable[[TreeWord], str]` | `None` | Verb form of an auxiliary without `VerbForm` (`predicate_form`); none by default |
| `subordinating_marks` | `Collection[str]` | `()` | Subordinating conjunctions in lower case, the words of a fixed expression after a space; none by default |
| `is_subordinating_mark` | `Callable[[TreeWord], bool]` | `None` | Whether a mark is a subordinating conjunction; `is_subordinating_mark` of the module with `subordinating_marks` if not given |

A value that is not a `TreeWord`, a check or a form of an auxiliary that is not callable and marks that are not a collection of strings raise `SourceTypeError`.
<!-- --8<-- [end:is_infinitive_clause_head] -->

</div>

<div class="metric-card" markdown>

### Production units of L2SCA { #l2sca }

`t_units_per_sent` · `mean_t_unit_len` · `clauses_per_t_unit` · `p_complex_t_units` · `verb_phrases_per_t_unit` · `coordinate_phrases_per_clause` · `complex_nominals_per_clause` · [Lu 2010](https://doi.org/10.1075/ijcl.15.4.02lu)
{ .metric-meta }

<!-- --8<-- [start:SyntaxStats-l2sca] -->
The indices of the L2 Syntactic Complexity Analyzer (L2SCA) that the other metrics do not give, on Universal Dependencies. MLC and C/S are `mean_clause_len` and `clauses_per_sent`; MLS and DC/C come from the counts, `n_words / n_sents` and `n_subordinate_clauses / n_clauses`.

- A T-unit is a main clause with the clauses that depend on it: the head of a sentence and every clause head joined to it through `conj` or `parataxis` (`anyts.constants.MAIN_CLAUSE_DEPS`), so *I came, and he left* holds two; a conjunct of a subordinate clause is none. A conjunct without a subject of its own (*I came and left*) is a predicate sharing the T-unit of the clause it is coordinated to, as in L2SCA, unless its person, number or gender - those of its auxiliary or copula, its own without one - differ from those of that clause: in a language that drops its subjects the ending names another one (*llegamos al puerto y nos esperabas*). An existential *there* (`expl` of ClearNLP) is a subject. A conjunct or a parataxis with a subordinating mark (`is_subordinating_mark`) heads a subordinate or an infinitive clause, which is no T-unit, nor is a clause under it. A finite conjunct with a subject of its own of an infinitive clause, a predicate a model attaches to the infinitive, joins the clause of the first word above the infinitives that is none (*he came to help and she stayed*: two T-units). A T-unit is complex with a subordinate clause (`is_subordinate_clause_head`) whose nearest T-unit above is it.
- A verb phrase is a predicate (`is_predicate`) that is no auxiliary or copula: a verb, an auxiliary used as a predicate (*there **is** trouble*), a word with a subject or a copula; an infinitive that makes one predicate with its head (`is_infinitive_periphrasis`), and its infinitive conjunct, is part of the verb phrase of the head. A participle or another non-finite form under `amod` or `acl`, or coordinated to one, without an auxiliary, a copula or a subject of its own is an attribute of its noun (*the house built by workers*), as in L2SCA, not a verb phrase.
- A coordinate phrase is a coordination with a conjunct that is no clause head (*the man and the woman*, *is big and nice*) or a predicate without a subject of its own (*came and left*), counted once by its first conjunct; a coordination of clauses with their own subjects counts as clauses.
- The clauses of C/T, CP/C and CN/C are those of L2SCA (`n_l2sca_clauses`): the clauses of `is_clause_head` without the predicates sharing a subject (*came and left*) and the infinitive clauses, as L2SCA counts finite clauses with a subject. The head of a sentence heads a clause and a T-unit even without a predicate (*Yes.*, a heading, the name of a speaker), as a fragment does in L2SCA. C/S and MLC keep the clauses of the other metrics, so C/S runs higher and MLC lower than in L2SCA.
- A complex nominal is a noun with a modifier of `anyts.constants.COMPLEX_NOMINAL_DEPS` (an adjective, a complement, a relative or participial clause, an apposition, a possessive), or a nominal clause, a clause head of `anyts.constants.NOMINAL_CLAUSE_DEPS` or a conjunct of one.

$$
\textrm{MLT} = \frac{\textrm{Words}}{\textrm{T-units}}, \quad
\textrm{C/T} = \frac{\textrm{Clauses of L2SCA}}{\textrm{T-units}}, \quad
\textrm{CT/T} = \frac{\textrm{Complex T-units}}{\textrm{T-units}}, \quad
\textrm{CN/C} = \frac{\textrm{Complex nominals}}{\textrm{Clauses of L2SCA}}
$$
<!-- --8<-- [end:SyntaxStats-l2sca] -->

</div>

<div class="metric-card" markdown>

### Modifiers of a noun { #noun_modifiers }

`modifiers_per_noun`
{ .metric-meta }

<!-- --8<-- [start:count_noun_modifiers] -->
``` {.python .signature}
count_noun_modifiers(word)
```

Counts the modifiers of a noun phrase: the dependent words (`get_children`) with the relations `amod`, `det`, `nmod`, `nummod`, `acl` and their subtypes (`anyts.constants.NOUN_MODIFIER_DEPS`); `conj` and `appos` are no modifiers.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `word` | `TreeWord` | - | Word of the tree |
<!-- --8<-- [end:count_noun_modifiers] -->

</div>

<div class="metric-card" markdown>

### Prepositional chains { #prep_chains }

`prep_chains_per_sent` · `max_prep_chain_len` · [Profiling-UD](https://aclanthology.org/2020.lrec-1.883/)
{ .metric-meta }

<!-- --8<-- [start:SyntaxStats-prep_chains] -->
A prepositional chain is two or more nested complements with a preposition, each hanging on the previous one: *on the mat of the house of the mayor* (length 3). The links are the words of the hook `is_prep_complement`, and the chains and their lengths are those of `calc_modifier_chains`; a chain may start at a complement of a verb (`obl`) or at a prepositional predicate with a copula (*was in the house of the mayor*), but not at a conjunct of a complement (*in Madrid and in the centre of the city*), and a predicate of a relative clause (*the house that was by the river*) is no link of the chain of its noun. The chains read Universal Dependencies alone: ClearNLP heads a phrase by its preposition (`prep`, `pobj`), so its parses give no chains.
<!-- --8<-- [end:SyntaxStats-prep_chains] -->

<!-- --8<-- [start:is_prep_complement] -->
``` {.python .signature}
is_prep_complement(word)
```

Checks whether a word is a complement with a preposition: a word with the relation `nmod` or `obl` or a subtype of them (`anyts.constants.PREP_COMPLEMENT_DEPS`), or a predicate with a copula or a subject of its own out of a relative clause (`acl`), such as a nominal predicate of a language that drops the copula of the present tense, that has a dependent of the relation `case` that is an adposition (`ADP`) or begins one of several words (`fixed`: *in front of*). A noun in a case without a preposition and a possessive marker are none.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `word` | `TreeWord` | - | Word of the tree |

A value that is not a `TreeWord` raises `SourceTypeError`.
<!-- --8<-- [end:is_prep_complement] -->

</div>

<div class="metric-card" markdown>

### Participial clauses { #participle_clauses }

`participle_clauses_per_sent` · `mean_participle_clause_len`
{ .metric-meta }

<!-- --8<-- [start:SyntaxStats-participle_clauses] -->
The clauses headed by the words of the hook `is_participle_clause`; the length of a clause is the number of the words in the subtree of its head (`subtree_len`).
<!-- --8<-- [end:SyntaxStats-participle_clauses] -->

</div>

<div class="metric-card" markdown>

### Passive { #passive }

`p_passive` · `p_agentless_passive`
{ .metric-meta }

<!-- --8<-- [start:is_passive] -->
``` {.python .signature}
is_passive(word)
```

Checks whether a word is a passive verb form: a verb with `Voice=Pass` or a dependent `nsubj:pass`, `csubj:pass`, `aux:pass`, or `nsubjpass`, `csubjpass`, `auxpass` of ClearNLP (`PASSIVE_DEPS`).

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `word` | `TreeWord` | - | Word of the tree |

A value that is not a `TreeWord` raises `SourceTypeError`.
<!-- --8<-- [end:is_passive] -->

<!-- --8<-- [start:has_agent] -->
``` {.python .signature}
has_agent(word)
```

Checks whether a word has an agent: a dependent `obl:agent`, or `agent` of ClearNLP (`AGENT_DEPS`). The argument and the error are those of `is_passive`.
<!-- --8<-- [end:has_agent] -->

<!-- --8<-- [start:is_agentless] -->
``` {.python .signature}
is_agentless(word)
```

Checks whether a word is a passive form (`is_passive`) without an agent (`has_agent`), with the same argument and error.
<!-- --8<-- [end:is_agentless] -->

</div>

<div class="metric-card" markdown>

### Infinitives, negations and split predicates { #constructions }

`infinitives_per_sent` · `negations_per_sent` · `split_predicates_per_sent`
{ .metric-meta }

<!-- --8<-- [start:SyntaxStats-constructions] -->
The infinitives (`is_infinitive` of `anyts.utils`), the words of negation of the hook `is_negation` and the split predicates of the hook `find_split_predicates`, per sentence.
<!-- --8<-- [end:SyntaxStats-constructions] -->

</div>

<div class="metric-card" markdown>

### Order of the subjects and the objects { #word_order }

`p_preverbal_subjects` · `p_preverbal_objects` · [Profiling-UD](https://aclanthology.org/2020.lrec-1.883/)
{ .metric-meta }

<!-- --8<-- [start:SyntaxStats-word_order] -->
The order of the subjects and of the direct objects in the manner of Profiling-UD: the shares of those before their head, the predicate. Only the nominal ones (`NOUN`, `PROPN`) count: the place of a pronoun, such as a clitic object, is set by the grammar. A subject is a word of `nsubj` (`anyts.constants.NOMINAL_SUBJECT_DEPS`), an object one of `obj` (`anyts.constants.OBJECT_DEPS`), with the relations of ClearNLP and the subtypes.

$$
\frac{\textrm{Nominal subjects before their head}}{\textrm{Nominal subjects}}, \quad
\frac{\textrm{Nominal objects before their head}}{\textrm{Nominal objects}}
$$
<!-- --8<-- [end:SyntaxStats-word_order] -->

</div>

<div class="metric-card" markdown>

### Similarity of adjacent sentences { #similarity }

`pos_edit_distance` · `syntax_similarity` · [Coh-Metrix](https://doi.org/10.1017/CBO9780511894664)
{ .metric-meta }

<!-- --8<-- [start:SyntaxStats-similarity] -->
How alike the structures of two adjacent sentences are, averaged over the $S - 1$ pairs. `pos_edit_distance` is the edit distance of the parts of speech $P_s$ of the words of the sentences (SYNMEDpos of Coh-Metrix) over the length $n$ of the longer sentence of the pair, `calc_edit_distance`. `syntax_similarity` is the similarity of the multisets of the dependency triples $T$ of the two sentences (`dependency_triples`, `calc_multiset_similarity`), in the manner of SYNSTRUT of Coh-Metrix, which compares the nodes of phrase-structure trees. The edit distance reads only the order of the parts of speech: a sentence with its object first and one with its subject first are alike when that order is the same (a distance of 0). The triples read no order of the words at all: any order of the words of one tree gives a similarity of 1. The order of the subject and the object is read by [`p_preverbal_subjects` and `p_preverbal_objects`](#word_order). The similarity of the triples grows with the length of the sentences.

$$
\frac{1}{S - 1} \sum_{s=1}^{S-1} \frac{\textrm{lev}(P_s, P_{s+1})}{\max(n_s, n_{s+1})}, \quad
\frac{1}{S - 1} \sum_{s=1}^{S-1} \frac{|T_s \cap T_{s+1}|}{|T_s \cup T_{s+1}|}
$$
<!-- --8<-- [end:SyntaxStats-similarity] -->

<!-- --8<-- [start:dependency_triples] -->
``` {.python .signature}
dependency_triples(words)
```

The dependency triples of the words of a sentence (`get_words`), in their order: the part of speech of the head of a word - the nearest word above it through punctuation - its relation without a subtype (`base_dep`) and its own part of speech, such as `("NOUN", "amod", "ADJ")` for *a red house*. The head of the sentence, and a word with no word above it, give an empty head and the relation `root`, whatever its label.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `words` | `list[TreeWord]` | - | Words of the tree of a sentence |

Words that are not a list of `TreeWord` objects raise `SourceTypeError`.
<!-- --8<-- [end:dependency_triples] -->

<!-- --8<-- [start:calc_edit_distance] -->
``` {.python .signature}
calc_edit_distance(sents)
```

The mean edit distance of the items of adjacent sentences: the Levenshtein distance of every two - the fewest insertions, deletions and substitutions that turn one into the other - over the number of the items of the longer one, 0 for the same sequences and 1 for ones with no item in common; `nan` for fewer than two sentences.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `sents` | `list[list]` | - | Items of every sentence, such as its parts of speech |

Sentences that are not a list of lists, or items that cannot be hashed, raise `SourceTypeError`.
<!-- --8<-- [end:calc_edit_distance] -->

<!-- --8<-- [start:calc_multiset_similarity] -->
``` {.python .signature}
calc_multiset_similarity(sents)
```

The mean similarity of the multisets of the items of adjacent sentences: the weighted Jaccard similarity of every two - the items they share, each as many times as the sentence with fewer of them has it, over the items of both, each as many times as the sentence with more of them has it - 1 for the same multisets and for two empty ones, 0 for disjoint ones; `nan` for fewer than two sentences. A mapping is read by its keys, as a set.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `sents` | `list[list]` | - | Items of every sentence, such as its dependency triples |

Sentences that are not a list of collections, or items that cannot be hashed, raise `SourceTypeError`.
<!-- --8<-- [end:calc_multiset_similarity] -->

=== "Code"

    ``` python
    from anyts.syntax_stats import calc_edit_distance, calc_multiset_similarity

    calc_edit_distance([["DET", "NOUN", "VERB"], ["DET", "ADJ", "NOUN", "VERB"]])
    calc_multiset_similarity([["a", "a", "b"], ["a", "b", "b"]])
    ```

=== "Result"

    ```
    0.25
    0.5
    ```

</div>

<div class="metric-card" markdown>

### Ratio of the nouns to the verbs { #noun_verb_ratio }

`noun_verb_ratio`
{ .metric-meta }

<!-- --8<-- [start:SyntaxStats-noun_verb_ratio] -->
The number of the nouns `n_nouns` to the number of the verb forms `n_verbs`.

$$
\frac{\textrm{Number of nouns}}{\textrm{Number of verb forms}}
$$
<!-- --8<-- [end:SyntaxStats-noun_verb_ratio] -->

</div>


## Methods

The methods `get_stats`, `to_dataframe`, `print_stats` and `describe` are those of the [statistics interface](stats.md).

The functions of the tree take the words of the tree of a document (`TreeWord` of [`get_tree`](../document.md#get_tree)): a word, or a sequence of them such as a sentence of the tree, whose words are those of `get_words`. They read the relations that Universal Dependencies and the ClearNLP labels of the English models share: the head of a word, `cc`, `conj`, `parataxis`, `punct` and `aux`, the subjects `nsubj` and `csubj`, the modifiers of a noun `amod`, `det`, `nmod`, `nummod` and `acl`, the clause relations `ccomp`, `advcl` and `xcomp`, and the root; the copula `cop` of `predicate_form` and `is_predicate` exists in Universal Dependencies alone. The passive and its agent (`is_passive`, `has_agent`) and the order of the subjects and the objects read the relations of both schemes (`PASSIVE_DEPS`, `AGENT_DEPS`, `NOMINAL_SUBJECT_DEPS`, `OBJECT_DEPS`); the prepositional complements of `is_prep_complement` read Universal Dependencies alone. Everything else is up to a language library.

## Words of a sequence { #get_words }

<!-- --8<-- [start:get_words] -->
``` {.python .signature}
get_words(words)
```

The words of a sequence of words of the tree in their order: those with a letter or a digit, so punctuation marks and symbols are left out.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `words` | `list[TreeWord]` | - | Words of the tree, such as those of a sentence |
<!-- --8<-- [end:get_words] -->

## Head of a sentence { #is_root }

<!-- --8<-- [start:is_root] -->
``` {.python .signature}
is_root(word)
```

Checks whether a word is the head of its sentence: it has no head. A value that is no `TreeWord`, such as a spaCy `Token`, raises `SourceTypeError`.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `word` | `TreeWord` | - | Word of the tree |
<!-- --8<-- [end:is_root] -->

## Base relation { #base_dep }

<!-- --8<-- [start:base_dep] -->
``` {.python .signature}
base_dep(word)
```

The relation of a word without its subtype, which Universal Dependencies separates by a colon: `nsubj:pass` gives `nsubj`, `expl:pass` gives `expl`; a word without a relation gives an empty string.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `word` | `TreeWord` | - | Word of the tree |
<!-- --8<-- [end:base_dep] -->

## Dependent words { #get_children }

<!-- --8<-- [start:get_children] -->
``` {.python .signature}
get_children(word)
```

The dependent words of a word, punctuation marks and symbols left out.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `word` | `TreeWord` | - | Word of the tree |
<!-- --8<-- [end:get_children] -->

<!-- --8<-- [start:count_children] -->
``` {.python .signature}
count_children(word)
```

The number of the dependent words of a word; the argument is that of `get_children`.
<!-- --8<-- [end:count_children] -->

<!-- --8<-- [start:subtree_len] -->
``` {.python .signature}
subtree_len(word)
```

The number of words in the subtree of a word: the word itself and all of its direct and indirect dependents, punctuation left out; the argument is that of `get_children`.
<!-- --8<-- [end:subtree_len] -->

## Verb form of a predicate { #verb-forms }

<!-- --8<-- [start:predicate_form] -->
``` {.python .signature}
predicate_form(word, auxiliary_form=None)
```

The verb form of a predicate by the forms (`VerbForm`) of its auxiliaries and copulas (`aux` and `cop` with their subtypes, `anyts.constants.AUXILIARY_DEPS`), as Universal Dependencies annotates them. A finite auxiliary makes the predicate finite wherever it stands (*had arrived*, the German *gekommen sein wird*); otherwise the first auxiliary decides (*to have gone* is an infinitive, *being chosen* a gerund), and without auxiliaries the word itself. A past participle auxiliary counts as finite, since it follows a finite one the parser may attach to another word (*had been chosen*); a present participle (*having eaten*) does not. A ClearNLP parse has no copula relation: its copula heads the clause with its own form, and its passive auxiliary `auxpass` is not read. An auxiliary the model leaves without a form is read by the language hook `auxiliary_form`, which gives its form or an empty string to skip it; without the hook it is skipped. A word with no verb form gives an empty string.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `word` | `TreeWord` | - | Word of the tree |
| `auxiliary_form` | `Callable[[TreeWord], str]` | `None` | Verb form of an auxiliary without `VerbForm` |

A value that is not a `TreeWord` and a hook that is not callable raise `SourceTypeError`.
<!-- --8<-- [end:predicate_form] -->

=== "Code"

    ``` python
    import spacy
    from spacy.tokens import Doc

    from anyts.document import get_tree, to_document
    from anyts.syntax_stats import predicate_form

    vocab = spacy.blank("en").vocab
    doc = Doc(
        vocab,
        words=["She", "had", "been", "chosen"],
        heads=[3, 3, 3, 3],
        deps=["nsubj:pass", "aux", "aux:pass", "ROOT"],
        morphs=["Case=Nom", "VerbForm=Fin", "VerbForm=Part", "VerbForm=Part"],
    )
    chosen = get_tree(to_document(doc)).words[3]
    predicate_form(chosen)
    # An auxiliary the model left without a form, read by the hook
    doc = Doc(
        vocab,
        words=["to", "have", "gone"],
        heads=[2, 2, 2],
        deps=["mark", "aux", "ROOT"],
        morphs=["", "", "VerbForm=Part"],
    )
    gone = get_tree(to_document(doc)).words[2]
    predicate_form(gone), predicate_form(gone, lambda aux: "Inf" if aux.form.lower() == "have" else "")
    ```

=== "Result"

    ```
    'Fin'
    ('Part', 'Inf')
    ```

## Predicate of a clause { #is_predicate }

<!-- --8<-- [start:is_predicate] -->
``` {.python .signature}
is_predicate(word)
```

Checks whether a word can be the predicate of its clause: a verb (`VERB`, `AUX`), a word with a subject of its own (`nsubj`, `csubj` and their subtypes, `anyts.constants.SUBJECT_DEPS`) or with a copula (`cop`), so the nominal predicate of `he is tall` and of a language that drops the subject passes and a parenthetical word does not.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `word` | `TreeWord` | - | Word of the tree |

A value that is not a `TreeWord` raises `SourceTypeError`.
<!-- --8<-- [end:is_predicate] -->

## Chains of modifiers { #calc_modifier_chains }

<!-- --8<-- [start:calc_modifier_chains] -->
``` {.python .signature}
calc_modifier_chains(words, is_modifier)
```

The lengths of the chains of nested modifiers, in the order of the words. A chain is two or more modifiers each hanging on the previous one, such as the complements of `the increase of the efficiency of the use of resources` (length 3); the check `is_modifier` of a language says what a modifier is (a complement with a preposition, a noun in the genitive). A chain starts at a modifier whose head is none, and its length is the number of modifiers in its longest branch. The links are those of `get_children`: punctuation is no link.

| Parameter | Type | Default | Description |
| :-------- | :--- | :------ | :---------- |
| `words` | `list[TreeWord]` | - | Words of the tree, such as those of a sentence |
| `is_modifier` | `Callable[[TreeWord], bool]` | - | Whether a word is a modifier of the chain |

A check that is not callable raises `SourceTypeError`.
<!-- --8<-- [end:calc_modifier_chains] -->

=== "Code"

    ``` python
    import spacy
    from spacy.tokens import Doc

    from anyts.document import get_tree, to_document
    from anyts.syntax_stats import calc_modifier_chains

    doc = Doc(
        spacy.blank("en").vocab,
        words=["the", "use", "of", "the", "water", "of", "the", "river"],
        heads=[1, 1, 4, 4, 1, 7, 7, 4],
        deps=["det", "ROOT", "case", "det", "nmod", "case", "det", "nmod"],
    )
    sentence = get_tree(to_document(doc)).sentences[0]
    calc_modifier_chains(sentence, lambda word: word.deprel == "nmod")
    ```

=== "Result"

    ```
    [2]
    ```

## For library developers { #hooks }

<details class="library-hooks" markdown>
<summary>Language hooks of a subclass</summary>

<!-- --8<-- [start:SyntaxStats-hooks] -->
A language library subclasses `SyntaxStats`. The hooks of a word get a `TreeWord` of the tree of the document of `parse` (`get_tree`). The defaults read Universal Dependencies with its morphological features and the relations it shares with ClearNLP; the passive, its agent and the order of the subjects and the objects read the relations of both, the prepositional chains those of Universal Dependencies:

| Hook | Kind | Description |
| :--- | :--- | :---------- |
| `parse(source)` | method | Document of the source, from `Stats`; a library sets it to parse and annotate a string in its language |
| `is_clause_head(word)` | method | Whether a word heads a clause; by default `is_clause_head` of the module with the hooks `is_infinitive_periphrasis` and `auxiliary_form` |
| `is_infinitive_periphrasis(word)` | method | Whether an infinitive under `xcomp`, an infinitive conjunct or an infinitive subject (`csubj`) of a modal word makes one predicate with its head, a modal or phasal verb (*can leave*, *begins to leave*): one clause and one verb phrase; none by default |
| `auxiliary_form(word)` | method | Verb form the checks of the clauses read for an auxiliary or a copula without `VerbForm` (`predicate_form`); by default an empty string, which skips it |
| `is_subordinate_clause_head(word)` | method | Whether a clause head heads a subordinate clause, asked only of the words of `is_clause_head`; by default `is_subordinate_clause_head` of the module over the hooks `is_clause_head`, `auxiliary_form` and `is_subordinating_mark` |
| `is_infinitive_clause_head(word)` | method | Whether a clause head heads an infinitive clause (*wants to leave*, *came to help*), counted apart from the subordinate ones; by default `is_infinitive_clause_head` of the module over the hooks `is_clause_head`, `auxiliary_form` and `is_subordinating_mark` |
| `is_subordinating_mark(word)` | method | Whether a mark of a conjunct or a parataxis is a subordinating conjunction, which makes it a subordinate clause (an infinitive one with an infinitive); by default `is_subordinating_mark` of the module with `subordinating_marks`; a library reads the context of a word that is a conjunction and a pronoun |
| `is_prep_complement(word)` | method | Whether a word is a link of a prepositional chain; by default `is_prep_complement` of the module. It gets the words of `sents` on first use |
| `is_participle_clause(word)` | method | Whether a word heads a participial clause; by default a participle that is not the head of the sentence, has no auxiliary or copula and has a dependent (`calc_valency`) |
| `is_passive(word)` | method | Whether a word is a passive verb form; by default `is_passive` of the module |
| `is_agentless(word)` | method | Whether a passive form has no agent; by default the hook `is_passive` without an agent (`has_agent` of the module) |
| `is_negation(word)` | method | Whether a word is a word of negation; by default `Polarity=Neg` or a word of `negation_words`, a conjunction excluded |
| `find_split_predicates(words)` | method | Pairs of a light verb and the noun that carries its meaning (`to make a decision`) among the words of the text; none by default |
| `negation_words` | class attribute | Words of negation besides `Polarity=Neg`, in lower case; none by default |
| `subordinating_marks` | class attribute | Subordinating conjunctions in lower case, the words of a fixed expression after a space, for the hook `is_subordinating_mark` (*because*, *so that*); none by default |
| `requires_lemmas` | class attribute | Whether the source must carry lemmas, for hooks that read them |
| `stats_desc`, `stats_headers` | class attributes | Statistics of `get_stats` with their descriptions (`SYNTAX_STATS_DESC` by default), headers of the columns for `print_stats` |
| `messages` | class attribute | Messages of the errors by key; `MESSAGES` by default |

The subclass adds the statistics of the constructions of its language (chains of complements by `calc_modifier_chains`, its own clauses) in its constructor from `sents`, with its own `stats_desc`. A `negation_words` or `subordinating_marks` that is not a collection of strings raises `SourceTypeError` when the class is defined, and so does a `parse` that does not return a `Document` when the statistics are computed.
<!-- --8<-- [end:SyntaxStats-hooks] -->

</details>
