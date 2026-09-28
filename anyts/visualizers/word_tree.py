from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import Enum
from itertools import count
from typing import Any

from graphviz import Digraph, escape

from ..exceptions import ParameterError, SourceError, SourceTypeError
from ..utils import check_integer, check_sequence, check_words


class _Direction(Enum):
    """Direction of a subtree of words from the keyword"""

    Forward = 1
    Backward = 2


@dataclass
class _FreqNode:
    """Node of a word tree: the frequency of its N-gram and the following words"""

    freq: int
    children: dict[str, "_FreqNode"]


class _TreeDrawer:
    """
    Class for drawing a word tree

    Arguments:
        keyword (str): Keyword whose context is shown
        fwd_tree (_FreqNode): Subtree after the keyword
        bwd_tree (_FreqNode): Subtree before the keyword
        max_font_size (int): Largest size of the font
        min_font_size (int): Smallest size of the font
        font_interp (Callable): Function of the relative frequency of a node, from 0 to
            1, giving the share of the range of the font sizes, from 0 to 1

    Attributes:
        max_freq (int): Greatest frequency
        graph (Digraph): Directed graph

    Methods:
        interpolate_fontsize: Computing the size of the font of a node of the tree
        add_node: Adding a node with a generated identifier and the word as its label
        draw_subtree: Drawing a subtree of words
        draw: Drawing the word tree as a directed graph
    """

    def __init__(
        self,
        keyword: str,
        fwd_tree: _FreqNode,
        bwd_tree: _FreqNode,
        max_font_size: int = 30,
        min_font_size: int = 12,
        font_interp: Callable[[float], float] | None = None,
    ) -> None:
        self.keyword = keyword
        self.fwd_tree = fwd_tree
        self.bwd_tree = bwd_tree
        self.max_font_size = max_font_size
        self.min_font_size = min_font_size
        self.font_interp = font_interp
        self.max_freq = max(
            [t.freq for t in fwd_tree.children.values()]
            + [t.freq for t in bwd_tree.children.values()]
        )
        self.graph = Digraph(escape(keyword), format="png")
        self.graph.attr("graph", rankdir="LR")
        self.graph.attr("node", shape="plaintext", margin="0")
        self._ids = count()

    def interpolate_fontsize(self, freq: int) -> int:
        """
        Computing the size of the font of a node of the tree

        Arguments:
            freq (int): Frequency of the N-gram

        Returns:
            int: Size of the font
        """
        lower = self.min_font_size
        upper = self.max_font_size
        t = freq / self.max_freq

        def quad(t: float) -> float:
            return float(t ** (1.0 / 3))

        font_interp = quad if self.font_interp is None else self.font_interp
        return int(font_interp(t) * (upper - lower) + lower)

    def add_node(self, word: str, fontsize: int) -> str:
        """
        Adding a node with a generated identifier and the word as its label

        Description:
            The identifier is n0, n1, ...: graphviz would read a colon in a word
            as a port (10:30)

        Arguments:
            word (str): Word of the node
            fontsize (int): Size of the font

        Returns:
            str: Identifier of the node
        """
        node = f"n{next(self._ids)}"
        self.graph.node(node, label=escape(word), fontsize=str(fontsize))
        return node

    def draw_subtree(self, tree: _FreqNode, direction: _Direction, parent: str) -> None:
        """
        Drawing a subtree of words

        Arguments:
            tree (_FreqNode): Subtree of words
            direction (_Direction): Direction of the subtree
            parent (str): Identifier of the node the subtree grows from
        """
        for word, subtree in tree.children.items():
            node = self.add_node(word, self.interpolate_fontsize(subtree.freq))
            if direction == _Direction.Forward:
                self.graph.edge(parent, node)
            else:
                self.graph.edge(node, parent)
            self.draw_subtree(subtree, direction, node)

    def draw(self) -> Digraph:
        """
        Drawing the word tree as a directed graph

        Returns:
            Digraph: Word tree
        """
        root = self.add_node(self.keyword, self.max_font_size)
        self.draw_subtree(self.bwd_tree, _Direction.Backward, root)
        self.draw_subtree(self.fwd_tree, _Direction.Forward, root)
        return self.graph


class _WordTree:
    """
    Class for building a word tree

    Arguments:
        texts (list[list[str]]): List of lists of words
        keyword (str): Keyword whose context is shown
        max_n (int): Largest size of the context
        max_per_n (int): Largest number of examples for every size of the context

    Attributes:
        ngrams (list[str]): List of N-grams
        frequencies (list[int]): List of the frequencies of the N-grams

    Methods:
        search: Finding the N-grams that start or end with the keyword and their frequencies
        select: Selecting the N-grams of one side of the keyword
        build_tree: Building a subtree of words
        build_trees: Building the subtrees of words before and after the keyword
        draw: Drawing the word tree as a directed graph

    Raises:
        SourceTypeError: If the texts are not a list of lists of words or the
            keyword is not a string
        SourceError: If there are no texts
        ParameterError: If the size of the context is below 2 or the number of
            examples below one
    """

    def __init__(
        self,
        texts: list[list[str]],
        keyword: str,
        max_n: int = 5,
        max_per_n: int = 8,
    ):
        check_sequence(texts, "lists of words")
        if not all(isinstance(text, (list, tuple)) for text in texts):
            raise SourceTypeError("The texts must be a list of lists of words")
        for text in texts:
            check_words(text)
        if not texts:
            raise SourceError("The data source has no words")
        if not isinstance(keyword, str):
            raise SourceTypeError(f"The keyword must be a string, not {type(keyword).__name__}")
        check_integer(max_n, "size of the context")
        check_integer(max_per_n, "number of examples")
        if max_n < 2:
            raise ParameterError("The size of the context must be at least 2")
        if max_per_n < 1:
            raise ParameterError(
                "The number of examples for every size of the context must be greater than 0"
            )
        self.texts = texts
        self.keyword = keyword
        self.max_n = max_n
        self.max_per_n = max_per_n
        self.ngrams: list[tuple[str, ...]] = []
        self.frequencies: list[int] = []

    def search(self) -> None:
        """Finding the N-grams that start or end with the keyword and their frequencies"""
        frequencies_dict: defaultdict[tuple[str, ...], int] = defaultdict(int)
        for sent in self.texts:
            for n in range(2, self.max_n + 1):
                for i in range(0, len(sent) - n + 1):
                    ngram = sent[i : i + n]
                    if ngram[0] == self.keyword or ngram[-1] == self.keyword:
                        frequencies_dict[tuple(ngram)] += 1
        for found_ngram, freq in frequencies_dict.items():
            self.ngrams.append(found_ngram)
            self.frequencies.append(freq)

    @staticmethod
    def build_tree(ngrams: Sequence[Sequence[str]], frequencies: Sequence[int]) -> _FreqNode:
        """
        Building a subtree of words

        Arguments:
            ngrams (Sequence[Sequence[str]]): List of N-grams
            frequencies (Sequence[int]): List of the frequencies of the N-grams

        Returns:
            _FreqNode: Subtree of words
        """
        tree = _FreqNode(freq=0, children={})
        for ngram, freq in zip(ngrams, frequencies, strict=False):
            subtree = tree
            for gram in ngram:
                if gram not in subtree.children:
                    subtree.children[gram] = _FreqNode(children={}, freq=freq)
                subtree = subtree.children[gram]
            subtree.freq = freq
        return tree

    def select(self, forward: bool) -> tuple[list[tuple[str, ...]], list[int]]:
        """
        Selecting the N-grams of one side of the keyword

        Description:
            An N-gram is a candidate only when its (N-1)-gram on the same side
            was kept; of the candidates of every size the max_per_n most
            frequent are kept, alphabetically when equal

        Arguments:
            forward (bool): The side after the keyword; False - the side before it

        Returns:
            tuple[list[tuple[str, ...]], list[int]]: Kept N-grams and their frequencies
        """
        found = {
            ngram: freq
            for ngram, freq in zip(self.ngrams, self.frequencies, strict=True)
            if (ngram[0] if forward else ngram[-1]) == self.keyword
        }
        kept: dict[tuple[str, ...], int] = {}
        for n in range(2, self.max_n + 1):
            candidates = [
                ngram
                for ngram in found
                if len(ngram) == n and (n == 2 or (ngram[:-1] if forward else ngram[1:]) in kept)
            ]
            candidates.sort(key=lambda ngram: (-found[ngram], ngram))
            kept.update((ngram, found[ngram]) for ngram in candidates[: self.max_per_n])
        return list(kept), list(kept.values())

    def build_trees(self) -> tuple[_FreqNode, _FreqNode]:
        """
        Building the subtrees of words before and after the keyword

        Returns:
            tuple[_FreqNode, _FreqNode]: Subtrees of words after and before the keyword
        """
        forward_ngrams, forward_frequencies = self.select(forward=True)
        backward_ngrams, backward_frequencies = self.select(forward=False)
        forward_tree = self.build_tree(
            [ngram[1:] for ngram in forward_ngrams], forward_frequencies
        )
        backward_tree = self.build_tree(
            [ngram[-2::-1] for ngram in backward_ngrams], backward_frequencies
        )
        return forward_tree, backward_tree

    def draw(self, **kwargs: Any) -> Digraph:
        """
        Drawing the word tree as a directed graph

        Arguments:
            kwargs: Drawing parameters - max_font_size, min_font_size, font_interp

        Returns:
            Digraph: Word tree
        """
        forward_tree, backward_tree = self.build_trees()
        return _TreeDrawer(self.keyword, forward_tree, backward_tree, **kwargs).draw()


def wordtree(
    texts: list[list[str]], keyword: str, max_n: int = 5, max_per_n: int = 8, **kwargs: Any
) -> Digraph:
    """
    Building a word tree that shows the contexts of a keyword in texts

    Description:
        The N-grams of up to max_n words that start or end with the keyword
        are counted in every text (a sentence, for instance); on each side the
        max_per_n most frequent of every size are kept and joined into a tree,
        with the size of the font by frequency. Rendering
        needs the executables of Graphviz

    References:
        https://www.cg.tuwien.ac.at/courses/InfoVis/HallOfFame/2011/Gruppe05/Homepage/Paper/wordtree-paper-wattenberg.pdf

    Arguments:
        texts (list[list[str]]): List of lists of words
        keyword (str): Keyword whose context is shown
        max_n (int): Largest size of the context
        max_per_n (int): Largest number of examples for every size of the context
        kwargs: Drawing parameters - max_font_size, min_font_size, font_interp

    Returns:
        Digraph: Word tree

    Raises:
        SourceTypeError: If the texts are not a list of lists of words or the
            keyword is not a string
        SourceError: If there are no texts or the keyword has a word next to it
            in none of them
        ParameterError: If the size of the context is below 2 or the number of
            examples below one

    Example:
        >>> from anyts.visualizers import wordtree
        >>> tree = wordtree([["the", "cat", "sleeps"], ["the", "cat", "eats"]], "cat", max_n=2)
        >>> tree.name, len(tree.body)
        ('cat', 9)
    """
    wt = _WordTree(
        texts,
        keyword,
        max_n=max_n,
        max_per_n=max_per_n,
    )
    wt.search()
    if not wt.ngrams:
        raise SourceError("The keyword is not found or has no word next to it")
    return wt.draw(**kwargs)
