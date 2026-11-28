"""Documents of anySeg with hand-made annotations for the tests"""

from collections.abc import Sequence

from anyseg import Document

from anyts.constants import MESSAGES
from anyts.document import _sent_starts
from anyts.utils import _separators

# Whitespace, control characters and the invisible marks, which anySeg keeps out of tokens
SEPARATORS = _separators()


def parsed(
    words: Sequence[str],
    heads: Sequence[int] | None = None,
    deps: Sequence[str] | None = None,
    *,
    spaces: Sequence[bool] | None = None,
    pos: Sequence[str] | None = None,
    tags: Sequence[str] | None = None,
    morphs: Sequence[str] | None = None,
    lemmas: Sequence[str] | None = None,
    sent_starts: Sequence[bool | None] | None = None,
) -> Document:
    """
    A document of tokens with their annotations

    Description:
        The text is the tokens, each followed by a space unless spaces says
        otherwise. Whitespace and invisible marks at the edges of a token are
        left out, and a token of nothing else is dropped. Heads are the indices
        of the head tokens, and a token that heads itself is the root of its
        sentence; a token with an empty relation has no head. The sentences are
        those of the parse (one starts at the first token of the subtree of every
        root), else of sent_starts given for every token after the first, else
        those SentsExtractor finds in the text. An empty annotation is None, and
        the features are sorted by name, as Universal Dependencies orders them
    """
    count = len(words)
    spaces = [True] * count if spaces is None else spaces
    text = "".join(word + " " * bool(space) for word, space in zip(words, spaces, strict=True))
    starts: list[int] = []
    ends: list[int] = []
    kept: list[int] = []
    positions = [-1] * count
    offset = 0
    for index, word in enumerate(words):
        start, end = offset, offset + len(word)
        offset = end + bool(spaces[index])
        rest = word.lstrip(SEPARATORS)
        if not rest:
            continue
        start = end - len(rest)
        end = start + len(rest.rstrip(SEPARATORS))
        positions[index] = len(kept)
        starts.append(start)
        ends.append(end)
        kept.append(index)
    marks = _marks(count, heads, deps, sent_starts)
    sentence_starts = None
    if marks is not None:
        sentence_starts = []
        pending = True
        for index in range(count):
            pending = pending or marks[index]
            if positions[index] >= 0 and pending:
                sentence_starts.append(positions[index])
                pending = False
    document = Document.from_tokens(text, starts, ends, sentence_starts=sentence_starts)
    if marks is None:
        document = document.with_sentences(
            _sent_starts(document.text, document.tokens.starts, None, MESSAGES)
        )
    columns: dict[str, list[str | int | None]] = {}
    for name, values in (("lemma", lemmas), ("upos", pos), ("xpos", tags)):
        if values is not None and any(values):
            columns[name] = [values[index] or None for index in kept]
    if morphs is not None and any(value not in ("", "_") for value in morphs):
        columns["feats"] = [_features(morphs[index]) for index in kept]
    if heads is not None and deps is not None and any(deps):
        columns["head"], columns["deprel"] = _relations(document, kept, positions, heads, deps)
    if columns:
        document.set_columns(**columns)
    return document


def _marks(
    count: int,
    heads: Sequence[int] | None,
    deps: Sequence[str] | None,
    sent_starts: Sequence[bool | None] | None,
) -> list[bool] | None:
    """Whether each token starts a sentence, None without the sentences of a parse or complete
    sent_starts"""
    if heads is not None and deps is not None and any(deps):
        marks = [not index for index in range(count)]
        for index in range(count):
            if heads[index] == index and deps[index]:
                marks[_left_edge(index, heads, deps)] = True
        return marks
    if sent_starts is not None and all(start is not None for start in sent_starts[1:]):
        return [bool(start) or not index for index, start in enumerate(sent_starts)]
    return None


def _left_edge(root: int, heads: Sequence[int], deps: Sequence[str]) -> int:
    """The first token of the subtree of a root"""
    edge = root
    for index in range(len(heads)):
        head = index
        for _ in range(len(heads)):
            if head == root or not deps[head] or heads[head] == head:
                break
            head = heads[head]
        if head == root:
            edge = min(edge, index)
    return edge


def _features(morph: str) -> str | None:
    """Features sorted by name regardless of case, None for none"""
    if morph in ("", "_"):
        return None
    return "|".join(sorted(morph.split("|"), key=lambda feature: feature.split("=")[0].lower()))


def _relations(
    document: Document,
    kept: list[int],
    positions: list[int],
    heads: Sequence[int],
    deps: Sequence[str],
) -> tuple[list[str | int | None], list[str | int | None]]:
    """Columns head and deprel: the heads counted from 1 in their sentences, 0 at a root; a word
    whose head is in another sentence is a root, and a second root of a sentence depends on the
    first with the relation dep"""
    first = [0] * len(kept)
    for sentence in document.sentences:
        tokens = sentence.tokens
        for index in range(tokens[0].index, tokens[0].index + len(tokens)):
            first[index] = tokens[0].index
    columns_heads: list[str | int | None] = []
    columns_deprels: list[str | int | None] = []
    roots: dict[int, int] = {}
    loose: list[int] = []
    for position, index in enumerate(kept):
        if not deps[index]:
            columns_heads.append(None)
            columns_deprels.append(None)
            continue
        head = heads[index]
        for _ in range(len(heads)):
            if positions[head] >= 0 or heads[head] == head or not deps[head]:
                break
            head = heads[head]
        target = positions[head]
        if head == index or target < 0 or first[target] != first[position]:
            if head == index:
                roots.setdefault(first[position], position)
            loose.append(position)
            columns_heads.append(0)
            columns_deprels.append("root")
        else:
            columns_heads.append(target - first[position] + 1)
            columns_deprels.append(deps[index])
    for position in loose:
        root = roots.setdefault(first[position], position)
        if root != position:
            columns_heads[position] = root - first[position] + 1
            columns_deprels[position] = "dep"
    return columns_heads, columns_deprels
