from collections import Counter
from collections.abc import Iterable

from spacy.tokens import Token

from .constants import VALENCY_IGNORED_DEPS
from .utils import is_punctuation


def is_word(token: Token) -> bool:
    """
    Checking whether a token is a word - not a punctuation mark and not whitespace

    Description:
        The tokens of is_punctuation (symbols like %, €, + and invisible
        characters) are no words either

    Arguments:
        token (Token): Token

    Returns:
        bool: Result of the check
    """
    return not token.is_space and not is_punctuation(token.text)


def get_words(tokens: Iterable[Token]) -> list[Token]:
    """
    Getting the words of a sequence of tokens

    Arguments:
        tokens (Doc|Span|list[Token]): Sequence of tokens

    Returns:
        list[Token]: List of words
    """
    return [token for token in tokens if is_word(token)]


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


def get_children(token: Token) -> list[Token]:
    """
    Getting the dependent words of a token

    Arguments:
        token (Token): Token

    Returns:
        list[Token]: List of the dependents without punctuation and whitespace
    """
    return [child for child in token.children if is_word(child)]


def count_children(token: Token) -> int:
    """
    Counting the dependent words of a token

    Arguments:
        token (Token): Token

    Returns:
        int: Number of dependent words
    """
    return len(get_children(token))


def subtree_len(token: Token) -> int:
    """
    Computing the length of the subtree of a token in words

    Description:
        The token itself and all of its direct and indirect dependents

    Arguments:
        token (Token): Token

    Returns:
        int: Number of words in the subtree
    """
    return sum(1 for descendant in token.subtree if is_word(descendant))


def calc_dependency_distances(tokens: Iterable[Token]) -> list[int]:
    """
    Computing the dependency distances

    Description:
        The distance of a dependency is the distance between a word and its head
        in positions of words, punctuation left out (Liu 2008); the head of a
        sentence has no dependency and is skipped, as is a word whose head lies
        outside the given sequence

    References:
        Liu H. Dependency distance as a metric for language comprehension difficulty.
        Journal of Cognitive Science, 2008, 9(2), 159-191

    Arguments:
        tokens (Doc|Span|list[Token]): Sequence of tokens

    Returns:
        list[int]: Distances in the order of the words
    """
    words = get_words(tokens)
    positions = {token.i: position for position, token in enumerate(words)}
    return [
        abs(positions[token.i] - positions[token.head.i])
        for token in words
        if not is_root(token) and token.head.i in positions
    ]


def calc_tree_depth(tokens: Iterable[Token]) -> int:
    """
    Computing the depth of the dependency tree

    Description:
        The longest path from the head of the sentence to a leaf in relations;
        for a sequence of several sentences the maximum is taken, for a sentence
        of one word the depth is 0

    Arguments:
        tokens (Doc|Span|list[Token]): Sequence of tokens

    Returns:
        int: Depth of the tree
    """
    words = get_words(tokens)
    ids = {token.i for token in words}
    return max(
        (sum(1 for ancestor in token.ancestors if ancestor.i in ids) for token in words),
        default=0,
    )


def has_feature(token: Token, field: str, value: str) -> bool:
    """
    Checking whether a token carries a morphological feature with a given value

    Arguments:
        token (Token): Token
        field (str): Name of the feature of Universal Dependencies (VerbForm, Mood)
        value (str): Value of the feature (Part, Ger, Fin)

    Returns:
        bool: Result of the check
    """
    return value in token.morph.get(field, [])


def calc_valency(token: Token) -> int:
    """
    Computing the valency of a token

    Description:
        The number of dependent words, the relations cc, conj and parataxis
        left out

    Arguments:
        token (Token): Token

    Returns:
        int: Number of dependent words
    """
    return sum(1 for child in get_children(token) if child.dep_ not in VALENCY_IGNORED_DEPS)


def calc_coordination_chains(tokens: Iterable[Token]) -> list[int]:
    """
    Computing the lengths of the coordination chains

    Description:
        A chain is a group of words linked by the relation conj, whichever word
        each conjunct hangs on: Universal Dependencies attaches every conjunct
        to the first one, ClearNLP to the previous one; a nested coordination
        (A and B, or C) and an enumeration the parser splits between several
        heads give one chain. The length of a chain is the number of its words

    Arguments:
        tokens (Doc|Span|list[Token]): Sequence of tokens

    Returns:
        list[int]: Lengths of the chains in the order of their first words
    """
    words = get_words(tokens)
    parent = {token.i: token.i for token in words}

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for token in words:
        if token.dep_ == "conj" and token.head.i in parent:
            parent[find(token.i)] = find(token.head.i)
    sizes = Counter(find(token.i) for token in words)
    chains: dict[int, int] = {}
    for token in words:
        root = find(token.i)
        if sizes[root] > 1:
            chains.setdefault(root, sizes[root])
    return list(chains.values())
