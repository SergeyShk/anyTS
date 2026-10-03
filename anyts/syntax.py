from collections import Counter
from collections.abc import Iterable, Sequence

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


def joins_previous(token: Token) -> bool:
    """
    Checking whether a token continues a word the tokenizer split at its hyphens

    Description:
        The token is a word that follows a hyphen with no whitespace around it,
        and the hyphen follows a word, with no sentence starting at the hyphen
        or at the token: known in well-known, as iter_doc_units joins them

    Arguments:
        token (Token): Token

    Returns:
        bool: Result of the check
    """
    doc = token.doc
    i = token.i
    return (
        i >= 2
        and doc[i - 1].text == "-"
        and not doc[i - 2].whitespace_
        and not doc[i - 1].whitespace_
        and is_word(doc[i - 2])
        and is_word(token)
        and not doc[i - 1].is_sent_start
        and not token.is_sent_start
    )


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


def _hyphenated_word(token: Token) -> list[Token] | None:
    """Tokens of the hyphenated word a token or an inner hyphen belongs to, None for no word"""
    doc = token.doc
    i = token.i
    if not is_word(token):
        if token.text != "-" or i + 1 >= len(doc) or not joins_previous(doc[i + 1]):
            return None
        i += 1
    elif (i == 0 or doc[i - 1].text != "-") and (i + 1 >= len(doc) or doc[i + 1].text != "-"):
        # A word without a hyphen next to it is a word of its own, the common case
        return [token]
    start = i
    while joins_previous(doc[start]):
        start -= 2
    end = i
    while end + 2 < len(doc) and joins_previous(doc[end + 2]):
        end += 2
    return list(doc[start : end + 1])


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


def get_words(tokens: Iterable[Token], join_hyphens: bool = False) -> list[Token]:
    """
    Getting the words of a sequence of tokens

    Description:
        With join_hyphens, a word the tokenizer split at its hyphens is one
        word, given by its part that holds its relation: the head of the
        sentence or the part hanging outside the word, the nearest to the root,
        as in get_children; by its first part when a hyphen holds the relation
        or the parts form a loop

    Arguments:
        tokens (Doc|Span|list[Token]): Sequence of tokens
        join_hyphens (bool): Join the parts of hyphenated words (joins_previous)

    Returns:
        list[Token]: List of words
    """
    return [_word_part(unit) for unit in _word_units(tokens, join_hyphens)]


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
        With join_hyphens, a hyphenated word is one word with its hyphens: its
        dependents are the words whose head (the part hanging outside the word,
        the nearest to the root) hangs on one of its tokens, each given by that
        part, or by its first part when it hangs by a hyphen

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
        The token itself and all of its direct and indirect dependents; with
        join_hyphens, the hyphenated word the token belongs to and the words that
        hang on it (get_children), directly or through punctuation

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
        The distance of a dependency is the distance between a word and its head
        in positions of words, punctuation left out (Liu 2008); the head of a
        sentence has no dependency and is skipped, as is a word whose head lies
        outside the given sequence. With join_hyphens, a hyphenated word is one
        position with its hyphens; a word holding the head of the sentence has
        no dependency, and the head of another one is that of its part hanging
        outside it, the nearest to the root

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
        for a sequence of several sentences the maximum is taken, for a sentence
        of one word the depth is 0. With join_hyphens, a hyphenated word is one
        word with its hyphens, hanging by its part outside it, the nearest to
        the root, as in calc_dependency_distances

    Arguments:
        tokens (Doc|Span|list[Token]): Sequence of tokens
        join_hyphens (bool): Join the parts of hyphenated words (joins_previous)

    Returns:
        int: Depth of the tree
    """
    if join_hyphens:
        parents = _unit_parents(_word_units(tokens, True))
        depths: dict[int, int] = {}
        for start in range(len(parents)):
            chain: list[int] = []
            node: int | None = start
            # A broken parse can link the parts of two words in a loop
            while node is not None and node not in depths and node not in chain:
                chain.append(node)
                node = parents[node]
            depth = depths[node] if node is not None and node in depths else -1
            for member in reversed(chain):
                depth += 1
                depths[member] = depth
        return max(depths.values(), default=0)
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


def calc_valency(token: Token, join_hyphens: bool = False) -> int:
    """
    Computing the valency of a token

    Description:
        The number of dependent words, the relations cc, conj and parataxis
        left out

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
        A chain is a group of words linked by the relation conj, whichever word
        each conjunct hangs on: Universal Dependencies attaches every conjunct
        to the first one, ClearNLP to the previous one; a nested coordination
        (A and B, or C) and an enumeration the parser splits between several
        heads give one chain. The length of a chain is the number of its words.
        With join_hyphens, a hyphenated word is one word, linked by the conj
        relations of all of its parts with other words

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
