from collections.abc import Iterable, Mapping
from numbers import Integral

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from spacy.tokens import Doc

from ..constants import VISUALIZER_LABELS
from ..exceptions import ParameterError, SourceError, SourceTypeError
from ..extractors import SentsExtractor, WordsExtractor
from ..utils import check_integer, iter_doc_words, merge_labels


def sentence_lengths_plot(
    source: str | Doc | Iterable[int],
    window: int = 10,
    inset: bool = True,
    ax: Axes | None = None,
    labels: Mapping[str, str] | None = None,
    sents_extractor: SentsExtractor | None = None,
    words_extractor: WordsExtractor | None = None,
    join_hyphens: bool = False,
) -> Axes:
    """
    Plotting the curve of the lengths of the sentences

    Description:
        The length of every sentence in words in the order of the text, the
        moving average over a window of sentences and an inset with the
        histogram of the lengths; the lengths come from sentence_lengths

    Arguments:
        source (str|Doc|Iterable[int]): Text, Doc object or lengths of the
            sentences (a list, a numpy array, a Series)
        window (int): Window of the moving average in sentences
        inset (bool): Show the inset with the histogram
        ax (Axes): Axes for the plot; if not given, a new figure is created
        labels (dict[str, str]): Labels over VISUALIZER_LABELS["sentence_lengths_plot"]
        sents_extractor (SentsExtractor): Extractor of the sentences of a string
        words_extractor (WordsExtractor): Extractor of the words of a sentence of a string
        join_hyphens (bool): Join the parts of hyphenated words of a Doc (iter_doc_words)

    Returns:
        Axes: Axes with the plot

    Raises:
        SourceTypeError: If the data source or an extractor is set incorrectly
        ParameterError: If the window is not an integer or is below one, or the
            labels are set incorrectly (merge_labels)
        SourceError: If there are no sentences
    """
    captions = merge_labels(VISUALIZER_LABELS["sentence_lengths_plot"], labels)
    check_integer(window, "window")
    if window < 1:
        raise ParameterError("The window must be at least one")
    lengths = sentence_lengths(source, sents_extractor, words_extractor, join_hyphens)
    if not lengths:
        raise SourceError("The data source has no sentences")
    if ax is None:
        _, ax = plt.subplots(figsize=(9, 4))
    numbers = np.arange(1, len(lengths) + 1)
    ax.plot(numbers, lengths, marker=".", linewidth=1, color="tab:blue", label=captions["length"])
    if len(lengths) >= window:
        average = np.convolve(lengths, np.ones(window) / window, mode="valid")
        ax.plot(
            numbers[window - 1 :] - (window - 1) / 2,
            average,
            linewidth=2,
            color="tab:red",
            label=captions["average"].format(window=window),
        )
    ax.set_xlabel(captions["xlabel"])
    ax.set_ylabel(captions["ylabel"])
    ax.set_title(captions["title"])
    ax.legend(loc="upper left")
    if inset:
        ax.set_ylim(top=max(lengths) * 1.7)
        histogram = ax.inset_axes((0.7, 0.62, 0.28, 0.33))
        histogram.hist(lengths, bins="auto", color="tab:gray")
        histogram.set_title(captions["distribution"], fontsize=8)
        histogram.tick_params(labelsize=7)
    return ax


def sentence_lengths(
    source: str | Doc | Iterable[int],
    sents_extractor: SentsExtractor | None = None,
    words_extractor: WordsExtractor | None = None,
    join_hyphens: bool = False,
) -> list[int]:
    """
    Extracting the lengths of the sentences in words

    Description:
        A string is split into sentences by sents_extractor and every
        sentence into words by words_extractor; a Doc by its sentence
        boundaries (iter_doc_words), or as its text without them; ready
        lengths (any iterable of integers) are used as they are. Sentences
        without words are skipped

    Arguments:
        source (str|Doc|Iterable[int]): Text, Doc object or ready lengths
        sents_extractor (SentsExtractor): Extractor of the sentences of a string;
            SentsExtractor() by default
        words_extractor (WordsExtractor): Extractor of the words of a sentence of a
            string; WordsExtractor() by default
        join_hyphens (bool): Join the parts of hyphenated words of a Doc (iter_doc_words)

    Returns:
        list[int]: Lengths of the sentences in order

    Raises:
        SourceTypeError: If the data source or an extractor is set incorrectly

    Example:
        >>> from anyts.visualizers import sentence_lengths
        >>> sentence_lengths("The cat sleeps. Does the dog? It eats, she said.")
        [3, 3, 4]
    """
    if sents_extractor is not None and not isinstance(sents_extractor, SentsExtractor):
        raise SourceTypeError("The sentence extractor must be a SentsExtractor")
    if words_extractor is not None and not isinstance(words_extractor, WordsExtractor):
        raise SourceTypeError("The word extractor must be a WordsExtractor")
    if isinstance(source, str):
        sents = (sents_extractor or SentsExtractor()).extract(source)
        words = words_extractor or WordsExtractor()
        lengths = [len(words.extract(sent)) for sent in sents]
        return [length for length in lengths if length]
    if isinstance(source, Doc):
        if source.has_annotation("SENT_START"):
            lengths = [sum(1 for _ in iter_doc_words(sent, join_hyphens)) for sent in source.sents]
            return [length for length in lengths if length]
        return sentence_lengths(source.text, sents_extractor, words_extractor)
    if isinstance(source, Iterable):
        lengths = list(source)
        if all(isinstance(length, Integral) for length in lengths):
            return [int(length) for length in lengths]
    raise SourceTypeError("The data source is set incorrectly")
