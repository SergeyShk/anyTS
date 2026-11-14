from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Collection, Hashable, Iterable, Mapping, Sequence
from functools import cache, cached_property, partial, wraps
from itertools import pairwise
from math import nan
from statistics import fmean, pstdev
from typing import TYPE_CHECKING, Any, ClassVar, TypeVar, cast

from .constants import (
    AGENT_DEPS,
    AUXILIARY_DEPS,
    CLAUSE_DEPS,
    COMPLEX_NOMINAL_DEPS,
    MAIN_CLAUSE_DEPS,
    NOMINAL_CLAUSE_DEPS,
    NOMINAL_SUBJECT_DEPS,
    NONFINITE_CLAUSE_FORMS,
    NOUN_MODIFIER_DEPS,
    OBJECT_DEPS,
    PASSIVE_DEPS,
    PREP_COMPLEMENT_DEPS,
    SUBJECT_DEPS,
    SUBORDINATE_CLAUSE_DEPS,
    SYNTAX_STATS_DESC,
    VALENCY_IGNORED_DEPS,
)
from .document import TreeWord, get_tree
from .exceptions import SourceError, SourceTypeError
from .stats import Stats
from .utils import (
    check_callable,
    check_sequence,
    check_words,
    has_feature,
    has_words,
    is_finite_verb,
    is_infinitive,
    safe_divide,
    safe_mean,
)

if TYPE_CHECKING:
    from anyseg import Document
    from spacy.tokens import Doc

_Function = TypeVar("_Function", bound=Callable[..., Any])

# Relations of the subject of a clause: a subtype counts as its base one, and ClearNLP marks
# the passive in the label
_SUBJECT_DEPS = SUBJECT_DEPS | {"csubjpass", "nsubjpass"}
# Features of a verb that agree with its subject
_AGREEMENT_FEATURES = ("Person", "Number", "Gender")


def _takes_word(function: _Function) -> _Function:
    """A function of a word: a value that is no TreeWord raises SourceTypeError"""

    @wraps(function)
    def checked(word: object, *args: Any, **kwargs: Any) -> Any:
        if not isinstance(word, TreeWord):
            raise SourceTypeError(f"A TreeWord is expected, not {type(word).__name__}")
        return function(word, *args, **kwargs)

    return cast(_Function, checked)


class SyntaxStats(Stats):
    """
    Base of the syntactic statistics of a text

    Description:
        Measures of the dependency tree and of the syntactic constructions
        (Ivanov, Solnyshkina and Solovyev 2018) over the tree of the document
        of parse (get_tree). Punctuation and symbols are no nodes of the tree,
        and the distances are counted in positions of words. The measures of a
        sentence (the longest dependency, the depth, the nodes per leaf) are
        averaged over the sentences, the constructions are given per sentence.
        A language library subclasses the class and sets its hooks; the
        defaults read Universal Dependencies and the relations it shares with
        ClearNLP. The subclass adds the statistics of its own constructions
        from sents. The units of L2SCA, the prepositional chains and the
        similarity of sentences are computed from sents on first use.
        get_stats, to_dataframe, print_stats and describe come from Stats

    References:
        https://universaldependencies.org/u/dep/
        https://dialogue-conf.org/media/4302/ivanovvv.pdf

    Arguments:
        source (str|Doc|Document): Data source with a dependency parse and parts of
            speech (a Doc, a Document, or what parse makes one of)

    Attributes:
        sents (tuple[tuple[TreeWord]]): Words of every sentence with words
        n_sents (int): Number of sentences with words
        n_words (int): Number of words
        n_leaves (int): Number of leaves - words with no dependent word
        n_subtrees (int): Number of subtrees - words with dependent words
        n_coordination_chains (int): Number of coordination chains
        n_clauses (int): Number of clauses
        n_subordinate_clauses (int): Number of subordinate clauses
        n_complex_sents (int): Number of sentences with a subordinate clause
        n_infinitive_clauses (int): Number of infinitive clauses
        n_t_units, n_complex_t_units (int): Numbers of the T-units and of those with a
            subordinate clause
        n_l2sca_clauses (int): Number of the clauses of L2SCA - clauses besides the
            predicates sharing a subject and the infinitive clauses
        n_verb_phrases, n_coordinate_phrases, n_complex_nominals (int): Numbers of the verb
            phrases, of the coordinate phrases and of the complex nominals
        n_nouns (int): Number of nouns
        n_prep_chains (int): Number of prepositional chains
        n_participle_clauses (int): Number of participial clauses
        n_verbs (int): Number of verb forms
        n_passive (int): Number of passive verb forms
        n_agentless_passive (int): Number of passive forms with no agent
        n_infinitives (int): Number of infinitives
        n_negations (int): Number of words of negation
        n_split_predicates (int): Number of split predicates
        n_nominal_subjects, n_preverbal_subjects (int): Numbers of the nominal subjects
            and of those before their head
        n_nominal_objects, n_preverbal_objects (int): Numbers of the nominal direct
            objects and of those before their head
        split_predicates (tuple[str]): Split predicates, the verb and the noun
        c_children (dict[int, int]): Distribution of words by number of dependent words
        c_deps (dict[str, int]): Distribution of words by syntactic relation
        mean_dependency_distance (float): Mean dependency distance
        std_dependency_distance (float): Standard deviation of the dependency distance
        max_dependency_distance (float): Mean of the longest dependencies of the
            sentences that have dependencies
        p_adjacent_dependencies (float): Share of adjacent dependencies - of length 1
        tree_depth (float): Mean depth of the dependency tree of a sentence
        leaves_per_sent (float): Leaves per sentence
        subtrees_per_sent (float): Subtrees per sentence
        nodes_per_leaf (float): Mean over the sentences of the words per leaf
        words_before_root (float): Mean number of words before the root of a sentence
        verb_valency (float): Mean number of dependents of a finite verb
        coordination_chains_per_sent (float): Coordination chains per sentence
        mean_coordination_chain_len (float): Mean length of a coordination chain
        clauses_per_sent (float): Clauses per sentence
        mean_clause_len (float): Mean length of a clause in words
        subordinate_clauses_per_sent (float): Subordinate clauses per sentence
        p_complex_sents (float): Share of sentences with a subordinate clause
        infinitive_clauses_per_sent (float): Infinitive clauses per sentence
        t_units_per_sent (float): T-units per sentence
        mean_t_unit_len (float): Mean length of a T-unit in words
        clauses_per_t_unit (float): Clauses per T-unit
        p_complex_t_units (float): Share of the T-units with a subordinate clause
        verb_phrases_per_t_unit (float): Verb phrases per T-unit
        coordinate_phrases_per_clause (float): Coordinate phrases per clause
        complex_nominals_per_clause (float): Complex nominals per clause
        modifiers_per_noun (float): Mean number of modifiers of a noun
        prep_chains_per_sent (float): Prepositional chains per sentence
        max_prep_chain_len (int): Length of the longest prepositional chain, 0 without
            chains
        participle_clauses_per_sent (float): Participial clauses per sentence
        mean_participle_clause_len (float): Mean length of a participial clause in words
        p_passive (float): Share of passive forms among the verb forms
        p_agentless_passive (float): Share of forms with no agent among the passive ones
        infinitives_per_sent (float): Infinitives per sentence
        negations_per_sent (float): Words of negation per sentence
        split_predicates_per_sent (float): Split predicates per sentence
        p_preverbal_subjects (float): Share of the nominal subjects before their head
        p_preverbal_objects (float): Share of the nominal direct objects before their head
        pos_edit_distance (float): Mean edit distance of the parts of speech of adjacent
            sentences over the longer one
        syntax_similarity (float): Mean similarity of the dependency triples of adjacent
            sentences
        noun_verb_ratio (float): Ratio of the nouns to the verb forms

    Methods:
        is_clause_head: Whether a word heads a clause
        is_infinitive_periphrasis: Whether an infinitive makes one predicate with its head
        auxiliary_form: Verb form of an auxiliary without the feature VerbForm
        is_subordinate_clause_head: Whether a clause head heads a subordinate clause
        is_infinitive_clause_head: Whether a clause head heads an infinitive clause
        is_subordinating_mark: Whether a mark is a subordinating conjunction
        is_prep_complement: Whether a word is a link of a prepositional chain
        is_participle_clause: Whether a word heads a participial clause
        is_passive: Whether a word is a passive verb form
        is_agentless: Whether a passive form has no agent
        is_negation: Whether a word is a word of negation
        find_split_predicates: Split predicates of the words

    Class attributes:
        requires_lemmas (bool): Whether the source must carry lemmas
        negation_words (frozenset[str]): Words of negation besides Polarity=Neg, in
            lower case
        subordinating_marks (frozenset[str]): Subordinating conjunctions in lower case,
            with the words of their fixed expression after a space, that make a conjunct
            or a parataxis they mark a subordinate clause, an infinitive clause with an
            infinitive (is_subordinating_mark)
        stats_desc (dict[str, str]): Statistics of get_stats and their descriptions for
            print_stats

    Raises:
        SourceTypeError: If the source is neither a string, a Doc nor a Document
            object or parse does not return a Document; when a class is defined, if
            its negation_words or subordinating_marks are not a collection of strings
        SourceError: If the source has no dependency parse, no parts of speech, no
            lemmas when requires_lemmas, or no words, or a token of a Doc runs over a
            blank line
    """

    requires_lemmas: ClassVar[bool] = False
    negation_words: ClassVar[frozenset[str]] = frozenset()
    subordinating_marks: ClassVar[frozenset[str]] = frozenset()

    stats_desc: ClassVar[Mapping[str, str]] = SYNTAX_STATS_DESC

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        check_words(cls.negation_words, "negation_words", ordered=False)
        check_words(cls.subordinating_marks, "subordinating_marks", ordered=False)

    def __init__(self, source: str | Doc | Document):
        messages = self.messages
        document = self._document(source)
        if not any(document.column("deprel")):
            parsed = any(map(has_words, document.column("form")))
            raise SourceError(messages["no_parse" if parsed else "no_words"])
        tree = get_tree(document)
        tagged = [word for word in tree.words if _is_word(word)] or tree.words
        if not any(word.upos for word in tagged):
            raise SourceError(messages["no_pos"])
        if self.requires_lemmas and not any(word.lemma for word in tree.words):
            raise SourceError(messages["no_lemmas"])
        spans, sents = [], []
        for span in tree.sentences:
            if sent_words := get_words(span):
                spans.append(span)
                sents.append(tuple(sent_words))
        if not sents:
            raise SourceError(messages["no_words"])
        self.sents = tuple(sents)
        words = [word for sent in sents for word in sent]
        self.n_sents = len(sents)
        self.n_words = len(words)

        distances = [calc_dependency_distances(span) for span in spans]
        all_distances = [distance for sent in distances for distance in sent]
        depths = [calc_tree_depth(span) for span in spans]
        children = [[count_children(word) for word in sent] for sent in sents]
        leaves = [sum(1 for count in sent if not count) for sent in children]
        self.c_children = dict(
            sorted(Counter(count for sent in children for count in sent).items())
        )
        self.c_deps = dict(sorted(Counter(word.deprel or "" for word in words).items()))
        self.n_leaves = sum(leaves)
        self.n_subtrees = self.n_words - self.n_leaves
        finite_verbs = [word for word in words if is_finite_verb(word)]
        chains = [length for span in spans for length in calc_coordination_chains(span)]
        self.n_coordination_chains = len(chains)
        heads = [[word for word in sent if self.is_clause_head(word)] for sent in sents]
        self.n_clauses = sum(map(len, heads))
        subordinate = [
            [word for word in sent if self.is_subordinate_clause_head(word)] for sent in heads
        ]
        self.n_subordinate_clauses = sum(map(len, subordinate))
        self.n_complex_sents = sum(1 for sent in subordinate if sent)
        infinitive = [
            word.index for sent in heads for word in sent if self.is_infinitive_clause_head(word)
        ]
        self.n_infinitive_clauses = len(infinitive)
        nouns = [word for word in words if word.upos in ("NOUN", "PROPN")]
        self.n_nouns = len(nouns)
        participle_clauses = [
            subtree_len(word) for word in words if self.is_participle_clause(word)
        ]
        self.n_participle_clauses = len(participle_clauses)
        self.n_verbs = sum(1 for word in words if word.upos == "VERB")
        passive = [word for word in words if self.is_passive(word)]
        self.n_passive = len(passive)
        self.n_agentless_passive = sum(1 for word in passive if self.is_agentless(word))
        self.n_infinitives = sum(1 for word in words if is_infinitive(word))
        self.n_negations = sum(1 for word in words if self.is_negation(word))
        split_predicates = self.find_split_predicates(words)
        self.n_split_predicates = len(split_predicates)
        self.split_predicates = tuple(
            f"{verb.form} {noun.form}" for verb, noun in split_predicates
        )
        subjects = [word for word in nouns if base_dep(word) in NOMINAL_SUBJECT_DEPS]
        objects = [word for word in nouns if base_dep(word) in OBJECT_DEPS]
        self.n_nominal_subjects = len(subjects)
        self.n_preverbal_subjects = sum(1 for word in subjects if _before_head(word))
        self.n_nominal_objects = len(objects)
        self.n_preverbal_objects = sum(1 for word in objects if _before_head(word))
        # The units of the statistics computed on first use
        self._spans = tuple(spans)
        self._clause_heads = tuple(tuple(sent) for sent in heads)
        self._subordinate_heads = tuple(tuple(sent) for sent in subordinate)
        self._infinitive_heads = frozenset(infinitive)

        self.mean_dependency_distance = safe_mean(all_distances)
        self.std_dependency_distance = pstdev(all_distances) if all_distances else nan
        sent_maxima = [max(sent) for sent in distances if sent]
        self.max_dependency_distance = safe_mean(sent_maxima)
        self.p_adjacent_dependencies = safe_divide(
            sum(1 for distance in all_distances if distance == 1), len(all_distances), nan
        )
        self.tree_depth = fmean(depths)
        self.leaves_per_sent = self.n_leaves / self.n_sents
        self.subtrees_per_sent = self.n_subtrees / self.n_sents
        self.nodes_per_leaf = fmean(
            safe_divide(len(sent), n_leaves, nan)
            for sent, n_leaves in zip(sents, leaves, strict=True)
        )
        roots = [next((i for i, word in enumerate(sent) if is_root(word)), None) for sent in sents]
        self.words_before_root = safe_mean([i for i in roots if i is not None])
        self.verb_valency = safe_divide(
            sum(calc_valency(word) for word in finite_verbs), len(finite_verbs), nan
        )
        self.coordination_chains_per_sent = self.n_coordination_chains / self.n_sents
        self.mean_coordination_chain_len = safe_mean(chains)
        self.clauses_per_sent = self.n_clauses / self.n_sents
        self.mean_clause_len = safe_divide(self.n_words, self.n_clauses, nan)
        self.subordinate_clauses_per_sent = self.n_subordinate_clauses / self.n_sents
        self.p_complex_sents = self.n_complex_sents / self.n_sents
        self.infinitive_clauses_per_sent = self.n_infinitive_clauses / self.n_sents
        self.modifiers_per_noun = safe_divide(
            sum(count_noun_modifiers(word) for word in nouns), self.n_nouns, nan
        )
        self.participle_clauses_per_sent = self.n_participle_clauses / self.n_sents
        self.mean_participle_clause_len = safe_mean(participle_clauses)
        self.p_passive = safe_divide(self.n_passive, self.n_verbs, nan)
        self.p_agentless_passive = safe_divide(self.n_agentless_passive, self.n_passive, nan)
        self.infinitives_per_sent = self.n_infinitives / self.n_sents
        self.negations_per_sent = self.n_negations / self.n_sents
        self.split_predicates_per_sent = self.n_split_predicates / self.n_sents
        self.p_preverbal_subjects = safe_divide(
            self.n_preverbal_subjects, self.n_nominal_subjects, nan
        )
        self.p_preverbal_objects = safe_divide(
            self.n_preverbal_objects, self.n_nominal_objects, nan
        )
        self.noun_verb_ratio = safe_divide(self.n_nouns, self.n_verbs, nan)

    @cached_property
    def _l2sca(self) -> dict[str, int]:
        """Numbers of the units of L2SCA"""
        words = [word for sent in self.sents for word in sent]
        heads = self._clause_heads
        clause_ids = {word.index for sent in heads for word in sent}
        # A conjunct or a parataxis with a subordinating mark heads a subordinate or an infinitive
        # clause: no T-unit nor a clause under it, no member of the coordination it hangs on
        marked = {
            word.index
            for sent in heads
            for word in sent
            if base_dep(word) in MAIN_CLAUSE_DEPS and _has_mark(word, self.is_subordinating_mark)
        }
        firsts = _first_conjuncts(words, marked)
        # A finite conjunct with a subject of its own of an infinitive clause, a predicate a model
        # attaches to the infinitive, joins the clause the chain of infinitives completes
        reattached = {
            word.index: owner
            for sent in heads
            for word in sent
            if base_dep(word) == "conj"
            and (first := firsts[word.index]) is not None
            and first.index in self._infinitive_heads
            and word.index not in self._infinitive_heads
            and not _shares_subject(word)
            and (owner := _infinitive_owner(first, self.auxiliary_form)) is not None
        }
        n_t_units = n_complex_t_units = 0
        for sent, subordinate in zip(heads, self._subordinate_heads, strict=True):
            units = {word.index for word in _t_unit_heads(sent, marked, reattached)}
            n_t_units += len(units)
            n_complex_t_units += len(_t_units_of(subordinate, units) - {None})
        coordinations: dict[int, list[TreeWord]] = {}
        for word in words:
            first = firsts[word.index]
            if base_dep(word) == "conj" and first is not None and word.index not in marked:
                coordinations.setdefault(first.index, []).append(word)
        nouns = [word for word in words if word.upos in ("NOUN", "PROPN")]
        modified = _heads_of(words, COMPLEX_NOMINAL_DEPS)
        word_of = {word.index: word for word in words}
        predicates = {
            word.index
            for word in words
            if word.upos in ("VERB", "AUX") and not self._is_attributive(word, firsts)
        } | _heads_of(words, SUBJECT_DEPS | {"cop"})
        return {
            "n_t_units": n_t_units,
            "n_complex_t_units": n_complex_t_units,
            "n_l2sca_clauses": sum(
                1
                for sent in heads
                for word in sent
                if (word.index in marked or not _shares_subject(word))
                and word.index not in self._infinitive_heads
            ),
            # A coordination of phrases, or of predicates sharing a subject
            "n_coordinate_phrases": sum(
                1
                for first, conjuncts in coordinations.items()
                if first not in clause_ids
                or any(word.index not in clause_ids or _shares_subject(word) for word in conjuncts)
            ),
            "n_complex_nominals": sum(1 for word in nouns if word.index in modified)
            + sum(
                1
                for sent in heads
                for word in sent
                if (first := firsts[word.index]) is not None
                and base_dep(first) in NOMINAL_CLAUSE_DEPS
            ),
            "n_verb_phrases": sum(
                1
                for i in predicates
                if i in word_of
                and base_dep(word_of[i]) not in AUXILIARY_DEPS | {"auxpass"}
                and not _in_periphrasis(
                    word_of[i], self.is_infinitive_periphrasis, self.auxiliary_form
                )
            ),
        }

    def _is_attributive(self, word: TreeWord, firsts: Mapping[int, TreeWord | None]) -> bool:
        """Whether a non-finite verb form is an attribute of a noun: under amod or acl, or
        coordinated to one, without an auxiliary or a copula, which L2SCA takes for a part of
        the noun phrase; one with a subject of its own stays a predicate (is_predicate)"""
        if predicate_form(word, self.auxiliary_form) not in NONFINITE_CLAUSE_FORMS:
            return False
        first = firsts[word.index]
        return base_dep(first if first is not None else word) in ("acl", "amod") and not any(
            base_dep(child) in AUXILIARY_DEPS for child in word.children
        )

    @property
    def n_t_units(self) -> int:
        return self._l2sca["n_t_units"]

    @property
    def n_complex_t_units(self) -> int:
        return self._l2sca["n_complex_t_units"]

    @property
    def n_verb_phrases(self) -> int:
        return self._l2sca["n_verb_phrases"]

    @property
    def n_coordinate_phrases(self) -> int:
        return self._l2sca["n_coordinate_phrases"]

    @property
    def n_complex_nominals(self) -> int:
        return self._l2sca["n_complex_nominals"]

    @property
    def n_l2sca_clauses(self) -> int:
        return self._l2sca["n_l2sca_clauses"]

    @property
    def t_units_per_sent(self) -> float:
        return self.n_t_units / self.n_sents

    @property
    def mean_t_unit_len(self) -> float:
        return safe_divide(self.n_words, self.n_t_units, nan)

    @property
    def clauses_per_t_unit(self) -> float:
        return safe_divide(self.n_l2sca_clauses, self.n_t_units, nan)

    @property
    def p_complex_t_units(self) -> float:
        return safe_divide(self.n_complex_t_units, self.n_t_units, nan)

    @property
    def verb_phrases_per_t_unit(self) -> float:
        return safe_divide(self.n_verb_phrases, self.n_t_units, nan)

    @property
    def coordinate_phrases_per_clause(self) -> float:
        return safe_divide(self.n_coordinate_phrases, self.n_l2sca_clauses, nan)

    @property
    def complex_nominals_per_clause(self) -> float:
        return safe_divide(self.n_complex_nominals, self.n_l2sca_clauses, nan)

    @cached_property
    def _prep_chains(self) -> list[int]:
        """Lengths of the prepositional chains"""
        return [
            length
            for span in self._spans
            for length in calc_modifier_chains(span, self.is_prep_complement)
        ]

    @property
    def n_prep_chains(self) -> int:
        return len(self._prep_chains)

    @property
    def prep_chains_per_sent(self) -> float:
        return self.n_prep_chains / self.n_sents

    @property
    def max_prep_chain_len(self) -> int:
        return max(self._prep_chains, default=0)

    @cached_property
    def pos_edit_distance(self) -> float:
        return _mean_edit_distance([[word.upos or "" for word in sent] for sent in self.sents])

    @cached_property
    def syntax_similarity(self) -> float:
        return _mean_multiset_similarity(
            [Counter(_word_triple(word) for word in sent) for sent in self.sents]
        )

    def is_clause_head(self, word: TreeWord) -> bool:
        """
        Checking whether a word heads a clause

        Description:
            is_clause_head of the module with the hooks is_infinitive_periphrasis
            and auxiliary_form

        Arguments:
            word (TreeWord): Word of the tree

        Returns:
            bool: Result of the check
        """
        return is_clause_head(word, self.is_infinitive_periphrasis, self.auxiliary_form)

    def is_infinitive_periphrasis(self, word: TreeWord) -> bool:
        """
        Checking whether an infinitive makes one predicate with its head

        Description:
            A periphrasis of a modal or phasal verb with an infinitive (can
            leave, begins to leave) is one clause and one verb phrase of L2SCA; the
            check gets an infinitive under xcomp, an infinitive conjunct and an
            infinitive subject (csubj) of a modal word (is_clause_head); none by default

        Arguments:
            word (TreeWord): Word of the tree

        Returns:
            bool: Result of the check
        """
        return False

    def auxiliary_form(self, word: TreeWord) -> str:
        """
        Getting the verb form of an auxiliary without the feature VerbForm

        Description:
            The form the checks of the clauses read for an auxiliary or a copula
            the model leaves without one (predicate_form); an empty string, which
            skips the auxiliary, by default

        Arguments:
            word (TreeWord): Auxiliary or copula

        Returns:
            str: Value of VerbForm, an empty string to skip the auxiliary
        """
        return ""

    def is_subordinate_clause_head(self, word: TreeWord) -> bool:
        """
        Checking whether a word heads a subordinate clause

        Description:
            is_subordinate_clause_head of the module over the hooks is_clause_head,
            auxiliary_form and is_subordinating_mark

        Arguments:
            word (TreeWord): Word of the tree

        Returns:
            bool: Result of the check
        """
        return is_subordinate_clause_head(
            word,
            self.is_clause_head,
            self.auxiliary_form,
            is_subordinating_mark=self.is_subordinating_mark,
        )

    def is_infinitive_clause_head(self, word: TreeWord) -> bool:
        """
        Checking whether a word heads an infinitive clause

        Description:
            is_infinitive_clause_head of the module over the hooks is_clause_head,
            auxiliary_form and is_subordinating_mark

        Arguments:
            word (TreeWord): Word of the tree

        Returns:
            bool: Result of the check
        """
        return is_infinitive_clause_head(
            word,
            self.is_clause_head,
            self.auxiliary_form,
            is_subordinating_mark=self.is_subordinating_mark,
        )

    def is_subordinating_mark(self, word: TreeWord) -> bool:
        """
        Checking whether a mark is a subordinating conjunction

        Description:
            The check a dependent mark of a conjunct or a parataxis passes to make
            it a subordinate clause, or an infinitive one with an infinitive (a
            model may attach a clause of because as conj): is_subordinating_mark of
            the module with subordinating_marks of the class by default; a library
            reads the context of a word that is a conjunction and a pronoun

        Arguments:
            word (TreeWord): Word with the relation mark

        Returns:
            bool: Result of the check
        """
        return _is_subordinating_mark(word, self.subordinating_marks)

    def is_prep_complement(self, word: TreeWord) -> bool:
        """
        Checking whether a word is a link of a prepositional chain

        Description:
            is_prep_complement of the module by default. The chains are computed
            on first use, from the words of sents

        Arguments:
            word (TreeWord): Word of the tree

        Returns:
            bool: Result of the check
        """
        return is_prep_complement(word)

    def is_participle_clause(self, word: TreeWord) -> bool:
        """
        Checking whether a word heads a participial clause

        Description:
            A participle (VerbForm=Part) that is not the head of the sentence,
            has no auxiliary or copula (has been built is a predicate) and has a
            dependent besides cc, conj and parataxis (calc_valency)

        Arguments:
            word (TreeWord): Word of the tree

        Returns:
            bool: Result of the check
        """
        if not has_feature(word, "VerbForm", "Part") or is_root(word):
            return False
        if any(base_dep(child) in AUXILIARY_DEPS for child in word.children):
            return False
        return calc_valency(word) > 0

    def is_passive(self, word: TreeWord) -> bool:
        """
        Checking whether a word is a passive verb form

        Description:
            is_passive of the module

        Arguments:
            word (TreeWord): Word of the tree

        Returns:
            bool: Result of the check
        """
        return is_passive(word)

    def is_agentless(self, word: TreeWord) -> bool:
        """
        Checking whether a word is a passive form with no agent

        Description:
            A passive form by the hook is_passive with no agent (has_agent)

        Arguments:
            word (TreeWord): Word of the tree

        Returns:
            bool: Result of the check
        """
        return self.is_passive(word) and not has_agent(word)

    def is_negation(self, word: TreeWord) -> bool:
        """
        Checking whether a word is a word of negation

        Description:
            A word with Polarity=Neg or one of negation_words in lower case; a
            conjunction (neither... nor) is none. Every such word counts

        Arguments:
            word (TreeWord): Word of the tree

        Returns:
            bool: Result of the check
        """
        if word.upos in ("CCONJ", "SCONJ"):
            return False
        return has_feature(word, "Polarity", "Neg") or word.form.lower() in self.negation_words

    def find_split_predicates(self, words: Sequence[TreeWord]) -> list[tuple[TreeWord, TreeWord]]:
        """
        Finding the split predicates

        Description:
            A light verb with a noun that carries its meaning (to make a
            decision); none by default, as they depend on the language

        Arguments:
            words (list[TreeWord]): Words of the text

        Returns:
            list[tuple[TreeWord, TreeWord]]: Pairs of the verb and the noun in the order of the
                words
        """
        return []


def _is_word(word: TreeWord) -> bool:
    """Whether a word of the tree is a word: it holds a letter or a digit (has_words)"""
    return has_words(word.form)


def _before_head(word: TreeWord) -> bool:
    """Whether a word stands before the word it hangs on"""
    return word.head is not None and word.index < word.head.index


def _word_triple(word: TreeWord) -> tuple[str, str, str]:
    """Dependency triple of a word: the part of speech of its head, the nearest word above it
    through punctuation, its base relation and its own part of speech; a word with no word
    above it has an empty head and the relation root"""
    head, seen = word, {word.index}
    # A broken parse can link the marks above a word in a loop
    while head.head is not None and head.head.index not in seen:
        head = head.head
        if _is_word(head):
            return (head.upos or "", base_dep(word), word.upos or "")
        seen.add(head.index)
    return ("", "root", word.upos or "")


def _t_unit_heads(
    heads: Sequence[TreeWord], marked: Collection[int], reattached: Mapping[int, TreeWord]
) -> list[TreeWord]:
    """Clause heads of a sentence that head a T-unit: the head of the sentence and the main
    clauses joined to it through conj or parataxis, but for a conjunct without a subject of its
    own, a predicate of the clause it is coordinated to; a marked clause head is no main clause,
    and a reattached one joins the clause of its word"""
    ids = {word.index for word in heads}
    known: dict[int, bool] = {}
    return [
        word
        for word in heads
        if _is_main_clause(word, ids, known, marked, reattached) and not _shares_subject(word)
    ]


def _is_main_clause(
    word: TreeWord,
    ids: Collection[int],
    known: dict[int, bool],
    marked: Collection[int],
    reattached: Mapping[int, TreeWord],
) -> bool:
    """Whether a clause head reaches the head of the sentence through main clauses alone, none
    of them marked; known keeps the answers for the clause heads on the way"""
    path: list[int] = []
    on_path: set[int] = set()
    while word.index not in known:
        path.append(word.index)
        on_path.add(word.index)
        if word.index in marked:
            outcome = False
            break
        if is_root(word):
            outcome = True
            break
        parent = reattached.get(word.index)
        if parent is None:
            parent = _chain_parent(word)
            if base_dep(word) not in MAIN_CLAUSE_DEPS:
                parent = None
        if parent is None or parent.index not in ids or parent.index in on_path:
            outcome = False
            break
        word = parent
    else:
        outcome = known[word.index]
    for i in path:
        known[i] = outcome
    return outcome


def _shares_subject(word: TreeWord) -> bool:
    """Whether a conjunct is a predicate sharing the subject of the clause it is coordinated
    to: no subject of its own, and no person, number or gender of its own either, which in a
    language that drops its subjects tell another one (llegamos y nos esperabas)"""
    if base_dep(word) != "conj":
        return False
    if any(
        base_dep(child) in _SUBJECT_DEPS or child.deprel == "expl" for child in get_children(word)
    ):
        return False
    head = _chain_parent(word)
    own, other = _agreement(word), _agreement(head) if head is not None else {}
    return all(own[feature] == other[feature] for feature in own.keys() & other.keys())


def _agreement(word: TreeWord) -> dict[str, str]:
    """Person, number and gender of a predicate: those of its first auxiliary or copula that
    has them, which agree with the subject where a participle or a noun has its own (hemos
    llegado, es un equipo), else those of the word"""
    for part in [*(child for child in word.children if base_dep(child) in AUXILIARY_DEPS), word]:
        found = {feature: part.feats.get(feature, "") for feature in _AGREEMENT_FEATURES}
        if any(found.values()):
            return {feature: values for feature, values in found.items() if values}
    return {}


def _t_units_of(words: Iterable[TreeWord], units: Collection[int]) -> set[int | None]:
    """Positions of the heads of the T-units the clauses belong to, the nearest ones above
    them; None for a clause under none"""
    known: dict[int, int | None] = {}
    found = set()
    for word in words:
        path, seen = [], {word.index}
        unit = None
        parent = _chain_parent(word)
        while parent is not None and parent.index not in seen:
            if parent.index in known:
                unit = known[parent.index]
                break
            if parent.index in units:
                unit = parent.index
                break
            path.append(parent.index)
            seen.add(parent.index)
            parent = _chain_parent(parent)
        for i in path:
            known[i] = unit
        found.add(unit)
    return found


def _first_conjuncts(
    words: Iterable[TreeWord], starts: Collection[int] = ()
) -> dict[int, TreeWord | None]:
    """First conjunct of the coordination of every word by its position, the word itself out
    of one or at one of starts; None through a punctuation mark or a loop of conjuncts"""
    known: dict[int, TreeWord | None] = {}
    for start in words:
        path: list[int] = []
        on_path: set[int] = set()
        word = start
        while True:
            if word.index in known:
                first = known[word.index]
                break
            if base_dep(word) != "conj" or word.index in starts:
                first = known[word.index] = word
                break
            path.append(word.index)
            on_path.add(word.index)
            parent = _chain_parent(word)
            if parent is None or parent.index in on_path:
                first = None
                break
            word = parent
        for i in path:
            known[i] = first
    return known


def _heads_of(words: Iterable[TreeWord], relations: Collection[str]) -> set[int]:
    """Positions of the words some of the words hang on by one of the relations"""
    return {
        parent.index
        for word in words
        if base_dep(word) in relations and (parent := _chain_parent(word)) is not None
    }


def _mean_edit_distance(sents: Sequence[Sequence[Hashable]]) -> float:
    """Mean edit distance of the adjacent sentences, without the checks"""
    return safe_mean(
        [
            safe_divide(_edit_distance(first, second), max(len(first), len(second)), 0.0)
            for first, second in pairwise(sents)
        ]
    )


def _edit_distance(first: Sequence[Hashable], second: Sequence[Hashable]) -> int:
    """Levenshtein distance of two sequences by the bit-parallel algorithm of Myers in the
    form of Hyyrö, the longer one as the pattern"""
    if len(first) < len(second):
        first, second = second, first
    size = len(first)
    if not len(second):
        return size
    full = (1 << size) - 1
    last = 1 << (size - 1)
    masks: dict[Hashable, int] = {}
    for i, item in enumerate(first):
        masks[item] = masks.get(item, 0) | (1 << i)
    plus, minus, score = full, 0, size
    for item in second:
        match = masks.get(item, 0) | minus
        diagonal = (((match & plus) + plus) ^ plus) | match
        up = minus | (~(diagonal | plus) & full)
        down = plus & diagonal
        if up & last:
            score += 1
        elif down & last:
            score -= 1
        shifted = ((up << 1) | 1) & full
        minus = shifted & diagonal
        plus = ((down << 1) & full) | (~(shifted | diagonal) & full)
    return score


def _mean_multiset_similarity(counts: Sequence[Counter[Hashable]]) -> float:
    """Mean similarity of the multisets of the adjacent sentences, without the checks"""
    return safe_mean([_multiset_similarity(first, second) for first, second in pairwise(counts)])


def _multiset_similarity(first: Counter[Hashable], second: Counter[Hashable]) -> float:
    """Weighted Jaccard similarity of two multisets, 1 for two empty ones"""
    union = sum((first | second).values())
    return sum((first & second).values()) / union if union else 1.0


def get_words(words: Iterable[TreeWord]) -> list[TreeWord]:
    """
    Getting the words of a sequence of words of the tree

    Description:
        The words with a letter or a digit (has_words): punctuation marks and
        symbols are no nodes of the measures

    Arguments:
        words (list[TreeWord]): Words of the tree, such as those of a sentence

    Returns:
        list[TreeWord]: List of words
    """
    return [word for word in words if _is_word(word)]


def is_root(word: TreeWord) -> bool:
    """
    Checking whether a word is the head of its sentence

    Arguments:
        word (TreeWord): Word of the tree

    Returns:
        bool: Result of the check
    """
    return word.head is None


def base_dep(word: TreeWord) -> str:
    """
    Getting the syntactic relation of a word without its subtype

    Description:
        The subtypes of Universal Dependencies are separated by a colon:
        expl:pass - expl, nsubj:pass - nsubj; a word without a relation gives an
        empty string

    Arguments:
        word (TreeWord): Word of the tree

    Returns:
        str: Base relation
    """
    return _base_relation(word.deprel or "")


@cache
def _base_relation(relation: str) -> str:
    """A relation without its subtype, once for every label"""
    return relation.split(":")[0]


def get_children(word: TreeWord) -> list[TreeWord]:
    """
    Getting the dependent words of a word

    Arguments:
        word (TreeWord): Word of the tree

    Returns:
        list[TreeWord]: List of the dependents without punctuation marks and symbols
    """
    return [child for child in word.children if _is_word(child)]


def count_children(word: TreeWord) -> int:
    """
    Counting the dependent words of a word

    Arguments:
        word (TreeWord): Word of the tree

    Returns:
        int: Number of dependent words (get_children)
    """
    return len(get_children(word))


def subtree_len(word: TreeWord) -> int:
    """
    Computing the length of the subtree of a word in words

    Description:
        The word and all of its direct and indirect dependents, punctuation
        left out

    Arguments:
        word (TreeWord): Word of the tree

    Returns:
        int: Number of words in the subtree
    """
    count = 0
    words = [word]
    # A broken parse can link words in a loop
    seen = {word.index}
    while words:
        current = words.pop()
        count += _is_word(current)
        for child in current.children:
            if child.index not in seen:
                seen.add(child.index)
                words.append(child)
    return count


def calc_dependency_distances(words: Iterable[TreeWord]) -> list[int]:
    """
    Computing the dependency distances

    Description:
        The distance between a word and its head in positions of words,
        punctuation left out (Liu 2008); the head of a sentence and a word whose
        head lies outside the sequence or is a punctuation mark are skipped

    References:
        Liu H. Dependency distance as a metric for language comprehension difficulty.
        Journal of Cognitive Science, 2008, 9(2), 159-191

    Arguments:
        words (list[TreeWord]): Words of the tree, such as those of a sentence

    Returns:
        list[int]: Distances in the order of the words
    """
    words = get_words(words)
    positions = {word.index: position for position, word in enumerate(words)}
    return [
        abs(position - positions[word.head.index])
        for position, word in enumerate(words)
        if word.head is not None and word.head.index in positions
    ]


def calc_tree_depth(words: Iterable[TreeWord]) -> int:
    """
    Computing the depth of the dependency tree

    Description:
        The longest path from the head of the sentence to a leaf in relations,
        through punctuation; the maximum for several sentences, 0 for a sentence
        of one word

    Arguments:
        words (list[TreeWord]): Words of the tree, such as those of a sentence

    Returns:
        int: Depth of the tree
    """
    parents = _word_parents(get_words(words))
    depths: dict[int, int] = {}
    for start in range(len(parents)):
        chain: list[int] = []
        node: int | None = start
        # A broken parse can link words in a loop
        while node is not None and node not in depths and node not in chain:
            chain.append(node)
            node = parents[node]
        depth = depths[node] if node is not None and node in depths else -1
        for member in reversed(chain):
            depth += 1
            depths[member] = depth
    return max(depths.values(), default=0)


def _word_parents(words: Sequence[TreeWord]) -> list[int | None]:
    """
    Position in the sequence of the word every word hangs on, through punctuation and words
    outside the sequence; None for a word with no such head
    """
    position_of = {word.index: n for n, word in enumerate(words)}
    parents: list[int | None] = []
    for n, word in enumerate(words):
        parent = None
        head = word.head
        seen = set()
        while head is not None and head.index not in seen:
            seen.add(head.index)
            if position_of.get(head.index, n) != n:
                parent = position_of[head.index]
                break
            head = head.head
        parents.append(parent)
    return parents


@_takes_word
def predicate_form(word: TreeWord, auxiliary_form: Callable[[TreeWord], str] | None = None) -> str:
    """
    Getting the verb form of a predicate

    Description:
        The form the auxiliaries and copulas of a word give (AUXILIARY_DEPS),
        as Universal Dependencies annotates them: Fin when one of them is
        finite or the first one is a past participle (had been chosen),
        otherwise the form of the first one (to have gone is an infinitive),
        and without them the form of the word itself. An auxiliary without
        VerbForm is read by the language hook auxiliary_form, which gives its
        form or an empty string to skip it; without the hook it is skipped

    Arguments:
        word (TreeWord): Word of the tree
        auxiliary_form (callable): Verb form of an auxiliary without the feature
            VerbForm

    Returns:
        str: Value of VerbForm (Fin, Inf, Ger, Part and the others of the model),
            an empty string for a word with no verb form

    Raises:
        SourceTypeError: If the word is not a TreeWord or auxiliary_form is not callable

    Example:
        >>> import spacy
        >>> from spacy.tokens import Doc
        >>> from anyts.document import get_tree, to_document
        >>> from anyts.syntax_stats import predicate_form
        >>> doc = Doc(
        ...     spacy.blank("en").vocab,
        ...     words=["She", "had", "arrived"],
        ...     heads=[2, 2, 2],
        ...     deps=["nsubj", "aux", "ROOT"],
        ...     morphs=["Case=Nom", "VerbForm=Fin", "VerbForm=Part"],
        ... )
        >>> she, _, arrived = get_tree(to_document(doc)).words
        >>> predicate_form(arrived), predicate_form(she)
        ('Fin', '')
    """
    if auxiliary_form is not None:
        check_callable(auxiliary_form, "verb form of an auxiliary")
    auxiliaries = [
        (child, form)
        for child in word.children
        if base_dep(child) in AUXILIARY_DEPS
        and (form := _verb_form(child) or (auxiliary_form(child) if auxiliary_form else ""))
    ]
    if not auxiliaries:
        return _verb_form(word)
    if any(form == "Fin" for _, form in auxiliaries):
        return "Fin"
    auxiliary, form = auxiliaries[0]
    if form == "Part" and not has_feature(auxiliary, "Tense", "Pres"):
        return "Fin"
    return form


def _verb_form(word: TreeWord) -> str:
    """Verb form of a word, the first of several, an empty string without one"""
    return word.feats.get("VerbForm", "").split(",")[0]


def calc_valency(word: TreeWord) -> int:
    """
    Computing the valency of a word

    Description:
        The number of dependent words without cc, conj and parataxis

    Arguments:
        word (TreeWord): Word of the tree

    Returns:
        int: Number of dependent words
    """
    return sum(1 for child in get_children(word) if child.deprel not in VALENCY_IGNORED_DEPS)


def calc_coordination_chains(words: Iterable[TreeWord]) -> list[int]:
    """
    Computing the lengths of the coordination chains

    Description:
        A chain is a group of words linked by conj, whichever word each
        conjunct hangs on (the first one in Universal Dependencies, the
        previous one in ClearNLP); a nested coordination (A and B, or C) and an
        enumeration split between several heads are one chain. Its length is
        the number of its words

    Arguments:
        words (list[TreeWord]): Words of the tree, such as those of a sentence

    Returns:
        list[int]: Lengths of the chains in the order of their first words
    """
    words = get_words(words)
    ids = {word.index for word in words}
    links = [
        (word.index, word.head.index)
        for word in words
        if word.deprel == "conj" and word.head is not None and word.head.index in ids
    ]
    return _chain_sizes([word.index for word in words], links)


def _chain_sizes(nodes: Iterable[int], links: Iterable[tuple[int, int]]) -> list[int]:
    """Sizes of the groups of nodes the links join, of two or more, in the order of the nodes"""
    nodes = list(nodes)
    parent = {node: node for node in nodes}

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for a, b in links:
        parent[find(a)] = find(b)
    sizes = Counter(find(node) for node in nodes)
    chains: dict[int, int] = {}
    for node in nodes:
        root = find(node)
        if sizes[root] > 1:
            chains.setdefault(root, sizes[root])
    return list(chains.values())


@_takes_word
def is_predicate(word: TreeWord) -> bool:
    """
    Checking whether a word can be the predicate of its clause

    Description:
        A verb (VERB, AUX), a word with a subject of its own (nsubj, csubj and
        their subtypes) or with a copula (cop): the nominal predicate of he is
        tall and of a language that drops the subject (y estaba cansado) passes,
        a parenthetical word does not

    Arguments:
        word (TreeWord): Word of the tree

    Returns:
        bool: Result of the check

    Raises:
        SourceTypeError: If the word is not a TreeWord
    """
    return word.upos in ("VERB", "AUX") or any(
        base_dep(child) in SUBJECT_DEPS or base_dep(child) == "cop" for child in get_children(word)
    )


@_takes_word
def is_clause_head(
    word: TreeWord,
    is_infinitive_periphrasis: Callable[[TreeWord], bool] | None = None,
    auxiliary_form: Callable[[TreeWord], str] | None = None,
) -> bool:
    """
    Checking whether a word heads a clause

    Description:
        The head of the sentence, or a word with a relation of CLAUSE_DEPS
        (ccomp, advcl, acl, csubj, parataxis and their subtypes) whose
        predicate (predicate_form) is not a participle, a converb or a gerund
        (counted apart), nor an infinitive under acl (the wish to leave); under
        xcomp, a finite predicate or an infinitive clause (is_infinitive_clause:
        wants to leave). A parataxis and a conjunct of a clause head count only
        as predicates (is_predicate), so a parenthetical word is no clause, nor
        is an infinitive conjunct or an infinitive subject (csubj) by the check
        is_infinitive_periphrasis, since a model may attach the infinitive of a
        periphrasis to its verb as conj and to a modal word as csubj; a loop of
        conjuncts is none

    Arguments:
        word (TreeWord): Word of the tree
        is_infinitive_periphrasis (callable): Whether an infinitive makes one
            predicate with its head (is_infinitive_clause); none by default
        auxiliary_form (callable): Verb form of an auxiliary without the feature
            VerbForm (predicate_form); none by default

    Returns:
        bool: Result of the check

    Raises:
        SourceTypeError: If the word is not a TreeWord, or is_infinitive_periphrasis
            or auxiliary_form is not callable
    """
    if is_infinitive_periphrasis is not None:
        check_callable(is_infinitive_periphrasis, "check of an infinitive periphrasis")
    if auxiliary_form is not None:
        check_callable(auxiliary_form, "verb form of an auxiliary")
    return _is_clause_head(word, is_infinitive_periphrasis, auxiliary_form)


def _is_clause_head(
    word: TreeWord,
    is_infinitive_periphrasis: Callable[[TreeWord], bool] | None,
    auxiliary_form: Callable[[TreeWord], str] | None,
) -> bool:
    """is_clause_head with checked hooks"""
    seen = set()
    # Up the chains of conjuncts and infinitive complements to the word that is none
    while _is_word(word) and word.index not in seen:
        head = word.head
        if head is None:
            return True
        form = predicate_form(word, auxiliary_form)
        if form in NONFINITE_CLAUSE_FORMS:
            return False
        dep = base_dep(word)
        if dep != "conj":
            if dep == "xcomp":
                if form == "Fin":
                    return True
                completed = (
                    _completed_word(word, is_infinitive_periphrasis, auxiliary_form)
                    if _is_infinitive_complement(word, is_infinitive_periphrasis, auxiliary_form)
                    else None
                )
                if completed is None:
                    return False
                seen.add(word.index)
                word = completed
                continue
            if dep not in CLAUSE_DEPS:
                return False
            if dep == "parataxis":
                return is_predicate(word)
            if dep == "csubj" and form == "Inf" and is_infinitive_periphrasis:
                return not is_infinitive_periphrasis(word)
            return not (dep == "acl" and form == "Inf")
        if form == "Inf" and is_infinitive_periphrasis and is_infinitive_periphrasis(word):
            return False
        if not is_predicate(word):
            return False
        seen.add(word.index)
        word = head
    return False


@_takes_word
def is_infinitive_clause(
    word: TreeWord,
    is_infinitive_periphrasis: Callable[[TreeWord], bool] | None = None,
    is_clause_head: Callable[[TreeWord], bool] | None = None,
    auxiliary_form: Callable[[TreeWord], str] | None = None,
) -> bool:
    """
    Checking whether an infinitive complement heads a clause of its own

    Description:
        A predicate in the form of an infinitive (predicate_form) under xcomp
        (wants to leave, asked him to leave, wants to be chosen), unless it
        makes one predicate with its head by the language check
        is_infinitive_periphrasis (can leave, begins to leave) or the word it
        completes, the first one up its chain of non-finite complements under
        xcomp (kept trying to leave), heads no clause by the check
        is_clause_head: an infinitive in a participial phrase or under an
        infinitive under acl (trying to leave, the wish to try to leave)
        belongs to that phrase

    Arguments:
        word (TreeWord): Word of the tree
        is_infinitive_periphrasis (callable): Whether an infinitive makes one
            predicate with its head; none by default
        is_clause_head (callable): Whether a word heads a clause; by default
            is_clause_head of the module with the hooks of this check
        auxiliary_form (callable): Verb form of an auxiliary without the feature
            VerbForm (predicate_form); none by default

    Returns:
        bool: Result of the check

    Raises:
        SourceTypeError: If the word is not a TreeWord, or is_infinitive_periphrasis,
            is_clause_head or auxiliary_form is not callable
    """
    if is_infinitive_periphrasis is not None:
        check_callable(is_infinitive_periphrasis, "check of an infinitive periphrasis")
    if auxiliary_form is not None:
        check_callable(auxiliary_form, "verb form of an auxiliary")
    if is_clause_head is None:
        is_clause_head = _clause_head_check(is_infinitive_periphrasis, auxiliary_form)
    check_callable(is_clause_head, "check of a clause head")
    return _is_infinitive_clause(word, is_infinitive_periphrasis, is_clause_head, auxiliary_form)


def _clause_head_check(
    is_infinitive_periphrasis: Callable[[TreeWord], bool] | None,
    auxiliary_form: Callable[[TreeWord], str] | None,
) -> Callable[[TreeWord], bool]:
    """is_clause_head of the module with checked hooks"""
    return partial(
        _is_clause_head,
        is_infinitive_periphrasis=is_infinitive_periphrasis,
        auxiliary_form=auxiliary_form,
    )


def _is_infinitive_clause(
    word: TreeWord,
    is_infinitive_periphrasis: Callable[[TreeWord], bool] | None,
    is_clause_head: Callable[[TreeWord], bool],
    auxiliary_form: Callable[[TreeWord], str] | None,
) -> bool:
    """is_infinitive_clause with checked hooks"""
    if not _is_infinitive_complement(word, is_infinitive_periphrasis, auxiliary_form):
        return False
    completed = _completed_word(word, is_infinitive_periphrasis, auxiliary_form)
    return completed is not None and is_clause_head(completed)


def _is_infinitive_complement(
    word: TreeWord,
    is_infinitive_periphrasis: Callable[[TreeWord], bool] | None,
    auxiliary_form: Callable[[TreeWord], str] | None,
) -> bool:
    """Infinitive under xcomp that makes no periphrasis with its head"""
    if base_dep(word) != "xcomp" or predicate_form(word, auxiliary_form) != "Inf":
        return False
    return not (is_infinitive_periphrasis is not None and is_infinitive_periphrasis(word))


def _completed_word(
    word: TreeWord,
    is_infinitive_periphrasis: Callable[[TreeWord], bool] | None,
    auxiliary_form: Callable[[TreeWord], str] | None,
) -> TreeWord | None:
    """
    Word an infinitive complement completes, up its non-finite complements and the
    infinitives of a periphrasis a model attaches as conj or csubj, an infinitive conjunct
    of a periphrasis among them (is ready to come and help us live); None in a loop or for
    a complement with no head
    """
    seen = {word.index}
    completed = word.head
    while (
        completed is not None
        and completed.head is not None
        and completed.index not in seen
        and (
            (base_dep(completed) == "xcomp" and predicate_form(completed, auxiliary_form) != "Fin")
            or (
                is_infinitive_periphrasis is not None
                and base_dep(completed) in ("conj", "csubj")
                and _in_periphrasis(completed, is_infinitive_periphrasis, auxiliary_form)
            )
        )
    ):
        seen.add(completed.index)
        completed = completed.head
    if completed is None:
        return None
    # A loop through the words above would bring the checks back to the infinitive
    above = completed
    while above.head is not None and above.index not in seen:
        seen.add(above.index)
        above = above.head
    return None if above.index == word.index else completed


def _in_periphrasis(
    word: TreeWord,
    is_infinitive_periphrasis: Callable[[TreeWord], bool],
    auxiliary_form: Callable[[TreeWord], str] | None,
) -> bool:
    """Whether an infinitive makes one predicate with its head (is_infinitive_periphrasis),
    itself or through the infinitive conjuncts above it, as is_clause_head asks"""
    seen = set()
    current: TreeWord | None = word
    while (
        current is not None
        and current.index not in seen
        and predicate_form(current, auxiliary_form) == "Inf"
    ):
        dep = base_dep(current)
        if dep in ("xcomp", "csubj", "conj") and is_infinitive_periphrasis(current):
            return True
        if dep != "conj":
            return False
        seen.add(current.index)
        current = current.head
    return False


@_takes_word
def is_subordinate_clause_head(
    word: TreeWord,
    is_clause_head: Callable[[TreeWord], bool] | None = None,
    auxiliary_form: Callable[[TreeWord], str] | None = None,
    subordinating_marks: Collection[str] = (),
    is_subordinating_mark: Callable[[TreeWord], bool] | None = None,
) -> bool:
    """
    Checking whether a word heads a subordinate clause

    Description:
        The head of a clause by is_clause_head with a relation of
        SUBORDINATE_CLAUSE_DEPS (ccomp, advcl, acl, csubj and their subtypes) or
        xcomp (a complement a model attaches as xcomp), or a conjunct of one: the
        relation of the first word up its chain of conjuncts decides, and neither
        the predicate of that word nor its own (predicate_form) is an infinitive;
        a finite conjunct with a subject of its own of an infinitive takes the kind
        of the clause of the first word above the infinitives that is none. An
        infinitive heads an infinitive clause (is_infinitive_clause_head). A
        conjunct or a parataxis with a subordinating mark (is_subordinating_mark)
        is a subordinate clause, since a model may attach a clause of because as
        conj, and so are its conjuncts with a subject of its own; those sharing the
        subject are not, as a model attaches the predicates of the main clause to it
        as well

    Arguments:
        word (TreeWord): Word of the tree
        is_clause_head (callable): Whether a word heads a clause; by default
            is_clause_head of the module with the hooks of this check
        auxiliary_form (callable): Verb form of an auxiliary without the feature
            VerbForm (predicate_form); none by default
        subordinating_marks (list[str]): Subordinating conjunctions in lower case, with
            the words of their fixed expression after a space; none by default
        is_subordinating_mark (callable): Whether a mark is a subordinating
            conjunction; is_subordinating_mark of the module with subordinating_marks
            if not given

    Returns:
        bool: Result of the check

    Raises:
        SourceTypeError: If the word is not a TreeWord, is_clause_head, auxiliary_form
            or is_subordinating_mark is not callable, or subordinating_marks is not a
            collection of strings
    """
    is_clause_head, is_marked = _clause_kind_hooks(
        is_clause_head, auxiliary_form, subordinating_marks, is_subordinating_mark
    )
    if is_root(word) or not is_clause_head(word):
        return False
    first, dep = _clause_relation(word, is_marked, auxiliary_form)
    if predicate_form(word, auxiliary_form) == "Inf":
        return False
    if predicate_form(first, auxiliary_form) == "Inf":
        # A finite conjunct with a subject of its own, which a model attaches to an infinitive,
        # takes the kind of the clause the chain of infinitives completes
        owner = None if _shares_subject(word) else _infinitive_owner(first, auxiliary_form)
        if owner is None:
            return False
        first, dep = _clause_relation(owner, is_marked, auxiliary_form)
        if predicate_form(first, auxiliary_form) == "Inf":
            return False
    return dep == "xcomp" or (not is_root(first) and dep in SUBORDINATE_CLAUSE_DEPS)


@_takes_word
def is_infinitive_clause_head(
    word: TreeWord,
    is_clause_head: Callable[[TreeWord], bool] | None = None,
    auxiliary_form: Callable[[TreeWord], str] | None = None,
    subordinating_marks: Collection[str] = (),
    is_subordinating_mark: Callable[[TreeWord], bool] | None = None,
) -> bool:
    """
    Checking whether a word heads an infinitive clause

    Description:
        The head of a clause by is_clause_head whose own predicate is an
        infinitive, under xcomp or a relation of SUBORDINATE_CLAUSE_DEPS (wants to
        leave, asked him to leave, came to help, it is hard to say) or a conjunct of
        one: the relation of the first word up its chain of conjuncts decides, as in
        is_subordinate_clause_head; an infinitive under conj or parataxis with a
        subordinating mark, or an infinitive conjunct of it, heads one too (came , in
        order to help). Such a clause is counted apart from the subordinate ones, as
        grammars of many languages take it for a part of a simple sentence

    Arguments:
        word (TreeWord): Word of the tree
        is_clause_head (callable): Whether a word heads a clause; by default
            is_clause_head of the module with the hooks of this check
        auxiliary_form (callable): Verb form of an auxiliary without the feature
            VerbForm (predicate_form); none by default
        subordinating_marks (list[str]): Subordinating conjunctions in lower case, with
            the words of their fixed expression after a space; none by default
        is_subordinating_mark (callable): Whether a mark is a subordinating
            conjunction; is_subordinating_mark of the module with subordinating_marks
            if not given

    Returns:
        bool: Result of the check

    Raises:
        SourceTypeError: If the word is not a TreeWord, is_clause_head, auxiliary_form
            or is_subordinating_mark is not callable, or subordinating_marks is not a
            collection of strings
    """
    is_clause_head, is_marked = _clause_kind_hooks(
        is_clause_head, auxiliary_form, subordinating_marks, is_subordinating_mark
    )
    if is_root(word) or not is_clause_head(word):
        return False
    _, dep = _clause_relation(word, is_marked, auxiliary_form)
    return predicate_form(word, auxiliary_form) == "Inf" and (
        dep == "xcomp" or dep in SUBORDINATE_CLAUSE_DEPS
    )


def _infinitive_owner(
    word: TreeWord, auxiliary_form: Callable[[TreeWord], str] | None
) -> TreeWord | None:
    """Word a chain of infinitives completes: the first word above an infinitive that is no
    infinitive, or the head of the sentence; None in a loop"""
    seen = {word.index}
    while predicate_form(word, auxiliary_form) == "Inf" and word.head is not None:
        word = word.head
        if word.index in seen:
            return None
        seen.add(word.index)
    return word


def _clause_kind_hooks(
    is_clause_head: Callable[[TreeWord], bool] | None,
    auxiliary_form: Callable[[TreeWord], str] | None,
    subordinating_marks: Collection[str],
    is_subordinating_mark: Callable[[TreeWord], bool] | None,
) -> tuple[Callable[[TreeWord], bool], Callable[[TreeWord], bool]]:
    """Checked hooks of the checks of the kind of a clause: the check of a clause head, the
    one of the module by default, and the check of a subordinating mark"""
    if auxiliary_form is not None:
        check_callable(auxiliary_form, "verb form of an auxiliary")
    check_words(subordinating_marks, "subordinating_marks", ordered=False)
    if is_subordinating_mark is None:
        is_subordinating_mark = partial(_is_subordinating_mark, marks=subordinating_marks)
    check_callable(is_subordinating_mark, "check of a subordinating mark")
    if is_clause_head is None:
        is_clause_head = _clause_head_check(None, auxiliary_form)
    check_callable(is_clause_head, "check of a clause head")
    return is_clause_head, is_subordinating_mark


def _clause_relation(
    word: TreeWord,
    is_subordinating_mark: Callable[[TreeWord], bool],
    auxiliary_form: Callable[[TreeWord], str] | None,
) -> tuple[TreeWord, str]:
    """First word up the chain of conjuncts of a clause head and its relation, advcl for a
    conjunct or a parataxis with a subordinating mark, of its own or of a clause it is
    coordinated to when it is an infinitive or has a subject of its own: a conjunct sharing the
    subject may be a predicate of the main clause"""
    if base_dep(word) in MAIN_CLAUSE_DEPS and _has_mark(word, is_subordinating_mark):
        return word, "advcl"
    inherits = predicate_form(word, auxiliary_form) == "Inf" or not _shares_subject(word)
    seen = set()
    while base_dep(word) == "conj" and word.head is not None and word.index not in seen:
        seen.add(word.index)
        word = word.head
        if (
            inherits
            and base_dep(word) in MAIN_CLAUSE_DEPS
            and _has_mark(word, is_subordinating_mark)
        ):
            return word, "advcl"
    return word, base_dep(word)


def _has_mark(word: TreeWord, is_subordinating_mark: Callable[[TreeWord], bool]) -> bool:
    """Whether a word has a dependent mark that is a subordinating conjunction"""
    return any(
        base_dep(child) == "mark" and is_subordinating_mark(child) for child in word.children
    )


@_takes_word
def is_subordinating_mark(word: TreeWord, subordinating_marks: Collection[str] = ()) -> bool:
    """
    Checking whether a mark is a subordinating conjunction

    Description:
        A word with the relation mark whose form in lower case, with the words of
        its fixed expression after a space (so that), is one of subordinating_marks

    Arguments:
        word (TreeWord): Word of the tree
        subordinating_marks (list[str]): Subordinating conjunctions in lower case, with
            the words of their fixed expression after a space; none by default

    Returns:
        bool: Result of the check

    Raises:
        SourceTypeError: If the word is not a TreeWord or subordinating_marks is not a
            collection of strings

    Example:
        >>> import spacy
        >>> from spacy.tokens import Doc
        >>> from anyts.document import get_tree, to_document
        >>> from anyts.syntax_stats import is_subordinating_mark
        >>> doc = Doc(
        ...     spacy.blank("en").vocab,
        ...     words=["left", "so", "that", "we", "slept"],
        ...     heads=[0, 4, 1, 4, 0],
        ...     deps=["ROOT", "mark", "fixed", "nsubj", "parataxis"],
        ... )
        >>> so = get_tree(to_document(doc)).words[1]
        >>> is_subordinating_mark(so, {"so that"}), is_subordinating_mark(so, {"so"})
        (True, False)
    """
    check_words(subordinating_marks, "subordinating_marks", ordered=False)
    return _is_subordinating_mark(word, subordinating_marks)


def _is_subordinating_mark(word: TreeWord, marks: Collection[str]) -> bool:
    """is_subordinating_mark with checked marks"""
    if not marks or base_dep(word) != "mark":
        return False
    fixed = (child for child in word.children if base_dep(child) == "fixed")
    return " ".join(part.form.lower() for part in (word, *fixed)) in marks


@_takes_word
def is_passive(word: TreeWord) -> bool:
    """
    Checking whether a word is a passive verb form

    Description:
        A verb with Voice=Pass or with a dependent of PASSIVE_DEPS: nsubj:pass,
        csubj:pass, aux:pass of Universal Dependencies and nsubjpass,
        csubjpass, auxpass of ClearNLP

    Arguments:
        word (TreeWord): Word of the tree

    Returns:
        bool: Result of the check

    Raises:
        SourceTypeError: If the word is not a TreeWord
    """
    if word.upos != "VERB":
        return False
    return has_feature(word, "Voice", "Pass") or any(
        child.deprel in PASSIVE_DEPS for child in get_children(word)
    )


@_takes_word
def has_agent(word: TreeWord) -> bool:
    """
    Checking whether a word has an agent

    Description:
        A dependent of AGENT_DEPS: obl:agent of Universal Dependencies and
        agent of ClearNLP

    Arguments:
        word (TreeWord): Word of the tree

    Returns:
        bool: Result of the check

    Raises:
        SourceTypeError: If the word is not a TreeWord
    """
    return any(child.deprel in AGENT_DEPS for child in get_children(word))


@_takes_word
def is_agentless(word: TreeWord) -> bool:
    """
    Checking whether a word is a passive form with no agent

    Description:
        A passive form (is_passive) with no agent (has_agent)

    Arguments:
        word (TreeWord): Word of the tree

    Returns:
        bool: Result of the check

    Raises:
        SourceTypeError: If the word is not a TreeWord
    """
    return is_passive(word) and not has_agent(word)


def count_noun_modifiers(word: TreeWord) -> int:
    """
    Counting the modifiers of a noun phrase

    Description:
        The dependents with the relations amod, det, nmod, nummod and acl and
        their subtypes (NOUN_MODIFIER_DEPS); conj and appos are no modifiers

    Arguments:
        word (TreeWord): Word of the tree

    Returns:
        int: Number of modifiers
    """
    return sum(1 for child in get_children(word) if base_dep(child) in NOUN_MODIFIER_DEPS)


@_takes_word
def is_prep_complement(word: TreeWord) -> bool:
    """
    Checking whether a word is a complement with a preposition

    Description:
        A word with the relation nmod or obl or a subtype of them
        (PREP_COMPLEMENT_DEPS), or a predicate with a copula or a subject of its
        own out of a relative clause (acl), that has a dependent of the relation
        case that is an adposition or a word with a fixed adposition (in front
        of): the house of the father, went to the house, was in the house, and a
        nominal predicate of a language that drops the copula of the present
        tense. A noun in a case without a preposition is none. The links of a
        prepositional chain (calc_modifier_chains)

    Arguments:
        word (TreeWord): Word of the tree

    Returns:
        bool: Result of the check

    Raises:
        SourceTypeError: If the word is not a TreeWord

    Example:
        >>> import spacy
        >>> from spacy.tokens import Doc
        >>> from anyts.document import get_tree, to_document
        >>> from anyts.syntax_stats import is_prep_complement
        >>> doc = Doc(
        ...     spacy.blank("en").vocab,
        ...     words=["the", "house", "of", "the", "father"],
        ...     heads=[1, 1, 4, 4, 1],
        ...     deps=["det", "ROOT", "case", "det", "nmod"],
        ...     pos=["DET", "NOUN", "ADP", "DET", "NOUN"],
        ... )
        >>> words = get_tree(to_document(doc)).words
        >>> is_prep_complement(words[4]), is_prep_complement(words[1])
        (True, False)
    """
    relation = base_dep(word)
    if relation == "acl":
        return False
    children = word.children
    if relation not in PREP_COMPLEMENT_DEPS and not any(
        base_dep(child) == "cop" or base_dep(child) in _SUBJECT_DEPS for child in children
    ):
        return False
    return any(base_dep(child) == "case" and _is_adposition(child) for child in children)


def _is_adposition(word: TreeWord) -> bool:
    """Whether a word is an adposition or begins one of several words (fixed)"""
    return word.upos == "ADP" or any(
        base_dep(child) == "fixed" and child.upos == "ADP" for child in word.children
    )


def dependency_triples(words: Sequence[TreeWord]) -> list[tuple[str, str, str]]:
    """
    Getting the dependency triples of the words of a sentence

    Description:
        For every word (get_words) the part of speech of its head, the nearest
        word above it through punctuation, its relation without a subtype
        (base_dep) and its own part of speech: (NOUN, amod, ADJ) for a red house;
        the head of the sentence, and a word with no word above it, give an empty
        head and the relation root, whatever its label

    Arguments:
        words (list[TreeWord]): Words of the tree, such as those of a sentence

    Returns:
        list[tuple[str, str, str]]: Triples in the order of the words

    Raises:
        SourceTypeError: If the words are not a list of TreeWord objects

    Example:
        >>> import spacy
        >>> from spacy.tokens import Doc
        >>> from anyts.document import get_tree, to_document
        >>> from anyts.syntax_stats import dependency_triples
        >>> doc = Doc(
        ...     spacy.blank("en").vocab,
        ...     words=["a", "red", "house"],
        ...     heads=[2, 2, 2],
        ...     deps=["det", "amod", "ROOT"],
        ...     pos=["DET", "ADJ", "NOUN"],
        ... )
        >>> dependency_triples(get_tree(to_document(doc)).sentences[0])
        [('NOUN', 'det', 'DET'), ('NOUN', 'amod', 'ADJ'), ('', 'root', 'NOUN')]
    """
    if not (isinstance(words, Sequence) and all(isinstance(word, TreeWord) for word in words)):
        raise SourceTypeError("The words must be a list of TreeWord objects")
    return [_word_triple(word) for word in get_words(words)]


def calc_edit_distance(sents: Sequence[Sequence[Hashable]]) -> float:
    """
    Computing the mean edit distance of adjacent sentences

    Description:
        The Levenshtein distance of the items of every two adjacent sentences -
        the fewest insertions, deletions and substitutions that turn one into the
        other - over the number of the items of the longer one, averaged over
        the pairs: 0 for the same sequences, 1 for ones with no item in common.
        For the parts of speech it is the SYNMEDpos of Coh-Metrix

    Arguments:
        sents (list[list]): Items of every sentence, such as its parts of speech

    Returns:
        float: Mean distance, nan for fewer than two sentences

    Raises:
        SourceTypeError: If the sentences are not a list of lists (check_sequence) or
            an item cannot be hashed

    Example:
        >>> from anyts.syntax_stats import calc_edit_distance
        >>> calc_edit_distance([["DET", "NOUN", "VERB"], ["DET", "ADJ", "NOUN", "VERB"]])
        0.25
    """
    check_sequence(sents, "sentences")
    for sent in sents:
        check_sequence(sent, "items of a sentence")
    _check_hashable(sents)
    return _mean_edit_distance(sents)


def _check_hashable(sents: Iterable[Iterable[object]]) -> None:
    """Checking that the items of the sentences can be compared as keys"""
    for sent in sents:
        for item in sent:
            try:
                hash(item)
            except TypeError:
                raise SourceTypeError(
                    f"The items of a sentence must be hashable, not {type(item).__name__}"
                ) from None


def calc_multiset_similarity(sents: Sequence[Iterable[Hashable]]) -> float:
    """
    Computing the mean similarity of the multisets of the items of adjacent sentences

    Description:
        The weighted Jaccard similarity of the items of every two adjacent
        sentences - the items they share, each as many times as the sentence
        with fewer of them has it, over the items of both, each as many times as
        the sentence with more of them has it - averaged over the pairs: 1 for
        the same multisets, 0 for disjoint ones, 1 for two empty ones. For the
        dependency triples (dependency_triples) it is the syntactic similarity of
        adjacent sentences in the manner of the SYNSTRUT of Coh-Metrix. A mapping
        is read by its keys, as a set

    Arguments:
        sents (list[list]): Items of every sentence, such as its dependency triples

    Returns:
        float: Mean similarity, nan for fewer than two sentences

    Raises:
        SourceTypeError: If the sentences are not a list of collections (check_sequence)
            or an item cannot be hashed

    Example:
        >>> from anyts.syntax_stats import calc_multiset_similarity
        >>> calc_multiset_similarity([["a", "a", "b"], ["a", "b", "b"]])
        0.5
    """
    check_sequence(sents, "sentences")
    for sent in sents:
        check_sequence(sent, "items of a sentence", ordered=False)
    _check_hashable(sents)
    return _mean_multiset_similarity([Counter(iter(sent)) for sent in sents])


def calc_modifier_chains(
    words: Iterable[TreeWord], is_modifier: Callable[[TreeWord], bool]
) -> list[int]:
    """
    Computing the lengths of the chains of nested modifiers

    Description:
        Two or more nested modifiers of is_modifier, such as the complements of
        the increase of the efficiency of the use of resources (length 3); a
        chain starts at a modifier whose head is none, and its length is the
        number of modifiers in its longest branch. The links are those of
        get_children: punctuation is no link

    Arguments:
        words (list[TreeWord]): Words of the tree, such as those of a sentence
        is_modifier (Callable[[TreeWord], bool]): Whether a word is a modifier of the chain

    Returns:
        list[int]: Lengths of the chains in the order of the words

    Raises:
        SourceTypeError: If is_modifier is not callable
    """
    if not callable(is_modifier):
        raise SourceTypeError(
            f"The check of a modifier must be callable, not {type(is_modifier).__name__}"
        )
    chains = []
    for word in get_words(words):
        if not is_modifier(word):
            continue
        parent = _chain_parent(word)
        if not (parent is not None and is_modifier(parent)):
            length = _chain_len(word, is_modifier)
            if length >= 2:
                chains.append(length)
    return chains


def _chain_parent(word: TreeWord) -> TreeWord | None:
    """Word a word hangs on as get_children gives it, None through punctuation or at the root"""
    head = word.head
    return head if head is not None and _is_word(head) else None


def _chain_len(word: TreeWord, is_modifier: Callable[[TreeWord], bool]) -> int:
    """Number of the modifiers in the longest branch of a chain from a word, without recursion
    for a chain of any depth"""
    longest = 0
    stack = [(word, 1)]
    seen = {word.index}
    while stack:
        current, depth = stack.pop()
        longest = max(longest, depth)
        for child in get_children(current):
            if child.index not in seen and is_modifier(child):
                seen.add(child.index)
                stack.append((child, depth + 1))
    return longest
