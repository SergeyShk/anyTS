from __future__ import annotations

import zlib
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
from .exceptions import SourceError, SourceTypeError
from .stats import Stats
from .utils import (
    check_callable,
    check_sequence,
    check_words,
    has_feature,
    has_sents,
    is_doc,
    is_finite_verb,
    is_infinitive,
    is_span,
    is_token,
    is_word,
    joins_previous,
    safe_divide,
    safe_mean,
    source_type_error,
)

if TYPE_CHECKING:
    from spacy.tokens import Doc, Token
    from spacy.vocab import Vocab

_Function = TypeVar("_Function", bound=Callable[..., Any])

# Relations of the subject of a clause: a subtype counts as its base one, and ClearNLP marks
# the passive in the label
_SUBJECT_DEPS = SUBJECT_DEPS | {"csubjpass", "nsubjpass"}
# Features of a verb that agree with its subject
_AGREEMENT_FEATURES = ("Person", "Number", "Gender")


def _takes_token(function: _Function) -> _Function:
    """A function of a token: a value that is no Token raises SourceTypeError, not AttributeError"""

    @wraps(function)
    def checked(token: object, *args: Any, **kwargs: Any) -> Any:
        try:
            return function(token, *args, **kwargs)
        except AttributeError:
            if is_token(token):
                raise
            raise SourceTypeError(f"A Token is expected, not {type(token).__name__}") from None

    return cast(_Function, checked)


class SyntaxStats(Stats):
    """
    Base of the syntactic statistics of a text

    Description:
        Measures of the dependency tree and of the syntactic constructions
        (Ivanov, Solnyshkina and Solovyev 2018). Punctuation, symbols and
        whitespace are no nodes of the tree, and the distances are counted in
        positions of words. The measures of a sentence (the longest dependency,
        the depth, the nodes per leaf) are averaged over the sentences, the
        constructions are given per sentence.
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
        source (Doc): Data source (a Doc object with a dependency parse and parts of
            speech, or what parse makes one of)

    Attributes:
        sents (tuple[tuple[Token]]): Words of every sentence with words
        n_sents (int): Number of sentences with words
        n_words (int): Number of words
        n_leaves (int): Number of leaves - words with no dependent word
        n_subtrees (int): Number of subtrees - words with dependent words
        n_coordination_chains (int): Number of coordination chains
        n_clauses (int): Number of clauses
        n_subordinate_clauses (int): Number of subordinate clauses
        n_complex_sents (int): Number of sentences with a subordinate clause
        n_infinitive_clauses (int): Number of infinitive clauses under a verb
        n_t_units, n_complex_t_units (int): Numbers of the T-units and of those with a
            subordinate clause
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
        infinitive_clauses_per_sent (float): Infinitive clauses under a verb per sentence
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
        parse: Doc of a source
        is_clause_head: Whether a word heads a clause
        is_infinitive_periphrasis: Whether an infinitive makes one predicate with its head
        auxiliary_form: Verb form of an auxiliary without the feature VerbForm
        is_subordinate_clause_head: Whether a clause head heads a subordinate clause
        is_infinitive_clause_head: Whether a clause head heads an infinitive clause
        is_prep_complement: Whether a word is a link of a prepositional chain
        is_participle_clause: Whether a word heads a participial clause
        is_passive: Whether a word is a passive verb form
        is_agentless: Whether a passive form has no agent
        is_negation: Whether a word is a word of negation
        find_split_predicates: Split predicates of the words

    Class attributes:
        join_hyphens (bool): Take a word the tokenizer split at its hyphens for one
            word (joins_previous)
        requires_lemmas (bool): Whether the source must carry lemmas
        negation_words (frozenset[str]): Words of negation besides Polarity=Neg, in
            lower case
        stats_desc (dict[str, str]): Statistics of get_stats and their descriptions for
            print_stats

    Raises:
        SourceTypeError: If the source is not a Doc object or parse does not return
            one; when a class is defined, if its negation_words are not a collection
            of strings
        SourceError: If the source has no dependency parse, no parts of speech, no
            lemmas when requires_lemmas, or no words
    """

    join_hyphens: ClassVar[bool] = False
    requires_lemmas: ClassVar[bool] = False
    negation_words: ClassVar[frozenset[str]] = frozenset()

    stats_desc: ClassVar[Mapping[str, str]] = SYNTAX_STATS_DESC

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        check_words(cls.negation_words, "negation_words", ordered=False)

    def __init__(self, source: Doc):
        messages = self.messages
        doc = self.parse(source)
        if not is_doc(doc):
            raise SourceTypeError(
                messages["hook_doc"].format(
                    hook="parse", cls=type(self).__name__, type=type(doc).__name__
                )
            )
        if not doc.has_annotation("DEP") or not has_sents(doc):
            raise SourceError(messages["no_parse"])
        if not doc.has_annotation("POS"):
            raise SourceError(messages["no_pos"])
        if self.requires_lemmas and not doc.has_annotation("LEMMA"):
            raise SourceError(messages["no_lemmas"])
        join_hyphens = self.join_hyphens
        spans, sents = [], []
        for span in doc.sents:
            if sent_words := get_words(span, join_hyphens):
                spans.append(span)
                sents.append(tuple(sent_words))
        if not sents:
            raise SourceError(messages["no_words"])
        self.sents = _light_sents(doc, sents)
        words = [token for sent in sents for token in sent]
        self.n_sents = len(sents)
        self.n_words = len(words)

        # A whole sentence: a dependent can hang on the second part of a hyphenated word
        distances = [calc_dependency_distances(span, join_hyphens) for span in spans]
        all_distances = [distance for sent in distances for distance in sent]
        depths = [calc_tree_depth(span, join_hyphens) for span in spans]
        children = [[count_children(token, join_hyphens) for token in sent] for sent in sents]
        leaves = [sum(1 for count in sent if not count) for sent in children]
        self.c_children = dict(
            sorted(Counter(count for sent in children for count in sent).items())
        )
        self.c_deps = dict(sorted(Counter(token.dep_ for token in words).items()))
        self.n_leaves = sum(leaves)
        self.n_subtrees = self.n_words - self.n_leaves
        finite_verbs = [token for token in words if is_finite_verb(token)]
        chains = [
            length for span in spans for length in calc_coordination_chains(span, join_hyphens)
        ]
        self.n_coordination_chains = len(chains)
        heads = [[token for token in sent if self.is_clause_head(token)] for sent in sents]
        self.n_clauses = sum(map(len, heads))
        subordinate = [
            [token for token in sent if self.is_subordinate_clause_head(token)] for sent in heads
        ]
        self.n_subordinate_clauses = sum(map(len, subordinate))
        self.n_complex_sents = sum(1 for sent in subordinate if sent)
        self.n_infinitive_clauses = sum(
            1 for sent in heads for token in sent if self.is_infinitive_clause_head(token)
        )
        nouns = [token for token in words if token.pos_ in ("NOUN", "PROPN")]
        self.n_nouns = len(nouns)
        participle_clauses = [
            subtree_len(token, join_hyphens) for token in words if self.is_participle_clause(token)
        ]
        self.n_participle_clauses = len(participle_clauses)
        self.n_verbs = sum(1 for token in words if token.pos_ == "VERB")
        passive = [token for token in words if self.is_passive(token)]
        self.n_passive = len(passive)
        self.n_agentless_passive = sum(1 for token in passive if self.is_agentless(token))
        self.n_infinitives = sum(1 for token in words if is_infinitive(token))
        self.n_negations = sum(1 for token in words if self.is_negation(token))
        split_predicates = self.find_split_predicates(words)
        self.n_split_predicates = len(split_predicates)
        self.split_predicates = tuple(
            f"{verb.text} {noun.text}" for verb, noun in split_predicates
        )
        subjects = [token for token in nouns if base_dep(token) in NOMINAL_SUBJECT_DEPS]
        objects = [token for token in nouns if base_dep(token) in OBJECT_DEPS]
        self.n_nominal_subjects = len(subjects)
        self.n_preverbal_subjects = sum(1 for token in subjects if token.i < token.head.i)
        self.n_nominal_objects = len(objects)
        self.n_preverbal_objects = sum(1 for token in objects if token.i < token.head.i)
        # The units of the statistics computed on first use
        self._spans = tuple((span.start, span.end) for span in spans)
        self._clause_heads = tuple(tuple(token.i for token in sent) for sent in heads)
        self._subordinate_heads = tuple(tuple(token.i for token in sent) for sent in subordinate)

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
        roots = [
            next((i for i, token in enumerate(sent) if is_root(token)), None) for sent in sents
        ]
        self.words_before_root = safe_mean([i for i in roots if i is not None])
        self.verb_valency = safe_divide(
            sum(calc_valency(token, join_hyphens) for token in finite_verbs),
            len(finite_verbs),
            nan,
        )
        self.coordination_chains_per_sent = self.n_coordination_chains / self.n_sents
        self.mean_coordination_chain_len = safe_mean(chains)
        self.clauses_per_sent = self.n_clauses / self.n_sents
        self.mean_clause_len = safe_divide(self.n_words, self.n_clauses, nan)
        self.subordinate_clauses_per_sent = self.n_subordinate_clauses / self.n_sents
        self.p_complex_sents = self.n_complex_sents / self.n_sents
        self.infinitive_clauses_per_sent = self.n_infinitive_clauses / self.n_sents
        self.modifiers_per_noun = safe_divide(
            sum(count_noun_modifiers(token, join_hyphens) for token in nouns), self.n_nouns, nan
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
        join_hyphens = self.join_hyphens
        doc = self.sents[0][0].doc
        words = [token for sent in self.sents for token in sent]
        heads = [[doc[i] for i in sent] for sent in self._clause_heads]
        clause_ids = {token.i for sent in heads for token in sent}
        n_t_units = n_complex_t_units = 0
        for sent, subordinate in zip(heads, self._subordinate_heads, strict=True):
            units = {token.i for token in _t_unit_heads(sent, join_hyphens)}
            n_t_units += len(units)
            n_complex_t_units += len(
                _t_units_of([doc[i] for i in subordinate], units, join_hyphens) - {None}
            )
        firsts = _first_conjuncts(words, join_hyphens)
        coordinations: dict[int, list[Token]] = {}
        for token in words:
            first = firsts[token.i]
            if base_dep(token) == "conj" and first is not None:
                coordinations.setdefault(first.i, []).append(token)
        nouns = [token for token in words if token.pos_ in ("NOUN", "PROPN")]
        modified = _heads_of(words, COMPLEX_NOMINAL_DEPS, join_hyphens)
        word_of = {token.i: token for token in words}
        predicates = {token.i for token in words if token.pos_ in ("VERB", "AUX")} | _heads_of(
            words, SUBJECT_DEPS | {"cop"}, join_hyphens
        )
        return {
            "n_t_units": n_t_units,
            "n_complex_t_units": n_complex_t_units,
            # A coordination of phrases, or of predicates sharing a subject
            "n_coordinate_phrases": sum(
                1
                for first, conjuncts in coordinations.items()
                if first not in clause_ids
                or any(
                    token.i not in clause_ids or _shares_subject(token, join_hyphens)
                    for token in conjuncts
                )
            ),
            "n_complex_nominals": sum(1 for token in nouns if token.i in modified)
            + sum(
                1
                for sent in heads
                for token in sent
                if (first := firsts[token.i]) is not None
                and base_dep(first) in NOMINAL_CLAUSE_DEPS
            ),
            "n_verb_phrases": sum(
                1
                for i in predicates
                if i in word_of and base_dep(word_of[i]) not in AUXILIARY_DEPS | {"auxpass"}
            ),
        }

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
    def t_units_per_sent(self) -> float:
        return self.n_t_units / self.n_sents

    @property
    def mean_t_unit_len(self) -> float:
        return safe_divide(self.n_words, self.n_t_units, nan)

    @property
    def clauses_per_t_unit(self) -> float:
        return safe_divide(self.n_clauses, self.n_t_units, nan)

    @property
    def p_complex_t_units(self) -> float:
        return safe_divide(self.n_complex_t_units, self.n_t_units, nan)

    @property
    def verb_phrases_per_t_unit(self) -> float:
        return safe_divide(self.n_verb_phrases, self.n_t_units, nan)

    @property
    def coordinate_phrases_per_clause(self) -> float:
        return safe_divide(self.n_coordinate_phrases, self.n_clauses, nan)

    @property
    def complex_nominals_per_clause(self) -> float:
        return safe_divide(self.n_complex_nominals, self.n_clauses, nan)

    @cached_property
    def _prep_chains(self) -> list[int]:
        """Lengths of the prepositional chains"""
        doc = self.sents[0][0].doc
        return [
            length
            for start, end in self._spans
            for length in calc_modifier_chains(
                doc[start:end], self.is_prep_complement, self.join_hyphens
            )
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
        return _mean_edit_distance([[token.pos_ for token in sent] for sent in self.sents])

    @cached_property
    def syntax_similarity(self) -> float:
        return _mean_multiset_similarity(
            [Counter(_word_triple(token) for token in sent) for sent in self.sents]
        )

    def __getstate__(self) -> dict[str, Any]:
        """State for pickle and copy: spaCy pickles no token, so sents goes as the compressed
        bytes of its Doc and the positions of the words"""
        state = self.__dict__.copy()
        sents = state.pop("sents", None)
        if sents:
            doc = sents[0][0].doc
            data = zlib.compress(doc.to_bytes(exclude=["tensor", "user_data"]))
            state["_sents_doc"] = (doc.lang_, data)
            state["_sents_positions"] = tuple(tuple(token.i for token in sent) for sent in sents)
        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
        """Restoring the tokens of sents on a blank vocabulary of the language of the Doc"""
        state = dict(state)
        saved = state.pop("_sents_doc", None)
        positions = state.pop("_sents_positions", ())
        self.__dict__.update(state)
        if saved is not None:
            from spacy.tokens import Doc

            lang, data = saved
            doc = Doc(_blank_vocab(lang)).from_bytes(zlib.decompress(data))
            self.sents = tuple(tuple(doc[i] for i in sent) for sent in positions)

    def parse(self, source: Doc) -> Doc:
        """
        Getting the Doc of a source

        Description:
            The source itself, which must be a Doc; a library that parses
            strings overrides the method

        Arguments:
            source (Doc): Data source

        Returns:
            Doc: Doc with a dependency parse and parts of speech

        Raises:
            SourceTypeError: If the source is not a Doc object
        """
        if not is_doc(source):
            raise source_type_error(self.messages, source)
        return source

    def is_clause_head(self, token: Token) -> bool:
        """
        Checking whether a word heads a clause

        Description:
            is_clause_head of the module with join_hyphens of the class and the
            hooks is_infinitive_periphrasis and auxiliary_form

        Arguments:
            token (Token): Token

        Returns:
            bool: Result of the check
        """
        return is_clause_head(
            token, self.join_hyphens, self.is_infinitive_periphrasis, self.auxiliary_form
        )

    def is_infinitive_periphrasis(self, token: Token) -> bool:
        """
        Checking whether an infinitive makes one predicate with its head

        Description:
            A periphrasis of a modal or phasal verb with an infinitive (can
            leave, begins to leave) is one clause; the check gets an infinitive
            under xcomp, an infinitive conjunct and an infinitive subject (csubj)
            of a modal word (is_clause_head); none by default

        Arguments:
            token (Token): Token

        Returns:
            bool: Result of the check
        """
        return False

    def auxiliary_form(self, token: Token) -> str:
        """
        Getting the verb form of an auxiliary without the feature VerbForm

        Description:
            The form the checks of the clauses read for an auxiliary or a copula
            the model leaves without one (predicate_form); an empty string, which
            skips the auxiliary, by default

        Arguments:
            token (Token): Auxiliary or copula

        Returns:
            str: Value of VerbForm, an empty string to skip the auxiliary
        """
        return ""

    def is_subordinate_clause_head(self, token: Token) -> bool:
        """
        Checking whether a word heads a subordinate clause

        Description:
            is_subordinate_clause_head of the module over the hooks is_clause_head
            and auxiliary_form

        Arguments:
            token (Token): Token

        Returns:
            bool: Result of the check
        """
        return is_subordinate_clause_head(token, self.is_clause_head, self.auxiliary_form)

    def is_infinitive_clause_head(self, token: Token) -> bool:
        """
        Checking whether a word heads an infinitive clause under a verb

        Description:
            is_infinitive_clause_head of the module over the hooks is_clause_head
            and auxiliary_form

        Arguments:
            token (Token): Token

        Returns:
            bool: Result of the check
        """
        return is_infinitive_clause_head(token, self.is_clause_head, self.auxiliary_form)

    def is_prep_complement(self, token: Token) -> bool:
        """
        Checking whether a word is a link of a prepositional chain

        Description:
            is_prep_complement of the module with join_hyphens of the class by
            default. The chains are computed on first use, from the words of sents:
            the tokens of a copy of the Doc without its user data and tensor, on a
            blank vocabulary after pickling

        Arguments:
            token (Token): Token

        Returns:
            bool: Result of the check
        """
        return is_prep_complement(token, self.join_hyphens)

    def is_participle_clause(self, token: Token) -> bool:
        """
        Checking whether a word heads a participial clause

        Description:
            A participle (VerbForm=Part) that is not the head of the sentence,
            has no auxiliary or copula (has been built is a predicate) and has a
            dependent besides cc, conj and parataxis (calc_valency)

        Arguments:
            token (Token): Token

        Returns:
            bool: Result of the check
        """
        if not has_feature(token, "VerbForm", "Part") or is_root(token):
            return False
        if any(base_dep(child) in AUXILIARY_DEPS for child in token.children):
            return False
        return calc_valency(token, self.join_hyphens) > 0

    def is_passive(self, token: Token) -> bool:
        """
        Checking whether a word is a passive verb form

        Description:
            is_passive of the module with join_hyphens of the class

        Arguments:
            token (Token): Token

        Returns:
            bool: Result of the check
        """
        return is_passive(token, self.join_hyphens)

    def is_agentless(self, token: Token) -> bool:
        """
        Checking whether a word is a passive form with no agent

        Description:
            A passive form by the hook is_passive with no agent (has_agent)

        Arguments:
            token (Token): Token

        Returns:
            bool: Result of the check
        """
        return self.is_passive(token) and not has_agent(token, self.join_hyphens)

    def is_negation(self, token: Token) -> bool:
        """
        Checking whether a word is a word of negation

        Description:
            A word with Polarity=Neg or one of negation_words in lower case; a
            conjunction (neither... nor) is none. Every such word counts

        Arguments:
            token (Token): Token

        Returns:
            bool: Result of the check
        """
        if token.pos_ in ("CCONJ", "SCONJ"):
            return False
        return has_feature(token, "Polarity", "Neg") or token.text.lower() in self.negation_words

    def find_split_predicates(self, words: Sequence[Token]) -> list[tuple[Token, Token]]:
        """
        Finding the split predicates

        Description:
            A light verb with a noun that carries its meaning (to make a
            decision); none by default, as they depend on the language

        Arguments:
            words (list[Token]): Words of the text

        Returns:
            list[tuple[Token, Token]]: Pairs of the verb and the noun in the order of the words
        """
        return []


def _light_sents(doc: Doc, sents: Sequence[Sequence[Token]]) -> tuple[tuple[Token, ...], ...]:
    """
    Words of the sentences on a copy of the Doc without its tensor and user data: the
    statistics keep neither the activations of the model nor a cycle through an extension
    """
    from spacy.tokens import Doc

    light = Doc.from_docs([doc], exclude=["spans", "tensor", "user_data"])  # type: ignore[call-arg]  # not in the stub of spaCy
    return tuple(tuple(light[token.i] for token in sent) for sent in sents)


@cache
def _blank_vocab(lang: str) -> Vocab:
    """Blank vocabulary of a language, one per process, for the Doc of a restored SyntaxStats"""
    import spacy
    from spacy.vocab import Vocab

    return spacy.blank(lang).vocab if lang else Vocab()


def _word_triple(token: Token) -> tuple[str, str, str]:
    """Dependency triple of a word: the part of speech of its head, the nearest word above it
    through punctuation, its base relation and its own part of speech; a word with no word
    above it has an empty head and the relation root"""
    head, seen = token, {token.i}
    # A broken parse can link the marks above a word in a loop
    while not is_root(head) and head.head.i not in seen:
        head = head.head
        if is_word(head):
            return (head.pos_, base_dep(token), token.pos_)
        seen.add(head.i)
    return ("", "root", token.pos_)


def _t_unit_heads(heads: Sequence[Token], join_hyphens: bool) -> list[Token]:
    """Clause heads of a sentence that head a T-unit: the head of the sentence and the main
    clauses joined to it through conj or parataxis, but for a conjunct without a subject of its
    own, a predicate of the clause it is coordinated to"""
    ids = {token.i for token in heads}
    known: dict[int, bool] = {}
    return [
        token
        for token in heads
        if _is_main_clause(token, ids, join_hyphens, known)
        and not _shares_subject(token, join_hyphens)
    ]


def _is_main_clause(
    token: Token, ids: Collection[int], join_hyphens: bool, known: dict[int, bool]
) -> bool:
    """Whether a clause head reaches the head of the sentence through main clauses alone; known
    keeps the answers for the clause heads on the way"""
    path: list[int] = []
    on_path: set[int] = set()
    while token.i not in known:
        path.append(token.i)
        on_path.add(token.i)
        if is_root(token):
            outcome = True
            break
        parent = _chain_parent(token, join_hyphens)
        if (
            base_dep(token) not in MAIN_CLAUSE_DEPS
            or parent is None
            or parent.i not in ids
            or parent.i in on_path
        ):
            outcome = False
            break
        token = parent
    else:
        outcome = known[token.i]
    for i in path:
        known[i] = outcome
    return outcome


def _shares_subject(token: Token, join_hyphens: bool) -> bool:
    """Whether a conjunct is a predicate sharing the subject of the clause it is coordinated
    to: no subject of its own, and no person, number or gender of its own either, which in a
    language that drops its subjects tell another one (llegamos y nos esperabas)"""
    if base_dep(token) != "conj":
        return False
    if any(
        base_dep(child) in _SUBJECT_DEPS or child.dep_ == "expl"
        for child in get_children(token, join_hyphens)
    ):
        return False
    head = _chain_parent(token, join_hyphens)
    own, other = _agreement(token), _agreement(head) if head is not None else {}
    return all(own[feature] == other[feature] for feature in own.keys() & other.keys())


def _agreement(token: Token) -> dict[str, list[str]]:
    """Person, number and gender of a predicate, those of its auxiliary or copula where the
    word has none (hemos llegado)"""
    found = {feature: token.morph.get(feature, []) for feature in _AGREEMENT_FEATURES}
    for child in token.children:
        if base_dep(child) in AUXILIARY_DEPS:
            for feature in _AGREEMENT_FEATURES:
                found[feature] = found[feature] or child.morph.get(feature, [])
    return {feature: values for feature, values in found.items() if values}


def _t_units_of(
    tokens: Iterable[Token], units: Collection[int], join_hyphens: bool
) -> set[int | None]:
    """Positions of the heads of the T-units the clauses belong to, the nearest ones above
    them; None for a clause under none"""
    known: dict[int, int | None] = {}
    found = set()
    for token in tokens:
        path, seen = [], {token.i}
        unit = None
        parent = _chain_parent(token, join_hyphens)
        while parent is not None and parent.i not in seen:
            if parent.i in known:
                unit = known[parent.i]
                break
            if parent.i in units:
                unit = parent.i
                break
            path.append(parent.i)
            seen.add(parent.i)
            parent = _chain_parent(parent, join_hyphens)
        for i in path:
            known[i] = unit
        found.add(unit)
    return found


def _first_conjuncts(words: Iterable[Token], join_hyphens: bool) -> dict[int, Token | None]:
    """First conjunct of the coordination of every word by its position, the word itself out
    of one; None through a punctuation mark or a loop of conjuncts"""
    known: dict[int, Token | None] = {}
    for token in words:
        path: list[int] = []
        on_path: set[int] = set()
        word = token
        while True:
            if word.i in known:
                first = known[word.i]
                break
            if base_dep(word) != "conj":
                first = known[word.i] = word
                break
            path.append(word.i)
            on_path.add(word.i)
            parent = _chain_parent(word, join_hyphens)
            if parent is None or parent.i in on_path:
                first = None
                break
            word = parent
        for i in path:
            known[i] = first
    return known


def _heads_of(words: Iterable[Token], relations: Collection[str], join_hyphens: bool) -> set[int]:
    """Positions of the words some of the words hang on by one of the relations"""
    return {
        parent.i
        for token in words
        if base_dep(token) in relations
        and (parent := _chain_parent(token, join_hyphens)) is not None
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


def get_words(tokens: Iterable[Token], join_hyphens: bool = False) -> list[Token]:
    """
    Getting the words of a sequence of tokens

    Description:
        With join_hyphens, a word the tokenizer split at its hyphens is one
        word, given by the part that holds its relation (the head of the
        sentence, or the part hanging outside the word, the nearest to the
        root), or by its first part when a hyphen holds the relation or the
        parts form a loop

    Arguments:
        tokens (Doc|Span|list[Token]): Sequence of tokens
        join_hyphens (bool): Join the parts of hyphenated words (joins_previous)

    Returns:
        list[Token]: List of words
    """
    return [_word_part(unit) for unit in _word_units(tokens, join_hyphens)]


def _word_units(tokens: Iterable[Token], join_hyphens: bool) -> list[list[Token]]:
    """
    Words of a sequence of tokens as lists of their tokens

    Description:
        With join_hyphens the parts of a hyphenated word and the hyphens between
        them are one word, when its earlier parts are in the sequence
    """
    units: list[list[Token]] = []
    unit_of: dict[int, list[Token]] = {}
    for token in tokens:
        if not is_word(token):
            continue
        first = token.i - 2
        if join_hyphens and first in unit_of and joins_previous(token):
            unit = unit_of[first]
            unit.extend((token.doc[token.i - 1], token))
        else:
            unit = [token]
            units.append(unit)
        unit_of[token.i] = unit
    return units


def _word_part(unit: Sequence[Token]) -> Token:
    """
    Part that gives a word: the one holding the head of its sentence or hanging
    outside it (_word_head), the first part when that is a hyphen or there is none
    """
    if len(unit) == 1:
        return unit[0]
    part = next((token for token in unit if is_root(token)), None)
    if part is None:
        part = _word_head(unit)
    return part if part is not None and is_word(part) else unit[0]


def _word_head(unit: Sequence[Token]) -> Token | None:
    """
    Part of a word that hangs on a token outside it, the nearest to the root and
    a word rather than a hyphen when equal; None for a word that holds the head
    of its sentence or has no part hanging outside it
    """
    if len(unit) == 1:
        return None if is_root(unit[0]) else unit[0]
    if any(is_root(token) for token in unit):
        return None
    ids = {token.i for token in unit}
    outside = [token for token in unit if token.head.i not in ids]
    if not outside:
        # A broken parse can link the parts of one word in a loop
        return None
    if len(outside) == 1:
        return outside[0]
    return min(outside, key=lambda token: (sum(1 for _ in token.ancestors), not is_word(token)))


def is_root(token: Token) -> bool:
    """
    Checking whether a token is the head of its sentence

    Arguments:
        token (Token): Token

    Returns:
        bool: Result of the check
    """
    return token.head.i == token.i


def base_dep(token: Token) -> str:
    """
    Getting the syntactic relation of a token without its subtype

    Description:
        The subtypes of Universal Dependencies are separated by a colon:
        expl:pass - expl, nsubj:pass - nsubj

    Arguments:
        token (Token): Token

    Returns:
        str: Base relation
    """
    return _base_relation(token.dep_)


@cache
def _base_relation(relation: str) -> str:
    """A relation without its subtype, once for every label"""
    return relation.split(":")[0]


def get_children(token: Token, join_hyphens: bool = False) -> list[Token]:
    """
    Getting the dependent words of a token

    Description:
        With join_hyphens, the dependents of a hyphenated word are the words
        whose head (the part hanging outside the word, the nearest to the root)
        hangs on one of its tokens, each given by that part, or by its first
        part when it hangs by a hyphen

    Arguments:
        token (Token): Token
        join_hyphens (bool): Join the parts of hyphenated words (joins_previous)

    Returns:
        list[Token]: List of the dependents without punctuation and whitespace
    """
    if not join_hyphens:
        return [child for child in token.children if is_word(child)]
    word = _hyphenated_word(token) or [token]
    ids = {part.i for part in word}
    children: dict[int, Token] = {}
    for part in word:
        for child in part.children:
            unit = _hyphenated_word(child) if child.i not in ids else None
            if unit is None or unit[0].i in children:
                continue
            if len(unit) == 1:
                children[child.i] = child
                continue
            head = _word_head(unit)
            if head is not None and head.head.i in ids:
                children[unit[0].i] = _word_part(unit)
    return [children[start] for start in sorted(children)]


def _hyphenated_word(token: Token) -> list[Token] | None:
    """Tokens of the hyphenated word a token or an inner hyphen belongs to, None for no word"""
    doc = token.doc
    i = token.i
    if not is_word(token):
        if token.text != "-" or i + 1 >= len(doc) or not joins_previous(doc[i + 1]):
            return None
        i += 1
    elif (i == 0 or doc[i - 1].text != "-") and (i + 1 >= len(doc) or doc[i + 1].text != "-"):
        # The common case: no hyphen next to the word
        return [token]
    start = i
    while joins_previous(doc[start]):
        start -= 2
    end = i
    while end + 2 < len(doc) and joins_previous(doc[end + 2]):
        end += 2
    return list(doc[start : end + 1])


def count_children(token: Token, join_hyphens: bool = False) -> int:
    """
    Counting the dependent words of a token

    Arguments:
        token (Token): Token
        join_hyphens (bool): Join the parts of hyphenated words (get_children)

    Returns:
        int: Number of dependent words
    """
    return len(get_children(token, join_hyphens))


def subtree_len(token: Token, join_hyphens: bool = False) -> int:
    """
    Computing the length of the subtree of a token in words

    Description:
        The token and all of its direct and indirect dependents; with
        join_hyphens, the hyphenated word of the token and the words that hang
        on it (get_children), directly or through punctuation

    Arguments:
        token (Token): Token
        join_hyphens (bool): Join the parts of hyphenated words (joins_previous)

    Returns:
        int: Number of words in the subtree
    """
    if not join_hyphens:
        count = 0
        tokens = [token]
        # A broken parse can link tokens in a loop, and Token.subtree never ends then
        seen = {token.i}
        while tokens:
            current = tokens.pop()
            count += is_word(current)
            for child in current.children:
                if child.i not in seen:
                    seen.add(child.i)
                    tokens.append(child)
        return count
    count = 0
    words = [_hyphenated_word(token) or [token]]
    seen = {part.i for part in words[0]}
    while words:
        word = words.pop()
        count += is_word(word[0])
        ids = {part.i for part in word}
        tokens = [child for part in word for child in part.children if child.i not in ids]
        while tokens:
            child = tokens.pop()
            # A broken parse can link tokens in a loop
            if child.i in seen:
                continue
            seen.add(child.i)
            unit = _hyphenated_word(child)
            if unit is None:
                tokens.extend(child.children)
            elif len(unit) == 1 or ((head := _word_head(unit)) is not None and head.i == child.i):
                seen.update(part.i for part in unit)
                words.append(unit)
    return count


def calc_dependency_distances(tokens: Iterable[Token], join_hyphens: bool = False) -> list[int]:
    """
    Computing the dependency distances

    Description:
        The distance between a word and its head in positions of words,
        punctuation left out (Liu 2008); the head of a sentence and a word whose
        head lies outside the sequence are skipped. With join_hyphens, a
        hyphenated word is one position, and its head is that of its part
        hanging outside it, the nearest to the root

    References:
        Liu H. Dependency distance as a metric for language comprehension difficulty.
        Journal of Cognitive Science, 2008, 9(2), 159-191

    Arguments:
        tokens (Doc|Span|list[Token]): Sequence of tokens
        join_hyphens (bool): Join the parts of hyphenated words (joins_previous)

    Returns:
        list[int]: Distances in the order of the words
    """
    units = _word_units(tokens, join_hyphens)
    positions = {token.i: position for position, unit in enumerate(units) for token in unit}
    distances = []
    for position, unit in enumerate(units):
        head = _word_head(unit)
        if head is not None and head.head.i in positions:
            distances.append(abs(position - positions[head.head.i]))
    return distances


def calc_tree_depth(tokens: Iterable[Token], join_hyphens: bool = False) -> int:
    """
    Computing the depth of the dependency tree

    Description:
        The longest path from the head of the sentence to a leaf in relations;
        the maximum for several sentences, 0 for a sentence of one word. With
        join_hyphens, a hyphenated word is one node, as in
        calc_dependency_distances

    Arguments:
        tokens (Doc|Span|list[Token]): Sequence of tokens
        join_hyphens (bool): Join the parts of hyphenated words (joins_previous)

    Returns:
        int: Depth of the tree
    """
    parents = _unit_parents(_word_units(tokens, join_hyphens))
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


def _unit_parents(units: Sequence[Sequence[Token]]) -> list[int | None]:
    """
    Index of the word every word of a sequence hangs on, through punctuation and
    tokens outside the sequence; None for a word with no such head
    """
    unit_of = {token.i: n for n, unit in enumerate(units) for token in unit}
    parents: list[int | None] = []
    for n, unit in enumerate(units):
        head = _word_head(unit)
        parent = None
        token = head.head if head is not None else None
        seen = set()
        while token is not None and token.i not in seen:
            seen.add(token.i)
            if unit_of.get(token.i, n) != n:
                parent = unit_of[token.i]
                break
            token = None if is_root(token) else token.head
        parents.append(parent)
    return parents


@_takes_token
def predicate_form(token: Token, auxiliary_form: Callable[[Token], str] | None = None) -> str:
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
        token (Token): Token
        auxiliary_form (callable): Verb form of an auxiliary without the feature
            VerbForm

    Returns:
        str: Value of VerbForm (Fin, Inf, Ger, Part and the others of the model),
            an empty string for a word with no verb form

    Raises:
        SourceTypeError: If the token is not a Token or auxiliary_form is not callable

    Example:
        >>> import spacy
        >>> from spacy.tokens import Doc
        >>> from anyts.syntax_stats import predicate_form
        >>> doc = Doc(
        ...     spacy.blank("en").vocab,
        ...     words=["She", "had", "arrived"],
        ...     heads=[2, 2, 2],
        ...     deps=["nsubj", "aux", "ROOT"],
        ...     morphs=["Case=Nom", "VerbForm=Fin", "VerbForm=Part"],
        ... )
        >>> predicate_form(doc[2]), predicate_form(doc[0])
        ('Fin', '')
    """
    if auxiliary_form is not None:
        check_callable(auxiliary_form, "verb form of an auxiliary")
    auxiliaries = [
        (child, form)
        for child in token.children
        if base_dep(child) in AUXILIARY_DEPS
        and (form := _verb_form(child) or (auxiliary_form(child) if auxiliary_form else ""))
    ]
    if not auxiliaries:
        return _verb_form(token)
    if any(form == "Fin" for _, form in auxiliaries):
        return "Fin"
    auxiliary, form = auxiliaries[0]
    if form == "Part" and not has_feature(auxiliary, "Tense", "Pres"):
        return "Fin"
    return form


def _verb_form(token: Token) -> str:
    """Verb form of a token, an empty string without one"""
    return next(iter(token.morph.get("VerbForm", [])), "")


def calc_valency(token: Token, join_hyphens: bool = False) -> int:
    """
    Computing the valency of a token

    Description:
        The number of dependent words without cc, conj and parataxis

    Arguments:
        token (Token): Token
        join_hyphens (bool): Join the parts of hyphenated words (get_children)

    Returns:
        int: Number of dependent words
    """
    return sum(
        1 for child in get_children(token, join_hyphens) if child.dep_ not in VALENCY_IGNORED_DEPS
    )


def calc_coordination_chains(tokens: Iterable[Token], join_hyphens: bool = False) -> list[int]:
    """
    Computing the lengths of the coordination chains

    Description:
        A chain is a group of words linked by conj, whichever word each
        conjunct hangs on (the first one in Universal Dependencies, the
        previous one in ClearNLP); a nested coordination (A and B, or C) and an
        enumeration split between several heads are one chain. Its length is
        the number of its words. With join_hyphens, a hyphenated word is one
        word, linked by the conj of any of its parts

    Arguments:
        tokens (Doc|Span|list[Token]): Sequence of tokens
        join_hyphens (bool): Join the parts of hyphenated words (joins_previous)

    Returns:
        list[int]: Lengths of the chains in the order of their first words
    """
    if join_hyphens:
        units = _word_units(tokens, True)
        unit_of = {token.i: n for n, unit in enumerate(units) for token in unit}
        # Any part can be the conjunct: the parser links the parts of a compound adjective apart
        links = [
            (n, unit_of[token.head.i])
            for n, unit in enumerate(units)
            for token in unit
            if token.dep_ == "conj" and is_word(token) and unit_of.get(token.head.i, n) != n
        ]
        return _chain_sizes(range(len(units)), links)
    words = get_words(tokens)
    ids = {token.i for token in words}
    links = [
        (token.i, token.head.i) for token in words if token.dep_ == "conj" and token.head.i in ids
    ]
    return _chain_sizes([token.i for token in words], links)


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


@_takes_token
def is_predicate(token: Token, join_hyphens: bool = False) -> bool:
    """
    Checking whether a word can be the predicate of its clause

    Description:
        A verb (VERB, AUX), a word with a subject of its own (nsubj, csubj and
        their subtypes) or with a copula (cop): the nominal predicate of he is
        tall and of a language that drops the subject (y estaba cansado) passes,
        a parenthetical word does not

    Arguments:
        token (Token): Token
        join_hyphens (bool): Join the parts of hyphenated words (get_children)

    Returns:
        bool: Result of the check

    Raises:
        SourceTypeError: If the token is not a Token
    """
    return token.pos_ in ("VERB", "AUX") or any(
        base_dep(child) in SUBJECT_DEPS or base_dep(child) == "cop"
        for child in get_children(token, join_hyphens)
    )


@_takes_token
def is_clause_head(
    token: Token,
    join_hyphens: bool = False,
    is_infinitive_periphrasis: Callable[[Token], bool] | None = None,
    auxiliary_form: Callable[[Token], str] | None = None,
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
        token (Token): Token
        join_hyphens (bool): Join the parts of hyphenated words (is_predicate)
        is_infinitive_periphrasis (callable): Whether an infinitive makes one
            predicate with its head (is_infinitive_clause); none by default
        auxiliary_form (callable): Verb form of an auxiliary without the feature
            VerbForm (predicate_form); none by default

    Returns:
        bool: Result of the check

    Raises:
        SourceTypeError: If the token is not a Token, or is_infinitive_periphrasis or
            auxiliary_form is not callable
    """
    if is_infinitive_periphrasis is not None:
        check_callable(is_infinitive_periphrasis, "check of an infinitive periphrasis")
    if auxiliary_form is not None:
        check_callable(auxiliary_form, "verb form of an auxiliary")
    return _is_clause_head(token, join_hyphens, is_infinitive_periphrasis, auxiliary_form)


def _is_clause_head(
    token: Token,
    join_hyphens: bool,
    is_infinitive_periphrasis: Callable[[Token], bool] | None,
    auxiliary_form: Callable[[Token], str] | None,
) -> bool:
    """is_clause_head with checked hooks"""
    seen = set()
    # Up the chains of conjuncts and infinitive complements to the word that is none
    while is_word(token) and token.i not in seen:
        if is_root(token):
            return True
        form = predicate_form(token, auxiliary_form)
        if form in NONFINITE_CLAUSE_FORMS:
            return False
        dep = base_dep(token)
        if dep != "conj":
            if dep == "xcomp":
                if form == "Fin":
                    return True
                completed = (
                    _completed_word(token, is_infinitive_periphrasis, auxiliary_form)
                    if _is_infinitive_complement(token, is_infinitive_periphrasis, auxiliary_form)
                    else None
                )
                if completed is None:
                    return False
                seen.add(token.i)
                token = completed
                continue
            if dep not in CLAUSE_DEPS:
                return False
            if dep == "parataxis":
                return is_predicate(token, join_hyphens)
            if dep == "csubj" and form == "Inf" and is_infinitive_periphrasis:
                return not is_infinitive_periphrasis(token)
            return not (dep == "acl" and form == "Inf")
        if form == "Inf" and is_infinitive_periphrasis and is_infinitive_periphrasis(token):
            return False
        if not is_predicate(token, join_hyphens):
            return False
        seen.add(token.i)
        token = token.head
    return False


@_takes_token
def is_infinitive_clause(
    token: Token,
    is_infinitive_periphrasis: Callable[[Token], bool] | None = None,
    is_clause_head: Callable[[Token], bool] | None = None,
    auxiliary_form: Callable[[Token], str] | None = None,
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
        token (Token): Token
        is_infinitive_periphrasis (callable): Whether an infinitive makes one
            predicate with its head; none by default
        is_clause_head (callable): Whether a word heads a clause; by default
            is_clause_head of the module with the hooks of this check
        auxiliary_form (callable): Verb form of an auxiliary without the feature
            VerbForm (predicate_form); none by default

    Returns:
        bool: Result of the check

    Raises:
        SourceTypeError: If the token is not a Token, or is_infinitive_periphrasis,
            is_clause_head or auxiliary_form is not callable
    """
    if is_infinitive_periphrasis is not None:
        check_callable(is_infinitive_periphrasis, "check of an infinitive periphrasis")
    if auxiliary_form is not None:
        check_callable(auxiliary_form, "verb form of an auxiliary")
    if is_clause_head is None:
        is_clause_head = _clause_head_check(is_infinitive_periphrasis, auxiliary_form)
    check_callable(is_clause_head, "check of a clause head")
    return _is_infinitive_clause(token, is_infinitive_periphrasis, is_clause_head, auxiliary_form)


def _clause_head_check(
    is_infinitive_periphrasis: Callable[[Token], bool] | None,
    auxiliary_form: Callable[[Token], str] | None,
) -> Callable[[Token], bool]:
    """is_clause_head of the module with checked hooks"""
    return partial(
        _is_clause_head,
        join_hyphens=False,
        is_infinitive_periphrasis=is_infinitive_periphrasis,
        auxiliary_form=auxiliary_form,
    )


def _is_infinitive_clause(
    token: Token,
    is_infinitive_periphrasis: Callable[[Token], bool] | None,
    is_clause_head: Callable[[Token], bool],
    auxiliary_form: Callable[[Token], str] | None,
) -> bool:
    """is_infinitive_clause with checked hooks"""
    if not _is_infinitive_complement(token, is_infinitive_periphrasis, auxiliary_form):
        return False
    completed = _completed_word(token, is_infinitive_periphrasis, auxiliary_form)
    return completed is not None and is_clause_head(completed)


def _is_infinitive_complement(
    token: Token,
    is_infinitive_periphrasis: Callable[[Token], bool] | None,
    auxiliary_form: Callable[[Token], str] | None,
) -> bool:
    """Infinitive under xcomp that makes no periphrasis with its head"""
    if base_dep(token) != "xcomp" or predicate_form(token, auxiliary_form) != "Inf":
        return False
    return not (is_infinitive_periphrasis is not None and is_infinitive_periphrasis(token))


def _completed_word(
    token: Token,
    is_infinitive_periphrasis: Callable[[Token], bool] | None,
    auxiliary_form: Callable[[Token], str] | None,
) -> Token | None:
    """
    Word an infinitive complement completes, up its non-finite complements and the
    infinitives of a periphrasis a model attaches as conj or csubj; None in a loop
    """
    seen = {token.i}
    word = token.head
    while word.i not in seen and (
        (base_dep(word) == "xcomp" and predicate_form(word, auxiliary_form) != "Fin")
        or (
            is_infinitive_periphrasis is not None
            and base_dep(word) in ("conj", "csubj")
            and predicate_form(word, auxiliary_form) == "Inf"
            and is_infinitive_periphrasis(word)
        )
    ):
        seen.add(word.i)
        word = word.head
    # A loop through the words above would bring the checks back to the infinitive
    above = word
    while not is_root(above) and above.i not in seen:
        seen.add(above.i)
        above = above.head
    return None if above.i == token.i else word


@_takes_token
def is_subordinate_clause_head(
    token: Token,
    is_clause_head: Callable[[Token], bool] | None = None,
    auxiliary_form: Callable[[Token], str] | None = None,
) -> bool:
    """
    Checking whether a word heads a subordinate clause

    Description:
        The head of a clause by is_clause_head with a relation of
        SUBORDINATE_CLAUSE_DEPS (ccomp, advcl, acl, csubj and their subtypes),
        or under xcomp with a finite predicate (a complement a model attaches
        as xcomp), or a conjunct of one: the relation of the first word up its
        chain of conjuncts decides. An infinitive under xcomp heads an
        infinitive clause (is_infinitive_clause_head), not a subordinate one

    Arguments:
        token (Token): Token
        is_clause_head (callable): Whether a word heads a clause; by default
            is_clause_head of the module with the hooks of this check
        auxiliary_form (callable): Verb form of an auxiliary without the feature
            VerbForm (predicate_form); none by default

    Returns:
        bool: Result of the check

    Raises:
        SourceTypeError: If the token is not a Token, or is_clause_head or auxiliary_form
            is not callable
    """
    if auxiliary_form is not None:
        check_callable(auxiliary_form, "verb form of an auxiliary")
    if is_clause_head is None:
        is_clause_head = _clause_head_check(None, auxiliary_form)
    check_callable(is_clause_head, "check of a clause head")
    if is_root(token) or not is_clause_head(token):
        return False
    seen = set()
    while base_dep(token) == "conj" and token.i not in seen:
        seen.add(token.i)
        token = token.head
    dep = base_dep(token)
    if dep == "xcomp":
        return predicate_form(token, auxiliary_form) != "Inf"
    return not is_root(token) and dep in SUBORDINATE_CLAUSE_DEPS


@_takes_token
def is_infinitive_clause_head(
    token: Token,
    is_clause_head: Callable[[Token], bool] | None = None,
    auxiliary_form: Callable[[Token], str] | None = None,
) -> bool:
    """
    Checking whether a word heads an infinitive clause under a verb

    Description:
        The head of a clause by is_clause_head whose predicate is an infinitive
        under xcomp (wants to leave, asked him to leave), or a conjunct of one:
        the first word up its chain of conjuncts decides. Such a clause is
        counted apart from the subordinate ones, as grammars of many languages
        take it for a part of a simple sentence

    Arguments:
        token (Token): Token
        is_clause_head (callable): Whether a word heads a clause; by default
            is_clause_head of the module with the hooks of this check
        auxiliary_form (callable): Verb form of an auxiliary without the feature
            VerbForm (predicate_form); none by default

    Returns:
        bool: Result of the check

    Raises:
        SourceTypeError: If the token is not a Token, or is_clause_head or auxiliary_form
            is not callable
    """
    if auxiliary_form is not None:
        check_callable(auxiliary_form, "verb form of an auxiliary")
    if is_clause_head is None:
        is_clause_head = _clause_head_check(None, auxiliary_form)
    check_callable(is_clause_head, "check of a clause head")
    if is_root(token) or not is_clause_head(token):
        return False
    seen = set()
    while base_dep(token) == "conj" and token.i not in seen:
        seen.add(token.i)
        token = token.head
    return base_dep(token) == "xcomp" and predicate_form(token, auxiliary_form) == "Inf"


@_takes_token
def is_passive(token: Token, join_hyphens: bool = False) -> bool:
    """
    Checking whether a word is a passive verb form

    Description:
        A verb with Voice=Pass or with a dependent of PASSIVE_DEPS: nsubj:pass,
        csubj:pass, aux:pass of Universal Dependencies and nsubjpass,
        csubjpass, auxpass of ClearNLP

    Arguments:
        token (Token): Token
        join_hyphens (bool): Join the parts of hyphenated words (get_children)

    Returns:
        bool: Result of the check

    Raises:
        SourceTypeError: If the token is not a Token
    """
    if token.pos_ != "VERB":
        return False
    return has_feature(token, "Voice", "Pass") or any(
        child.dep_ in PASSIVE_DEPS for child in get_children(token, join_hyphens)
    )


@_takes_token
def has_agent(token: Token, join_hyphens: bool = False) -> bool:
    """
    Checking whether a word has an agent

    Description:
        A dependent of AGENT_DEPS: obl:agent of Universal Dependencies and
        agent of ClearNLP

    Arguments:
        token (Token): Token
        join_hyphens (bool): Join the parts of hyphenated words (get_children)

    Returns:
        bool: Result of the check

    Raises:
        SourceTypeError: If the token is not a Token
    """
    return any(child.dep_ in AGENT_DEPS for child in get_children(token, join_hyphens))


@_takes_token
def is_agentless(token: Token, join_hyphens: bool = False) -> bool:
    """
    Checking whether a word is a passive form with no agent

    Description:
        A passive form (is_passive) with no agent (has_agent)

    Arguments:
        token (Token): Token
        join_hyphens (bool): Join the parts of hyphenated words (get_children)

    Returns:
        bool: Result of the check

    Raises:
        SourceTypeError: If the token is not a Token
    """
    return is_passive(token, join_hyphens) and not has_agent(token, join_hyphens)


def count_noun_modifiers(token: Token, join_hyphens: bool = False) -> int:
    """
    Counting the modifiers of a noun phrase

    Description:
        The dependents with the relations amod, det, nmod, nummod and acl and
        their subtypes (NOUN_MODIFIER_DEPS); conj and appos are no modifiers

    Arguments:
        token (Token): Token
        join_hyphens (bool): Join the parts of hyphenated words (get_children)

    Returns:
        int: Number of modifiers
    """
    return sum(
        1 for child in get_children(token, join_hyphens) if base_dep(child) in NOUN_MODIFIER_DEPS
    )


@_takes_token
def is_prep_complement(token: Token, join_hyphens: bool = False) -> bool:
    """
    Checking whether a word is a complement with a preposition

    Description:
        A word with the relation nmod or obl or a subtype of them
        (PREP_COMPLEMENT_DEPS), or a predicate with a copula out of a relative
        clause (acl), that has a dependent of the relation case that is an
        adposition or a word with a fixed adposition (in front of): the house of
        the father, went to the house, was in the house. A noun in a case
        without a preposition is none. The links of a prepositional chain
        (calc_modifier_chains)

    Arguments:
        token (Token): Token
        join_hyphens (bool): Join the parts of hyphenated words (get_children)

    Returns:
        bool: Result of the check

    Raises:
        SourceTypeError: If the token is not a Token

    Example:
        >>> import spacy
        >>> from spacy.tokens import Doc
        >>> from anyts.syntax_stats import is_prep_complement
        >>> doc = Doc(
        ...     spacy.blank("en").vocab,
        ...     words=["the", "house", "of", "the", "father"],
        ...     heads=[1, 1, 4, 4, 1],
        ...     deps=["det", "ROOT", "case", "det", "nmod"],
        ...     pos=["DET", "NOUN", "ADP", "DET", "NOUN"],
        ... )
        >>> is_prep_complement(doc[4]), is_prep_complement(doc[1])
        (True, False)
    """
    relation = base_dep(token)
    if relation == "acl":
        return False
    children = _dependents(token, join_hyphens)
    if relation not in PREP_COMPLEMENT_DEPS and not any(
        base_dep(child) == "cop" for child in children
    ):
        return False
    return any(base_dep(child) == "case" and _is_adposition(child) for child in children)


def _dependents(token: Token, join_hyphens: bool) -> list[Token]:
    """Dependents of a word for a check of their relations: those of get_children for a
    hyphenated word with join_hyphens, the children of its token otherwise"""
    if join_hyphens and len(_hyphenated_word(token) or ()) > 1:
        return get_children(token, join_hyphens)
    return list(token.children)


def _is_adposition(token: Token) -> bool:
    """Whether a word is an adposition or begins one of several words (fixed)"""
    return token.pos_ == "ADP" or any(
        base_dep(child) == "fixed" and child.pos_ == "ADP" for child in token.children
    )


def dependency_triples(
    tokens: Iterable[Token], join_hyphens: bool = False
) -> list[tuple[str, str, str]]:
    """
    Getting the dependency triples of the words of a sentence

    Description:
        For every word (get_words) the part of speech of its head, the nearest
        word above it through punctuation, its relation without a subtype
        (base_dep) and its own part of speech: (NOUN, amod, ADJ) for a red house;
        the head of the sentence, and a word with no word above it, give an empty
        head and the relation root, whatever its label

    Arguments:
        tokens (Doc|Span|list[Token]): Sequence of tokens
        join_hyphens (bool): Join the parts of hyphenated words (get_words)

    Returns:
        list[tuple[str, str, str]]: Triples in the order of the words

    Raises:
        SourceTypeError: If the tokens are not a Doc, a Span or a list of Token objects

    Example:
        >>> import spacy
        >>> from spacy.tokens import Doc
        >>> from anyts.syntax_stats import dependency_triples
        >>> doc = Doc(
        ...     spacy.blank("en").vocab,
        ...     words=["a", "red", "house"],
        ...     heads=[2, 2, 2],
        ...     deps=["det", "amod", "ROOT"],
        ...     pos=["DET", "ADJ", "NOUN"],
        ... )
        >>> dependency_triples(doc)
        [('NOUN', 'det', 'DET'), ('NOUN', 'amod', 'ADJ'), ('', 'root', 'NOUN')]
    """
    if not (is_doc(tokens) or is_span(tokens)):
        check_sequence(tokens, "tokens")
        if not all(is_token(token) for token in tokens):
            raise SourceTypeError("The tokens must be a Doc, a Span or a list of Token objects")
    return [_word_triple(token) for token in get_words(tokens, join_hyphens)]


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
    tokens: Iterable[Token], is_modifier: Callable[[Token], bool], join_hyphens: bool = False
) -> list[int]:
    """
    Computing the lengths of the chains of nested modifiers

    Description:
        Two or more nested modifiers of is_modifier, such as the complements of
        the increase of the efficiency of the use of resources (length 3); a
        chain starts at a modifier whose head is none, and its length is the
        number of modifiers in its longest branch. The links are those of
        get_children: punctuation is no link, and with join_hyphens a
        hyphenated word is one link

    Arguments:
        tokens (Doc|Span|list[Token]): Sequence of tokens
        is_modifier (Callable[[Token], bool]): Whether a word is a modifier of the chain
        join_hyphens (bool): Join the parts of hyphenated words (get_words)

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
    for token in get_words(tokens, join_hyphens):
        if not is_modifier(token):
            continue
        parent = _chain_parent(token, join_hyphens)
        if not (parent is not None and is_modifier(parent)):
            length = _chain_len(token, is_modifier, join_hyphens)
            if length >= 2:
                chains.append(length)
    return chains


def _chain_parent(token: Token, join_hyphens: bool) -> Token | None:
    """Word a word hangs on as get_children gives it, None through punctuation or at the root"""
    if not join_hyphens:
        head = token.head
        return head if not is_root(token) and is_word(head) else None
    unit = _hyphenated_word(token) or [token]
    part = _word_head(unit)
    if part is None:
        return None
    word = _hyphenated_word(part.head)
    return _word_part(word) if word is not None else None


def _chain_len(token: Token, is_modifier: Callable[[Token], bool], join_hyphens: bool) -> int:
    """Number of the modifiers in the longest branch of a chain from a token, without recursion
    for a chain of any depth"""
    longest = 0
    stack = [(token, 1)]
    seen = {token.i}
    while stack:
        word, depth = stack.pop()
        longest = max(longest, depth)
        for child in get_children(word, join_hyphens):
            if child.i not in seen and is_modifier(child):
                seen.add(child.i)
                stack.append((child, depth + 1))
    return longest
