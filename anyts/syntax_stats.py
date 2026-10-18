from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from math import nan
from statistics import fmean, pstdev
from typing import TYPE_CHECKING, Any, ClassVar

from .constants import (
    AGENT_DEPS,
    AUXILIARY_DEPS,
    CLAUSE_DEPS,
    NONFINITE_CLAUSE_FORMS,
    NOUN_MODIFIER_DEPS,
    PASSIVE_DEPS,
    SUBJECT_DEPS,
    SUBORDINATE_CLAUSE_DEPS,
    SYNTAX_STATS_DESC,
    VALENCY_IGNORED_DEPS,
)
from .exceptions import SourceError, SourceTypeError
from .stats import Stats
from .utils import (
    check_words,
    has_feature,
    has_sents,
    is_doc,
    is_finite_verb,
    is_infinitive,
    is_word,
    joins_previous,
    safe_divide,
    safe_mean,
)

if TYPE_CHECKING:
    from spacy.tokens import Doc, Token


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
        from sents.
        get_stats, to_dataframe, print_stats and describe come from Stats

    References:
        https://universaldependencies.org/u/dep/
        https://dialogue-conf.org/media/4302/ivanovvv.pdf

    Arguments:
        source (Doc): Data source (a Doc object with a dependency parse, or what
            parse makes one of)

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
        n_nouns (int): Number of nouns
        n_participle_clauses (int): Number of participial clauses
        n_verbs (int): Number of verb forms
        n_passive (int): Number of passive verb forms
        n_agentless_passive (int): Number of passive forms with no agent
        n_infinitives (int): Number of infinitives
        n_negations (int): Number of words of negation
        n_split_predicates (int): Number of split predicates
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
        verb_valency (float): Mean number of dependents of a finite verb
        coordination_chains_per_sent (float): Coordination chains per sentence
        mean_coordination_chain_len (float): Mean length of a coordination chain
        clauses_per_sent (float): Clauses per sentence
        mean_clause_len (float): Mean length of a clause in words
        subordinate_clauses_per_sent (float): Subordinate clauses per sentence
        p_complex_sents (float): Share of sentences with a subordinate clause
        modifiers_per_noun (float): Mean number of modifiers of a noun
        participle_clauses_per_sent (float): Participial clauses per sentence
        mean_participle_clause_len (float): Mean length of a participial clause in words
        p_passive (float): Share of passive forms among the verb forms
        p_agentless_passive (float): Share of forms with no agent among the passive ones
        infinitives_per_sent (float): Infinitives per sentence
        negations_per_sent (float): Words of negation per sentence
        split_predicates_per_sent (float): Split predicates per sentence
        noun_verb_ratio (float): Ratio of the nouns to the verb forms

    Methods:
        parse: Doc of a source
        is_clause_head: Whether a word heads a clause
        is_subordinate_clause_head: Whether a clause head heads a subordinate clause
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
        SourceError: If the source has no dependency parse, no lemmas when
            requires_lemmas, or no words
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
                messages["hook_result"].format(
                    hook="parse",
                    cls=type(self).__name__,
                    expected="a Doc",
                    type=type(doc).__name__,
                )
            )
        if not doc.has_annotation("DEP") or not has_sents(doc):
            raise SourceError(messages["no_parse"])
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
        self.sents = tuple(sents)
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
            sum(1 for token in sent if self.is_subordinate_clause_head(token)) for sent in heads
        ]
        self.n_subordinate_clauses = sum(subordinate)
        self.n_complex_sents = sum(1 for count in subordinate if count)
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
        self.noun_verb_ratio = safe_divide(self.n_nouns, self.n_verbs, nan)

    def parse(self, source: Doc) -> Doc:
        """
        Getting the Doc of a source

        Description:
            The source itself, which must be a Doc; a library that parses
            strings overrides the method

        Arguments:
            source (Doc): Data source

        Returns:
            Doc: Doc with a dependency parse

        Raises:
            SourceTypeError: If the source is not a Doc object
        """
        if not is_doc(source):
            raise SourceTypeError(self.messages["source_type"])
        return source

    def is_clause_head(self, token: Token) -> bool:
        """
        Checking whether a word heads a clause

        Description:
            The head of the sentence, or a word with a relation of CLAUSE_DEPS
            (ccomp, advcl, acl, csubj, parataxis and their subtypes) whose
            predicate (predicate_form) is not a participle, a converb or a
            gerund (counted apart), nor an infinitive under acl (the wish to
            leave). A parataxis and a conjunct of a clause head count only as
            predicates (is_predicate), so a parenthetical word is no clause

        Arguments:
            token (Token): Token

        Returns:
            bool: Result of the check
        """
        seen = set()
        # Up the chain of conjuncts to the word that is none
        while is_word(token) and token.i not in seen:
            if is_root(token):
                return True
            form = predicate_form(token)
            if form in NONFINITE_CLAUSE_FORMS:
                return False
            dep = base_dep(token)
            if dep != "conj":
                if dep not in CLAUSE_DEPS:
                    return False
                if dep == "parataxis":
                    return is_predicate(token, self.join_hyphens)
                return not (dep == "acl" and form == "Inf")
            if not is_predicate(token, self.join_hyphens):
                return False
            seen.add(token.i)
            token = token.head
        return False

    def is_subordinate_clause_head(self, token: Token) -> bool:
        """
        Checking whether a word heads a subordinate clause

        Description:
            The head of a clause (is_clause_head) with a relation of
            SUBORDINATE_CLAUSE_DEPS (ccomp, advcl, acl, csubj and their
            subtypes), or a conjunct of one: the relation of the first word up
            its chain of conjuncts decides

        Arguments:
            token (Token): Token

        Returns:
            bool: Result of the check
        """
        if is_root(token) or not self.is_clause_head(token):
            return False
        seen = set()
        while base_dep(token) == "conj" and token.i not in seen:
            seen.add(token.i)
            token = token.head
        return not is_root(token) and base_dep(token) in SUBORDINATE_CLAUSE_DEPS

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
            A verb with Voice=Pass or with a dependent of PASSIVE_DEPS: nsubj:pass,
            csubj:pass, aux:pass of Universal Dependencies and nsubjpass,
            csubjpass, auxpass of ClearNLP

        Arguments:
            token (Token): Token

        Returns:
            bool: Result of the check
        """
        if token.pos_ != "VERB":
            return False
        return has_feature(token, "Voice", "Pass") or any(
            child.dep_ in PASSIVE_DEPS for child in get_children(token, self.join_hyphens)
        )

    def is_agentless(self, token: Token) -> bool:
        """
        Checking whether a word is a passive form with no agent

        Description:
            A passive form (is_passive) with no dependent of AGENT_DEPS:
            obl:agent of Universal Dependencies and agent of ClearNLP

        Arguments:
            token (Token): Token

        Returns:
            bool: Result of the check
        """
        return self.is_passive(token) and not any(
            child.dep_ in AGENT_DEPS for child in get_children(token, self.join_hyphens)
        )

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
    return token.dep_.split(":")[0]


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
        SourceTypeError: If auxiliary_form is not callable

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
    if auxiliary_form is not None and not callable(auxiliary_form):
        raise SourceTypeError(
            f"auxiliary_form must be callable, not {type(auxiliary_form).__name__}"
        )
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


def is_predicate(token: Token, join_hyphens: bool = False) -> bool:
    """
    Checking whether a word can be the predicate of its clause

    Description:
        A verb (VERB, AUX) or a word with a subject of its own (nsubj, csubj and
        their subtypes): the nominal predicate of he is tall passes, a
        parenthetical word does not

    Arguments:
        token (Token): Token
        join_hyphens (bool): Join the parts of hyphenated words (get_children)

    Returns:
        bool: Result of the check
    """
    return token.pos_ in ("VERB", "AUX") or any(
        base_dep(child) in SUBJECT_DEPS for child in get_children(token, join_hyphens)
    )


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
    """Number of the modifiers in the longest branch of a chain from a token"""
    return 1 + max(
        (
            _chain_len(child, is_modifier, join_hyphens)
            for child in get_children(token, join_hyphens)
            if is_modifier(child)
        ),
        default=0,
    )
